from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from pathlib import Path
import os

router = APIRouter()

UPLOAD_DIR = Path("data/uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.get("/images/{filename}")
def get_image(filename: str):
    """Serve images from uploads dir only (secure: no path traversal)."""

    # Security: prevent path traversal attacks
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    filepath = UPLOAD_DIR / filename
    if not filepath.exists() or not filepath.is_file():
        raise HTTPException(status_code=404, detail="Image not found")

    return FileResponse(str(filepath), media_type="image/jpeg")
