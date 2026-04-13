from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter(prefix="/materials", tags=["materials"])


@router.get("", response_model=list[schemas.MaterialRead])
def get_materials(db: Session = Depends(get_db)):
    return crud.list_materials(db)


@router.post("", response_model=schemas.MaterialRead)
def create_material(payload: schemas.MaterialCreate, db: Session = Depends(get_db)):
    return crud.create_material(db, payload)


@router.get("/{material_id}", response_model=schemas.MaterialRead)
def get_material(material_id: int, db: Session = Depends(get_db)):
    return crud.get_material(db, material_id)


@router.put("/{material_id}", response_model=schemas.MaterialRead)
def update_material(material_id: int, payload: schemas.MaterialUpdate, db: Session = Depends(get_db)):
    return crud.update_material(db, material_id, payload)


@router.delete("/{material_id}", response_model=schemas.MaterialRead)
def delete_material(material_id: int, db: Session = Depends(get_db)):
    return crud.soft_delete_material(db, material_id)


@router.delete("/{material_id}/hard-delete")
def hard_delete_material(material_id: int, db: Session = Depends(get_db)):
    return crud.hard_delete_material(db, material_id)
