from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter(tags=["bom"])


@router.get("/boms", response_model=list[schemas.BOMHeaderRead])
def get_boms(db: Session = Depends(get_db)):
    return crud.list_boms(db)


@router.post("/boms", response_model=schemas.BOMHeaderRead)
def create_bom(payload: schemas.BOMHeaderCreate, db: Session = Depends(get_db)):
    return crud.create_bom(db, payload)


@router.get("/boms/{bom_id}", response_model=schemas.BOMDetailRead)
def get_bom(bom_id: int, db: Session = Depends(get_db)):
    return crud.get_bom_detail(db, bom_id)


@router.put("/boms/{bom_id}", response_model=schemas.BOMHeaderRead)
def update_bom(bom_id: int, payload: schemas.BOMHeaderUpdate, db: Session = Depends(get_db)):
    return crud.update_bom(db, bom_id, payload)


@router.delete("/boms/{bom_id}")
def delete_bom(
    bom_id: int,
    password: str = Body(..., embed=True),
    db: Session = Depends(get_db),
):
    if password != "649238":
        raise HTTPException(status_code=403, detail="删除密码错误")
    return crud.delete_bom(db, bom_id)


@router.post("/boms/{bom_id}/set-current", response_model=schemas.BOMHeaderRead)
def set_current_bom(bom_id: int, db: Session = Depends(get_db)):
    return crud.set_current_bom(db, bom_id)


@router.get("/boms/{bom_id}/items", response_model=list[schemas.BOMItemRead])
def get_bom_items(bom_id: int, db: Session = Depends(get_db)):
    return crud.list_bom_items(db, bom_id)


@router.post("/boms/{bom_id}/items", response_model=schemas.BOMItemRead)
def create_bom_item(bom_id: int, payload: schemas.BOMItemCreate, db: Session = Depends(get_db)):
    return crud.create_bom_item(db, bom_id, payload)


@router.put("/bom-items/{item_id}", response_model=schemas.BOMItemRead)
def update_bom_item(item_id: int, payload: schemas.BOMItemUpdate, db: Session = Depends(get_db)):
    return crud.update_bom_item(db, item_id, payload)


@router.delete("/bom-items/{item_id}")
def delete_bom_item(item_id: int, db: Session = Depends(get_db)):
    return crud.delete_bom_item(db, item_id)
