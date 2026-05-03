import csv
import math
from uuid import uuid4
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.api.database import get_db
from src.api.models import CalibrationConfig, PixelSize
from src.api.services.calibration_detector import CalibrationDetector

router = APIRouter()


@router.get("/fixed-scale")
def get_fixed_scale(db: Session = Depends(get_db)):
    """Return admin-configured fixed mm/px for local scanners."""
    config = (
        db.query(CalibrationConfig)
        .filter(CalibrationConfig.key == "scanner_scale")
        .first()
    )
    if not config:
        return {"mm_per_pixel": None, "configured": False}
    return {"mm_per_pixel": float(config.value), "configured": True}


@router.post("/manual")
def calculate_manual_calibration(data: dict):
    """Calculate mm/px from 2 user points + real distance, or from template.

    Body parameters:
    - x1, y1, x2, y2: Coordinates of two points (in pixels)
    - real_distance_mm: Real distance between points (in mm)
      OR
    - template: Template ID (e.g. "ruler_150mm") from CALIBRATION_TEMPLATES
    """
    try:
        x1 = float(data.get("x1", 0))
        y1 = float(data.get("y1", 0))
        x2 = float(data.get("x2", 0))
        y2 = float(data.get("y2", 0))

        # Support for templates
        template_id = data.get("template")
        if template_id:
            real_distance_mm = _get_calibration_value(template_id)
            if real_distance_mm <= 0:
                raise ValueError(f"Unknown template: {template_id}")
        else:
            real_distance_mm = float(data.get("real_distance_mm", 0))

        if real_distance_mm <= 0:
            raise ValueError("Real distance must be positive")

        pixel_distance = math.hypot(x2 - x1, y2 - y1)
        if pixel_distance == 0:
            raise ValueError("Points must be different")

        mm_per_pixel = real_distance_mm / pixel_distance
        template_info = f" (template: {template_id})" if template_id else ""
        return {
            "mm_per_pixel": round(mm_per_pixel, 6),
            "real_distance_mm": real_distance_mm,
            "pixel_distance": round(pixel_distance, 2),
            "template": template_id or None
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# === CALIBRATION TEMPLATES ===
# Common calibration objects with known dimensions (in mm)
CALIBRATION_TEMPLATES = {
    "ruler_150mm": 150.0,
    "ruler_100mm": 100.0,
    "ruler_50mm": 50.0,
    "us_coin_26.5mm": 26.5,
    "eur_coin_25.7mm": 25.7,
}


def _get_calibration_value(template_id: str) -> float:
    """Get known dimension for a calibration template."""
    val = CALIBRATION_TEMPLATES.get(template_id)
    return float(val) if val is not None else None


# === AUTO CALIBRATION USING CSV (RECOMMENDED) ===
# This uses the pre-measured pixel_size from cephalogram_machine_mappings.csv
# which is the CLINICALLY CORRECT approach per Aariz dataset standard

def _get_pixel_size_from_csv(image_id: str) -> float:
    """Look up pixel_size from cephalogram_machine_mappings.csv.
    Uses SSOT path from config. Returns 0 if not found."""
    from src.core.config import CALIBRATION_CSV_PATH
    csv_path = CALIBRATION_CSV_PATH

    if not csv_path.exists():
        return None
    try:
        with open(csv_path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                row_id = row.get("cephalogram_id", "").strip()
                # Remove .png/.jpg extension from row_id
                if row_id.endswith(".png") or row_id.endswith(".jpg"):
                    row_id = Path(row_id).stem
                if image_id.endswith(".png") or image_id.endswith(".jpg"):
                    img_id = Path(image_id).stem
                else:
                    img_id = image_id
                if row_id == img_id:
                    val = row.get("pixel_size")
                    if val is None or str(val).strip() == "":
                        continue
                    return float(val)
    except Exception:
        pass
    return None


@router.get("/auto")
def auto_calibration(image_id: str):
    """Automatically get mm/px from cephalogram_machine_mappings.csv.
    This is the RECOMMENDED method - uses pre-measured pixel sizes.
    """
    if not image_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="image_id parameter is required",
        )
    mm_per_pixel = _get_pixel_size_from_csv(image_id)
    if mm_per_pixel is None or mm_per_pixel <= 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No pixel_size found for image_id: {image_id}. Use /manual instead.",
        )
    return {"mm_per_pixel": round(mm_per_pixel, 6), "method": "auto_from_csv"}


@router.get("/coin")
def detect_coin(image_id: str):
    """Detect coin in image and calculate mm/px.
    NOTE: Not implemented - would require coin detection algorithm.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Coin detection not yet implemented. Use /auto or /manual instead.",
    )


@router.get("/templates")
def list_templates():
    """List available calibration templates with known dimensions."""
    return {
        "templates": [
            {"id": tid, "name": tid.replace("_", " ").title(), "real_mm": val}
            for tid, val in CALIBRATION_TEMPLATES.items()
        ]
    }


@router.get("/presets")
def get_equipment_presets():
    """Return available radiographic equipment presets with known mm/px values."""
    presets = CalibrationDetector.get_all_presets()
    return {
        "presets": [
            {
                "id": pid,
                "name": info["name"],
                "manufacturer": info["manufacturer"],
                "mm_per_pixel": info["mm_per_pixel"],
                "description": info["description"],
                "valid": CalibrationDetector.validate_calibration(info["mm_per_pixel"])
            }
            for pid, info in presets.items()
        ]
    }


@router.post("/apply-preset")
def apply_preset(data: dict):
    """Apply a radiographic equipment preset and save calibration to database.

    Body parameters:
    - image_id: The image identifier (required)
    - preset_id: Equipment preset ID (e.g. "carestream_cs8100") (required)

    Saves the calibration to PixelSize table with calibration_source field.
    """
    try:
        image_id = data.get("image_id")
        preset_id = data.get("preset_id")

        if not image_id:
            raise ValueError("image_id is required")
        if not preset_id:
            raise ValueError("preset_id is required")

        preset = CalibrationDetector.get_preset_by_id(preset_id)
        if not preset:
            raise ValueError(f"Unknown preset: {preset_id}")

        mm_per_pixel = preset["mm_per_pixel"]

        if not CalibrationDetector.validate_calibration(mm_per_pixel):
            raise ValueError(
                f"Calibration value {mm_per_pixel} mm/px is outside valid range (0.05-0.15 mm/px)"
            )

        db = next(get_db())
        try:
            # Check if PixelSize already exists for this image
            existing = (
                db.query(PixelSize)
                .filter(PixelSize.image_id == image_id)
                .first()
            )

            if existing:
                existing.mm_per_pixel = mm_per_pixel
                existing.calibration_source = preset_id
            else:
                pixel_size = PixelSize(
                    id=str(uuid4()),
                    image_id=image_id,
                    mm_per_pixel=mm_per_pixel,
                    calibration_source=preset_id,
                )
                db.add(pixel_size)

            db.commit()
            db.refresh(existing if existing else pixel_size)
        finally:
            db.close()

        return {
            "image_id": image_id,
            "mm_per_pixel": mm_per_pixel,
            "preset_id": preset_id,
            "preset_name": preset["name"],
            "calibration_source": preset_id,
            "validated": True,
            "method": "preset_from_equipment",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
