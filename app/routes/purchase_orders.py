from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.database import BASE_DIR, get_db
from app.purchase_pdf import build_purchase_order_pdf
from app.utils import parse_optional_tax_amount

router = APIRouter(prefix="/purchase-orders", tags=["purchase-orders"])

UPLOAD_ROOT = Path(BASE_DIR)


def _receipt_progress(po: models.PurchaseOrder) -> str:
    if not po.lines:
        return "none"
    rq = [Decimal(str(l.received_qty or 0)) for l in po.lines]
    tq = [Decimal(str(l.qty)) for l in po.lines]
    if all(r >= q for r, q in zip(rq, tq)):
        return "complete"
    if any(r > 0 for r in rq):
        return "partial"
    return "none"


def _supplier_payment_term_map(db: Session, company_names: set[str]) -> dict[str, int | None]:
    if not company_names:
        return {}
    rows = db.scalars(select(models.Supplier).where(models.Supplier.company_name.in_(company_names))).all()
    return {s.company_name: s.payment_term_days for s in rows}


def _payment_due_fields(order_date, term_days: int | None) -> tuple[date | None, int | None]:
    if term_days is None:
        return None, None
    od = order_date.date() if hasattr(order_date, "date") else order_date
    due = od + timedelta(days=int(term_days))
    today = date.today()
    remaining = (due - today).days
    return due, remaining


def _po_to_read(
    po: models.PurchaseOrder,
    db: Session | None = None,
    term_days_by_company: dict[str, int | None] | None = None,
) -> schemas.PurchaseOrderRead:
    lines = []
    for ln in sorted(po.lines, key=lambda x: x.line_no):
        q_ord = Decimal(str(ln.qty))
        q_rec = Decimal(str(ln.received_qty or 0))
        q_open = (q_ord - q_rec) if q_ord >= q_rec else Decimal("0")
        lines.append(
            schemas.PurchaseOrderLineRead(
                id=ln.id,
                purchase_order_id=ln.purchase_order_id,
                line_no=ln.line_no,
                material_id=ln.material_id,
                material_code=ln.material_code,
                material_name=ln.material_name,
                spec_drawing=ln.spec_drawing,
                unit=ln.unit,
                qty=ln.qty,
                received_qty=ln.received_qty or Decimal("0"),
                qty_open=q_open,
                unit_price=ln.unit_price,
                line_amount=ln.line_amount,
                tax_rate_note=ln.tax_rate_note,
                remark=ln.remark,
            )
        )
    invs = sorted(getattr(po, "invoices", None) or [], key=lambda x: x.id)
    invoices = [
        schemas.PurchaseInvoiceRead(
            id=i.id,
            purchase_order_id=i.purchase_order_id,
            invoice_no=i.invoice_no,
            amount_with_tax=i.amount_with_tax,
            original_filename=i.original_filename,
            remark=i.remark,
            created_at=i.created_at,
        )
        for i in invs
    ]
    pay = getattr(po, "payment_status", None) or "unpaid"
    term_days: int | None = None
    if term_days_by_company is not None:
        term_days = term_days_by_company.get(po.supplier_company)
    elif db is not None:
        term_days = db.scalar(
            select(models.Supplier.payment_term_days).where(
                models.Supplier.company_name == po.supplier_company
            )
        )
    due_date, due_remaining = _payment_due_fields(po.order_date, term_days)
    return schemas.PurchaseOrderRead(
        id=po.id,
        order_no=po.order_no,
        status=po.status,
        payment_status=pay,
        receipt_progress=_receipt_progress(po),
        order_date=po.order_date,
        supplier_company=po.supplier_company,
        supplier_tax_no=po.supplier_tax_no,
        supplier_bank=po.supplier_bank,
        supplier_account=po.supplier_account,
        supplier_address=po.supplier_address,
        supplier_phone=po.supplier_phone,
        supplier_contact=po.supplier_contact,
        delivery_address=po.delivery_address,
        payment_terms=po.payment_terms,
        delivery_terms=po.delivery_terms,
        header_remark=po.header_remark,
        total_with_tax=po.total_with_tax,
        created_at=po.created_at,
        updated_at=po.updated_at,
        lines=lines,
        invoices=invoices,
        payment_due_date=due_date,
        payment_due_days_remaining=due_remaining,
    )


@router.get("", response_model=list[schemas.PurchaseOrderRead])
def list_orders(db: Session = Depends(get_db)):
    rows = crud.list_purchase_orders(db)
    names = {r.supplier_company for r in rows if (r.supplier_company or "").strip()}
    term_map = _supplier_payment_term_map(db, names)
    return [_po_to_read(r, term_days_by_company=term_map) for r in rows]


@router.post("", response_model=schemas.PurchaseOrderRead)
def create_order(payload: schemas.PurchaseOrderCreate, db: Session = Depends(get_db)):
    if not payload.lines:
        raise HTTPException(status_code=400, detail="至少一行明细")
    po = crud.create_purchase_order(db, payload)
    return _po_to_read(po, db=db)


@router.post("/{po_id}/receive", response_model=schemas.PurchaseOrderRead)
def receive_goods(po_id: int, payload: schemas.PurchaseOrderReceiveIn, db: Session = Depends(get_db)):
    if not payload.lines:
        raise HTTPException(status_code=400, detail="至少指定一行入库数量")
    po = crud.receive_purchase_order(db, po_id, payload)
    return _po_to_read(po, db=db)


@router.post("/{po_id}/invoices", response_model=schemas.PurchaseInvoiceRead)
async def upload_invoice(
    po_id: int,
    invoice_no: str = Form(...),
    amount_with_tax: str | None = Form(None),
    remark: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not (invoice_no or "").strip():
        raise HTTPException(status_code=400, detail="发票号码不能为空")
    try:
        amt = parse_optional_tax_amount(amount_with_tax)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e) or "含税金额格式无效") from e
    content = await file.read()
    inv = crud.add_purchase_invoice(
        db,
        po_id,
        invoice_no.strip(),
        content,
        file.filename or "",
        amt,
        remark,
        UPLOAD_ROOT,
    )
    return schemas.PurchaseInvoiceRead(
        id=inv.id,
        purchase_order_id=inv.purchase_order_id,
        invoice_no=inv.invoice_no,
        amount_with_tax=inv.amount_with_tax,
        original_filename=inv.original_filename,
        remark=inv.remark,
        created_at=inv.created_at,
    )


@router.get("/{po_id}/invoices/{invoice_id}/file")
def download_invoice_file(po_id: int, invoice_id: int, db: Session = Depends(get_db)):
    inv = db.get(models.PurchaseInvoice, invoice_id)
    if not inv or inv.purchase_order_id != po_id:
        raise HTTPException(status_code=404, detail="发票不存在")
    path = crud.purchase_invoice_file_path(UPLOAD_ROOT, inv)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="发票文件已丢失")
    return FileResponse(
        path=str(path),
        filename=inv.original_filename or f"invoice_{invoice_id}",
        media_type="application/octet-stream",
    )


@router.delete("/{po_id}/invoices/{invoice_id}", status_code=204)
def delete_invoice(po_id: int, invoice_id: int, db: Session = Depends(get_db)):
    crud.delete_purchase_invoice(db, po_id, invoice_id, UPLOAD_ROOT)
    return Response(status_code=204)


@router.get("/{po_id}/pdf")
def export_order_pdf(po_id: int, db: Session = Depends(get_db)):
    po = crud.get_purchase_order(db, po_id)
    company = crud.get_company_profile(db)
    try:
        pdf_bytes = build_purchase_order_pdf(po, company)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成 PDF 失败：{e}") from e
    filename = f"{po.order_no}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{po_id}", response_model=schemas.PurchaseOrderRead)
def get_order(po_id: int, db: Session = Depends(get_db)):
    return _po_to_read(crud.get_purchase_order(db, po_id), db=db)


@router.put("/{po_id}", response_model=schemas.PurchaseOrderRead)
def update_order(po_id: int, payload: schemas.PurchaseOrderUpdate, db: Session = Depends(get_db)):
    if payload.lines is not None and not payload.lines:
        raise HTTPException(status_code=400, detail="至少一行明细")
    po = crud.update_purchase_order(db, po_id, payload)
    return _po_to_read(po, db=db)
