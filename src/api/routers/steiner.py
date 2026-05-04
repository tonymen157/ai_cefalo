from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()


class LandmarkInput(BaseModel):
    x: float
    y: float


class SteinerRequest(BaseModel):
    landmarks: List[List[float]]  # 29 landmarks [x, y]
    pixel_size_mm: Optional[float] = None
    image_id: Optional[str] = None


@router.post("/steiner-analysis")
async def steiner_analysis(request: SteinerRequest):
    """
    Perform cephalometric analysis (Steiner, Ricketts, Jarabak, Dental).
    Returns all calculated measurements as a flat dictionary.
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
        result["success"] = True
        return result

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
