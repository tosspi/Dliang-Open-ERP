from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter(prefix="/company-profile", tags=["company-profile"])


@router.get("", response_model=schemas.CompanyProfileRead)
def read_company_profile(db: Session = Depends(get_db)):
    return crud.get_company_profile(db)


@router.put("", response_model=schemas.CompanyProfileRead)
def save_company_profile(payload: schemas.CompanyProfileUpdate, db: Session = Depends(get_db)):
    return crud.update_company_profile(db, payload)
