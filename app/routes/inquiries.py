from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter(prefix="/inquiries", tags=["inquiries"])


@router.get("", response_model=list[schemas.InquiryRead])
def list_inquiries(db: Session = Depends(get_db)):
    return crud.list_inquiries(db)


@router.post("", response_model=schemas.InquiryRead)
def create_inquiry(payload: schemas.InquiryCreate, db: Session = Depends(get_db)):
    return crud.create_inquiry(db, payload)


@router.get("/{inquiry_id}", response_model=schemas.InquiryRead)
def get_inquiry(inquiry_id: int, db: Session = Depends(get_db)):
    return crud.get_inquiry(db, inquiry_id)


@router.put("/{inquiry_id}", response_model=schemas.InquiryRead)
def update_inquiry(inquiry_id: int, payload: schemas.InquiryUpdate, db: Session = Depends(get_db)):
    return crud.update_inquiry(db, inquiry_id, payload)
