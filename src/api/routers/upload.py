from fastapi import APIRouter, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse, FileResponse
import os
import uuid
import shutil
from pathlib import Path

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
VAULT_DIR = BASE_DIR / "private_archive"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(VAULT_DIR, exist_ok=True)


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
        # Save copy to private archive (for dataset building, secure from web access)
        try:
            shutil.copy2(str(filepath), str(VAULT_DIR / filename))
        except Exception as archive_err:
            print(f"Warning: Could not archive file: {archive_err}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    return JSONResponse(
        status_code=201,
        content={
            "image_id": image_id,
            "filename": filename,
            "preview_url": f"/api/images/{filename}",
        },
    )
