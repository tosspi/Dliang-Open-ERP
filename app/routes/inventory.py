from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/transactions", response_model=list[schemas.StockTransactionRead])
def get_transactions(db: Session = Depends(get_db)):
    return crud.list_transactions(db)


@router.post("/transactions", response_model=schemas.StockTransactionRead)
def create_transaction(payload: schemas.StockTransactionCreate, db: Session = Depends(get_db)):
    return crud.create_transaction(db, payload)


@router.get("/materials/{material_id}/transactions", response_model=list[schemas.StockTransactionRead])
def get_transactions_by_material(material_id: int, db: Session = Depends(get_db)):
    return crud.list_transactions_by_material(db, material_id)
