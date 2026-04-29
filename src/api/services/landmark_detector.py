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
        tensor: (1, 1, 512, 512) - PyTorch (N, C, H, W)
        scale: scaling factor used in letterboxing
        x_offset: x padding offset
        y_offset: y padding offset
    """
    canvas, scale, x_offset, y_offset = preprocess_xray(img)
    tensor = torch.from_numpy(canvas).unsqueeze(0).unsqueeze(0).float()
    return tensor, scale, x_offset, y_offset


def detect_landmarks(image: np.ndarray, orig_w: int = None, orig_h: int = None):
    """Run inference and return 29 landmarks as (29, 2) array in original image coords.

    Uses proper letterboxing inverse transformation to handle non-square images.

    Args:
        image: Grayscale image (H, W) as numpy array
        orig_w: Original image width (if None, uses image width)
        orig_h: Original image height (if None, uses image height)
    Returns:
        landmarks: (29, 2) in original image coordinates (W, H)
    """
    if orig_w is None:
        orig_w = image.shape[1]
    if orig_h is None:
        orig_h = image.shape[0]

    model = get_model()

    # Preprocess image with letterboxing
    tensor, scale, x_offset, y_offset = preprocess_image(image)
    tensor = tensor.to(_device)

    # Inference
    with torch.no_grad():
        heatmaps = model(tensor)  # (1, 29, 128, 128)
        landmarks_norm = model.decode_heatmaps(heatmaps)  # (1, 29, 2) in [0, 1]

    # decode_heatmaps returns coords in [0,1] relative to heatmap (128x128)
    landmarks_1 = landmarks_norm.cpu().numpy()[0]  # (29, 2) in [0,1]

    # Convert to input space (512x512) - heatmap 128px -> input 512px
    landmarks_512 = landmarks_1 * INPUT_SIZE_WH[0]  # Now in [0, 512] canvas space

    # Inverse letterboxing: remove padding, then scale back using REAL scale
    landmarks_orig = landmarks_512.copy()
    landmarks_orig[:, 0] = (landmarks_512[:, 0] - x_offset) / scale
    landmarks_orig[:, 1] = (landmarks_512[:, 1] - y_offset) / scale

    return landmarks_orig.astype(np.float32)