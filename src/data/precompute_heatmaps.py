"""Pre-compute heatmaps for ALL Aariz images (TRAIN/VALID/TEST).

This eliminates the bottleneck of generating 29x128x128 heatmaps
on-the-fly. Heatmaps are saved as .pt files.

Generated structure:
    data/heatmaps/
    ├── TRAIN/
    │   ├── ck2ip8fq29y0yuf6ry9266i.pt  # (29, 128, 128) tensor
    │   └── ...
    ├── VALID/
    └── TEST/

Usage:
    venv/Scripts/python src/data/precompute_heatmaps.py
"""

import sys
sys.path.insert(0, '.')

import os
from pathlib import Path
import torch
import numpy as np
import cv2
import json

from src.core.config import HEATMAP_SIZE_HW, SIGMA_HEATMAP, NUM_LANDMARKS
from src.core.geometry import generate_heatmap


def scale_landmarks_with_padding(landmarks, orig_w, orig_h, target_w, target_h):
    """Scale landmarks from original to target size preserving aspect ratio with letterboxing."""
    scale = min(target_w / orig_w, target_h / orig_h)
    new_w = int(orig_w * scale)
    new_h = int(orig_h * scale)
    x_offset = (target_w - new_w) // 2
    y_offset = (target_h - new_h) // 2
    landmarks_scaled = landmarks.copy()
    landmarks_scaled[:, 0] = landmarks[:, 0] * scale + x_offset
    landmarks_scaled[:, 1] = landmarks[:, 1] * scale + y_offset
    return landmarks_scaled, scale, x_offset, y_offset


def _parse_landmarks(annotations_list):
    """Extrae pares (x, y) del formato Aariz."""
    pts = np.zeros((NUM_LANDMARKS, 2), dtype=np.float32)
    for i, lm in enumerate(annotations_list[:NUM_LANDMARKS]):
        val = lm.get("value", {})
        pts[i, 0] = float(val.get("x", 0.0))
        pts[i, 1] = float(val.get("y", 0.0))
    return pts


def process_split(dataset_path, split_name, output_dir):
    """Process one split (TRAIN/VALID/TEST)."""
    split_dir = Path(dataset_path) / split_name
    cephalograms_dir = split_dir / "Cephalograms"
    senior_dir = split_dir / "Annotations" / "Cephalometric Landmarks" / "Senior Orthodontists"
    junior_dir = split_dir / "Annotations" / "Cephalometric Landmarks" / "Junior Orthodontists"

    output_split_dir = output_dir / split_name
    output_split_dir.mkdir(parents=True, exist_ok=True)

    # Get all image files
    extensions = ["*.jpg", "*.jpeg", "*.png", "*.bmp"]
    image_files = []
    for ext in extensions:
        image_files.extend(cephalograms_dir.glob(ext))
    image_files = sorted(image_files)

    print(f"\nProcessing {split_name} ({len(image_files)} images)...")

    processed = 0
    for img_path in image_files:
        stem = img_path.stem
        output_path = output_split_dir / f"{stem}.pt"

        # Skip if already exists
        if output_path.exists():
            processed += 1
            continue

        # Load image to get original size
        img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
        if img is None:
            print(f"  WARNING: Could not read {img_path}")
            continue

        orig_h, orig_w = img.shape

        # Load and average landmarks (Senior + Junior)
        landmarks = None
        senior_path = senior_dir / f"{stem}.json"
        junior_path = junior_dir / f"{stem}.json"

        if senior_path.exists():
            with open(senior_path, "r") as f:
                data = json.load(f)
            senior_pts = _parse_landmarks(data.get("landmarks", []))
            landmarks = senior_pts

        if junior_path.exists():
            with open(junior_path, "r") as f:
                data = json.load(f)
            junior_pts = _parse_landmarks(data.get("landmarks", []))
            if landmarks is not None:
                landmarks = (landmarks + junior_pts) / 2.0
            else:
                landmarks = junior_pts

        if landmarks is None:
            print(f"  WARNING: No landmarks for {stem}")
            continue

        # Scale landmarks to heatmap size (512x512 -> 128x128) preserving aspect ratio
        landmarks_scaled, scale, x_offset, y_offset = scale_landmarks_with_padding(
            landmarks, orig_w, orig_h, HEATMAP_SIZE_HW[1], HEATMAP_SIZE_HW[0]
        )

        # Generate heatmaps - using centralized function
        heatmaps = generate_heatmap(
            landmarks_scaled,
            H=HEATMAP_SIZE_HW[0],
            W=HEATMAP_SIZE_HW[1],
            sigma=SIGMA_HEATMAP
        )

        # Save
        torch.save(heatmaps, output_path)
        processed += 1

        if processed % 50 == 0:
            print(f"  Progress: {processed}/{len(image_files)}", flush=True)

    print(f"  DONE: {processed}/{len(image_files)} heatmaps saved to {output_split_dir}")


def main():
    dataset_path = "data/raw/Aariz"
    output_dir = Path("data/heatmaps")

    print("=" * 60)
    print("PRE-COMPUTING HEATMAPS FOR ALL SPLITS")
    print("=" * 60)
    print(f"Output directory: {output_dir.absolute()}")
    print(f"Heatmap size: {HEATMAP_SIZE_HW} (H, W)")
    print(f"Sigma: {SIGMA_HEATMAP}")
    print()

    # Check available disk space
    import shutil
    total, used, free = shutil.disk_usage(output_dir.parent)
    print(f"Available disk space: {free / (1024**3):.1f} GB")

    # Process each split
    process_split(dataset_path, "train", output_dir)
    process_split(dataset_path, "valid", output_dir)
    process_split(dataset_path, "test", output_dir)

    print("\n" + "=" * 60)
    print("ALL HEATMAPS PRE-COMPUTED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    main()
