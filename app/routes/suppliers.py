from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


@router.get("", response_model=list[schemas.SupplierRead])
def get_suppliers(db: Session = Depends(get_db)):
    return crud.list_suppliers(db)


@router.post("", response_model=schemas.SupplierRead)
def create_supplier(payload: schemas.SupplierCreate, db: Session = Depends(get_db)):
    return crud.create_supplier(db, payload)


@router.get("/{supplier_id}", response_model=schemas.SupplierRead)
def get_supplier(supplier_id: int, db: Session = Depends(get_db)):
    return crud.get_supplier(db, supplier_id)


@router.put("/{supplier_id}", response_model=schemas.SupplierRead)
def update_supplier(supplier_id: int, payload: schemas.SupplierUpdate, db: Session = Depends(get_db)):
    return crud.update_supplier(db, supplier_id, payload)


@router.delete("/{supplier_id}", response_model=schemas.SupplierRead)
def delete_supplier(supplier_id: int, db: Session = Depends(get_db)):
    return crud.soft_delete_supplier(db, supplier_id)
