"""Funciones geométricas centralizadas para procesamiento de landmarks.

Única fuente de verdad para todas las operaciones geométricas:
- Escalado de landmarks
- Normalización / desnormalización
- Generación de heatmaps

TODO el procesamiento geométrico debe usar estas funciones.
"""

import numpy as np
import torch
import torch.nn.functional as F

from src.core.config import HEATMAP_SIZE_HW, HEATMAP_SIZE_WH


def scale_landmarks(landmarks, orig_w, orig_h, target_w, target_h):
    """Escala landmarks de espacio original a target manteniendo aspect ratio con padding.

    Aplica letterboxing: escala proporcional y centra en canvas target.
    Fórmula: new = orig * scale + offset

    Args:
        landmarks: np.array (N, 2) coordenadas (x, y) en espacio original
        orig_w: int - ancho original
        orig_h: int - alto original
        target_w: int - ancho destino
        target_h: int - alto destino

    Returns:
        scaled: np.array (N, 2) coordenadas escaladas en espacio target
    """
    scale = min(target_w / orig_w, target_h / orig_h)
    new_w = int(orig_w * scale)
    new_h = int(orig_h * scale)
    x_offset = (target_w - new_w) // 2
    y_offset = (target_h - new_h) // 2

    scaled = landmarks.copy()
    scaled[:, 0] = landmarks[:, 0] * scale + x_offset
    scaled[:, 1] = landmarks[:, 1] * scale + y_offset
    return scaled, scale, x_offset, y_offset


def normalize_landmarks(landmarks, ref_w, ref_h):
    """Normaliza landmarks a [0, 1] relativo a referencia.

    Args:
        landmarks: np.array (N, 2) coordenadas (x, y) en pixeles
        ref_w: int/float - ancho de referencia
        ref_h: int/float - alto de referencia

    Returns:
        normalized: np.array (N, 2) coordenadas en [0, 1]
    """
    normalized = landmarks.copy()
    normalized[:, 0] /= ref_w
    normalized[:, 1] /= ref_h
    return normalized


def denormalize_landmarks(landmarks_norm, ref_w, ref_h):
    """Desnormaliza landmarks de [0, 1] a pixeles.

    Args:
        landmarks_norm: np.array (N, 2) coordenadas en [0, 1]
        ref_w: int/float - ancho de referencia
        ref_h: int/float - alto de referencia

    Returns:
        denormalized: np.array (N, 2) coordenadas en pixeles
    """
    denormalized = landmarks_norm.copy()
    denormalized[:, 0] *= ref_w
    denormalized[:, 1] *= ref_h
    return denormalized


def generate_heatmap(landmarks_scaled, H=None, W=None, sigma=None):
    """Genera heatmaps Gaussianos vectorizados con sigma dinámico.

    Crea heatmaps 2D con pico exacto en 1.0 en cada landmark (x_c, y_c).
    Sigma se deriva dinámicamente: sigma = HEATMAP_SIZE_HW[1] * SIGMA_RATIO.

    Args:
        landmarks_scaled: np.array (N, 2) coordenadas (x, y) ya escaladas
                         al tamaño del heatmap (espera x=columna, y=fila)
        H: int - alto del heatmap. Por defecto HEATMAP_SIZE_HW[0]
        W: int - ancho del heatmap. Por defecto HEATMAP_SIZE_WH[0]
        sigma: float - sigma de la Gaussiana. Si None, se deriva dinámicamente.

    Returns:
        heatmaps: torch.Tensor (N, H, W) valores en [0, 1], pico=1.0 en centro
    """
    from src.core.config import HEATMAP_SIZE_HW, HEATMAP_SIZE_WH, get_sigma_heatmap

    C = landmarks_scaled.shape[0]
    H = H if H is not None else HEATMAP_SIZE_HW[0]
    W = W if W is not None else HEATMAP_SIZE_WH[0]

    # Sigma dinámico derivado de la geometría del heatmap
    if sigma is None:
        sigma = get_sigma_heatmap()

    # Grid de coordenadas (H, W) - indexing='ij' da (filas, columnas) = (Y, X)
    yy = torch.arange(H, dtype=torch.float32)
    xx = torch.arange(W, dtype=torch.float32)
    grid_y, grid_x = torch.meshgrid(yy, xx, indexing='ij')

    # Landmarks: landmarks_scaled[:, 0] = X (columnas), landmarks_scaled[:, 1] = Y (filas)
    cx = torch.from_numpy(landmarks_scaled[:, 0]).view(C, 1, 1)  # X coords
    cy = torch.from_numpy(landmarks_scaled[:, 1]).view(C, 1, 1)  # Y coords

    # Distancia euclidiana cuadrada: (x - cx)^2 + (y - cy)^2
    dist_sq = (grid_x.unsqueeze(0) - cx) ** 2 + (grid_y.unsqueeze(0) - cy) ** 2
    heatmaps = torch.exp(-dist_sq / (2.0 * sigma ** 2))

    return heatmaps
