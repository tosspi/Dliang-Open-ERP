from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter(prefix="/procurement", tags=["procurement"])


@router.post("/shortage-calc", response_model=schemas.ShortageCalcResponse)
def shortage_calc(payload: schemas.ShortageCalcRequest, db: Session = Depends(get_db)):
    return crud.calc_shortage(db, payload)
