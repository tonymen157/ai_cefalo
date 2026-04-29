from fastapi import APIRouter, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse, FileResponse
import os
import uuid
from pathlib import Path

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.get("/preview/{image_id}")
def preview_image(image_id: str):
    if not UPLOAD_DIR.exists():
        raise HTTPException(status_code=404, detail="Uploads directory not found")
    for f in os.listdir(UPLOAD_DIR):
        if f.startswith(image_id):
            filepath = UPLOAD_DIR / f
            return FileResponse(str(filepath), media_type="image/jpeg")
    raise HTTPException(status_code=404, detail="Image not found")

@router.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    if file.content_type not in ("image/jpeg", "image/png", "image/jpg"):
        raise HTTPException(status_code=400, detail="Only JPG/PNG images are allowed")
    image_id = str(uuid.uuid4())
    ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    filename = f"{image_id}.{ext}"
    filepath = UPLOAD_DIR / filename
    try:
        content = await file.read()
        with open(filepath, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    return JSONResponse(
        status_code=201,
        content={
            "image_id": image_id,
            "filename": filename,
            "preview_url": f"/api/preview/{image_id}",
        },
    )