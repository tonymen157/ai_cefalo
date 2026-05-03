"""Single Source of Truth - Configuración central del proyecto AI-Cefalo.

Todas las dimensiones, constantes y parámetros del proyecto se definen aquí.
Modificar INPUT_SIZE_WH afecta automáticamente todo el pipeline.
"""

# Número de landmarks cefalométricos (estándar Aariz)
NUM_LANDMARKS = 29

# Dimensiones de entrada del modelo (W, H) - Cambiar aquí escala TODO el pipeline
INPUT_SIZE_WH = (512, 512)     # (Ancho, Alto) - convención visual
INPUT_SIZE_HW = (512, 512)     # (Alto, Ancho) - convención PyTorch (N, C, H, W)

# Dimensiones de heatmaps de salida - SIEMPRE 1/4 del input
HEATMAP_SIZE_WH = (128, 128)   # (Ancho, Alto)
HEATMAP_SIZE_HW = (128, 128)   # (Alto, Ancho)

# Parámetro sigma para generación de heatmaps Gaussianos
# SIGMA_HEATMAP se deriva dinámicamente como: HEATMAP_SIZE_HW[1] * SIGMA_RATIO
SIGMA_RATIO = 5.0 / HEATMAP_SIZE_HW[1]  # sigma = 5.0 para heatmap de 128px
# SIGMA_HEATMAP ya NO es una constante hardcodeada, se calcula en runtime:

# Parámetros de preprocesamiento (SSOT - evitar magic numbers)
CLAHE_CLIP_LIMIT = 2.0
CLAHE_TILE_GRID_SIZE = (8, 8)
NLM_H = 10
NLM_TEMPLATE_WINDOW = 7
NLM_SEARCH_WINDOW = 21

# Límites de calibración (mm/px)
# Rango amplio: 0.01-2.0 cubre imágenes clínicas (0.05-0.5) y redimensionadas/pequeñas (hasta 2.0)
MIN_PIXEL_SIZE_MM = 0.01
MAX_PIXEL_SIZE_MM = 2.0

# Fallback scale factor when original image dimensions are invalid
FALLBACK_SCALE = 1.0

# Clinical thresholds
SILLA_THRESHOLD_OPEN = 128  # Silla > 128 deg -> open angle tendency
SILLA_THRESHOLD_CLOSED = 118  # Silla < 118 deg -> closed angle tendency

# Directorio base de datos
from pathlib import Path
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
CALIBRATION_CSV_PATH = DATA_DIR / "raw" / "Aariz" / "cephalogram_machine_mappings.csv"

def get_sigma_heatmap():
    """Deriva sigma dinámicamente del tamaño de heatmap y SIGMA_RATIO."""
    return HEATMAP_SIZE_HW[1] * SIGMA_RATIO

# Índices para puntos clave de análisis Steiner/Ricketts
IDX_SELLA = 10      # S (Sella)
IDX_NASION = 4      # N (Nasion)
IDX_A_POINT = 0     # A (A Point)
IDX_B_POINT = 2     # B (B Point)
IDX_POGONION = 6    # Pog (Pogonion)


def get_loss_config():
    """Retorna seccion de configuracion de perdidas desde config.yaml"""
    try:
        import yaml
        from pathlib import Path
        cfg_path = Path(__file__).parent.parent / 'training' / 'config.yaml'
        if cfg_path.exists():
            with open(cfg_path, 'r') as f:
                cfg = yaml.safe_load(f)
            return cfg.get('loss', {})
    except:
        pass
    return {}


def get_preprocessing_config():
    """Retorna seccion de preprocesamiento desde config.yaml"""
    try:
        import yaml
        from pathlib import Path
        cfg_path = Path(__file__).parent.parent / 'training' / 'config.yaml'
        if cfg_path.exists():
            with open(cfg_path, 'r') as f:
                cfg = yaml.safe_load(f)
            return cfg.get('data', {}).get('preprocessing', {})
    except:
        pass
    return {}


def get_augmentation_config():
    """Retorna seccion de augmentacion desde config.yaml"""
    try:
        import yaml
        from pathlib import Path
        cfg_path = Path(__file__).parent.parent / 'training' / 'config.yaml'
        if cfg_path.exists():
            with open(cfg_path, 'r') as f:
                cfg = yaml.safe_load(f)
            return cfg.get('data', {}).get('augmentation', {})
    except:
        pass
    return {}
