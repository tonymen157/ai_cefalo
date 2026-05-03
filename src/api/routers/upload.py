from fastapi import APIRouter, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse, FileResponse
import os
import uuid
import shutil
import time
from pathlib import Path

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
VAULT_DIR = BASE_DIR / "private_archive"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(VAULT_DIR, exist_ok=True)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Tiempo máximo de retención: 1 hora (3600 segundos)
MAX_FILE_AGE_SECONDS = 3600


def cleanup_old_uploads():
    """Elimina archivos de más de 1 hora en UPLOAD_DIR y VAULT_DIR."""
    current_time = time.time()
    cleaned = 0
    for directory in [UPLOAD_DIR, VAULT_DIR]:
        if not directory.exists():
            continue
        for filepath in directory.iterdir():
            if not filepath.is_file():
                continue
            try:
                file_age = current_time - filepath.stat().st_mtime
                if file_age > MAX_FILE_AGE_SECONDS:
                    filepath.unlink()
                    cleaned += 1
            except Exception as e:
                print(f"Warning: Could not delete {filepath}: {e}")
    if cleaned > 0:
        print(f"Cleaned {cleaned} old files (>{MAX_FILE_AGE_SECONDS}s)")


@router.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    # Limpiar archivos antiguos antes de procesar nueva subida
    cleanup_old_uploads()

    if file.content_type not in ("image/jpeg", "image/png", "image/jpg"):
        raise HTTPException(status_code=400, detail="Only JPG/PNG images are allowed")

    # Validar tamaño del archivo antes de leerlo completo en memoria
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="El archivo excede el límite de 10MB"
        )

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
