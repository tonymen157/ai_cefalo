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

                # --- AUDITORIA ANATOMICA (Penalizacion Z-Score Ideal) ---
        system_warnings = []
        try:
            import math
            import statistics

            # ESTADISTICAS ADAPTATIVAS (sin hardcoding)
            all_y = [landmarks[i][1] for i in range(29)]
            all_x = [landmarks[i][0] for i in range(29)]
            mean_y = statistics.mean(all_y)
            mean_x = statistics.mean(all_x)
            std_y = statistics.stdev(all_y) if len(all_y) > 1 else 1.0
            std_x = statistics.stdev(all_x) if len(all_x) > 1 else 1.0
            diag = math.sqrt((max(all_x)-min(all_x))**2 + (max(all_y)-min(all_y))**2)

            def z_penalty(violation_px, std_dev):
                """Penalizacion desactivada: retorna 1.0 siempre.
                Las confianzas se mantienen INTACTAS (crudas del TTA).
                """
                return 1.0

            def dist(i, j):
                return math.sqrt((landmarks[i][0]-landmarks[j][0])**2 + (landmarks[i][1]-landmarks[j][1])**2)

            # [0] A-point: DEBE estar ABAJO de Nasion [4]
            v = landmarks[0][1] - landmarks[4][1]
            if v > 0:
                f = z_penalty(v, std_y)
                confidences[0] *= f
                system_warnings.append(f"A-point {v:.1f}px abajo de Nasion ({f:.0%})")

            # [1] ANS: DEBE estar entre Nasion [4] y A-point [0]
            y_ans = landmarks[1][1]
            if y_ans > landmarks[4][1]:
                v = y_ans - landmarks[4][1]
                f = z_penalty(v, std_y)
                confidences[1] *= f
                system_warnings.append(f"ANS {v:.1f}px arriba de Nasion ({f:.0%})")
            elif y_ans < landmarks[0][1]:
                v = landmarks[0][1] - y_ans
                f = z_penalty(v, std_y)
                confidences[1] *= f
                system_warnings.append(f"ANS {v:.1f}px abajo de A-point ({f:.0%})")

            # [2] B-point: DEBE estar ABAJO de A-point [0]
            v = landmarks[2][1] - landmarks[0][1]
            if v > 0:
                f = z_penalty(v, std_y)
                confidences[2] *= f
                system_warnings.append(f"B-point {v:.1f}px abajo de A-point ({f:.0%})")

            # [3] Menton (Me): DEBE estar ABAJO de Nasion [4] y B-point [2]
            v1 = landmarks[3][1] - landmarks[4][1]
            if v1 > 0:
                f = z_penalty(v1, std_y)
                confidences[3] *= f
                system_warnings.append(f"Menton {v1:.1f}px arriba de Nasion ({f:.0%})")
            v2 = landmarks[3][1] - landmarks[2][1]
            if v2 > 0:
                f = z_penalty(v2, std_y)
                confidences[3] *= f
                system_warnings.append(f"Menton {v2:.1f}px arriba de B-point ({f:.0%})")

            # [4] Nasion (N): DEBE ser el mas arriba (menor Y)
            max_y_others = max(landmarks[i][1] for i in range(29) if i != 4)
            v = landmarks[4][1] - max_y_others
            if v > 0:
                f = z_penalty(v, std_y * 1.1)
                confidences[4] *= f
                system_warnings.append(f"Nasion {v:.1f}px NO es el mas arriba ({f:.0%})")

            # [5] Orbitale: cerca de Nasion [4] (misma altura)
            v = abs(landmarks[5][1] - landmarks[4][1])
            if v > std_y * 0.5:
                f = z_penalty(v - std_y * 0.5, std_y)
                confidences[5] *= f
                system_warnings.append(f"Orbitale {v:.1f}px de Nasion ({f:.0%})")

            # [6] Pogonion: cerca de B-point [2] (misma altura)
            v = abs(landmarks[6][1] - landmarks[2][1])
            if v > std_y * 0.5:
                f = z_penalty(v - std_y * 0.5, std_y)
                confidences[6] *= f
                system_warnings.append(f"Pogonion {v:.1f}px de B-point ({f:.0%})")

            # [7] PNS: ABAJO de ANS [1] y ARRIBA de Menton [3]
            if landmarks[7][1] < landmarks[1][1]:
                v = landmarks[1][1] - landmarks[7][1]
                f = z_penalty(v, std_y)
                confidences[7] *= f
                system_warnings.append(f"PNS {v:.1f}px arriba de ANS ({f:.0%})")
            if landmarks[7][1] > landmarks[3][1]:
                v = landmarks[7][1] - landmarks[3][1]
                f = z_penalty(v, std_y)
                confidences[7] *= f
                system_warnings.append(f"PNS {v:.1f}px abajo de Menton ({f:.0%})")

            # [8] Prosthion (Pn): Entre A-point [0] y Menton [3]
            if landmarks[8][1] < landmarks[0][1]:
                v = landmarks[0][1] - landmarks[8][1]
                f = z_penalty(v, std_y)
                confidences[8] *= f
                system_warnings.append(f"Prosthion {v:.1f}px arriba de A-point ({f:.0%})")
            if landmarks[8][1] > landmarks[3][1]:
                v = landmarks[8][1] - landmarks[3][1]
                f = z_penalty(v, std_y)
                confidences[8] *= f
                system_warnings.append(f"Prosthion {v:.1f}px abajo de Menton ({f:.0%})")

            # [9] Rhinion (R): Entre Nasion [4] y A-point [0]
            if landmarks[9][1] < landmarks[4][1]:
                v = landmarks[4][1] - landmarks[9][1]
                f = z_penalty(v, std_y)
                confidences[9] *= f
                system_warnings.append(f"Rhinion {v:.1f}px arriba de Nasion ({f:.0%})")
            if landmarks[9][1] > landmarks[0][1]:
                v = landmarks[9][1] - landmarks[0][1]
                f = z_penalty(v, std_y)
                confidences[9] *= f
                system_warnings.append(f"Rhinion {v:.1f}px abajo de A-point ({f:.0%})")

            # [10] Sella (S): ARRIBA de Articular [11] y ABAJO de Nasion [4]
            if landmarks[10][1] >= landmarks[11][1]:
                v = landmarks[10][1] - landmarks[11][1]
                f = z_penalty(v, std_y)
                confidences[10] *= f
                system_warnings.append(f"Sella {v:.1f}px abajo de Articular ({f:.0%})")
            if landmarks[10][1] <= landmarks[4][1]:
                v = landmarks[4][1] - landmarks[10][1]
                f = z_penalty(v, std_y)
                confidences[10] *= f
                system_warnings.append(f"Sella {v:.1f}px arriba de Nasion ({f:.0%})")

            # [11] Articular (Ar): ABAJO de Sella [10] y arriba de Gonion [14]
            if landmarks[11][1] <= landmarks[10][1]:
                v = landmarks[10][1] - landmarks[11][1]
                f = z_penalty(v, std_y)
                confidences[11] *= f
                system_warnings.append(f"Articular {v:.1f}px arriba de Sella ({f:.0%})")
            if landmarks[11][1] >= landmarks[14][1]:
                v = landmarks[11][1] - landmarks[14][1]
                f = z_penalty(v, std_y)
                confidences[11] *= f
                system_warnings.append(f"Articular {v:.1f}px abajo de Gonion ({f:.0%})")

            # [12] Condilo (Co): Cerca de Articular [11]
            v = dist(12, 11)
            max_dist = diag * 0.05
            if v > max_dist:
                f = z_penalty(v - max_dist, std_y)
                confidences[12] *= f
                system_warnings.append(f"Condilo {v:.1f}px de Articular ({f:.0%})")

            # [13] Gnathion (Gn): Cerca de Menton [3] y Pogonion [6]
            v1 = dist(13, 3)
            v2 = dist(13, 6)
            max_d = diag * 0.03
            if v1 > max_d:
                f = z_penalty(v1 - max_d, std_y)
                confidences[13] *= f
                system_warnings.append(f"Gnathion {v1:.1f}px de Menton ({f:.0%})")
            if v2 > max_d:
                f = z_penalty(v2 - max_d, std_y)
                confidences[13] *= f
                system_warnings.append(f"Gnathion {v2:.1f}px de Pogonion ({f:.0%})")

            # [14] Gonion (Go): ABAJO de Articular [11] y cerca de Mandibula
            if landmarks[14][1] <= landmarks[11][1]:
                v = landmarks[11][1] - landmarks[14][1]
                f = z_penalty(v, std_y)
                confidences[14] *= f
                system_warnings.append(f"Gonion {v:.1f}px arriba de Articular ({f:.0%})")
            v_b = dist(14, 2)
            v_p = dist(14, 6)
            max_w = diag * 0.08
            if v_b > max_w or v_p > max_w:
                f = z_penalty(max(v_b, v_p) - max_w, std_x)
                confidences[14] *= f
                system_warnings.append(f"Gonion lejos de mandibula ({f:.0%})")

            # [15] Porion (Po): ARRIBA de Articular [11] y Gonion [14]
            if landmarks[15][1] >= landmarks[11][1]:
                v = landmarks[15][1] - landmarks[11][1]
                f = z_penalty(v, std_y)
                confidences[15] *= f
                system_warnings.append(f"Porion {v:.1f}px abajo de Articular ({f:.0%})")
            if landmarks[15][1] >= landmarks[14][1]:
                v = landmarks[15][1] - landmarks[14][1]
                f = z_penalty(v, std_y)
                confidences[15] *= f
                system_warnings.append(f"Porion {v:.1f}px abajo de Gonion ({f:.0%})")

            # [16] LPM (Lower Molar Tip): Derecha de LIT [17] (en X)
            v = landmarks[16][0] - landmarks[17][0]
            if v < 0:
                f = z_penalty(-v, std_x)
                confidences[16] *= f
                system_warnings.append(f"LPM {(-v):.1f}px a la izquierda de LIT ({f:.0%})")

            # [17] LIT (Lower Incisor Tip): Izquierda de LMT [16] (en X)
            v = landmarks[17][0] - landmarks[16][0]
            if v > 0:
                f = z_penalty(v, std_x)
                confidences[17] *= f
                system_warnings.append(f"LIT {v:.1f}px a la derecha de LMT ({f:.0%})")

            # [18] UMT (Upper Molar Tip): Derecha de UIT [21] (en X)
            v = landmarks[18][0] - landmarks[21][0]
            if v < 0:
                f = z_penalty(-v, std_x)
                confidences[18] *= f
                system_warnings.append(f"UMT {(-v):.1f}px a la izquierda de UIT ({f:.0%})")

            # [19] UPM (Upper Molar Tip): Izquierda de UMT [18] (en X)
            v = landmarks[19][0] - landmarks[18][0]
            if v > 0:
                f = z_penalty(v, std_x)
                confidences[19] *= f
                system_warnings.append(f"UPM {v:.1f}px a la derecha de UMT ({f:.0%})")

            # [20] LPM (Lower Molar Tip): Izquierda de LMT [16] (en X)
            v = landmarks[20][0] - landmarks[16][0]
            if v > 0:
                f = z_penalty(v, std_x)
                confidences[20] *= f
                system_warnings.append(f"LPM {v:.1f}px a la derecha de LMT ({f:.0%})")

            # [21] UIT (Upper Incisor Tip): Izquierda de UMT [18] (en X)
            v = landmarks[21][0] - landmarks[18][0]
            if v > 0:
                f = z_penalty(v, std_y)
                confidences[21] *= f
                system_warnings.append(f"UIT {v:.1f}px a la derecha de UMT ({f:.0%})")

            # [22] UIA (Upper Incisor Apex): ARRIBA de UIT [21]
            v = landmarks[22][1] - landmarks[21][1]
            if v > 0:
                f = z_penalty(v, std_y)
                confidences[22] *= f
                system_warnings.append(f"UIA {v:.1f}px abajo de UIT ({f:.0%})")

            # [23] LIA (Lower Incisor Apex): ARRIBA de LIT [17]
            v = landmarks[23][1] - landmarks[17][1]
            if v > 0:
                f = z_penalty(v, std_y)
                confidences[23] *= f
                system_warnings.append(f"LIA {v:.1f}px abajo de LIT ({f:.0%})")

            # [24] Li (Lower Lip): Cerca de LIT [17]
            v = dist(24, 17)
            if v > diag * 0.03:
                f = z_penalty(v - diag * 0.03, std_y)
                confidences[24] *= f
                system_warnings.append(f"Lower Lip {v:.1f}px de LIT ({f:.0%})")

            # [25] Ls (Upper Lip): Cerca de UIT [21]
            v = dist(25, 21)
            if v > diag * 0.03:
                f = z_penalty(v - diag * 0.03, std_y)
                confidences[25] *= f
                system_warnings.append(f"Upper Lip {v:.1f}px de UIT ({f:.0%})")

            # [26] N' (N Prime): Cerca de Nasion [4]
            v = dist(26, 4)
            if v > diag * 0.02:
                f = z_penalty(v - diag * 0.02, std_y)
                confidences[26] *= f
                system_warnings.append(f"N' {v:.1f}px de Nasion ({f:.0%})")

            # [27] Pog' (Soft Pogonion): Cerca de Pogonion [6]
            v = dist(27, 6)
            if v > diag * 0.02:
                f = z_penalty(v - diag * 0.02, std_y)
                confidences[27] *= f
                system_warnings.append(f"Pog' {v:.1f}px de Pogonion ({f:.0%})")

            # [28] Sn (Subnasale): Entre Nasion [4] y A-point [0]
            if landmarks[28][1] < landmarks[4][1]:
                v = landmarks[4][1] - landmarks[28][1]
                f = z_penalty(v, std_y)
                confidences[28] *= f
                system_warnings.append(f"Sn {v:.1f}px arriba de Nasion ({f:.0%})")
            if landmarks[28][1] > landmarks[0][1]:
                v = landmarks[28][1] - landmarks[0][1]
                f = z_penalty(v, std_y)
                confidences[28] *= f
                system_warnings.append(f"Sn {v:.1f}px abajo de A-point ({f:.0%})")

        except (IndexError, TypeError, Exception) as e:
            print(f"[DEBUG-audit] Error in anatomical audit: {e}")
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
