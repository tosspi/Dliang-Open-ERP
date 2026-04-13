from collections import defaultdict
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
import uuid

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app import models, schemas, taobao_client, woocommerce_client
from app.utils import calc_total_price, money

ALLOW_NEGATIVE_STOCK = False


# -------------------------
# Material Categories
# -------------------------
def list_material_categories(db: Session):
    return db.scalars(select(models.MaterialCategory).order_by(models.MaterialCategory.sort_order.asc())).all()


def get_material_category(db: Session, category_id: int):
    category = db.get(models.MaterialCategory, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Material category not found")
    return category


def create_material_category(db: Session, payload: schemas.MaterialCategoryCreate):
    exists_name = db.scalar(select(models.MaterialCategory).where(models.MaterialCategory.name == payload.name))
    if exists_name:
        raise HTTPException(status_code=400, detail="Category name already exists")
    exists_prefix = db.scalar(select(models.MaterialCategory).where(models.MaterialCategory.code_prefix == payload.code_prefix))
    if exists_prefix:
        raise HTTPException(status_code=400, detail="Category code prefix already exists")
    category = models.MaterialCategory(**payload.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update_material_category(db: Session, category_id: int, payload: schemas.MaterialCategoryUpdate):
    category = get_material_category(db, category_id)
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"]:
        exists_name = db.scalar(
            select(models.MaterialCategory).where(
                models.MaterialCategory.name == data["name"],
                models.MaterialCategory.id != category_id,
            )
        )
        if exists_name:
            raise HTTPException(status_code=400, detail="Category name already exists")
    if "code_prefix" in data and data["code_prefix"]:
        exists_prefix = db.scalar(
            select(models.MaterialCategory).where(
                models.MaterialCategory.code_prefix == data["code_prefix"],
                models.MaterialCategory.id != category_id,
            )
        )
        if exists_prefix:
            raise HTTPException(status_code=400, detail="Category code prefix already exists")
    for key, value in data.items():
        setattr(category, key, value)
    db.commit()
    db.refresh(category)
    return category


def soft_delete_material_category(db: Session, category_id: int):
    category = get_material_category(db, category_id)
    category.is_active = False
    db.commit()
    db.refresh(category)
    return category


def hard_delete_material_category(db: Session, category_id: int):
    category = get_material_category(db, category_id)
    in_materials = db.scalar(
        select(func.count(models.Material.id)).where(models.Material.category == category.name)
    ) or 0
    if in_materials:
        raise HTTPException(status_code=400, detail="该物料分类已被物料使用，无法删除")
    in_suppliers = db.scalar(
        select(func.count(models.Supplier.id)).where(models.Supplier.supplier_categories.like(f"%{category.name}%"))
    ) or 0
    if in_suppliers:
        raise HTTPException(status_code=400, detail="该物料分类已被供应商使用，无法删除")
    db.delete(category)
    db.commit()
    return {"message": "Material category deleted"}


# -------------------------
# System Options
# -------------------------
VALID_OPTION_TYPES = {"unit", "tax_rate", "material_attr", "grade", "product_category"}


def list_system_options(db: Session, option_type: str | None = None):
    query = select(models.SystemOption)
    if option_type:
        query = query.where(models.SystemOption.option_type == option_type)
    query = query.order_by(models.SystemOption.option_type.asc(), models.SystemOption.sort_order.asc(), models.SystemOption.id.asc())
    return db.scalars(query).all()


def get_system_option(db: Session, option_id: int):
    option = db.get(models.SystemOption, option_id)
    if not option:
        raise HTTPException(status_code=404, detail="System option not found")
    return option


def create_system_option(db: Session, payload: schemas.SystemOptionCreate):
    if payload.option_type not in VALID_OPTION_TYPES:
        raise HTTPException(status_code=400, detail="Invalid option_type")
    exists = db.scalar(
        select(models.SystemOption).where(
            models.SystemOption.option_type == payload.option_type,
            models.SystemOption.name == payload.name,
        )
    )
    if exists:
        raise HTTPException(status_code=400, detail="Option already exists in this type")
    option = models.SystemOption(**payload.model_dump())
    db.add(option)
    db.commit()
    db.refresh(option)
    return option


def update_system_option(db: Session, option_id: int, payload: schemas.SystemOptionUpdate):
    option = get_system_option(db, option_id)
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"]:
        exists = db.scalar(
            select(models.SystemOption).where(
                models.SystemOption.option_type == option.option_type,
                models.SystemOption.name == data["name"],
                models.SystemOption.id != option_id,
            )
        )
        if exists:
            raise HTTPException(status_code=400, detail="Option already exists in this type")
    for key, value in data.items():
        setattr(option, key, value)
    db.commit()
    db.refresh(option)
    return option


def soft_delete_system_option(db: Session, option_id: int):
    option = get_system_option(db, option_id)
    option.is_active = False
    db.commit()
    db.refresh(option)
    return option


def hard_delete_system_option(db: Session, option_id: int):
    option = get_system_option(db, option_id)
    if option.option_type == "unit":
        used = db.scalar(select(func.count(models.Material.id)).where(models.Material.unit == option.name)) or 0
        if used:
            raise HTTPException(status_code=400, detail="该单位已被物料使用，无法删除")
    elif option.option_type == "tax_rate":
        used = db.scalar(select(func.count(models.Material.id)).where(models.Material.tax_rate == option.name)) or 0
        if used:
            raise HTTPException(status_code=400, detail="该税率已被物料使用，无法删除")
    elif option.option_type == "material_attr":
        used = db.scalar(
            select(func.count(models.Material.id)).where(models.Material.material_name_attr == option.name)
        ) or 0
        if used:
            raise HTTPException(status_code=400, detail="该材质已被物料使用，无法删除")
    elif option.option_type == "grade":
        used = db.scalar(select(func.count(models.Material.id)).where(models.Material.grade_attr == option.name)) or 0
        if used:
            raise HTTPException(status_code=400, detail="该等级已被物料使用，无法删除")
    elif option.option_type == "product_category":
        used = db.scalar(select(func.count(models.Product.id)).where(models.Product.product_category == option.name)) or 0
        if used:
            raise HTTPException(status_code=400, detail="该产品类别已被产品使用，无法删除")
    db.delete(option)
    db.commit()
    return {"message": "System option deleted"}


# -------------------------
# Materials
# -------------------------
def list_materials(db: Session):
    return db.scalars(select(models.Material).order_by(models.Material.id.desc())).all()


def get_material(db: Session, material_id: int):
    material = db.get(models.Material, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    return material


def create_material(db: Session, payload: schemas.MaterialCreate):
    data = payload.model_dump()
    category = data.get("category")
    if category:
        exists_category = db.scalar(
            select(models.MaterialCategory).where(
                models.MaterialCategory.name == category,
                models.MaterialCategory.is_active.is_(True),
            )
        )
        if not exists_category:
            raise HTTPException(status_code=400, detail="Invalid material category")
    if not data.get("code"):
        data["code"] = _generate_material_code(db, category)
    exists = db.scalar(select(models.Material).where(models.Material.code == data["code"]))
    if exists:
        raise HTTPException(status_code=400, detail="Material code already exists")
    material = models.Material(**data)
    db.add(material)
    db.commit()
    db.refresh(material)
    return material


def update_material(db: Session, material_id: int, payload: schemas.MaterialUpdate):
    material = get_material(db, material_id)
    data = payload.model_dump(exclude_unset=True)
    if "category" in data and data["category"]:
        exists_category = db.scalar(
            select(models.MaterialCategory).where(
                models.MaterialCategory.name == data["category"],
                models.MaterialCategory.is_active.is_(True),
            )
        )
        if not exists_category:
            raise HTTPException(status_code=400, detail="Invalid material category")
    data.pop("code", None)
    for key, value in data.items():
        setattr(material, key, value)
    _sync_all_bom_items_for_material(db, material)
    db.commit()
    db.refresh(material)
    return material


def soft_delete_material(db: Session, material_id: int):
    material = get_material(db, material_id)
    material.is_active = False
    db.commit()
    db.refresh(material)
    return material


def hard_delete_material(db: Session, material_id: int):
    material = get_material(db, material_id)
    rev_count = db.scalar(
        select(func.count(models.PartRevision.id)).where(models.PartRevision.material_id == material_id)
    ) or 0
    bom_item_count = db.scalar(
        select(func.count(models.BOMItem.id)).where(models.BOMItem.material_id == material_id)
    ) or 0
    tx_count = db.scalar(
        select(func.count(models.StockTransaction.id)).where(models.StockTransaction.material_id == material_id)
    ) or 0
    if rev_count or bom_item_count or tx_count:
        raise HTTPException(
            status_code=400,
            detail="Material is referenced by revisions/BOM/inventory transactions and cannot be deleted",
        )
    db.delete(material)
    db.commit()
    return {"message": "Material deleted"}


def _generate_material_code(db: Session, category: str | None):
    prefix = "WL"
    if category:
        cat = db.scalar(
            select(models.MaterialCategory).where(
                models.MaterialCategory.name == category,
                models.MaterialCategory.is_active.is_(True),
            )
        )
        if cat and cat.code_prefix:
            prefix = cat.code_prefix
    like_prefix = f"{prefix}-"
    rows = db.scalars(select(models.Material.code).where(models.Material.code.like(f"{like_prefix}%"))).all()
    max_no = 0
    for code in rows:
        try:
            n = int(str(code).split("-")[-1])
            if n > max_no:
                max_no = n
        except Exception:
            continue
    return f"{prefix}-{max_no + 1:04d}"


# -------------------------
# Suppliers
# -------------------------
def list_suppliers(db: Session):
    suppliers = db.scalars(select(models.Supplier).order_by(models.Supplier.id.desc())).all()
    return [_supplier_to_dict(db, s) for s in suppliers]


def get_supplier(db: Session, supplier_id: int):
    supplier = db.get(models.Supplier, supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return _supplier_to_dict(db, supplier)


def _supplier_to_dict(db: Session, supplier: models.Supplier):
    categories = []
    if supplier.supplier_categories:
        categories = [x for x in supplier.supplier_categories.split(",") if x]
    links = db.scalars(
        select(models.SupplierMaterial).where(models.SupplierMaterial.supplier_id == supplier.id)
    ).all()
    mids = [x.material_id for x in links]
    mats = db.scalars(select(models.Material).where(models.Material.id.in_(mids))).all() if mids else []
    mat_map = {m.id: m for m in mats}
    managed_materials = []
    for l in (links or []):
        m = mat_map.get(l.material_id)
        if not m:
            continue
        spec = (m.spec or "").strip()
        draw = (m.drawing_no or "").strip()
        managed_materials.append(
            {
                "id": m.id,
                "code": m.code,
                "name": m.name,
                "spec_drawing": " / ".join([x for x in (spec, draw) if x]) or None,
                "unit": m.unit,
                "unit_price": m.unit_price,
                "tax_rate": m.tax_rate,
                "remark": m.remark,
            }
        )
    return {
        "id": supplier.id,
        "supplier_code": supplier.supplier_code,
        "company_name": supplier.company_name,
        "supplier_categories": categories,
        "credit_code": supplier.credit_code,
        "bank_name": supplier.bank_name,
        "bank_account": supplier.bank_account,
        "bank_no": supplier.bank_no,
        "contact_person": supplier.contact_person,
        "phone": supplier.phone,
        "address": supplier.address,
        "payment_term_days": supplier.payment_term_days,
        "managed_material_ids": mids,
        "managed_materials": managed_materials,
        "is_active": supplier.is_active,
        "created_at": supplier.created_at,
        "updated_at": supplier.updated_at,
    }


def create_supplier(db: Session, payload: schemas.SupplierCreate):
    data = payload.model_dump()
    for c in data.get("supplier_categories", []):
        exists_category = db.scalar(
            select(models.MaterialCategory).where(
                models.MaterialCategory.name == c,
                models.MaterialCategory.is_active.is_(True),
            )
        )
        if not exists_category:
            raise HTTPException(status_code=400, detail=f"Invalid supplier category: {c}")
    if not data.get("supplier_code"):
        data["supplier_code"] = _generate_supplier_code(db)
    exists_supplier_code = db.scalar(select(models.Supplier).where(models.Supplier.supplier_code == data["supplier_code"]))
    if exists_supplier_code:
        raise HTTPException(status_code=400, detail="Supplier code already exists")
    exists_name = db.scalar(select(models.Supplier).where(models.Supplier.company_name == payload.company_name))
    if exists_name:
        raise HTTPException(status_code=400, detail="Supplier company name already exists")
    if payload.credit_code:
        exists_code = db.scalar(select(models.Supplier).where(models.Supplier.credit_code == payload.credit_code))
        if exists_code:
            raise HTTPException(status_code=400, detail="Supplier credit code already exists")
    managed_material_ids = list(dict.fromkeys(data.pop("managed_material_ids", []) or []))
    if managed_material_ids:
        exists_cnt = db.scalar(
            select(func.count(models.Material.id)).where(models.Material.id.in_(managed_material_ids))
        ) or 0
        if int(exists_cnt) != len(managed_material_ids):
            raise HTTPException(status_code=400, detail="Invalid managed material ids")
    data["supplier_categories"] = ",".join(data.get("supplier_categories", []))
    supplier = models.Supplier(**data)
    db.add(supplier)
    db.flush()
    for mid in managed_material_ids:
        db.add(models.SupplierMaterial(supplier_id=supplier.id, material_id=int(mid)))
    db.commit()
    db.refresh(supplier)
    return _supplier_to_dict(db, supplier)


def update_supplier(db: Session, supplier_id: int, payload: schemas.SupplierUpdate):
    supplier = db.get(models.Supplier, supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    data = payload.model_dump(exclude_unset=True)
    managed_material_ids = data.pop("managed_material_ids", None)
    if "supplier_categories" in data:
        for c in data["supplier_categories"] or []:
            exists_category = db.scalar(
                select(models.MaterialCategory).where(
                    models.MaterialCategory.name == c,
                    models.MaterialCategory.is_active.is_(True),
                )
            )
            if not exists_category:
                raise HTTPException(status_code=400, detail=f"Invalid supplier category: {c}")
        data["supplier_categories"] = ",".join(data["supplier_categories"] or [])
    # 供应商编码由系统生成，不允许手工修改
    data.pop("supplier_code", None)
    if "company_name" in data and data["company_name"]:
        exists_name = db.scalar(
            select(models.Supplier).where(
                models.Supplier.company_name == data["company_name"],
                models.Supplier.id != supplier_id,
            )
        )
        if exists_name:
            raise HTTPException(status_code=400, detail="Supplier company name already exists")
    if "credit_code" in data and data["credit_code"]:
        exists_code = db.scalar(
            select(models.Supplier).where(
                models.Supplier.credit_code == data["credit_code"],
                models.Supplier.id != supplier_id,
            )
        )
        if exists_code:
            raise HTTPException(status_code=400, detail="Supplier credit code already exists")
    if managed_material_ids is not None:
        uniq = list(dict.fromkeys(managed_material_ids or []))
        if uniq:
            exists_cnt = db.scalar(
                select(func.count(models.Material.id)).where(models.Material.id.in_(uniq))
            ) or 0
            if int(exists_cnt) != len(uniq):
                raise HTTPException(status_code=400, detail="Invalid managed material ids")
    for key, value in data.items():
        setattr(supplier, key, value)
    if managed_material_ids is not None:
        uniq = list(dict.fromkeys(managed_material_ids or []))
        db.query(models.SupplierMaterial).filter(models.SupplierMaterial.supplier_id == supplier.id).delete()
        for mid in uniq:
            db.add(models.SupplierMaterial(supplier_id=supplier.id, material_id=int(mid)))
    db.commit()
    db.refresh(supplier)
    return _supplier_to_dict(db, supplier)


def _generate_supplier_code(db: Session):
    prefix = "SUP"
    rows = db.scalars(
        select(models.Supplier.supplier_code).where(models.Supplier.supplier_code.like(f"{prefix}-%"))
    ).all()
    max_no = 0
    for code in rows:
        try:
            n = int(str(code).split("-")[-1])
            if n > max_no:
                max_no = n
        except Exception:
            continue
    return f"{prefix}-{max_no + 1:04d}"


def soft_delete_supplier(db: Session, supplier_id: int):
    supplier = db.get(models.Supplier, supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    supplier.is_active = False
    db.commit()
    db.refresh(supplier)
    return _supplier_to_dict(db, supplier)


# -------------------------
# Revisions
# -------------------------
def list_revisions(db: Session, material_id: int):
    get_material(db, material_id)
    return db.scalars(
        select(models.PartRevision)
        .where(models.PartRevision.material_id == material_id)
        .order_by(models.PartRevision.created_at.desc())
    ).all()


def list_nonstandard_revisions_flat(
    db: Session,
    *,
    material_code: str | None = None,
    material_name: str | None = None,
    category: str | None = None,
    revision: str | None = None,
    status: str | None = None,
    current_only: bool = False,
    material_id: int | None = None,
) -> list[schemas.RevisionListItem]:
    """列出自制件/装配件的所有版本（扁平表），支持筛选。"""
    q = (
        select(models.PartRevision, models.Material)
        .join(models.Material, models.PartRevision.material_id == models.Material.id)
        .where(models.Material.part_type.in_([models.PartType.custom, models.PartType.assembly]))
    )
    if material_id is not None:
        q = q.where(models.Material.id == material_id)
    if material_code and material_code.strip():
        q = q.where(models.Material.code.contains(material_code.strip()))
    if material_name and material_name.strip():
        q = q.where(models.Material.name.contains(material_name.strip()))
    if category and category.strip():
        q = q.where(models.Material.category == category.strip())
    if revision and revision.strip():
        q = q.where(models.PartRevision.revision.contains(revision.strip()))
    if status and status.strip():
        try:
            st = models.StatusType(status.strip())
        except ValueError:
            st = None
        if st is not None:
            q = q.where(models.PartRevision.status == st)
    if current_only:
        q = q.where(models.PartRevision.is_current.is_(True))
    q = q.order_by(models.Material.code.asc(), models.PartRevision.created_at.desc())
    out: list[schemas.RevisionListItem] = []
    for rev, mat in db.execute(q).all():
        base = schemas.RevisionRead.model_validate(rev)
        out.append(
            schemas.RevisionListItem(
                **base.model_dump(),
                material_code=mat.code,
                material_item_name=mat.name,
                material_category=mat.category,
                material_part_type=mat.part_type,
            )
        )
    return out


def _clear_current_revision(db: Session, material_id: int):
    db.query(models.PartRevision).filter(
        models.PartRevision.material_id == material_id,
        models.PartRevision.is_current.is_(True),
    ).update({"is_current": False})


def create_revision(db: Session, material_id: int, payload: schemas.RevisionCreate):
    material = get_material(db, material_id)
    if material.part_type == models.PartType.standard and payload.is_current:
        raise HTTPException(status_code=400, detail="Standard part does not need current revision")

    revision = models.PartRevision(material_id=material_id, **payload.model_dump())
    if payload.is_current:
        _clear_current_revision(db, material_id)
        material.current_revision = payload.revision
        material.drawing_no = payload.drawing_no or material.drawing_no
    db.add(revision)
    db.commit()
    db.refresh(revision)
    return revision


def update_revision(db: Session, revision_id: int, payload: schemas.RevisionUpdate):
    rev = db.get(models.PartRevision, revision_id)
    if not rev:
        raise HTTPException(status_code=404, detail="Revision not found")

    data = payload.model_dump(exclude_unset=True)
    if data.get("is_current") is True:
        _clear_current_revision(db, rev.material_id)
        material = get_material(db, rev.material_id)
        material.current_revision = data.get("revision", rev.revision)

    for key, value in data.items():
        setattr(rev, key, value)

    db.commit()
    db.refresh(rev)
    return rev


def set_current_revision(db: Session, revision_id: int):
    rev = db.get(models.PartRevision, revision_id)
    if not rev:
        raise HTTPException(status_code=404, detail="Revision not found")
    _clear_current_revision(db, rev.material_id)
    rev.is_current = True
    material = get_material(db, rev.material_id)
    material.current_revision = rev.revision
    material.drawing_no = rev.drawing_no or material.drawing_no
    db.commit()
    db.refresh(rev)
    return rev


# -------------------------
# BOM Header
# -------------------------
def list_boms(db: Session):
    return db.scalars(select(models.BOMHeader).order_by(models.BOMHeader.id.desc())).all()


def get_bom(db: Session, bom_id: int):
    bom = db.get(models.BOMHeader, bom_id)
    if not bom:
        raise HTTPException(status_code=404, detail="BOM not found")
    return bom


def _clear_current_bom(db: Session, product_code: str):
    db.query(models.BOMHeader).filter(
        models.BOMHeader.product_code == product_code,
        models.BOMHeader.is_current.is_(True),
    ).update({"is_current": False})


def create_bom(db: Session, payload: schemas.BOMHeaderCreate):
    bom = models.BOMHeader(**payload.model_dump())
    if bom.is_current:
        _clear_current_bom(db, bom.product_code)
    db.add(bom)
    db.commit()
    db.refresh(bom)
    return bom


def update_bom(db: Session, bom_id: int, payload: schemas.BOMHeaderUpdate):
    bom = get_bom(db, bom_id)
    data = payload.model_dump(exclude_unset=True)
    if data.get("is_current") is True:
        _clear_current_bom(db, bom.product_code)
    for key, value in data.items():
        setattr(bom, key, value)
    db.commit()
    db.refresh(bom)
    return bom


def set_current_bom(db: Session, bom_id: int):
    bom = get_bom(db, bom_id)
    _clear_current_bom(db, bom.product_code)
    bom.is_current = True
    db.commit()
    db.refresh(bom)
    return bom


# -------------------------
# BOM Items
# -------------------------
def list_bom_items(db: Session, bom_id: int):
    get_bom(db, bom_id)
    return db.scalars(
        select(models.BOMItem).where(models.BOMItem.bom_header_id == bom_id).order_by(models.BOMItem.line_no.asc())
    ).all()


def _sync_bom_item_with_material(item_data: dict, material: models.Material) -> None:
    """BOM 明细中与物料主数据一致的字段一律从物料带出（保存时以物料为准）。"""
    item_data["material_code"] = material.code
    item_data["material_name"] = material.name
    item_data["unit"] = material.unit
    item_data["revision"] = material.current_revision
    u = (material.usage or "").strip()
    item_data["usage"] = u if u else "—"
    item_data["material_name_attr"] = material.material_name_attr
    item_data["standard_attr"] = material.standard_attr
    item_data["grade_attr"] = material.grade_attr
    item_data["unit_price"] = material.unit_price


def _refresh_bom_item_row_from_material(item: models.BOMItem, material: models.Material) -> bool:
    """若 BOM 行快照与物料主数据不一致则写回，返回是否修改。"""
    dirty = False
    if item.material_code != material.code:
        item.material_code = material.code
        dirty = True
    if item.material_name != material.name:
        item.material_name = material.name
        dirty = True
    if (item.unit or "") != (material.unit or ""):
        item.unit = material.unit
        dirty = True
    nr = material.current_revision
    if (item.revision or "") != (nr or ""):
        item.revision = nr
        dirty = True
    exp_usage = (material.usage or "").strip() or "—"
    if (item.usage or "") != exp_usage:
        item.usage = exp_usage
        dirty = True
    if (item.material_name_attr or "") != (material.material_name_attr or ""):
        item.material_name_attr = material.material_name_attr
        dirty = True
    if (item.standard_attr or "") != (material.standard_attr or ""):
        item.standard_attr = material.standard_attr
        dirty = True
    if (item.grade_attr or "") != (material.grade_attr or ""):
        item.grade_attr = material.grade_attr
        dirty = True
    mat_up = Decimal(material.unit_price or 0)
    if Decimal(item.unit_price or 0) != mat_up:
        item.unit_price = material.unit_price
        dirty = True
    fixed_total = calc_total_price(item.qty, item.unit_price)
    if Decimal(item.total_price) != Decimal(fixed_total):
        item.total_price = fixed_total
        dirty = True
    return dirty


def _sync_all_bom_items_for_material(db: Session, material: models.Material) -> None:
    for it in db.scalars(select(models.BOMItem).where(models.BOMItem.material_id == material.id)).all():
        _refresh_bom_item_row_from_material(it, material)


def _next_bom_line_no(db: Session, bom_id: int) -> int:
    max_ln = db.scalar(select(func.max(models.BOMItem.line_no)).where(models.BOMItem.bom_header_id == bom_id))
    if max_ln is None:
        return 1
    return int(max_ln) + 1


def create_bom_item(db: Session, bom_id: int, payload: schemas.BOMItemCreate):
    get_bom(db, bom_id)
    material = get_material(db, payload.material_id)
    dup = db.scalar(
        select(func.count(models.BOMItem.id)).where(
            models.BOMItem.bom_header_id == bom_id,
            models.BOMItem.material_id == payload.material_id,
        )
    ) or 0
    if int(dup) > 0:
        raise HTTPException(status_code=400, detail="该物料已在当前BOM中，不能重复添加")
    data = payload.model_dump()
    _sync_bom_item_with_material(data, material)
    line_no = int(data.get("line_no") or 0)
    exists_line = db.scalar(
        select(func.count(models.BOMItem.id)).where(
            models.BOMItem.bom_header_id == bom_id,
            models.BOMItem.line_no == line_no,
        )
    ) or 0
    if line_no <= 0 or int(exists_line) > 0:
        data["line_no"] = _next_bom_line_no(db, bom_id)

    # 总价统一按数量*单价计算，避免前端传入值不一致
    data["total_price"] = calc_total_price(data["qty"], data["unit_price"])
    item = models.BOMItem(bom_header_id=bom_id, **data)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_bom_item(db: Session, item_id: int, payload: schemas.BOMItemUpdate):
    item = db.get(models.BOMItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="BOM item not found")
    data = payload.model_dump(exclude_unset=True)
    mid = data.get("material_id", item.material_id)
    material = get_material(db, mid)
    dup = db.scalar(
        select(func.count(models.BOMItem.id)).where(
            models.BOMItem.bom_header_id == item.bom_header_id,
            models.BOMItem.material_id == mid,
            models.BOMItem.id != item_id,
        )
    ) or 0
    if int(dup) > 0:
        raise HTTPException(status_code=400, detail="该物料已在当前BOM中，不能重复添加")
    data["material_id"] = mid
    _sync_bom_item_with_material(data, material)

    qty = Decimal(data.get("qty", item.qty))
    unit_price = Decimal(data.get("unit_price", item.unit_price))
    # 总价统一按数量*单价计算，忽略传入 total_price
    data["total_price"] = calc_total_price(qty, unit_price)

    for key, value in data.items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


def delete_bom_item(db: Session, item_id: int):
    item = db.get(models.BOMItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="BOM item not found")
    db.delete(item)
    db.commit()
    return {"message": "BOM item deleted"}


def delete_bom(db: Session, bom_id: int):
    bom = get_bom(db, bom_id)
    for it in list(bom.items):
        db.delete(it)
    db.delete(bom)
    db.commit()
    return {"message": "BOM deleted"}


def get_bom_detail(db: Session, bom_id: int):
    header = get_bom(db, bom_id)
    items = list_bom_items(db, bom_id)
    dirty = False
    sorted_items = sorted(items, key=lambda x: (x.line_no, x.id))
    seen_line_no: set[int] = set()
    for idx, i in enumerate(sorted_items, start=1):
        ln = int(i.line_no)
        if ln <= 0 or ln in seen_line_no or ln != idx:
            dirty = True
        seen_line_no.add(ln)
    if dirty:
        # 兼容历史脏数据：行号重排为 1..n（两阶段避免唯一索引冲突）
        for t, i in enumerate(sorted_items, start=1):
            i.line_no = -100000 - t
        db.flush()
        for idx, i in enumerate(sorted_items, start=1):
            i.line_no = idx
        db.commit()
        items = list_bom_items(db, bom_id)
    for i in items:
        m = get_material(db, i.material_id)
        spec = (m.spec or "").strip()
        draw = (m.drawing_no or "").strip()
        i.spec_drawing = " / ".join([x for x in (spec, draw) if x]) or None
        if _refresh_bom_item_row_from_material(i, m):
            dirty = True
    if dirty:
        db.commit()
    total_cost = sum((Decimal(i.total_price) for i in items), Decimal("0"))
    return {"header": header, "items": items, "total_cost": money(total_cost)}


# -------------------------
# Inventory
# -------------------------
def list_transactions(db: Session):
    return db.scalars(select(models.StockTransaction).order_by(models.StockTransaction.id.desc())).all()


def list_transactions_by_material(db: Session, material_id: int):
    get_material(db, material_id)
    return db.scalars(
        select(models.StockTransaction)
        .where(models.StockTransaction.material_id == material_id)
        .order_by(models.StockTransaction.id.desc())
    ).all()


def _apply_stock_transaction(db: Session, payload: schemas.StockTransactionCreate) -> models.StockTransaction:
    material = get_material(db, payload.material_id)
    qty = Decimal(payload.qty)
    current_stock = Decimal(material.current_stock)

    if payload.transaction_type == models.TransactionType.in_:
        new_stock = current_stock + qty
    elif payload.transaction_type == models.TransactionType.out:
        new_stock = current_stock - qty
        if (not ALLOW_NEGATIVE_STOCK) and new_stock < 0:
            raise HTTPException(status_code=400, detail="Insufficient stock")
    else:
        new_stock = current_stock + qty

    tx = models.StockTransaction(**payload.model_dump())
    material.current_stock = new_stock
    db.add(tx)
    return tx


def create_transaction(db: Session, payload: schemas.StockTransactionCreate):
    tx = _apply_stock_transaction(db, payload)
    db.commit()
    db.refresh(tx)
    return tx


# -------------------------
# Procurement shortage calculation
# -------------------------
def calc_shortage(db: Session, payload: schemas.ShortageCalcRequest):
    bom = get_bom(db, payload.bom_id)
    items = list_bom_items(db, bom.id)
    if not items:
        raise HTTPException(status_code=400, detail="BOM has no items")

    shortage_list: list[schemas.ShortageItem] = []
    supplier_map: dict[str, list[schemas.ShortageItem]] = defaultdict(list)
    total_estimated_cost = Decimal("0")

    for item in items:
        material = get_material(db, item.material_id)
        total_required = Decimal(item.qty) * Decimal(payload.production_qty)
        current_stock = Decimal(material.current_stock)
        safety_stock = Decimal(material.safety_stock)
        clear_shortage = max(Decimal("0"), total_required - current_stock)
        safety_shortage = max(Decimal("0"), total_required + safety_stock - current_stock)
        suggested_purchase_qty = safety_shortage
        unit_price = Decimal(item.unit_price or material.unit_price or 0)
        estimated_amount = money(suggested_purchase_qty * unit_price)

        _sp = (material.spec or "").strip()
        _dr = (material.drawing_no or "").strip()
        spec_drawing = " / ".join([x for x in (_sp, _dr) if x]) or None

        shortage_item = schemas.ShortageItem(
            material_id=material.id,
            material_code=item.material_code,
            material_name=item.material_name,
            spec_drawing=spec_drawing,
            revision=item.revision,
            usage=item.usage,
            unit=item.unit,
            unit_usage=Decimal(item.qty),
            total_required_qty=money(total_required),
            current_stock=money(current_stock),
            safety_stock=money(safety_stock),
            safety_shortage_qty=money(safety_shortage),
            clear_shortage_qty=money(clear_shortage),
            suggested_purchase_qty=money(suggested_purchase_qty),
            default_supplier=material.default_supplier,
            unit_price=money(unit_price),
            estimated_amount=estimated_amount,
        )
        shortage_list.append(shortage_item)
        supplier_key = material.default_supplier or "未指定供应商"
        supplier_map[supplier_key].append(shortage_item)
        total_estimated_cost += estimated_amount

    groups: list[schemas.SupplierGroup] = []
    for supplier, supplier_items in supplier_map.items():
        supplier_total = sum((i.estimated_amount for i in supplier_items), Decimal("0"))
        groups.append(
            schemas.SupplierGroup(
                supplier=supplier,
                items=supplier_items,
                supplier_total_amount=money(supplier_total),
            )
        )

    return schemas.ShortageCalcResponse(
        bom_id=payload.bom_id,
        production_qty=payload.production_qty,
        shortage_list=shortage_list,
        grouped_by_supplier=groups,
        total_estimated_cost=money(total_estimated_cost),
    )


# -------------------------
# Production plans + merged shortage / draft POs
# -------------------------
def _next_production_plan_no(db: Session) -> str:
    today = datetime.utcnow().strftime("%Y%m%d")
    prefix = f"PPL{today}"
    like = f"{prefix}%"
    cnt = db.scalar(select(func.count(models.ProductionPlan.id)).where(models.ProductionPlan.plan_no.like(like))) or 0
    return f"{prefix}{int(cnt) + 1:03d}"


def get_production_plan(db: Session, plan_id: int) -> models.ProductionPlan:
    plan = db.scalar(
        select(models.ProductionPlan)
        .where(models.ProductionPlan.id == plan_id)
        .options(selectinload(models.ProductionPlan.lines))
    )
    if not plan:
        raise HTTPException(status_code=404, detail="Production plan not found")
    return plan


def list_production_plans(db: Session):
    return db.scalars(
        select(models.ProductionPlan)
        .options(selectinload(models.ProductionPlan.lines))
        .order_by(models.ProductionPlan.id.desc())
    ).all()


def _validate_plan_lines(db: Session, lines: list[schemas.ProductionPlanLineIn]) -> None:
    if not lines:
        raise HTTPException(status_code=400, detail="至少一行计划明细")
    for ln in lines:
        get_bom(db, ln.bom_id)
        items = list_bom_items(db, ln.bom_id)
        if not items:
            raise HTTPException(status_code=400, detail=f"BOM id={ln.bom_id} 无明细，无法纳入计划")


def production_plan_to_read(db: Session, plan: models.ProductionPlan) -> schemas.ProductionPlanRead:
    line_reads: list[schemas.ProductionPlanLineRead] = []
    for ln in sorted(plan.lines, key=lambda x: (x.line_no, x.id)):
        bom = get_bom(db, ln.bom_id)
        line_reads.append(
            schemas.ProductionPlanLineRead(
                id=ln.id,
                line_no=ln.line_no,
                bom_id=ln.bom_id,
                product_code=bom.product_code,
                product_name=bom.product_name,
                bom_version=bom.bom_version,
                planned_qty=ln.planned_qty,
                remark=ln.remark,
            )
        )
    return schemas.ProductionPlanRead(
        id=plan.id,
        plan_no=plan.plan_no,
        plan_date=plan.plan_date,
        status=plan.status,
        remark=plan.remark,
        lines=line_reads,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


def create_production_plan(db: Session, payload: schemas.ProductionPlanCreate) -> models.ProductionPlan:
    lines_in = list(payload.lines or [])
    _validate_plan_lines(db, lines_in)
    pd = payload.plan_date or datetime.utcnow()
    plan = models.ProductionPlan(
        plan_no=_next_production_plan_no(db),
        plan_date=pd,
        status="draft",
        remark=payload.remark,
    )
    db.add(plan)
    db.flush()
    for idx, raw in enumerate(lines_in, start=1):
        line_no = raw.line_no if raw.line_no is not None and raw.line_no > 0 else idx
        db.add(
            models.ProductionPlanLine(
                plan_id=plan.id,
                line_no=line_no,
                bom_id=raw.bom_id,
                planned_qty=raw.planned_qty,
                remark=raw.remark,
            )
        )
    db.commit()
    db.refresh(plan)
    return get_production_plan(db, plan.id)


def update_production_plan(db: Session, plan_id: int, payload: schemas.ProductionPlanUpdate) -> models.ProductionPlan:
    plan = get_production_plan(db, plan_id)
    if plan.status != "draft":
        if payload.lines is not None:
            raise HTTPException(status_code=400, detail="仅草稿状态可修改明细")
        if payload.plan_date is not None or payload.remark is not None:
            pass
    data = payload.model_dump(exclude_unset=True)
    new_lines = data.pop("lines", None)
    status_in = data.pop("status", None)
    for k, v in data.items():
        setattr(plan, k, v)
    if status_in is not None:
        allowed = {"draft", "confirmed", "closed"}
        if status_in not in allowed:
            raise HTTPException(status_code=400, detail=f"无效状态，允许：{allowed}")
        plan.status = status_in
    if new_lines is not None:
        _validate_plan_lines(db, new_lines)
        db.query(models.ProductionPlanLine).filter(models.ProductionPlanLine.plan_id == plan.id).delete()
        db.flush()
        for idx, raw in enumerate(new_lines, start=1):
            line_no = raw.line_no if raw.line_no is not None and raw.line_no > 0 else idx
            db.add(
                models.ProductionPlanLine(
                    plan_id=plan.id,
                    line_no=line_no,
                    bom_id=raw.bom_id,
                    planned_qty=raw.planned_qty,
                    remark=raw.remark,
                )
            )
    db.commit()
    db.refresh(plan)
    return get_production_plan(db, plan.id)


def merge_shortage_for_production_plan(db: Session, plan_id: int) -> schemas.PlanShortageResponse:
    plan = get_production_plan(db, plan_id)
    required_by_mid: dict[int, Decimal] = defaultdict(Decimal)
    for ln in sorted(plan.lines, key=lambda x: (x.line_no, x.id)):
        get_bom(db, ln.bom_id)
        items = list_bom_items(db, ln.bom_id)
        if not items:
            raise HTTPException(status_code=400, detail=f"BOM id={ln.bom_id} 无明细")
        pq = Decimal(ln.planned_qty)
        for item in items:
            required_by_mid[item.material_id] += Decimal(item.qty) * pq

    shortage_list: list[schemas.ShortageItem] = []
    supplier_map: dict[str, list[schemas.ShortageItem]] = defaultdict(list)
    total_estimated_cost = Decimal("0")

    for mid, total_required in required_by_mid.items():
        material = get_material(db, mid)
        current_stock = Decimal(material.current_stock)
        safety_stock = Decimal(material.safety_stock)
        clear_shortage = max(Decimal("0"), total_required - current_stock)
        safety_shortage = max(Decimal("0"), total_required + safety_stock - current_stock)
        suggested_purchase_qty = safety_shortage
        unit_price = Decimal(material.unit_price or 0)
        estimated_amount = money(suggested_purchase_qty * unit_price)

        _sp = (material.spec or "").strip()
        _dr = (material.drawing_no or "").strip()
        spec_drawing = " / ".join([x for x in (_sp, _dr) if x]) or None

        shortage_item = schemas.ShortageItem(
            material_id=material.id,
            material_code=material.code,
            material_name=material.name,
            spec_drawing=spec_drawing,
            revision=None,
            usage="生产计划汇总",
            unit=material.unit,
            unit_usage=Decimal("0"),
            total_required_qty=money(total_required),
            current_stock=money(current_stock),
            safety_stock=money(safety_stock),
            safety_shortage_qty=money(safety_shortage),
            clear_shortage_qty=money(clear_shortage),
            suggested_purchase_qty=money(suggested_purchase_qty),
            default_supplier=material.default_supplier,
            unit_price=money(unit_price),
            estimated_amount=estimated_amount,
        )
        shortage_list.append(shortage_item)
        supplier_key = material.default_supplier or "未指定供应商"
        supplier_map[supplier_key].append(shortage_item)
        total_estimated_cost += estimated_amount

    groups: list[schemas.SupplierGroup] = []
    for supplier, supplier_items in supplier_map.items():
        supplier_total = sum((i.estimated_amount for i in supplier_items), Decimal("0"))
        groups.append(
            schemas.SupplierGroup(
                supplier=supplier,
                items=supplier_items,
                supplier_total_amount=money(supplier_total),
            )
        )

    shortage_list.sort(key=lambda x: x.material_code or "")
    return schemas.PlanShortageResponse(
        production_plan_id=plan.id,
        plan_no=plan.plan_no,
        shortage_list=shortage_list,
        grouped_by_supplier=groups,
        total_estimated_cost=money(total_estimated_cost),
    )


def _supplier_snapshot_for_po(db: Session, company_name: str) -> dict:
    s = db.scalar(
        select(models.Supplier).where(
            models.Supplier.company_name == company_name,
            models.Supplier.is_active.is_(True),
        )
    )
    if not s:
        return {
            "supplier_company": company_name,
            "supplier_tax_no": None,
            "supplier_bank": None,
            "supplier_account": None,
            "supplier_address": None,
            "supplier_phone": None,
            "supplier_contact": None,
        }
    return {
        "supplier_company": s.company_name,
        "supplier_tax_no": s.credit_code,
        "supplier_bank": s.bank_name,
        "supplier_account": s.bank_account,
        "supplier_address": s.address,
        "supplier_phone": s.phone,
        "supplier_contact": s.contact_person,
    }


def create_draft_purchase_orders_from_plan_shortage(
    db: Session, merged: schemas.PlanShortageResponse, plan_remark_suffix: str
) -> tuple[list[models.PurchaseOrder], bool]:
    """按供应商分组生成草稿采购订单；跳过「未指定供应商」。返回 (订单列表, 是否曾存在未指定组)。"""
    created: list[models.PurchaseOrder] = []
    skipped_unassigned = any(g.supplier == "未指定供应商" for g in merged.grouped_by_supplier)
    od = datetime.utcnow()
    for group in merged.grouped_by_supplier:
        if group.supplier == "未指定供应商":
            continue
        po_lines: list[schemas.PurchaseOrderLineIn] = []
        line_no = 1
        for it in group.items:
            if Decimal(it.suggested_purchase_qty) <= 0:
                continue
            mat = get_material(db, it.material_id)
            _sp = (mat.spec or "").strip()
            _dr = (mat.drawing_no or "").strip()
            spec_drawing = " / ".join([x for x in (_sp, _dr) if x]) or None
            po_lines.append(
                schemas.PurchaseOrderLineIn(
                    line_no=line_no,
                    material_id=mat.id,
                    material_code=mat.code or "",
                    material_name=mat.name or "",
                    spec_drawing=spec_drawing,
                    unit=mat.unit,
                    qty=it.suggested_purchase_qty,
                    unit_price=it.unit_price,
                    tax_rate_note=mat.tax_rate,
                    remark=None,
                )
            )
            line_no += 1
        if not po_lines:
            continue
        snap = _supplier_snapshot_for_po(db, group.supplier)
        header_remark = f"由生产计划 {merged.plan_no} 生成。{plan_remark_suffix}".strip()
        payload = schemas.PurchaseOrderCreate(
            order_date=od,
            supplier_company=snap["supplier_company"],
            supplier_tax_no=snap["supplier_tax_no"],
            supplier_bank=snap["supplier_bank"],
            supplier_account=snap["supplier_account"],
            supplier_address=snap["supplier_address"],
            supplier_phone=snap["supplier_phone"],
            supplier_contact=snap["supplier_contact"],
            delivery_address=None,
            payment_terms=None,
            delivery_terms=None,
            header_remark=header_remark[:2000] if header_remark else None,
            lines=po_lines,
        )
        created.append(create_purchase_order(db, payload))
    return created, skipped_unassigned


# -------------------------
# Integrations (Taobao) + Sales orders
# -------------------------
def get_or_create_integration_settings(db: Session) -> models.AppIntegrationSettings:
    row = db.get(models.AppIntegrationSettings, 1)
    if not row:
        row = models.AppIntegrationSettings(id=1)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def read_taobao_integration_config(db: Session) -> schemas.TaobaoIntegrationConfigRead:
    s = get_or_create_integration_settings(db)
    sess = db.scalar(select(models.TaobaoShopSession).order_by(models.TaobaoShopSession.id.desc()).limit(1))
    return schemas.TaobaoIntegrationConfigRead(
        taobao_app_key=s.taobao_app_key,
        taobao_app_secret_configured=bool(s.taobao_app_secret),
        taobao_redirect_uri=s.taobao_redirect_uri,
        taobao_default_logistics_code=s.taobao_default_logistics_code,
        taobao_authorized=sess is not None and bool(sess.access_token),
        taobao_seller_nick=sess.seller_nick if sess else None,
        taobao_token_expire_time=sess.expire_time if sess else None,
        taobao_last_increment_sync=s.taobao_last_increment_sync,
    )


def update_taobao_integration_config(db: Session, payload: schemas.TaobaoIntegrationConfigUpdate) -> models.AppIntegrationSettings:
    row = get_or_create_integration_settings(db)
    data = payload.model_dump(exclude_unset=True)
    if "taobao_app_secret" in data:
        sec = data.pop("taobao_app_secret")
        if sec:
            row.taobao_app_secret = sec
    for k, v in data.items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


def create_taobao_oauth_state(db: Session) -> str:
    import secrets

    token = secrets.token_urlsafe(24)
    exp = datetime.utcnow() + timedelta(minutes=15)
    db.add(models.IntegrationOAuthState(provider="taobao", state=token, expires_at=exp))
    db.commit()
    return token


def consume_oauth_state(db: Session, provider: str, state: str) -> bool:
    row = db.scalar(
        select(models.IntegrationOAuthState).where(
            models.IntegrationOAuthState.provider == provider,
            models.IntegrationOAuthState.state == state,
        )
    )
    if not row or row.expires_at < datetime.utcnow():
        return False
    db.delete(row)
    db.commit()
    return True


def save_taobao_oauth_token(db: Session, token_payload: dict) -> models.TaobaoShopSession:
    """写入或覆盖当前淘宝会话（单店）。"""
    access = token_payload.get("access_token") or ""
    if not access:
        raise HTTPException(status_code=400, detail="OAuth 响应缺少 access_token")
    nick = token_payload.get("taobao_user_nick") or token_payload.get("seller_nick") or ""
    uid = str(token_payload.get("taobao_user_id") or token_payload.get("user_id") or "")
    expires_in = token_payload.get("expires_in")
    exp = None
    if expires_in is not None:
        try:
            exp = datetime.utcnow() + timedelta(seconds=int(expires_in))
        except (TypeError, ValueError):
            exp = None
    refresh = token_payload.get("refresh_token")
    existing = db.scalar(select(models.TaobaoShopSession).order_by(models.TaobaoShopSession.id.desc()).limit(1))
    if existing:
        existing.seller_nick = nick
        existing.taobao_user_id = uid or existing.taobao_user_id
        existing.access_token = access
        existing.refresh_token = refresh
        existing.expire_time = exp
        db.commit()
        db.refresh(existing)
        return existing
    sess = models.TaobaoShopSession(
        seller_nick=nick,
        taobao_user_id=uid or None,
        access_token=access,
        refresh_token=refresh,
        expire_time=exp,
    )
    db.add(sess)
    db.commit()
    db.refresh(sess)
    return sess


def get_active_taobao_session(db: Session) -> models.TaobaoShopSession | None:
    return db.scalar(select(models.TaobaoShopSession).order_by(models.TaobaoShopSession.id.desc()).limit(1))


def _next_sales_order_no(db: Session) -> str:
    today = datetime.utcnow().strftime("%Y%m%d")
    prefix = f"SO{today}"
    like = f"{prefix}%"
    cnt = db.scalar(select(func.count(models.SalesOrder.id)).where(models.SalesOrder.internal_order_no.like(like))) or 0
    return f"{prefix}{int(cnt) + 1:03d}"


def _parse_taobao_dt(val) -> datetime | None:
    if val is None or val == "":
        return None
    s = str(val).strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
        try:
            return datetime.strptime(s[:26], fmt)
        except ValueError:
            continue
    return None


def _taobao_local_status(platform_status: str) -> str:
    m = {
        "WAIT_BUYER_PAY": "pending_payment",
        "WAIT_SELLER_SEND_GOODS": "pending_ship",
        "SELLER_CONSIGNED_PART": "partial_shipped",
        "WAIT_BUYER_CONFIRM_GOODS": "shipped",
        "TRADE_FINISHED": "completed",
        "TRADE_CLOSED": "closed",
        "TRADE_NO_CREATE_PAY": "pending_payment",
        "WAIT_BUYER_CONFIRM_GOODS_ACOUNT": "shipped",
    }
    return m.get(platform_status or "", "other")


def _extract_taobao_sub_orders(trade: dict) -> list[dict]:
    o = trade.get("orders")
    if not o:
        return []
    if isinstance(o, dict):
        inner = o.get("order")
        if inner is None:
            return []
        return inner if isinstance(inner, list) else [inner]
    return []


def _money_decimal(v) -> Decimal:
    try:
        return money(Decimal(str(v or 0)))
    except Exception:
        return Decimal("0")


def upsert_sales_order_from_taobao_trade(db: Session, trade: dict) -> models.SalesOrder:
    tid = str(trade.get("tid") or "")
    if not tid:
        raise HTTPException(status_code=400, detail="交易缺少 tid")
    st = str(trade.get("status") or "")
    pay_time = _parse_taobao_dt(trade.get("pay_time"))
    if pay_time is None and isinstance(trade.get("payment"), str):
        pay_time = _parse_taobao_dt(trade.get("payment"))
    modified = _parse_taobao_dt(trade.get("modified")) or _parse_taobao_dt(trade.get("end_time"))
    addr_parts = [
        trade.get("receiver_state") or "",
        trade.get("receiver_city") or "",
        trade.get("receiver_district") or "",
        trade.get("receiver_address") or "",
    ]
    receiver_address = "".join(addr_parts).strip() or None
    total_fee = _money_decimal(trade.get("total_fee"))
    post_fee = _money_decimal(trade.get("post_fee"))
    buyer = trade.get("buyer_nick") or trade.get("buyer_open_uid")

    existing = db.scalar(select(models.SalesOrder).where(models.SalesOrder.platform_tid == tid))
    if not existing:
        existing = models.SalesOrder(
            internal_order_no=_next_sales_order_no(db),
            channel="taobao",
            platform_tid=tid,
        )
        db.add(existing)
        db.flush()

    existing.platform_status = st
    existing.buyer_nick = buyer
    existing.receiver_name = trade.get("receiver_name")
    existing.receiver_mobile = trade.get("receiver_mobile")
    existing.receiver_address = receiver_address
    existing.total_amount = total_fee
    existing.post_fee = post_fee
    existing.pay_time = pay_time
    existing.platform_modified = modified
    new_local = _taobao_local_status(st)
    if existing.taobao_consigned_at and st == "WAIT_SELLER_SEND_GOODS" and existing.local_status == "shipped":
        new_local = "shipped"
    existing.local_status = new_local

    db.query(models.SalesOrderLine).filter(models.SalesOrderLine.sales_order_id == existing.id).delete()
    db.flush()

    sub = _extract_taobao_sub_orders(trade)
    for od in sub:
        oid = str(od.get("oid") or od.get("sub_order_tid") or "")
        if not oid:
            oid = str(od.get("num_iid") or "") + "-" + str(len(sub))
        qty = Decimal(str(od.get("num") or od.get("quantity") or 0))
        price = _money_decimal(od.get("price"))
        line_total = _money_decimal(od.get("total_fee"))
        if line_total == 0 and qty and price:
            line_total = money(qty * price)
        outer = od.get("outer_iid") or od.get("outer_sku_id")
        pic_path = (str(od.get("pic_path") or "").strip()[:512] or None)
        db.add(
            models.SalesOrderLine(
                sales_order_id=existing.id,
                platform_oid=oid,
                num_iid=str(od.get("num_iid") or "") or None,
                sku_id=str(od.get("sku_id") or "") or None,
                outer_iid=str(outer) if outer else None,
                title=str(od.get("title") or "")[:500],
                qty=qty,
                price=price,
                line_total=line_total,
                pic_url=pic_path,
                material_id=None,
            )
        )
    db.commit()
    db.refresh(existing)
    return existing


def sales_order_to_read(db: Session, o: models.SalesOrder) -> schemas.SalesOrderRead:
    lines = []
    for ln in sorted(o.lines, key=lambda x: x.id):
        lines.append(
            schemas.SalesOrderLineRead(
                id=ln.id,
                platform_oid=ln.platform_oid,
                num_iid=ln.num_iid,
                sku_id=ln.sku_id,
                outer_iid=ln.outer_iid,
                title=ln.title,
                qty=ln.qty,
                price=ln.price,
                line_total=ln.line_total,
                pic_url=ln.pic_url,
                material_id=ln.material_id,
                product_id=ln.product_id,
            )
        )
    return schemas.SalesOrderRead(
        id=o.id,
        internal_order_no=o.internal_order_no,
        channel=o.channel,
        platform_tid=o.platform_tid,
        platform_order_no=o.platform_order_no,
        platform_status=o.platform_status,
        buyer_nick=o.buyer_nick,
        receiver_name=o.receiver_name,
        receiver_mobile=o.receiver_mobile,
        receiver_address=o.receiver_address,
        header_remark=o.header_remark,
        total_amount=o.total_amount,
        post_fee=o.post_fee,
        pay_time=o.pay_time,
        platform_modified=o.platform_modified,
        local_status=o.local_status,
        invoice_status=o.invoice_status or "none",
        invoice_no=o.invoice_no,
        invoiced_at=o.invoiced_at,
        taobao_consign_error=o.taobao_consign_error,
        taobao_consigned_at=o.taobao_consigned_at,
        taobao_out_sid=o.taobao_out_sid,
        taobao_logistics_code=o.taobao_logistics_code,
        created_at=o.created_at,
        updated_at=o.updated_at,
        lines=lines,
    )


def list_sales_orders(db: Session):
    return db.scalars(
        select(models.SalesOrder).options(selectinload(models.SalesOrder.lines)).order_by(models.SalesOrder.id.desc())
    ).all()


def get_sales_order(db: Session, order_id: int) -> models.SalesOrder:
    o = db.scalar(
        select(models.SalesOrder)
        .where(models.SalesOrder.id == order_id)
        .options(selectinload(models.SalesOrder.lines))
    )
    if not o:
        raise HTTPException(status_code=404, detail="销售订单不存在")
    return o


def _qty_decimal(v) -> Decimal:
    return Decimal(str(v)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def _material_for_manual_line(
    db: Session, ln: schemas.ManualSalesOrderLineIn
) -> tuple[models.Material | None, str, str | None]:
    mat: models.Material | None = None
    if ln.material_id is not None:
        mat = db.get(models.Material, ln.material_id)
        if not mat:
            raise HTTPException(status_code=400, detail=f"物料 id {ln.material_id} 不存在")
    elif ln.material_code and str(ln.material_code).strip():
        code = str(ln.material_code).strip()
        mat = db.scalar(select(models.Material).where(models.Material.code == code))
        if not mat:
            raise HTTPException(status_code=400, detail=f"物料编码不存在: {code}")
    title = (ln.title or "").strip()
    if mat and not title:
        title = (mat.name or "")[:500]
    if not title:
        raise HTTPException(status_code=400, detail="明细需填写品名或指定物料")
    outer = ln.outer_iid.strip()[:128] if ln.outer_iid and str(ln.outer_iid).strip() else None
    if mat and not outer:
        outer = (mat.code or "")[:128] or None
    return mat, title[:500], outer


def _resolve_manual_line_row(
    db: Session, ln: schemas.ManualSalesOrderLineIn
) -> tuple[models.Material | None, str, str | None, int | None, Decimal]:
    """手工单行：返回 material、title、outer_iid、product_id、单价。"""
    if ln.product_id is not None:
        p = db.get(models.Product, ln.product_id)
        if not p:
            raise HTTPException(status_code=400, detail="产品不存在")
        if not p.is_active:
            raise HTTPException(status_code=400, detail="产品已停用")
        title = ((ln.title or "").strip() or (p.product_name or ""))[:500]
        if not title:
            raise HTTPException(status_code=400, detail="产品缺少名称，请填写品名")
        unit_price = money(ln.price) if ln.price is not None else money(p.sale_price_with_tax)
        if ln.outer_iid and str(ln.outer_iid).strip():
            outer = str(ln.outer_iid).strip()[:128]
        else:
            outer = (p.product_code or "").strip()[:128] or None
        mat = None
        if p.linked_material_id:
            mat = db.get(models.Material, p.linked_material_id)
        return mat, title, outer, p.id, unit_price

    mat, title, outer = _material_for_manual_line(db, ln)
    if ln.price is None:
        raise HTTPException(status_code=400, detail="未选择产品时须填写单价")
    return mat, title, outer, None, money(ln.price)


def _replace_manual_order_lines(db: Session, order_id: int, lines: list[schemas.ManualSalesOrderLineIn]) -> Decimal:
    db.query(models.SalesOrderLine).filter(models.SalesOrderLine.sales_order_id == order_id).delete()
    db.flush()
    subtotal = Decimal("0")
    for i, ln in enumerate(lines, 1):
        mat, title, outer, prod_id, unit_price = _resolve_manual_line_row(db, ln)
        qty = _qty_decimal(ln.qty)
        price = unit_price
        lt = money(ln.line_total) if ln.line_total is not None else money(qty * price)
        subtotal += lt
        oid = (ln.platform_oid or str(i)).strip()[:64] or str(i)
        db.add(
            models.SalesOrderLine(
                sales_order_id=order_id,
                platform_oid=oid,
                num_iid=None,
                sku_id=None,
                outer_iid=outer,
                title=title,
                qty=qty,
                price=price,
                line_total=lt,
                pic_url=None,
                material_id=mat.id if mat else None,
                product_id=prod_id,
            )
        )
    return money(subtotal)


def create_manual_sales_order(db: Session, payload: schemas.ManualSalesOrderCreate) -> models.SalesOrder:
    internal_no = _next_sales_order_no(db)
    tid = f"m-{internal_no}"
    post_fee = money(payload.post_fee or 0)
    local_status = "pending_ship" if payload.confirm_immediately else "draft"
    plat_st = "pending_ship" if local_status == "pending_ship" else "draft"
    cust = (payload.customer_ref or "").strip()[:64] or None
    o = models.SalesOrder(
        internal_order_no=internal_no,
        channel="manual",
        platform_tid=tid,
        platform_order_no=cust,
        platform_status=plat_st,
        buyer_nick=payload.buyer_nick,
        receiver_name=payload.receiver_name,
        receiver_mobile=payload.receiver_mobile,
        receiver_address=payload.receiver_address,
        header_remark=payload.header_remark,
        post_fee=post_fee,
        pay_time=payload.pay_time,
        local_status=local_status,
        invoice_status="none",
        total_amount=Decimal("0"),
    )
    db.add(o)
    db.flush()
    subtotal = _replace_manual_order_lines(db, o.id, payload.lines)
    o.total_amount = money(subtotal + post_fee)
    db.add(o)
    db.commit()
    db.refresh(o)
    return o


def update_manual_sales_order(db: Session, order_id: int, payload: schemas.ManualSalesOrderUpdate) -> models.SalesOrder:
    o = get_sales_order(db, order_id)
    if o.channel != "manual":
        raise HTTPException(status_code=400, detail="仅手工单可编辑")
    if o.local_status != "draft":
        raise HTTPException(status_code=400, detail="仅草稿可修改明细与金额")
    data = payload.model_dump(exclude_unset=True)
    if "buyer_nick" in data:
        o.buyer_nick = data["buyer_nick"]
    if "receiver_name" in data:
        o.receiver_name = data["receiver_name"]
    if "receiver_mobile" in data:
        o.receiver_mobile = data["receiver_mobile"]
    if "receiver_address" in data:
        o.receiver_address = data["receiver_address"]
    if "header_remark" in data:
        o.header_remark = data["header_remark"]
    if "customer_ref" in data:
        v = data["customer_ref"]
        if v is None:
            o.platform_order_no = None
        else:
            o.platform_order_no = str(v).strip()[:64] or None
    if "pay_time" in data:
        o.pay_time = data["pay_time"]
    if payload.post_fee is not None:
        o.post_fee = money(payload.post_fee)
    if payload.lines is not None:
        if not payload.lines:
            raise HTTPException(status_code=400, detail="至少保留一行明细")
        subtotal = _replace_manual_order_lines(db, o.id, payload.lines)
        o.total_amount = money(subtotal + o.post_fee)
    elif payload.post_fee is not None:
        oid = o.id
        raw_sum = db.scalar(
            select(func.coalesce(func.sum(models.SalesOrderLine.line_total), 0)).where(
                models.SalesOrderLine.sales_order_id == oid
            )
        ) or Decimal("0")
        o.total_amount = money(money(raw_sum) + o.post_fee)
    db.add(o)
    db.commit()
    db.refresh(o)
    return o


def confirm_manual_sales_order(db: Session, order_id: int) -> models.SalesOrder:
    o = get_sales_order(db, order_id)
    if o.channel != "manual":
        raise HTTPException(status_code=400, detail="非手工单")
    if o.local_status != "draft":
        raise HTTPException(status_code=400, detail="当前状态不可确认（仅草稿可确认）")
    o.local_status = "pending_ship"
    o.platform_status = "pending_ship"
    db.add(o)
    db.commit()
    db.refresh(o)
    return o


def ship_manual_sales_order(db: Session, order_id: int, payload: schemas.ManualShipRequest) -> models.SalesOrder:
    o = get_sales_order(db, order_id)
    if o.channel != "manual":
        raise HTTPException(status_code=400, detail="非手工单")
    if o.local_status != "pending_ship":
        raise HTTPException(status_code=400, detail="仅「待发货」手工单可登记本地发货")
    o.taobao_out_sid = payload.tracking_number.strip()[:64]
    o.taobao_logistics_code = (payload.carrier_name or "").strip()[:64] or None
    o.taobao_consign_error = None
    o.taobao_consigned_at = datetime.utcnow()
    o.local_status = "shipped"
    o.platform_status = "shipped"
    db.add(o)
    db.commit()
    db.refresh(o)
    return o


def patch_sales_order_invoice(db: Session, order_id: int, payload: schemas.SalesOrderInvoicePatch) -> models.SalesOrder:
    o = get_sales_order(db, order_id)
    allowed = {"none", "pending", "issued", "not_required"}
    data = payload.model_dump(exclude_unset=True)
    if "invoice_status" in data and data["invoice_status"] is not None:
        st = str(data["invoice_status"]).strip()
        if st not in allowed:
            raise HTTPException(status_code=400, detail="无效的发票状态")
        o.invoice_status = st
    if "invoice_no" in data:
        o.invoice_no = (data["invoice_no"] or "").strip()[:64] or None
    if "invoiced_at" in data:
        o.invoiced_at = data["invoiced_at"]
    if o.invoice_status == "issued":
        if not (o.invoice_no or "").strip():
            raise HTTPException(status_code=400, detail="已开票状态需填写发票号码")
        if o.invoiced_at is None:
            o.invoiced_at = datetime.utcnow()
    db.add(o)
    db.commit()
    db.refresh(o)
    return o


def sync_taobao_orders_incremental(db: Session, hours_back: int = 168) -> schemas.TaobaoSyncResult:
    """增量同步淘宝已卖出订单（需已 OAuth）。hours_back 首次或游标丢失时回溯小时数，默认 7 天。"""
    cfg = get_or_create_integration_settings(db)
    if not cfg.taobao_app_key or not cfg.taobao_app_secret:
        raise HTTPException(status_code=400, detail="请先在设置中配置淘宝 App Key 与 App Secret")
    sess = get_active_taobao_session(db)
    if not sess or not sess.access_token:
        raise HTTPException(status_code=400, detail="请先在设置中完成淘宝店铺授权")
    end = datetime.utcnow()
    start = cfg.taobao_last_increment_sync
    if start is None:
        start = end - timedelta(hours=max(1, min(hours_back, 720)))
    if start >= end:
        start = end - timedelta(minutes=5)
    start_s = start.strftime("%Y-%m-%d %H:%M:%S")
    end_s = end.strftime("%Y-%m-%d %H:%M:%S")
    fields = (
        "tid,type,status,created,modified,end_time,pay_time,buyer_nick,receiver_name,receiver_mobile,"
        "receiver_state,receiver_city,receiver_district,receiver_address,total_fee,post_fee,orders"
    )
    synced = 0
    page = 1
    page_size = 40
    while True:
        try:
            raw = taobao_client.top_request(
                cfg.taobao_app_key,
                cfg.taobao_app_secret,
                "taobao.trades.sold.increment.get",
                sess.access_token,
                {
                    "start_modified": start_s,
                    "end_modified": end_s,
                    "fields": fields,
                    "page_no": page,
                    "page_size": page_size,
                },
            )
        except RuntimeError as e:
            raise HTTPException(status_code=502, detail=str(e)) from e
        trades = taobao_client.parse_increment_trades(raw)
        for tr in trades:
            tid = str(tr.get("tid") or "")
            if not tid:
                continue
            try:
                detail_raw = taobao_client.top_request(
                    cfg.taobao_app_key,
                    cfg.taobao_app_secret,
                    "taobao.trade.fullinfo.get",
                    sess.access_token,
                    {"tid": tid, "fields": fields},
                )
                full = taobao_client.parse_trade_fullinfo(detail_raw)
                if full:
                    tr = full
            except RuntimeError:
                pass
            upsert_sales_order_from_taobao_trade(db, tr)
            synced += 1
        if len(trades) < page_size:
            break
        page += 1
        if page > 100:
            break
    cfg.taobao_last_increment_sync = end
    db.add(cfg)
    db.commit()
    return schemas.TaobaoSyncResult(synced_count=synced, message=f"同步窗口 {start_s} ~ {end_s}")


def ship_sales_order_taobao_offline(db: Session, order_id: int, payload: schemas.TaobaoShipRequest) -> models.SalesOrder:
    o = get_sales_order(db, order_id)
    if o.channel != "taobao":
        raise HTTPException(status_code=400, detail="非淘宝渠道订单")
    if o.platform_status != "WAIT_SELLER_SEND_GOODS":
        raise HTTPException(
            status_code=400,
            detail=f"当前淘宝状态为 {o.platform_status}，通常需在「等待卖家发货」时才能线下发货回写",
        )
    cfg = get_or_create_integration_settings(db)
    sess = get_active_taobao_session(db)
    if not cfg.taobao_app_key or not cfg.taobao_app_secret or not sess or not sess.access_token:
        raise HTTPException(status_code=400, detail="淘宝未配置或未授权")
    code = payload.company_code.strip()
    out_sid = payload.out_sid.strip()
    try:
        taobao_client.top_request(
            cfg.taobao_app_key,
            cfg.taobao_app_secret,
            "taobao.logistics.offline.send",
            sess.access_token,
            {"tid": o.platform_tid, "company_code": code, "out_sid": out_sid},
        )
    except RuntimeError as e:
        o.taobao_consign_error = str(e)[:500]
        db.add(o)
        db.commit()
        raise HTTPException(status_code=502, detail=str(e)) from e
    o.taobao_consign_error = None
    o.taobao_consigned_at = datetime.utcnow()
    o.taobao_out_sid = out_sid
    o.taobao_logistics_code = code
    o.local_status = "shipped"
    db.add(o)
    db.commit()
    db.refresh(o)
    return o


def read_woocommerce_integration_config(db: Session) -> schemas.WooCommerceIntegrationConfigRead:
    s = get_or_create_integration_settings(db)
    return schemas.WooCommerceIntegrationConfigRead(
        woocommerce_site_url=s.woocommerce_site_url,
        woocommerce_consumer_key_configured=bool(s.woocommerce_consumer_key),
        woocommerce_consumer_secret_configured=bool(s.woocommerce_consumer_secret),
        woocommerce_last_sync=s.woocommerce_last_sync,
    )


def update_woocommerce_integration_config(db: Session, payload: schemas.WooCommerceIntegrationConfigUpdate) -> models.AppIntegrationSettings:
    row = get_or_create_integration_settings(db)
    data = payload.model_dump(exclude_unset=True)
    if "woocommerce_consumer_key" in data:
        ck = data.pop("woocommerce_consumer_key")
        if ck:
            row.woocommerce_consumer_key = ck.strip()
    if "woocommerce_consumer_secret" in data:
        cs = data.pop("woocommerce_consumer_secret")
        if cs:
            row.woocommerce_consumer_secret = cs.strip()
    for k, v in data.items():
        if v is not None and isinstance(v, str):
            v = v.strip()
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


def _woo_tid(oid: int | str) -> str:
    return f"woo-{int(oid)}"


def _woo_parse_id(platform_tid: str) -> int:
    if platform_tid.startswith("woo-"):
        return int(platform_tid[4:])
    return int(platform_tid)


def _parse_iso_dt(val) -> datetime | None:
    if not val:
        return None
    s = str(val).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt
    except ValueError:
        pass
    try:
        return datetime.strptime(str(val)[:19], "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return _parse_taobao_dt(val)


def _woo_local_status(st: str) -> str:
    m = {
        "pending": "pending_payment",
        "processing": "pending_ship",
        "on-hold": "pending_payment",
        "completed": "completed",
        "cancelled": "closed",
        "refunded": "closed",
        "failed": "closed",
    }
    return m.get((st or "").lower(), "other")


def upsert_sales_order_from_woocommerce(db: Session, order: dict) -> models.SalesOrder:
    oid = order.get("id")
    if oid is None:
        raise HTTPException(status_code=400, detail="WooCommerce 订单缺少 id")
    tid_key = _woo_tid(oid)
    st = str(order.get("status") or "")
    billing = order.get("billing") or {}
    shipping = order.get("shipping") or {}
    buyer = billing.get("email") or f'{billing.get("first_name", "")} {billing.get("last_name", "")}'.strip() or None
    addr_parts = [
        shipping.get("country") or "",
        shipping.get("state") or "",
        shipping.get("city") or "",
        shipping.get("postcode") or "",
        shipping.get("address_1") or "",
        shipping.get("address_2") or "",
    ]
    receiver_address = " ".join(x for x in addr_parts if x).strip() or None
    receiver_name = f'{shipping.get("first_name", "")} {shipping.get("last_name", "")}'.strip() or None
    receiver_mobile = shipping.get("phone") or billing.get("phone")
    total = _money_decimal(order.get("total"))
    post_fee = _money_decimal(order.get("shipping_total"))
    pay_time = _parse_iso_dt(order.get("date_paid")) or _parse_iso_dt(order.get("date_paid_gmt"))
    modified = _parse_iso_dt(order.get("date_modified")) or _parse_iso_dt(order.get("date_modified_gmt"))
    order_no = str(order.get("number") or oid)

    existing = db.scalar(select(models.SalesOrder).where(models.SalesOrder.platform_tid == tid_key))
    if not existing:
        existing = models.SalesOrder(
            internal_order_no=_next_sales_order_no(db),
            channel="woocommerce",
            platform_tid=tid_key,
        )
        db.add(existing)
        db.flush()

    existing.platform_order_no = order_no
    existing.platform_status = st
    existing.buyer_nick = buyer
    existing.receiver_name = receiver_name
    existing.receiver_mobile = receiver_mobile
    existing.receiver_address = receiver_address
    existing.total_amount = total
    existing.post_fee = post_fee
    existing.pay_time = pay_time
    existing.platform_modified = modified
    new_local = _woo_local_status(st)
    if existing.taobao_consigned_at and st in ("processing", "on-hold") and existing.local_status in ("completed", "shipped"):
        new_local = existing.local_status
    existing.local_status = new_local

    db.query(models.SalesOrderLine).filter(models.SalesOrderLine.sales_order_id == existing.id).delete()
    db.flush()

    items = order.get("line_items") or []
    if isinstance(items, dict):
        inner = items.get("line_item") or items.get("item")
        items = inner if isinstance(inner, list) else ([inner] if inner else [])
    for it in items:
        if not isinstance(it, dict):
            continue
        lid = it.get("id")
        platform_oid = str(lid) if lid is not None else str(it.get("product_id", "")) + "-x"
        qty = Decimal(str(it.get("quantity") or 0))
        price = _money_decimal(it.get("price"))
        line_total = _money_decimal(it.get("total"))
        if line_total == 0 and qty and price:
            line_total = money(qty * price)
        sku = it.get("sku")
        pid = it.get("product_id")
        vid = it.get("variation_id")
        db.add(
            models.SalesOrderLine(
                sales_order_id=existing.id,
                platform_oid=platform_oid,
                num_iid=str(pid) if pid else None,
                sku_id=str(vid) if vid else None,
                outer_iid=str(sku).strip()[:128] if sku else None,
                title=str(it.get("name") or "")[:500],
                qty=qty,
                price=price,
                line_total=line_total,
                pic_url=None,
                material_id=None,
            )
        )
    db.commit()
    db.refresh(existing)
    return existing


def sync_woocommerce_orders(db: Session, hours_back: int = 720) -> schemas.WooCommerceSyncResult:
    cfg = get_or_create_integration_settings(db)
    if not (cfg.woocommerce_site_url or "").strip():
        raise HTTPException(status_code=400, detail="请先在设置中填写 WooCommerce 站点 URL")
    if not cfg.woocommerce_consumer_key or not cfg.woocommerce_consumer_secret:
        raise HTTPException(status_code=400, detail="请先在设置中配置 WooCommerce Consumer Key / Secret")
    site = cfg.woocommerce_site_url.strip().rstrip("/")
    key = cfg.woocommerce_consumer_key.strip()
    secret = cfg.woocommerce_consumer_secret.strip()
    end = datetime.utcnow()
    start = cfg.woocommerce_last_sync
    if start is None:
        start = end - timedelta(hours=max(1, min(hours_back, 2160)))
    after_iso = start.strftime("%Y-%m-%dT%H:%M:%S")
    statuses = ["processing", "on-hold", "pending", "completed", "cancelled", "refunded", "failed"]
    synced = 0
    page = 1
    per_page = 50
    max_modified = start
    while page <= 100:
        try:
            batch = woocommerce_client.list_orders(
                site,
                key,
                secret,
                after_iso=after_iso,
                statuses=statuses,
                page=page,
                per_page=per_page,
            )
        except RuntimeError as e:
            raise HTTPException(status_code=502, detail=str(e)) from e
        if not batch:
            break
        for order in batch:
            upsert_sales_order_from_woocommerce(db, order)
            synced += 1
            dm = _parse_iso_dt(order.get("date_modified")) or _parse_iso_dt(order.get("date_modified_gmt"))
            if dm and dm > max_modified:
                max_modified = dm
        if len(batch) < per_page:
            break
        page += 1
    cfg.woocommerce_last_sync = max_modified if max_modified > start else end
    db.add(cfg)
    db.commit()
    return schemas.WooCommerceSyncResult(
        synced_count=synced,
        message=f"modified_after={after_iso}，共处理 {synced} 条",
    )


def ship_sales_order_woocommerce(db: Session, order_id: int, payload: schemas.WooCommerceShipRequest) -> models.SalesOrder:
    o = get_sales_order(db, order_id)
    if o.channel != "woocommerce":
        raise HTTPException(status_code=400, detail="非 WooCommerce 订单")
    if o.platform_status not in ("processing", "on-hold"):
        raise HTTPException(
            status_code=400,
            detail=f"当前 WooCommerce 状态为 {o.platform_status}，一般仅在 processing / on-hold 时执行发货更新",
        )
    cfg = get_or_create_integration_settings(db)
    if not (cfg.woocommerce_site_url or "").strip() or not cfg.woocommerce_consumer_key or not cfg.woocommerce_consumer_secret:
        raise HTTPException(status_code=400, detail="WooCommerce 未配置完整")
    site = cfg.woocommerce_site_url.strip().rstrip("/")
    wid = _woo_parse_id(o.platform_tid)
    meta = [
        {"key": "_tracking_number", "value": payload.tracking_number.strip()},
    ]
    if payload.carrier_name and payload.carrier_name.strip():
        meta.append({"key": "_tracking_company", "value": payload.carrier_name.strip()})
    body: dict = {"meta_data": meta}
    if payload.set_status_completed:
        body["status"] = "completed"
    try:
        woocommerce_client.update_order(
            site,
            cfg.woocommerce_consumer_key.strip(),
            cfg.woocommerce_consumer_secret.strip(),
            wid,
            body,
        )
    except RuntimeError as e:
        o.taobao_consign_error = str(e)[:500]
        db.add(o)
        db.commit()
        raise HTTPException(status_code=502, detail=str(e)) from e
    o.taobao_consign_error = None
    o.taobao_consigned_at = datetime.utcnow()
    o.taobao_out_sid = payload.tracking_number.strip()
    o.taobao_logistics_code = (payload.carrier_name or "").strip() or None
    if payload.set_status_completed:
        o.local_status = "completed"
        o.platform_status = "completed"
    else:
        o.local_status = "shipped"
    db.add(o)
    db.commit()
    db.refresh(o)
    return o


# -------------------------
# Company profile
# -------------------------
def get_company_profile(db: Session) -> models.CompanyProfile:
    row = db.get(models.CompanyProfile, 1)
    if not row:
        row = models.CompanyProfile(id=1, company_name="")
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def update_company_profile(db: Session, payload: schemas.CompanyProfileUpdate) -> models.CompanyProfile:
    row = get_company_profile(db)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


# -------------------------
# Purchase orders (手工)
# -------------------------
def _next_po_no(db: Session) -> str:
    today = datetime.utcnow().strftime("%Y%m%d")
    prefix = f"PO{today}"
    like = f"{prefix}%"
    cnt = db.scalar(select(func.count(models.PurchaseOrder.id)).where(models.PurchaseOrder.order_no.like(like))) or 0
    return f"{prefix}{int(cnt) + 1:03d}"


def list_purchase_orders(db: Session):
    return db.scalars(
        select(models.PurchaseOrder)
        .options(
            selectinload(models.PurchaseOrder.lines),
            selectinload(models.PurchaseOrder.invoices),
        )
        .order_by(models.PurchaseOrder.id.desc())
    ).all()


def get_purchase_order(db: Session, po_id: int) -> models.PurchaseOrder:
    po = db.scalar(
        select(models.PurchaseOrder)
        .where(models.PurchaseOrder.id == po_id)
        .options(
            selectinload(models.PurchaseOrder.lines),
            selectinload(models.PurchaseOrder.invoices),
        )
    )
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return po


ALLOWED_PO_INVOICE_EXT = frozenset({".pdf", ".png", ".jpg", ".jpeg", ".ofd"})


def create_purchase_order(db: Session, payload: schemas.PurchaseOrderCreate) -> models.PurchaseOrder:
    od = payload.order_date or datetime.utcnow()
    order_no = _next_po_no(db)
    total = Decimal("0")
    line_rows: list[dict] = []
    for ln in payload.lines:
        amt = money(Decimal(ln.qty) * Decimal(ln.unit_price))
        total += amt
        line_rows.append(
            {
                "line_no": ln.line_no,
                "material_id": ln.material_id,
                "material_code": ln.material_code,
                "material_name": ln.material_name,
                "spec_drawing": ln.spec_drawing,
                "unit": ln.unit,
                "qty": ln.qty,
                "received_qty": Decimal("0"),
                "unit_price": money(ln.unit_price),
                "line_amount": amt,
                "tax_rate_note": ln.tax_rate_note,
                "remark": ln.remark,
            }
        )
    po = models.PurchaseOrder(
        order_no=order_no,
        status="draft",
        payment_status="unpaid",
        order_date=od,
        supplier_company=payload.supplier_company,
        supplier_tax_no=payload.supplier_tax_no,
        supplier_bank=payload.supplier_bank,
        supplier_account=payload.supplier_account,
        supplier_address=payload.supplier_address,
        supplier_phone=payload.supplier_phone,
        supplier_contact=payload.supplier_contact,
        delivery_address=payload.delivery_address,
        payment_terms=payload.payment_terms,
        delivery_terms=payload.delivery_terms,
        header_remark=payload.header_remark,
        total_with_tax=money(total),
    )
    db.add(po)
    db.flush()
    for row in line_rows:
        db.add(models.PurchaseOrderLine(purchase_order_id=po.id, **row))
    db.commit()
    db.refresh(po)
    return po


def _line_dict_from_update_item(ln) -> dict:
    if isinstance(ln, dict):
        return ln
    return ln.model_dump()


def update_purchase_order(db: Session, po_id: int, payload: schemas.PurchaseOrderUpdate) -> models.PurchaseOrder:
    po = get_purchase_order(db, po_id)
    data = payload.model_dump(exclude_unset=True)
    lines = data.pop("lines", None)
    for k, v in data.items():
        setattr(po, k, v)
    if lines is not None:
        existing_by_id = {ln.id: ln for ln in list(po.lines)}
        ids_kept: set[int] = set()
        total = Decimal("0")
        for raw in lines:
            d = _line_dict_from_update_item(raw)
            eid = d.get("id")
            line_no = d["line_no"]
            material_code = d.get("material_code") or ""
            material_name = d.get("material_name") or ""
            spec_drawing = d.get("spec_drawing")
            unit = d.get("unit")
            qty = d["qty"]
            unit_price = d.get("unit_price", 0)
            tax_rate_note = d.get("tax_rate_note")
            remark = d.get("remark")
            mid = d.get("material_id")
            amt = money(Decimal(qty) * Decimal(unit_price))
            total += amt

            if eid and eid in existing_by_id:
                row = existing_by_id[eid]
                ids_kept.add(eid)
                rq = Decimal(str(row.received_qty or 0))
                if Decimal(str(qty)) < rq:
                    raise HTTPException(
                        status_code=400,
                        detail=f"行 {line_no} 订购数量不能小于已入库数量 {rq}",
                    )
                row.line_no = line_no
                row.material_id = mid
                row.material_code = material_code
                row.material_name = material_name
                row.spec_drawing = spec_drawing
                row.unit = unit
                row.qty = qty
                row.unit_price = money(unit_price)
                row.line_amount = amt
                row.tax_rate_note = tax_rate_note
                row.remark = remark
            else:
                db.add(
                    models.PurchaseOrderLine(
                        purchase_order_id=po.id,
                        line_no=line_no,
                        material_id=mid,
                        material_code=material_code,
                        material_name=material_name,
                        spec_drawing=spec_drawing,
                        unit=unit,
                        qty=qty,
                        received_qty=Decimal("0"),
                        unit_price=money(unit_price),
                        line_amount=amt,
                        tax_rate_note=tax_rate_note,
                        remark=remark,
                    )
                )
        for oid, orow in existing_by_id.items():
            if oid not in ids_kept:
                if Decimal(str(orow.received_qty or 0)) > 0:
                    raise HTTPException(
                        status_code=400,
                        detail="不能删除已有入库记录的明细行；可减少订购数量或保留该行。",
                    )
                db.delete(orow)
        po.total_with_tax = money(total)
    db.commit()
    db.refresh(po)
    return po


def _sync_po_receipt_status(po: models.PurchaseOrder) -> None:
    if not po.lines or po.status in ("closed", "draft"):
        return
    all_full = all(Decimal(str(l.received_qty or 0)) >= Decimal(str(l.qty)) for l in po.lines)
    any_r = any(Decimal(str(l.received_qty or 0)) > 0 for l in po.lines)
    if all_full:
        po.status = "received"
    elif any_r and po.status in ("sent", "confirmed", "partial_received"):
        po.status = "partial_received"


def receive_purchase_order(db: Session, po_id: int, payload: schemas.PurchaseOrderReceiveIn) -> models.PurchaseOrder:
    po = get_purchase_order(db, po_id)
    if po.status == "draft":
        raise HTTPException(
            status_code=400,
            detail="草稿订单请先改为「已发送」或「已确认」后再入库。下单不扣库存，入库后写入库存流水。",
        )
    if po.status == "closed":
        raise HTTPException(status_code=400, detail="订单已关闭，无法继续入库")

    for it in payload.lines:
        line: models.PurchaseOrderLine | None = None
        if it.line_id is not None:
            line = db.get(models.PurchaseOrderLine, it.line_id)
            if not line or line.purchase_order_id != po.id:
                raise HTTPException(status_code=400, detail="无效明细行")
        else:
            line = next((x for x in po.lines if x.line_no == it.line_no), None)
            if not line:
                raise HTTPException(status_code=400, detail=f"找不到行号 {it.line_no}")

        recv = Decimal(str(it.qty))
        open_q = Decimal(str(line.qty)) - Decimal(str(line.received_qty or 0))
        if recv <= 0:
            raise HTTPException(status_code=400, detail="本次入库数量须大于 0")
        if recv > open_q:
            raise HTTPException(
                status_code=400,
                detail=f"行 {line.line_no} 超出可入库数量（尚可入 {open_q}）",
            )

        mid = line.material_id
        if mid is None:
            code = (line.material_code or "").strip()
            if not code:
                raise HTTPException(status_code=400, detail=f"行 {line.line_no} 缺少料号，无法入库")
            found = db.scalar(select(models.Material.id).where(models.Material.code == code))
            if not found:
                raise HTTPException(
                    status_code=400,
                    detail=f"行 {line.line_no} 料号「{code}」在物料主数据中不存在",
                )
            mid = int(found)
            line.material_id = mid

        remark = f"采购入库 {po.order_no} 行{line.line_no}"
        _apply_stock_transaction(
            db,
            schemas.StockTransactionCreate(
                material_id=int(line.material_id),
                transaction_type=models.TransactionType.in_,
                qty=recv,
                unit_price=money(line.unit_price),
                reference_type="purchase_order",
                reference_no=po.order_no,
                remark=remark,
            ),
        )
        line.received_qty = Decimal(str(line.received_qty or 0)) + recv

    _sync_po_receipt_status(po)
    db.commit()
    db.refresh(po)
    return po


def add_purchase_invoice(
    db: Session,
    po_id: int,
    invoice_no: str,
    file_content: bytes,
    original_filename: str,
    amount_with_tax: Decimal | None,
    remark: str | None,
    upload_root: Path,
) -> models.PurchaseInvoice:
    po = get_purchase_order(db, po_id)
    if not file_content:
        raise HTTPException(status_code=400, detail="必须上传发票电子版文件")
    ext = Path(original_filename or "").suffix.lower()
    if ext not in ALLOWED_PO_INVOICE_EXT:
        raise HTTPException(
            status_code=400,
            detail="发票附件仅支持 PDF、PNG、JPG、JPEG、OFD",
        )
    sub = upload_root / "uploads" / "purchase_invoices" / str(po_id)
    sub.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}{ext}"
    path_abs = sub / stored_name
    path_abs.write_bytes(file_content)
    rel = f"uploads/purchase_invoices/{po_id}/{stored_name}"
    inv = models.PurchaseInvoice(
        purchase_order_id=po.id,
        invoice_no=invoice_no.strip(),
        amount_with_tax=money(amount_with_tax) if amount_with_tax is not None else None,
        file_path=rel,
        original_filename=(original_filename or stored_name)[:250],
        remark=remark,
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return inv


def delete_purchase_invoice(db: Session, po_id: int, invoice_id: int, upload_root: Path) -> None:
    inv = db.get(models.PurchaseInvoice, invoice_id)
    if not inv or inv.purchase_order_id != po_id:
        raise HTTPException(status_code=404, detail="发票不存在")
    p = (upload_root / inv.file_path).resolve()
    db.delete(inv)
    db.commit()
    if p.is_file():
        try:
            p.unlink()
        except OSError:
            pass


def purchase_invoice_file_path(upload_root: Path, inv: models.PurchaseInvoice) -> Path:
    return (upload_root / inv.file_path).resolve()


def _current_bom_for_product_code(db: Session, product_code: str) -> models.BOMHeader | None:
    return db.scalar(
        select(models.BOMHeader).where(
            models.BOMHeader.product_code == product_code,
            models.BOMHeader.is_current.is_(True),
        )
    )


def _calc_product_cost(db: Session, product: models.Product) -> tuple[Decimal, int | None]:
    if product.product_type == models.ProductType.purchased:
        if not product.linked_material_id:
            return Decimal("0"), None
        m = db.get(models.Material, product.linked_material_id)
        if not m:
            return Decimal("0"), None
        return money(m.unit_price), None
    bom = _current_bom_for_product_code(db, product.product_code)
    if not bom:
        return Decimal("0"), None
    total = db.scalar(
        select(func.coalesce(func.sum(models.BOMItem.total_price), 0)).where(models.BOMItem.bom_header_id == bom.id)
    ) or Decimal("0")
    return money(total), bom.id


def _product_to_read(db: Session, product: models.Product) -> schemas.ProductRead:
    cost, bom_id = _calc_product_cost(db, product)
    return schemas.ProductRead(
        id=product.id,
        product_code=product.product_code,
        product_name=product.product_name,
        product_type=product.product_type,
        product_category=product.product_category,
        model_no=product.model_no,
        spec_drawing=product.spec_drawing,
        sale_price_with_tax=product.sale_price_with_tax,
        current_stock=product.current_stock,
        safety_stock=product.safety_stock,
        remark=product.remark,
        linked_material_id=product.linked_material_id,
        is_active=product.is_active,
        cost=cost,
        current_bom_id=bom_id,
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


def list_products(db: Session, product_type: models.ProductType | None = None) -> list[schemas.ProductRead]:
    q = select(models.Product).order_by(models.Product.id.desc())
    if product_type:
        q = q.where(models.Product.product_type == product_type)
    rows = db.scalars(q).all()
    return [_product_to_read(db, r) for r in rows]


def get_product(db: Session, product_id: int) -> schemas.ProductRead:
    row = db.get(models.Product, product_id)
    if not row:
        raise HTTPException(status_code=404, detail="Product not found")
    return _product_to_read(db, row)


def create_product(db: Session, payload: schemas.ProductCreate) -> schemas.ProductRead:
    data = payload.model_dump()
    product_category = data.get("product_category")
    if product_category:
        exists_pc = db.scalar(
            select(models.SystemOption).where(
                models.SystemOption.option_type == "product_category",
                models.SystemOption.name == product_category,
                models.SystemOption.is_active.is_(True),
            )
        )
        if not exists_pc:
            raise HTTPException(status_code=400, detail="Invalid product category")
    data["product_code"] = (data.get("product_code") or "").strip()
    if not data["product_code"]:
        raise HTTPException(status_code=400, detail="Product code is required")
    exists = db.scalar(select(models.Product).where(models.Product.product_code == data["product_code"]))
    if exists:
        raise HTTPException(status_code=400, detail="Product code already exists")
    if data.get("product_type") == models.ProductType.purchased and data.get("linked_material_id"):
        m = get_material(db, int(data["linked_material_id"]))
        data["spec_drawing"] = data.get("spec_drawing") or " / ".join(
            [x for x in ((m.spec or "").strip(), (m.drawing_no or "").strip()) if x]
        )
    row = models.Product(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _product_to_read(db, row)


def update_product(db: Session, product_id: int, payload: schemas.ProductUpdate) -> schemas.ProductRead:
    row = db.get(models.Product, product_id)
    if not row:
        raise HTTPException(status_code=404, detail="Product not found")
    data = payload.model_dump(exclude_unset=True)
    old_code = row.product_code
    if "product_code" in data:
        new_code = (data.get("product_code") or "").strip()
        if not new_code:
            raise HTTPException(status_code=400, detail="Product code is required")
        exists = db.scalar(
            select(models.Product).where(models.Product.product_code == new_code, models.Product.id != product_id)
        )
        if exists:
            raise HTTPException(status_code=400, detail="Product code already exists")
        data["product_code"] = new_code
    product_category = data.get("product_category")
    if product_category:
        exists_pc = db.scalar(
            select(models.SystemOption).where(
                models.SystemOption.option_type == "product_category",
                models.SystemOption.name == product_category,
                models.SystemOption.is_active.is_(True),
            )
        )
        if not exists_pc:
            raise HTTPException(status_code=400, detail="Invalid product category")
    if data.get("product_type") == models.ProductType.purchased and data.get("linked_material_id"):
        m = get_material(db, int(data["linked_material_id"]))
        if not data.get("spec_drawing"):
            data["spec_drawing"] = " / ".join([x for x in ((m.spec or "").strip(), (m.drawing_no or "").strip()) if x])
    for k, v in data.items():
        setattr(row, k, v)
    if "product_code" in data and data["product_code"] != old_code:
        db.query(models.BOMHeader).filter(models.BOMHeader.product_code == old_code).update(
            {"product_code": data["product_code"]}
        )
    db.commit()
    db.refresh(row)
    return _product_to_read(db, row)


def delete_product(db: Session, product_id: int):
    row = db.get(models.Product, product_id)
    if not row:
        raise HTTPException(status_code=404, detail="Product not found")
    ref_bom = db.scalar(select(func.count(models.BOMHeader.id)).where(models.BOMHeader.product_code == row.product_code)) or 0
    if ref_bom:
        raise HTTPException(status_code=400, detail="该产品已有BOM记录，无法删除")
    db.delete(row)
    db.commit()
    return {"message": "Product deleted"}


def _next_inquiry_no(db: Session) -> str:
    today = datetime.utcnow().strftime("%Y%m%d")
    prefix = f"INQ{today}"
    like = f"{prefix}%"
    cnt = db.scalar(select(func.count(models.Inquiry.id)).where(models.Inquiry.inquiry_no.like(like))) or 0
    return f"{prefix}{int(cnt) + 1:03d}"


def _inquiry_material_spec_drawing(m: models.Material) -> str | None:
    a = (m.spec or "").strip()
    b = (m.drawing_no or "").strip()
    s = " / ".join([x for x in (a, b) if x])
    return s or None


def _inquiry_line_read(db: Session, ln: models.InquiryLine) -> schemas.InquiryLineRead:
    m = get_material(db, ln.material_id)
    return schemas.InquiryLineRead(
        id=ln.id,
        inquiry_id=ln.inquiry_id,
        line_no=ln.line_no,
        material_id=ln.material_id,
        qty=ln.qty,
        remark=ln.remark,
        material_code=m.code,
        material_name=m.name,
        spec_drawing=_inquiry_material_spec_drawing(m),
        material_name_attr=m.material_name_attr,
        grade_attr=m.grade_attr,
        unit=m.unit,
        unit_price=None,
        line_total=None,
    )


def _inq_to_read(db: Session, inq: models.Inquiry) -> schemas.InquiryRead:
    lines = [_inquiry_line_read(db, ln) for ln in sorted(inq.lines, key=lambda x: x.line_no)]
    return schemas.InquiryRead(
        id=inq.id,
        inquiry_no=inq.inquiry_no,
        status=inq.status,
        inquiry_date=inq.inquiry_date,
        valid_until=inq.valid_until,
        supplier_company=inq.supplier_company,
        supplier_contact=inq.supplier_contact,
        supplier_phone=inq.supplier_phone,
        delivery_address=inq.delivery_address,
        payment_terms=inq.payment_terms,
        header_remark=inq.header_remark,
        total_estimated=Decimal("0"),
        created_at=inq.created_at,
        updated_at=inq.updated_at,
        lines=lines,
    )


def list_inquiries(db: Session) -> list[schemas.InquiryRead]:
    rows = db.scalars(select(models.Inquiry).order_by(models.Inquiry.id.desc())).all()
    return [_inq_to_read(db, r) for r in rows]


def get_inquiry(db: Session, inquiry_id: int) -> schemas.InquiryRead:
    row = db.get(models.Inquiry, inquiry_id)
    if not row:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    return _inq_to_read(db, row)


def create_inquiry(db: Session, payload: schemas.InquiryCreate) -> schemas.InquiryRead:
    if not payload.lines:
        raise HTTPException(status_code=400, detail="至少一行询价明细")
    od = payload.inquiry_date or datetime.utcnow()
    inq = models.Inquiry(
        inquiry_no=_next_inquiry_no(db),
        status="draft",
        inquiry_date=od,
        valid_until=payload.valid_until,
        supplier_company=payload.supplier_company,
        supplier_contact=payload.supplier_contact,
        supplier_phone=payload.supplier_phone,
        delivery_address=payload.delivery_address,
        payment_terms=payload.payment_terms,
        header_remark=payload.header_remark,
        total_estimated=Decimal("0"),
    )
    db.add(inq)
    db.flush()
    for ln in payload.lines:
        get_material(db, ln.material_id)
        db.add(
            models.InquiryLine(
                inquiry_id=inq.id,
                line_no=ln.line_no,
                material_id=ln.material_id,
                qty=ln.qty,
                remark=ln.remark,
            )
        )
    inq.total_estimated = Decimal("0")
    db.commit()
    db.refresh(inq)
    return _inq_to_read(db, inq)


def update_inquiry(db: Session, inquiry_id: int, payload: schemas.InquiryUpdate) -> schemas.InquiryRead:
    row = db.get(models.Inquiry, inquiry_id)
    if not row:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    data = payload.model_dump(exclude_unset=True)
    lines = data.pop("lines", None)
    for k, v in data.items():
        setattr(row, k, v)
    if lines is not None:
        for old in list(row.lines):
            db.delete(old)
        db.flush()
        for ln in lines:
            ln = ln if isinstance(ln, dict) else ln.model_dump()
            mid = int(ln["material_id"])
            get_material(db, mid)
            db.add(
                models.InquiryLine(
                    inquiry_id=row.id,
                    line_no=int(ln["line_no"]),
                    material_id=mid,
                    qty=ln["qty"],
                    remark=ln.get("remark"),
                )
            )
        row.total_estimated = Decimal("0")
    db.commit()
    db.refresh(row)
    return _inq_to_read(db, row)
