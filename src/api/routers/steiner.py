from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.api.database import get_db
from src.api.models import Job
from src.analysis.geometry import CephalometricAnalysis
import numpy as np
import json
from fastapi.responses import FileResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from io import BytesIO
from pathlib import Path

router = APIRouter()


@router.post("/steiner-analysis")
def steiner_analysis(data: dict):
    """Calculate Steiner analysis angles from landmarks using CephalometricAnalysis.

    Body parameters:
    - landmarks: (29, 2) array in original image coordinates (pixels)
    - calibration_mmpp: pixel size in mm/pixel for metric calculation (optional)

    Returns:
        dict with SNA, SNB, ANB, skeletal_class and evaluation vs normatives.
    """
    try:
        landmarks = data.get("landmarks")
        if not landmarks:
            raise ValueError("landmarks required")

        pixel_size = data.get("calibration_mmpp")

        lm_array = np.array(landmarks, dtype=np.float32)

        if lm_array.shape != (29, 2):
            raise ValueError(f"Expected landmarks shape (29, 2), got {lm_array.shape}")

        # Usa el módulo central de análisis cefalométrico
        analisis = CephalometricAnalysis(
            coords=lm_array,
            nombre_imagen="api_request",
            escala_mm=float(pixel_size) if pixel_size else None,
        )

        result = analisis.reporte_json()
        return result

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


def _generate_pdf_buffer(landmarks, steiner_results, image_id):
    """Genera PDF en memoria."""
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "AI-Cefalo Cephalometric Report")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 70, f"Image: {image_id}")
    c.setFont("Helvetica", 50)
    c.setFillColor(HexColor("#E5E7EB", alpha=0.15))
    c.saveState()
    c.translate(width / 2, height / 2)
    c.rotate(45)
    c.drawCentredString(0, 0, "PREVIEW")
    c.restoreState()
    y = height - 140
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Steiner Analysis")
    y -= 30
    c.setFont("Helvetica", 10)
    if isinstance(steiner_results, dict):
        angulos = steiner_results.get("angulos", {})
        for angle_name, data in angulos.items():
            if isinstance(data, dict) and "value" in data:
                text = f"{angle_name}: {data['value']:.2f}°"
                c.drawString(70, y, text)
                y -= 20
        classification = steiner_results.get("clase_esqueletica", "N/A")
        y -= 10
        c.setFont("Helvetica-Bold", 11)
        c.drawString(50, y, f"Classification: {classification}")
    y -= 40
    c.setFont("Helvetica", 8)
    c.setFillColor(HexColor("#6B7280"))
    c.drawString(50, y, "Disclaimer: AI-Cefalo es herramienta educativa. No reemplaza criterio clinico profesional.")
    c.save()
    buffer.seek(0)
    return buffer

@router.get("/download-report/{job_id}")
def download_report(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    if not job.landmarks:
        raise HTTPException(status_code=400, detail="Sin landmarks disponibles")
    landmarks = json.loads(job.landmarks)
    lm_array = np.array(landmarks, dtype=np.float32)
    pixel_size = float(job.calibration_mmpp) if job.calibration_mmpp and job.calibration_mmpp > 0 else None
    analisis = CephalometricAnalysis(coords=lm_array, nombre_imagen=job.image_id, escala_mm=pixel_size)
    result = analisis.reporte_json()
    pdf_buffer = _generate_pdf_buffer(landmarks, result, job.image_id)
    return FileResponse(pdf_buffer, media_type="application/pdf", filename=f"reporte_{job.image_id}.pdf")

@router.get("/preview-report/{job_id}")
def preview_report(job_id: str, db: Session = Depends(get_db)):
    return download_report(job_id, db)