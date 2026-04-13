from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter(prefix="/production-plans", tags=["production-plans"])


@router.get("", response_model=list[schemas.ProductionPlanRead])
def list_plans(db: Session = Depends(get_db)):
    rows = crud.list_production_plans(db)
    return [crud.production_plan_to_read(db, p) for p in rows]


@router.post("", response_model=schemas.ProductionPlanRead)
def create_plan(payload: schemas.ProductionPlanCreate, db: Session = Depends(get_db)):
    plan = crud.create_production_plan(db, payload)
    return crud.production_plan_to_read(db, plan)


@router.get("/{plan_id}", response_model=schemas.ProductionPlanRead)
def get_plan(plan_id: int, db: Session = Depends(get_db)):
    plan = crud.get_production_plan(db, plan_id)
    return crud.production_plan_to_read(db, plan)


@router.put("/{plan_id}", response_model=schemas.ProductionPlanRead)
def update_plan(plan_id: int, payload: schemas.ProductionPlanUpdate, db: Session = Depends(get_db)):
    plan = crud.update_production_plan(db, plan_id, payload)
    return crud.production_plan_to_read(db, plan)


@router.post("/{plan_id}/shortage", response_model=schemas.PlanShortageResponse)
def plan_shortage(plan_id: int, db: Session = Depends(get_db)):
    return crud.merge_shortage_for_production_plan(db, plan_id)


@router.post("/{plan_id}/draft-purchase-orders", response_model=schemas.DraftPOsFromPlanResponse)
def plan_draft_purchase_orders(plan_id: int, db: Session = Depends(get_db)):
    from app.routes.purchase_orders import _po_to_read

    merged = crud.merge_shortage_for_production_plan(db, plan_id)
    pos, skipped = crud.create_draft_purchase_orders_from_plan_shortage(db, merged, "")
    msg = None
    if not pos:
        msg = "未生成任何草稿订单（可能全部为「未指定供应商」或建议采购量为 0）。"
    elif skipped:
        msg = "已跳过「未指定供应商」的物料，请在物料主数据中维护默认供应商后单独采购。"
    return schemas.DraftPOsFromPlanResponse(
        created_orders=[_po_to_read(p, db=db) for p in pos],
        skipped_unassigned=skipped,
        message=msg,
    )
