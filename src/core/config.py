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

def get_sigma_heatmap():
    """Deriva sigma dinámicamente del tamaño de heatmap y SIGMA_RATIO."""
    return HEATMAP_SIZE_HW[1] * SIGMA_RATIO

# Nombres de los 29 landmarks (estándar Aariz)
LANDMARK_NAMES = [
    'A', 'ANS', 'B', 'Me', 'N', 'Or', 'Pog',
    'PNS', 'Pn', 'R', 'S', 'Ar', 'Co', 'Gn',
    'Go', 'Po', 'LPM', 'LIT', 'LMT', 'UPM',
    'UIA', 'UIT', 'UMT', 'LIA', 'Li', 'Ls',
    "N'", "Pog'", 'Sn'
]

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
