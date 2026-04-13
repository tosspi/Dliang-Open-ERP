import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.database import BASE_DIR, get_db

router = APIRouter(tags=["revisions"])

UPLOAD_ROOT = Path(BASE_DIR)

ALLOWED_PDF_EXT = {".pdf"}
ALLOWED_MODEL_EXT = {
    ".step",
    ".stp",
    ".iges",
    ".igs",
    ".dwg",
    ".dxf",
    ".zip",
    ".prt",
    ".sldprt",
    ".x_t",
    ".x_b",
    ".stl",
    ".3dm",
}


@router.get("/revisions/flat", response_model=list[schemas.RevisionListItem])
def list_revisions_flat(
    material_code: str | None = Query(None, description="物料编码，模糊"),
    material_name: str | None = Query(None, description="物料名称，模糊"),
    category: str | None = Query(None, description="物料分类，精确"),
    revision: str | None = Query(None, description="版本号，模糊"),
    status: str | None = Query(None, description="draft / released / obsolete"),
    current_only: bool = Query(False, description="仅当前生效版本"),
    material_id: int | None = Query(None, description="限定某一物料（如从物料页跳入）"),
    db: Session = Depends(get_db),
):
    return crud.list_nonstandard_revisions_flat(
        db,
        material_code=material_code,
        material_name=material_name,
        category=category,
        revision=revision,
        status=status,
        current_only=current_only,
        material_id=material_id,
    )


@router.get("/materials/{material_id}/revisions", response_model=list[schemas.RevisionRead])
def get_revisions(material_id: int, db: Session = Depends(get_db)):
    return crud.list_revisions(db, material_id)


@router.post("/materials/{material_id}/revisions", response_model=schemas.RevisionRead)
def create_revision(material_id: int, payload: schemas.RevisionCreate, db: Session = Depends(get_db)):
    return crud.create_revision(db, material_id, payload)


@router.put("/revisions/{revision_id}", response_model=schemas.RevisionRead)
def update_revision(revision_id: int, payload: schemas.RevisionUpdate, db: Session = Depends(get_db)):
    return crud.update_revision(db, revision_id, payload)


@router.post("/revisions/{revision_id}/set-current", response_model=schemas.RevisionRead)
def set_current_revision(revision_id: int, db: Session = Depends(get_db)):
    return crud.set_current_revision(db, revision_id)


def _revision_upload_allowed(material: models.Material) -> None:
    if material.part_type not in (models.PartType.custom, models.PartType.assembly):
        raise HTTPException(status_code=400, detail="仅自制件/装配件版本可上传图纸")


def _unlink_stored(rel_path: str | None) -> None:
    if not rel_path:
        return
    p = UPLOAD_ROOT / rel_path
    if p.is_file():
        try:
            p.unlink()
        except OSError:
            pass


@router.post("/revisions/{revision_id}/upload-drawing", response_model=schemas.RevisionRead)
async def upload_revision_drawing(
    revision_id: int,
    slot: str = Form("pdf", description="pdf 或 model"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    rev = db.get(models.PartRevision, revision_id)
    if not rev:
        raise HTTPException(status_code=404, detail="版本记录不存在")
    material = crud.get_material(db, rev.material_id)
    _revision_upload_allowed(material)

    slot_l = (slot or "pdf").strip().lower()
    if slot_l not in ("pdf", "model"):
        raise HTTPException(status_code=400, detail="slot 须为 pdf 或 model")

    raw_name = file.filename or "file"
    ext = Path(raw_name).suffix.lower()
    if not ext:
        raise HTTPException(status_code=400, detail="文件需带扩展名")
    if slot_l == "pdf":
        if ext not in ALLOWED_PDF_EXT:
            raise HTTPException(status_code=400, detail="PDF 图纸仅支持 .pdf")
        field = "file_path_pdf"
    else:
        if ext not in ALLOWED_MODEL_EXT:
            raise HTTPException(
                status_code=400,
                detail=f"模型文件扩展名不支持（允许: {', '.join(sorted(ALLOWED_MODEL_EXT))}）",
            )
        field = "file_path_model"

    stored = f"{uuid.uuid4().hex}{ext}"
    rel_dir = f"uploads/revision_drawings/{revision_id}"
    full_dir = UPLOAD_ROOT / rel_dir
    full_dir.mkdir(parents=True, exist_ok=True)
    rel_path = f"{rel_dir}/{stored}"
    full_path = UPLOAD_ROOT / rel_path

    old_rel = getattr(rev, field)
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="空文件")
    full_path.write_bytes(content)
    _unlink_stored(old_rel)
    setattr(rev, field, rel_path)
    db.add(rev)
    db.commit()
    db.refresh(rev)
    return schemas.RevisionRead.model_validate(rev)


@router.get("/revisions/{revision_id}/drawing-file")
def download_revision_drawing(
    revision_id: int,
    slot: str = Query("pdf", description="pdf 或 model"),
    db: Session = Depends(get_db),
):
    rev = db.get(models.PartRevision, revision_id)
    if not rev:
        raise HTTPException(status_code=404, detail="版本记录不存在")
    slot_l = (slot or "pdf").strip().lower()
    if slot_l not in ("pdf", "model"):
        raise HTTPException(status_code=400, detail="slot 须为 pdf 或 model")
    rel = rev.file_path_pdf if slot_l == "pdf" else rev.file_path_model
    if not rel:
        raise HTTPException(status_code=404, detail="该槽位未上传文件")
    path = UPLOAD_ROOT / rel
    if not path.is_file():
        raise HTTPException(status_code=404, detail="文件已丢失")
    suffix = path.suffix.lower() or ".bin"
    download_name = f"revision_{revision_id}_{slot_l}{suffix}"
    media = "application/pdf" if suffix == ".pdf" else "application/octet-stream"
    return FileResponse(str(path), filename=download_name, media_type=media)
