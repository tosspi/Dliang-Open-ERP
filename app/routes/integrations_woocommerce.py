from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter(prefix="/integrations/woocommerce", tags=["integrations-woocommerce"])


@router.get("/config", response_model=schemas.WooCommerceIntegrationConfigRead)
def get_woocommerce_config(db: Session = Depends(get_db)):
    return crud.read_woocommerce_integration_config(db)


@router.put("/config", response_model=schemas.WooCommerceIntegrationConfigRead)
def put_woocommerce_config(payload: schemas.WooCommerceIntegrationConfigUpdate, db: Session = Depends(get_db)):
    crud.update_woocommerce_integration_config(db, payload)
    return crud.read_woocommerce_integration_config(db)
