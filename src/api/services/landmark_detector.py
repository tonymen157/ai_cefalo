import sys
sys.path.insert(0, '.')

import torch
import numpy as np
from pathlib import Path
import cv2

from src.core.config import INPUT_SIZE_WH, INPUT_SIZE_HW, HEATMAP_SIZE_WH, NUM_LANDMARKS
from src.data.preprocessing import preprocess_xray
from src.models.unet import UNetResNet50

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
MODEL_PATH = BASE_DIR / "models" / "best_model.pth"
_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
_model = None


def get_model():
    """Load UNet+ResNet50 model (lazy loading)."""
    global _model
    if _model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Model not found at {MODEL_PATH}. "
                "Train the model first (Phase 3)."
            )
        print(f"Loading model from {MODEL_PATH}...", flush=True)
        _model = UNetResNet50(num_landmarks=NUM_LANDMARKS)
        checkpoint = torch.load(MODEL_PATH, map_location=_device, weights_only=False)
        if "model_state_dict" in checkpoint:
            _model.load_state_dict(checkpoint["model_state_dict"])
        else:
            _model.load_state_dict(checkpoint)
        _model.to(_device)
        _model.eval()
        print(f"Model loaded on {_device}", flush=True)
    return _model


def preprocess_image(img: np.ndarray):
    """Full preprocessing: CLAHE → NLM → Z-score → Resize 512x512 with letterboxing.

    Args:
        img: Grayscale image (H, W) as numpy array
    Returns:
        tensor: (1, 1, INPUT_SIZE_HW[0], INPUT_SIZE_HW[1]) - PyTorch (N, C, H, W)
        scale: scaling factor used in letterboxing
        x_offset: x padding offset
        y_offset: y padding offset
    """
    canvas, scale, x_offset, y_offset = preprocess_xray(img)
    tensor = torch.from_numpy(canvas).unsqueeze(0).unsqueeze(0).float()
    return tensor, scale, x_offset, y_offset


def detect_landmarks(image: np.ndarray, orig_w: int = None, orig_h: int = None):
    """Run inference and return 29 landmarks and confidences.

    Uses proper letterboxing inverse transformation to handle non-square images.

    Args:
        image: Grayscale image (H, W) as numpy array
        orig_w: Original image width (if None, uses image width)
        orig_h: Original image height (if None, uses image height)
    Returns:
        landmarks: (29, 2) in original image coordinates (W, H)
        confidences: (29,) confidence values in [0.0, 1.0]
    """
    if orig_w is None:
        orig_w = image.shape[1]
    if orig_h is None:
        orig_h = image.shape[0]

    model = get_model()

    # Preprocess image with letterboxing
    tensor, scale, x_offset, y_offset = preprocess_image(image)
    tensor = tensor.to(_device)

    # INFERENCIA CON TTA (Solo Iluminación - Rollback V46.0)
    with torch.no_grad():
        # Crear variantes de iluminación (Clamp para no salir del rango normalizado)
        tensor_normal = tensor
        tensor_bright = torch.clamp(tensor * 1.2, max=tensor.max().item())
        tensor_dark = tensor * 0.8

        # Pasar las 3 variantes por el modelo
        hm_normal = model(tensor_normal)
        hm_bright = model(tensor_bright)
        hm_dark = model(tensor_dark)

        # Promediar los heatmaps
        heatmaps = 0.5 * hm_normal + 0.25 * hm_bright + 0.25 * hm_dark

        # --- MEJORA V50.0: SUAVIZADO GAUSSIANO ---
        # Aplicamos un desenfoque leve para eliminar picos de ruido falsos
        # Sigma dinámico desde config (se ajusta a cualquier tamaño de heatmap)
        from src.core.config import get_sigma_heatmap
        kernel_size = 3
        sigma = get_sigma_heatmap()

        # Crear kernel gaussiano 2D
        x = torch.arange(kernel_size).to(_device) - (kernel_size - 1) / 2
        g = torch.exp(-x.pow(2) / (2 * sigma**2))
        g = g / g.sum()
        kernel = g.view(1, 1, -1, 1) * g.view(1, 1, 1, -1)
        kernel = kernel.repeat(29, 1, 1, 1)  # Repetir para los 29 canales (landmarks)

        # Aplicar convolución para suavizar cada canal de heatmap individualmente
        heatmaps = torch.nn.functional.pad(heatmaps, (1, 1, 1, 1), mode='replicate')
        heatmaps = torch.nn.functional.conv2d(heatmaps, kernel, groups=29)
        # ------------------------------------------

        # Decodificación: soft-argmax con ventana 3x3
        landmarks_norm = model.decode_heatmaps(heatmaps)  # (1, 29, 2) en [0, 1]

        # EXTRACCIÓN DE CONFIDENCE
        confidences = heatmaps.view(1, 29, -1).max(dim=-1)[0].cpu().numpy()[0]  # (29,)

    # decode_heatmaps returns coords in [0,1] relative to heatmap (128x128)
    landmarks_1 = landmarks_norm.cpu().numpy()[0]  # (29, 2) in [0,1]

    # Convert to input space (512x512) - heatmap 128px -> input 512px
    landmarks_512 = landmarks_1.copy()  # landmarks_1 ya es numpy array
    landmarks_512[:, 0] *= INPUT_SIZE_WH[0]  # x -> Width
    landmarks_512[:, 1] *= INPUT_SIZE_HW[0]  # y -> Height

    # Inverse letterboxing: remove padding, then scale back using REAL scale
    landmarks_orig = landmarks_512.copy()
    landmarks_orig[:, 0] = (landmarks_512[:, 0] - x_offset) / scale
    landmarks_orig[:, 1] = (landmarks_512[:, 1] - y_offset) / scale

    return landmarks_orig.astype(np.float32), confidences.astype(np.float32)