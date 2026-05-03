from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

router = APIRouter()


class LandmarkInput(BaseModel):
    x: float
    y: float


class SteinerRequest(BaseModel):
    landmarks: List[List[float]]  # 29 landmarks [x, y]
    pixel_size_mm: Optional[float] = None
    image_id: Optional[str] = None


class AngleResult(BaseModel):
    value: Optional[float] = None
    classification: Optional[str] = None
    color: Optional[str] = None


class SteinerResponse(BaseModel):
    SNA: Optional[AngleResult] = None
    SNB: Optional[AngleResult] = None
    ANB: Optional[AngleResult] = None
    WITS: Optional[float] = None
    Ls_E: Optional[float] = None
    Li_E: Optional[float] = None
    skeletal_class: Optional[str] = None
    success: bool = True


def _classify_angle(value: Optional[float], normal_low: float, normal_high: float) -> str:
    if value is None:
        return "N/A"
    if value < normal_low:
        return "Below normal"
    if value > normal_high:
        return "Above normal"
    return "Normal"


def _angle_color(value: Optional[float], normal_low: float, normal_high: float) -> str:
    if value is None:
        return "gray"
    if value < normal_low:
        return "blue"
    if value > normal_high:
        return "red"
    return "green"


@router.post("/steiner-analysis")
async def steiner_analysis(request: SteinerRequest):
    """
    Perform Steiner cephalometric analysis.

    Args:
        request: SteinerRequest with landmarks and optional pixel_size_mm

    Returns:
        SteinerResponse with calculated angles and classifications
    """
    try:
        import numpy as np
        from src.analysis.geometry import CephalometricAnalysis

        landmarks = np.array(request.landmarks)

        if landmarks.shape[0] != 29 or landmarks.shape[1] != 2:
            raise HTTPException(
                status_code=400,
                detail=f"Expected 29 landmarks with [x,y], got shape {landmarks.shape}"
            )

        analysis = CephalometricAnalysis(
            coords=landmarks,
            nombre_imagen=request.image_id or "",
            escala_mm=request.pixel_size_mm
        )

        result = analysis.reporte_json()

        def _make_angle(name: str, value, normal_low: float, normal_high: float) -> AngleResult:
            return AngleResult(
                value=value,
                classification=_classify_angle(value, normal_low, normal_high),
                color=_angle_color(value, normal_low, normal_high)
            )

        return SteinerResponse(
            SNA=_make_angle("SNA", result.get("SNA"), 80, 84),
            SNB=_make_angle("SNB", result.get("SNB"), 76, 80),
            ANB=_make_angle("ANB", result.get("ANB"), 0, 4),
            WITS=result.get("WITS"),
            Ls_E=result.get("Ls_E"),
            Li_E=result.get("Li_E"),
            skeletal_class=result.get("clase_esqueletal"),
            success=True
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Steiner analysis failed: {str(e)}")


@router.get("/steiner")
async def get_steiner_info():
    """Return Steiner analysis parameter info."""
    return {
        "description": "Steiner cephalometric analysis",
        "parameters": {
            "SNA": {"normal": "80-84°", "description": "Maxillary position"},
            "SNB": {"normal": "76-80°", "description": "Mandibular position"},
            "ANB": {"normal": "0-4°", "description": "Maxillo-mandibular relationship"},
            "WITS": {"unit": "mm", "description": "Wits appraisal"},
        },
        "landmarks_required": 29,
        "pixel_size_required": False
    }
