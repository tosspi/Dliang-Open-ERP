from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter(prefix="/system-options", tags=["system-options"])


@router.get("", response_model=list[schemas.SystemOptionRead])
def get_system_options(option_type: str | None = Query(default=None), db: Session = Depends(get_db)):
    return crud.list_system_options(db, option_type)


@router.post("", response_model=schemas.SystemOptionRead)
def create_system_option(payload: schemas.SystemOptionCreate, db: Session = Depends(get_db)):
    return crud.create_system_option(db, payload)


@router.get("/{option_id}", response_model=schemas.SystemOptionRead)
def get_system_option(option_id: int, db: Session = Depends(get_db)):
    return crud.get_system_option(db, option_id)


@router.put("/{option_id}", response_model=schemas.SystemOptionRead)
def update_system_option(option_id: int, payload: schemas.SystemOptionUpdate, db: Session = Depends(get_db)):
    return crud.update_system_option(db, option_id, payload)


@router.delete("/{option_id}", response_model=schemas.SystemOptionRead)
def delete_system_option(option_id: int, db: Session = Depends(get_db)):
    return crud.soft_delete_system_option(db, option_id)


@router.delete("/{option_id}/hard-delete")
def hard_delete_system_option(option_id: int, db: Session = Depends(get_db)):
    return crud.hard_delete_system_option(db, option_id)
