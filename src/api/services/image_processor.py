import cv2
import numpy as np
from pathlib import Path
from src.core.config import INPUT_SIZE_WH
from src.data.preprocessing import preprocess_xray


def process_image_for_inference(image_path):
    """Load and preprocess image for model inference.

    Returns:
        canvas: preprocessed image
        meta: dict with scale, offsets, original dimensions
    """
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"Could not read image: {image_path}")

    canvas, scale, x_offset, y_offset = preprocess_xray(img)
    return canvas, {"scale": scale, "x_offset": x_offset, "y_offset": y_offset, "orig_h": img.shape[0], "orig_w": img.shape[1]}


def scale_landmarks_to_original(landmarks_512, orig_w, orig_h, x_offset, y_offset):
    """Scale landmarks from input size (with padding) back to original image coordinates.

    Args:
        landmarks_512: (N, 2) landmarks in input space (with letterbox padding)
        orig_w: original image width
        orig_h: original image height
        x_offset: x padding offset used in letterboxing
        y_offset: y padding offset used in letterboxing

    Returns:
        landmarks_orig: (N, 2) landmarks in original image coordinates
    """
    from src.core.config import INPUT_SIZE_WH, INPUT_SIZE_HW
    landmarks_orig = landmarks_512.copy()
    landmarks_orig[:, 0] = (landmarks_512[:, 0] - x_offset) / INPUT_SIZE_WH[0] * orig_w
    landmarks_orig[:, 1] = (landmarks_512[:, 1] - y_offset) / INPUT_SIZE_WH[1] * orig_h
    return landmarks_orig


def get_image_path(image_id: str) -> Path:
    """Get image path from image_id.

    Checks:
    1. If image_id looks like a dataset filename (e.g., 'cks2ip8fq29y0yuf6ry9266i')
    2. Or checks data/uploads/ for uploaded images

    Returns:
        Path object or None if not found.
    """
    # Check dataset images (for testing)
    dataset_path = Path("data/raw/Aariz")
    for split in ["train", "valid", "test"]:
        img_path = dataset_path / split / "Cephalograms" / f"{image_id}.jpg"
        if img_path.exists():
            return img_path
        img_path = dataset_path / split / "Cephalograms" / f"{image_id}.png"
        if img_path.exists():
            return img_path

    # Check uploads folder (with and without extension)
    upload_path = Path("data/uploads") / image_id
    if upload_path.exists():
        return upload_path
    # Also try with common extensions
    for ext in ['.jpg', '.jpeg', '.png', '.bmp']:
        upload_path_ext = upload_path.with_suffix(ext)
        if upload_path_ext.exists():
            return upload_path_ext

    return None