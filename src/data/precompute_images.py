"""Pre-compute preprocessed images AND adjusted landmarks for ALL Aariz splits.

Applies: CLAHE → NLM denoising → Z-score → Resize to INPUT_SIZE_WH with letterboxing.
Saves:
  - Preprocessed images as .pt tensors (1, H, W)
  - Original sizes + padding metadata + adjusted landmarks in .json

The JSON allows AarizDataset to ONLY READ, never recalculate landmark positions.

Usage:
    venv/Scripts/python src/data/precompute_images.py
"""

import sys
sys.path.insert(0, '.')

import os
from pathlib import Path
import cv2
import numpy as np
import torch
import json

from src.data.preprocessing import preprocess_xray
from src.core.config import INPUT_SIZE_WH, INPUT_SIZE_HW, NUM_LANDMARKS
from src.core.geometry import scale_landmarks


def preprocess_image(img_path_str):
    """Full preprocessing: CLAHE → NLM → Z-score → Resize to INPUT_SIZE_WH with letterboxing.

    Args:
        img_path_str: path to raw image

    Returns:
        img_tensor: (1, H, W) float32 tensor - PyTorch (C, H, W) using config dimensions
        orig_w, orig_h: original image dimensions
        scale, x_offset, y_offset: padding metadata
    """
    img = cv2.imread(img_path_str, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(f"Could not read image: {img_path_str}")

    orig_h, orig_w = img.shape

    # Use dynamic target size from config (not hardcoded 512)
    canvas, scale, x_offset, y_offset = preprocess_xray(img, target_size=INPUT_SIZE_WH)

    # To tensor: (H, W) -> (1, H, W) for PyTorch
    img_tensor = torch.from_numpy(canvas).unsqueeze(0).float()
    return img_tensor, orig_w, orig_h, scale, x_offset, y_offset


def load_landmarks_raw(stem, senior_dir, junior_dir):
    """Load raw landmarks from JSON files and return average (Senior + Junior).

    Args:
        stem: image file stem (ceph_id)
        senior_dir: Path to Senior Orthodontists annotations
        junior_dir: Path to Junior Orthodontists annotations

    Returns:
        landmarks: np.array (NUM_LANDMARKS, 2) - averaged (x, y) in original pixel space
    """
    import json

    def _parse(path):
        if not path.exists():
            return None
        with open(path, 'r') as f:
            data = json.load(f)
        pts = np.zeros((NUM_LANDMARKS, 2), dtype=np.float32)
        for i, lm in enumerate(data.get('landmarks', [])[:NUM_LANDMARKS]):
            val = lm.get('value', {})
            pts[i, 0] = float(val.get('x', 0.0))
            pts[i, 1] = float(val.get('y', 0.0))
        return pts

    senior = _parse(senior_dir / f"{stem}.json")
    junior = _parse(junior_dir / f"{stem}.json")

    if senior is not None and junior is not None:
        return (senior + junior) / 2.0
    elif senior is not None:
        return senior
    elif junior is not None:
        return junior
    else:
        return np.zeros((NUM_LANDMARKS, 2), dtype=np.float32)


def process_split(dataset_path, split_name, output_dir):
    """Process one split (TRAIN/VALID/TEST): images + adjusted landmarks."""
    split_dir = Path(dataset_path) / split_name
    cephalograms_dir = split_dir / "Cephalograms"
    senior_dir = split_dir / "Annotations" / "Cephalometric Landmarks" / "Senior Orthodontists"
    junior_dir = split_dir / "Annotations" / "Cephalometric Landmarks" / "Junior Orthodontists"

    output_split_dir = output_dir / split_name
    output_split_dir.mkdir(parents=True, exist_ok=True)

    # JSON file to store original image dimensions + padding + adjusted landmarks
    sizes_json = output_dir / f"{split_name}_sizes.json"

    # Get all image files
    extensions = ["*.jpg", "*.jpeg", "*.png", "*.bmp"]
    image_files = []
    for ext in extensions:
        image_files.extend(cephalograms_dir.glob(ext))
    image_files = sorted(image_files)

    print(f"\nProcessing {split_name} ({len(image_files)} images)...")

    # Load existing sizes if available
    sizes_dict = {}
    if sizes_json.exists():
        with open(sizes_json, "r") as f:
            sizes_dict = json.load(f)

    processed = 0
    for img_path in image_files:
        stem = img_path.stem
        output_path = output_split_dir / f"{stem}.pt"

        # Skip if already exists and in sizes_dict with landmarks
        if output_path.exists() and stem in sizes_dict and "landmarks_512" in sizes_dict[stem]:
            processed += 1
            continue

        try:
            img_tensor, orig_w, orig_h, scale, x_offset, y_offset = preprocess_image(str(img_path))

            # Load raw landmarks and scale them to INPUT_SIZE_WH with letterboxing
            landmarks_raw = load_landmarks_raw(stem, senior_dir, junior_dir)
            landmarks_scaled, _, _, _ = scale_landmarks(
                landmarks_raw, orig_w, orig_h, INPUT_SIZE_WH[0], INPUT_SIZE_WH[1]
            )

            torch.save(img_tensor, output_path)
            sizes_dict[stem] = {
                "orig_w": int(orig_w),
                "orig_h": int(orig_h),
                "scale": float(scale),
                "x_offset": int(x_offset),
                "y_offset": int(y_offset),
                "landmarks_512": landmarks_scaled.tolist()  # Save adjusted landmarks
            }
            processed += 1

            if processed % 50 == 0:
                print(f"  Progress: {processed}/{len(image_files)}", flush=True)
        except Exception as e:
            print(f"  ERROR processing {stem}: {e}", flush=True)

    # Save sizes JSON
    with open(sizes_json, "w") as f:
        json.dump(sizes_dict, f, indent=2)

    print(f"  DONE: {processed}/{len(image_files)} images saved to {output_split_dir}")
    print(f"  Landmarks adjusted and saved to {sizes_json}")


def main():
    dataset_path = "data/raw/Aariz"
    output_dir = Path("data/preprocessed")

    print("=" * 60)
    print("PRE-COMPUTING PREPROCESSED IMAGES + LANDMARKS FOR ALL SPLITS")
    print("=" * 60)
    print(f"Output directory: {output_dir.absolute()}")
    print(f"Input size from config: INPUT_SIZE_WH={INPUT_SIZE_WH}, INPUT_SIZE_HW={INPUT_SIZE_HW}")
    print(f"Sigma ratio: SIGMA_RATIO applied dynamically")
    print()

    # Check available disk space (~1.7 GB needed)
    import shutil
    total, used, free = shutil.disk_usage(output_dir.parent)
    print(f"Available disk space: {free / (1024**3):.1f} GB")
    if free < 2 * 1024**3:
        print("WARNING: Less than 2GB free. May not be enough.")
        return

    # Process each split
    process_split(dataset_path, "train", output_dir)
    process_split(dataset_path, "valid", output_dir)
    process_split(dataset_path, "test", output_dir)

    print("\n" + "=" * 60)
    print("ALL IMAGES + LANDMARKS PRE-COMPUTED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    main()
