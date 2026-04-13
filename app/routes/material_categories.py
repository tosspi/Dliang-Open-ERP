from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter(prefix="/material-categories", tags=["material-categories"])


@router.get("", response_model=list[schemas.MaterialCategoryRead])
def get_material_categories(db: Session = Depends(get_db)):
    return crud.list_material_categories(db)


@router.post("", response_model=schemas.MaterialCategoryRead)
def create_material_category(payload: schemas.MaterialCategoryCreate, db: Session = Depends(get_db)):
    return crud.create_material_category(db, payload)


@router.get("/{category_id}", response_model=schemas.MaterialCategoryRead)
def get_material_category(category_id: int, db: Session = Depends(get_db)):
    return crud.get_material_category(db, category_id)


@router.put("/{category_id}", response_model=schemas.MaterialCategoryRead)
def update_material_category(category_id: int, payload: schemas.MaterialCategoryUpdate, db: Session = Depends(get_db)):
    return crud.update_material_category(db, category_id, payload)


@router.delete("/{category_id}", response_model=schemas.MaterialCategoryRead)
def delete_material_category(category_id: int, db: Session = Depends(get_db)):
    return crud.soft_delete_material_category(db, category_id)


@router.delete("/{category_id}/hard-delete")
def hard_delete_material_category(category_id: int, db: Session = Depends(get_db)):
    return crud.hard_delete_material_category(db, category_id)
