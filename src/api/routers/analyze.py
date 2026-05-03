from src.core.config import MIN_PIXEL_SIZE_MM, MAX_PIXEL_SIZE_MM
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.api.database import get_db, SessionLocal
from src.api.models import Job
from src.api.services.landmark_detector import detect_landmarks
from src.api.services.image_processor import get_image_path
from src.analysis.geometry import CephalometricAnalysis
from pathlib import Path
import uuid
import json
import cv2
import numpy as np
import asyncio

router = APIRouter()


def run_inference(job_id: str, image_id: str, calibration_mmpp: float):
    """Run actual model inference in a worker thread (DB session created internally)."""
    db = SessionLocal()
    try:
        # Get image path
        image_path = get_image_path(image_id)
        if not image_path or not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_id}")

        # Load image in original color for visualization
        # Read image as bytes then decode to guarantee 3 channels (IMREAD_COLOR)
        with open(image_path, "rb") as img_f:
            img_bytes = img_f.read()
        nparr = np.frombuffer(img_bytes, np.uint8)
        img_color = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img_color is None:
            raise ValueError(f"Could not read image: {image_path}")

        # shape[:2] is safe: (H, W, C)[:2] -> (H, W)
        orig_h, orig_w = img_color.shape[:2]

        # Load grayscale for inference
        img_gray = cv2.cvtColor(img_color, cv2.COLOR_BGR2GRAY)
        landmarks, confidences = detect_landmarks(img_gray, orig_w=orig_w, orig_h=orig_h)

        # --- AUDITORÍA ANATÓMICA (Sanity Checks) ---
        system_warnings = []
        try:
            # Regla de Oro 1: El Nasion (frente) debe estar arriba del Menton (barbilla)
            if landmarks[4][1] >= landmarks[3][1]:
                confidences[4] = 0.0
                confidences[3] = 0.0
                system_warnings.append("Inconsistencia: Nasion no está arriba de Menton")

            # Regla de Oro 2: La Sella Turca debe estar arriba del punto Articular
            if landmarks[10][1] >= landmarks[11][1]:
                confidences[10] = 0.0
                confidences[11] = 0.0
                system_warnings.append("Inconsistencia: Sella no está arriba de Articular")

            # Regla de Oro 3: El Nasion [4] debe estar arriba del punto Subespinal (A-point) [0]
            if landmarks[4][1] >= landmarks[0][1]:
                confidences[4] = 0.0
                confidences[0] = 0.0
                system_warnings.append("Inconsistencia: Nasion no está arriba de A-point")

        except (IndexError, TypeError):
            pass

        # Draw landmarks on image (same style as predict.py)
        colors = [
            (0, 0, 255),      # Red
            (0, 255, 0),      # Green
            (255, 0, 0),      # Blue
            (0, 255, 255),    # Yellow
            (255, 0, 255),    # Magenta
            (255, 128, 0),    # Orange
        ]

        from src.core.landmarks import LANDMARK_NAMES
        for i, (x, y) in enumerate(landmarks.tolist()):
            x_int, y_int = int(round(x)), int(round(y))
            color = colors[i % len(colors)]

            # Filled circle (radius 4)
            cv2.circle(img_color, (x_int, y_int), 4, color, -1)
            # White border (radius 6)
            cv2.circle(img_color, (x_int, y_int), 6, (255, 255, 255), 1)

            # Label
            label = LANDMARK_NAMES[i] if i < len(LANDMARK_NAMES) else f"{i}"
            cv2.putText(
                img_color,
                label,
                (x_int + 8, y_int - 8),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                1,
                cv2.LINE_AA,
            )

        # Save processed image as pred_{image_id}.jpg in data/uploads/
        upload_dir = Path("data/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)
        pred_filename = f"pred_{image_id}.jpg"
        pred_path = upload_dir / pred_filename
        cv2.imwrite(str(pred_path), img_color)

        # Update job with results
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = "completed"
            job.progress = 100.0
            job.landmarks = json.dumps(landmarks.tolist())
            job.confidences = json.dumps(confidences.tolist())
            job.system_warnings = json.dumps(system_warnings)
            job.pred_image_path = str(pred_path)

            # Ejecutar motor Fase 2 y guardar análisis completo
            try:
                analisis = CephalometricAnalysis(
                    coords=landmarks,
                    nombre_imagen=image_id,
                    escala_mm=calibration_mmpp if calibration_mmpp is not None and calibration_mmpp > 0 else None,
                )
                full_analysis = analisis.reporte_json()
                job.analysis_results = json.dumps(full_analysis)
            except Exception as analysis_err:
                print(f"Warning: Could not compute analysis: {analysis_err}")

            db.commit()
    except Exception as e:
        # Update job with error
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = "failed"
            job.error = str(e)
            db.commit()
    finally:
        db.close()


@router.post("/analyze")
async def start_analysis(
    data: dict,
    db: Session = Depends(get_db)
):
    """Start landmark detection job.

    Expected payload:
    - image_id: identifier of the image to analyze
    - calibration_mmpp: optional pixel size in mm/pixel (if not provided, auto-detect via CSV)
    """
    image_id = data.get("image_id")
    if not image_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="image_id is required"
        )

    # calibration_mmpp can be provided directly, auto-detected from CSV, or fallback to None
    calibration_mmpp = data.get("calibration_mmpp")
    calibration_source = data.get("calibration_source", None)
    auto_detected = False

    if calibration_mmpp is None:
        # Auto-detect from cephalogram_machine_mappings.csv (recommended)
        from src.api.routers.calibrate import _get_pixel_size_from_csv
        calibration_mmpp = _get_pixel_size_from_csv(str(image_id))
        if calibration_mmpp and calibration_mmpp > 0:
            auto_detected = True
            calibration_source = "auto_from_csv"
        else:
            calibration_mmpp = None

    # Guard de seguridad: validar calibración clínica ANTES de lanzar inferencia
    if calibration_mmpp is None or calibration_mmpp == 0 or calibration_mmpp < MIN_PIXEL_SIZE_MM or calibration_mmpp > MAX_PIXEL_SIZE_MM:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Calibración clínica inválida o ausente. Debe calibrar la imagen primero."
        )

    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        image_id=image_id,
        calibration_mmpp=float(calibration_mmpp) if calibration_mmpp is not None else None,
        status="processing",
        progress=0.0,
    )
    db.add(job)
    db.commit()

    # Launch inference in worker thread (offloads synchronous CPU-bound work from event loop)
    await asyncio.to_thread(
        run_inference, job_id, image_id, float(calibration_mmpp) if calibration_mmpp is not None else None
    )

    return {
        "job_id": job_id,
        "status": "processing",
        "calibration_mmpp": calibration_mmpp,
        "calibration_source": calibration_source,
        "auto_detected": auto_detected,
    }



@router.get("/jobs/{job_id}")
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """Return job status and progress."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    response = {
        "job_id": job.id,
        "status": job.status,
        "progress": job.progress,
    }
    if job.landmarks:
        response["landmarks"] = json.loads(job.landmarks)
    if job.analysis_results:
        response["analysis_results"] = json.loads(job.analysis_results)
    if job.error:
        response["error"] = job.error
    if job.pred_image_path:
        response["pred_image_path"] = job.pred_image_path
    if job.confidences:
        response["confidences"] = json.loads(job.confidences)
    if job.system_warnings:
        response["system_warnings"] = json.loads(job.system_warnings)

    return response
