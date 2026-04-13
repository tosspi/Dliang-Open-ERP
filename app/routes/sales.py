from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter(prefix="/sales", tags=["sales"])


@router.get("/orders", response_model=list[schemas.SalesOrderRead])
def list_sales_orders(db: Session = Depends(get_db)):
    rows = crud.list_sales_orders(db)
    return [crud.sales_order_to_read(db, o) for o in rows]


@router.get("/orders/{order_id}", response_model=schemas.SalesOrderRead)
def get_sales_order(order_id: int, db: Session = Depends(get_db)):
    o = crud.get_sales_order(db, order_id)
    return crud.sales_order_to_read(db, o)


@router.post("/orders/sync-taobao", response_model=schemas.TaobaoSyncResult)
def sync_taobao_orders(hours_back: int = Query(168, ge=1, le=720), db: Session = Depends(get_db)):
    return crud.sync_taobao_orders_incremental(db, hours_back=hours_back)


@router.post("/orders/{order_id}/taobao-ship", response_model=schemas.SalesOrderRead)
def taobao_ship_order(order_id: int, payload: schemas.TaobaoShipRequest, db: Session = Depends(get_db)):
    o = crud.ship_sales_order_taobao_offline(db, order_id, payload)
    return crud.sales_order_to_read(db, o)


@router.post("/orders/sync-woocommerce", response_model=schemas.WooCommerceSyncResult)
def sync_woocommerce_orders(hours_back: int = Query(720, ge=1, le=2160), db: Session = Depends(get_db)):
    return crud.sync_woocommerce_orders(db, hours_back=hours_back)


@router.post("/orders/{order_id}/woocommerce-ship", response_model=schemas.SalesOrderRead)
def woocommerce_ship_order(order_id: int, payload: schemas.WooCommerceShipRequest, db: Session = Depends(get_db)):
    o = crud.ship_sales_order_woocommerce(db, order_id, payload)
    return crud.sales_order_to_read(db, o)


@router.post("/orders/manual", response_model=schemas.SalesOrderRead)
def create_manual_sales_order(payload: schemas.ManualSalesOrderCreate, db: Session = Depends(get_db)):
    o = crud.create_manual_sales_order(db, payload)
    return crud.sales_order_to_read(db, o)


@router.put("/orders/{order_id}/manual", response_model=schemas.SalesOrderRead)
def update_manual_sales_order(order_id: int, payload: schemas.ManualSalesOrderUpdate, db: Session = Depends(get_db)):
    o = crud.update_manual_sales_order(db, order_id, payload)
    return crud.sales_order_to_read(db, o)


@router.post("/orders/{order_id}/manual/confirm", response_model=schemas.SalesOrderRead)
def confirm_manual_sales_order(order_id: int, db: Session = Depends(get_db)):
    o = crud.confirm_manual_sales_order(db, order_id)
    return crud.sales_order_to_read(db, o)


@router.post("/orders/{order_id}/manual/ship", response_model=schemas.SalesOrderRead)
def ship_manual_sales_order(order_id: int, payload: schemas.ManualShipRequest, db: Session = Depends(get_db)):
    o = crud.ship_manual_sales_order(db, order_id, payload)
    return crud.sales_order_to_read(db, o)


@router.patch("/orders/{order_id}/invoice", response_model=schemas.SalesOrderRead)
def patch_sales_order_invoice(order_id: int, payload: schemas.SalesOrderInvoicePatch, db: Session = Depends(get_db)):
    o = crud.patch_sales_order_invoice(db, order_id, payload)
    return crud.sales_order_to_read(db, o)
