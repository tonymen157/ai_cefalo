"""Preprocesamiento de radiografías - SSOT para preprocesado offline.

Única función: preprocess_xray().
Usa dimensiones dinámicas desde src.core.config.

Pipeline: CLAHE -> NLM Denoising -> Z-score -> Resize con letterboxing.
"""

import cv2
import numpy as np
import hashlib
from src.core.config import INPUT_SIZE_WH

# Cache manual para NLM Denoising (max 10 imágenes en memoria)
_nlm_cache = {}
_MAX_CACHE_SIZE = 10


def _hash_img(img):
    """Genera hash MD5 de la imagen para usar como clave de caché."""
    return hashlib.md5(img.tobytes()).hexdigest()


def _nlmeans_denoise_cached(img, h, template_window, search_window):
    """NLM con caché manual (evita recalcular la misma imagen)."""
    key = _hash_img(img)
    if key in _nlm_cache:
        return _nlm_cache[key].copy()

    result = cv2.fastNlMeansDenoising(
        img, None, h=h,
        templateWindowSize=template_window,
        searchWindowSize=search_window
    )

    _nlm_cache[key] = result.copy()
    if len(_nlm_cache) > _MAX_CACHE_SIZE:
        _nlm_cache.pop(next(iter(_nlm_cache)))
    return result


def preprocess_xray(img: np.ndarray, target_size=None, config=None):
    """
    Preprocesar radiografía manteniendo aspect ratio (letterboxing).

    Args:
        img: numpy array (H, W) - imagen raw en escala de grises
        target_size: (W, H) - tamaño objetivo. Si None, usa INPUT_SIZE_WH del config.
        config: opcional, dict con parámetros de preprocessing.

    Returns:
        canvas: (target_h, target_w) imagen preprocesada con padding negro
        scale: factor de escala aplicado
        x_offset: padding en X (columnas)
        y_offset: padding en Y (filas)
    """
    if img.ndim == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Parámetros por defecto si no se pasa config
    clip_limit = 2.0
    tile_grid_size = (8, 8)
    nlm_h = 10
    nlm_template_window = 7
    nlm_search_window = 21

    if config is not None:
        pcfg = config.get('preprocessing', {})
        clahe_cfg = pcfg.get('clahe', {})
        clip_limit = clahe_cfg.get('clip_limit', 2.0)
        tile_grid_size = tuple(clahe_cfg.get('tile_grid_size', [8, 8]))
        nlm_h = pcfg.get('nlm_h', 10)
        nlm_template_window = pcfg.get('nlm_template_window', 7)
        nlm_search_window = pcfg.get('nlm_search_window', 21)

    # CLAHE
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
    img = clahe.apply(img)

    # NLM denoising (con caché manual para evitar recálculo)
    img = _nlmeans_denoise_cached(
        img, h=nlm_h,
        template_window=nlm_template_window,
        search_window=nlm_search_window
    )

    # Z-score normalization
    img = ((img - img.mean()) / (img.std() + 1e-8)).astype(np.float32)

    # Resize con aspect ratio preservado (letterboxing)
    h, w = img.shape

    if target_size is None:
        target_w, target_h = INPUT_SIZE_WH
    else:
        target_w, target_h = target_size

    scale = min(target_w / w, target_h / h)
    new_w = int(w * scale)
    new_h = int(h * scale)

    img_resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

    # Canvas negro y centrar imagen
    canvas = np.zeros((target_h, target_w), dtype=np.float32)
    y_offset = (target_h - new_h) // 2
    x_offset = (target_w - new_w) // 2
    canvas[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = img_resized

    return canvas, scale, x_offset, y_offset
