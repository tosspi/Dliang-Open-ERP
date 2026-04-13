from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates

from app.database import get_db
from app import models

templates = Jinja2Templates(directory="app/templates")
router = APIRouter(prefix="/ui", tags=["ui"])


def _render(request: Request, template_name: str, page_title: str, **kwargs):
    context = {"request": request, "page_title": page_title}
    context.update(kwargs)
    return templates.TemplateResponse(request=request, name=template_name, context=context)


@router.get("")
@router.get("/dashboard")
def dashboard_page(request: Request):
    return _render(request, "dashboard.html", "仪表盘")


@router.get("/materials")
def materials_page(request: Request):
    return _render(request, "materials.html", "物料主数据", view_mode="all")


@router.get("/standard-materials")
def standard_materials_page(request: Request):
    return _render(request, "materials.html", "标准件管理", view_mode="standard")


@router.get("/nonstandard-materials")
def nonstandard_materials_page(request: Request):
    return _render(request, "materials.html", "非标件管理", view_mode="nonstandard")


@router.get("/revisions")
def revisions_page(request: Request):
    return _render(request, "revisions.html", "版本管理", focus_material_id=None)


@router.get("/materials/{material_id}/revisions")
def revisions_page_for_material(request: Request, material_id: int):
    return _render(request, "revisions.html", "版本管理", focus_material_id=material_id)


@router.get("/boms")
def boms_page(request: Request):
    return _render(request, "boms.html", "BOM管理")


@router.get("/self-products")
def self_products_page(request: Request):
    return _render(request, "products.html", "自产品管理", view_mode="self_made")


@router.get("/purchased-products")
def purchased_products_page(request: Request):
    return _render(request, "products.html", "外购品管理", view_mode="purchased")


@router.get("/boms/{bom_id}")
def bom_detail_page(request: Request, bom_id: int):
    return _render(request, "bom_detail.html", "BOM明细", bom_id=bom_id)


@router.get("/inventory")
def inventory_page(request: Request):
    return _render(request, "inventory.html", "库存管理")


@router.get("/procurement")
def procurement_page(request: Request):
    return _render(request, "procurement.html", "缺料 / 采购建议")


@router.get("/production-plans")
def production_plans_page(request: Request):
    return _render(request, "production_plans.html", "生产计划")


@router.get("/suppliers")
def suppliers_page(request: Request):
    return _render(request, "suppliers.html", "供应商管理")


@router.get("/categories")
def categories_page(request: Request):
    return _render(request, "categories.html", "类别管理")


@router.get("/settings/integrations")
def settings_integrations_page(request: Request):
    return _render(request, "settings_integrations.html", "电商集成")


@router.get("/settings")
def settings_page(request: Request):
    return _render(request, "settings.html", "基础设置")


@router.get("/sales-orders")
def sales_orders_page(request: Request):
    return _render(request, "sales_orders.html", "销售订单（淘宝 / WooCommerce）")


@router.get("/purchase-orders")
def purchase_orders_page(request: Request):
    return _render(request, "purchase_orders.html", "采购订单")


@router.get("/purchase-receipts")
def purchase_receipts_page(request: Request):
    return _render(request, "purchase_receipts.html", "采购入库")


@router.get("/purchase-invoices")
def purchase_invoices_page(request: Request):
    return _render(request, "purchase_invoice_mgmt.html", "采购发票")


@router.get("/inquiries")
def inquiries_page(request: Request):
    return _render(request, "inquiries.html", "询价管理")


@router.get("/tutorial")
def tutorial_page(request: Request):
    return _render(request, "tutorial.html", "使用教程")


@router.get("/api/dashboard-stats")
def dashboard_stats(db: Session = Depends(get_db)):
    total_materials = db.scalar(select(func.count(models.Material.id))) or 0
    standard_count = db.scalar(
        select(func.count(models.Material.id)).where(models.Material.part_type == models.PartType.standard)
    ) or 0
    custom_count = db.scalar(
        select(func.count(models.Material.id)).where(models.Material.part_type == models.PartType.custom)
    ) or 0
    assembly_count = db.scalar(
        select(func.count(models.Material.id)).where(models.Material.part_type == models.PartType.assembly)
    ) or 0

    current_bom_count = db.scalar(
        select(func.count(models.BOMHeader.id)).where(models.BOMHeader.is_current.is_(True))
    ) or 0
    low_stock_count = db.scalar(
        select(func.count(models.Material.id)).where(models.Material.current_stock < models.Material.safety_stock)
    ) or 0
    current_revision_count = db.scalar(
        select(func.count(models.PartRevision.id)).where(models.PartRevision.is_current.is_(True))
    ) or 0

    return {
        "total_materials": total_materials,
        "standard_count": standard_count,
        "custom_count": custom_count,
        "assembly_count": assembly_count,
        "current_bom_count": current_bom_count,
        "low_stock_count": low_stock_count,
        "current_revision_count": current_revision_count,
    }
