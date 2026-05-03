from typing import Optional, Dict

# Equipos cefalométricos comunes en Ecuador/Latinoamérica
EQUIPMENT_PRESETS = {
    "carestream_cs8100": {
        "name": "Carestream CS 8100",
        "manufacturer": "Carestream",
        "mm_per_pixel": 0.10,
        "description": "Equipo panorámico/cefalométrico digital"
    },
    "planmeca_promax": {
        "name": "Planmeca ProMax",
        "manufacturer": "Planmeca",
        "mm_per_pixel": 0.095,
        "description": "Sistema de imágenes 2D/3D"
    },
    "sirona_orthophos": {
        "name": "Sirona Orthophos XG",
        "manufacturer": "Sirona",
        "mm_per_pixel": 0.10,
        "description": "Panorámico digital"
    },
    "standard_cephalometric": {
        "name": "Valor Estándar Cefalométrico",
        "manufacturer": "Genérico",
        "mm_per_pixel": 0.10,
        "description": "Valor típico para equipos digitales modernos (±5% precisión)"
    }
}

class CalibrationDetector:

    @staticmethod
    def get_preset_by_id(preset_id: str) -> Optional[Dict]:
        """Obtiene preset de equipo por ID"""
        return EQUIPMENT_PRESETS.get(preset_id)

    @staticmethod
    def get_all_presets() -> Dict:
        """Retorna todos los presets disponibles"""
        return EQUIPMENT_PRESETS

    @staticmethod
    def validate_calibration(mm_per_pixel: float) -> bool:
        """
        Valida que el valor esté en rango clínico aceptable.
        Rango: MIN_PIXEL_SIZE_MM - MAX_PIXEL_SIZE_MM desde config.
        """
        from src.core.config import MIN_PIXEL_SIZE_MM, MAX_PIXEL_SIZE_MM
        return MIN_PIXEL_SIZE_MM <= mm_per_pixel <= MAX_PIXEL_SIZE_MM