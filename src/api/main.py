from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi import HTTPException
from src.api.database import init_db
import os
import sys
from pathlib import Path

# Añadir path para evitar ModuleNotFoundError
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

app = FastAPI(
    title="AI-Cefalo",
    description="Automatic cephalometric landmark detection system",
    version="0.2.0",
)

# CORS - Configuración para desarrollo y producción
from os import getenv
ALLOWED_ORIGINS = getenv("ALLOWED_ORIGINS", "")
if ALLOWED_ORIGINS:
    ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS.split(",") if origin.strip()]
else:
    ALLOWED_ORIGINS = ["http://127.0.0.1:3000", "http://localhost:3000",
                     "http://127.0.0.1:5173", "http://localhost:5173"]
print(f"[CORS] Allowed origins: {ALLOWED_ORIGINS}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "PUT", "DELETE"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Routers
from src.api.routers.upload import router as upload_router
from src.api.routers.calibrate import router as calibrate_router
from src.api.routers.analyze import router as analyze_router
from src.api.routers.steiner import router as steiner_router
from src.api.routers.credit import router as credit_router
from src.api.routers.admin import router as admin_router
from src.api.routers.images import router as images_router

app.include_router(upload_router, prefix="/api")
app.include_router(calibrate_router, prefix="/api/calibrate")
app.include_router(analyze_router, prefix="/api")
app.include_router(steiner_router, prefix="/api")
app.include_router(credit_router, prefix="/api")
app.include_router(admin_router, prefix="/api/admin")
app.include_router(images_router, prefix="/api")

# Inicializar BD
init_db()


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
