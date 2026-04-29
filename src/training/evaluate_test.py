import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader
import numpy as np
import cv2
from pathlib import Path
import json
import os

from src.core.config import HEATMAP_SIZE_HW, INPUT_SIZE_WH, INPUT_SIZE_HW, NUM_LANDMARKS
from src.data.dataset import AarizDataset, pixel_mre_to_mm
from src.models.unet import UNetResNet50


def load_original_sizes(mode="TEST"):
    """Load original image sizes from preprocessed JSON files."""
    sizes_path = Path("data/preprocessed") / f"{mode.lower()}_sizes.json"
    with open(sizes_path, "r") as f:
        return json.load(f)


def setup_device():
    """Configure CUDA device."""
    if torch.cuda.is_available():
        device = torch.device('cuda')
        print(f"Using GPU: {torch.cuda.get_device_name(0)}")
    else:
        device = torch.device('cpu')
        print("WARNING: Using CPU (evaluation will be slower)")
    return device


def load_model(checkpoint_path: Path, device):
    """Load UNet+ResNet50 model from checkpoint."""
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Model checkpoint not found: {checkpoint_path}")

    print(f"Loading model from: {checkpoint_path}")
    model = UNetResNet50(num_landmarks=NUM_LANDMARKS)

    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    if "model_state_dict" in checkpoint:
        model.load_state_dict(checkpoint["model_state_dict"])
    else:
        model.load_state_dict(checkpoint)

    model.to(device)
    model.eval()
    print("Model loaded and set to eval mode.")
    return model


def predict_landmarks(model, img_tensor, device):
    """Run inference on preprocessed image tensor.

    Args:
        model: UNetResNet50 model
        img_tensor: (1, 1, H, W) preprocessed tensor (already CLAHE+NLM+Z-score+resize)
        device: torch device

    Returns:
        landmarks_pred: (29, 2) in ORIGINAL image coordinates (W, H) in pixels
        landmarks_norm: (29, 2) normalized [0, 1]
        heatmaps: (29, 128, 128) raw heatmaps
    """
    with torch.no_grad():
        img_tensor = img_tensor.to(device)
        # Use model's expected input size (512x512)
        if img_tensor.shape[-2:] != (INPUT_SIZE_HW[0], INPUT_SIZE_WH[0]):
            img_tensor = F.interpolate(
                img_tensor,
                size=(INPUT_SIZE_HW[0], INPUT_SIZE_WH[0]),
                mode='bilinear',
                align_corners=False
            )
        heatmaps = model(img_tensor)  # (1, 29, 128, 128)
        # decode_heatmaps returns (1, 29, 2) in [0, 1]
        landmarks_norm = model.decode_heatmaps(heatmaps)  # sigmoid already in model

    landmarks_norm_np = landmarks_norm.cpu().numpy()[0]  # (29, 2)
    heatmaps_np = heatmaps.cpu().numpy()[0]  # (29, 128, 128)

    # Denormalize: [0,1] -> INPUT_SIZE_WH coordinates
    landmarks_input = landmarks_norm_np.copy()
    landmarks_input[:, 0] *= INPUT_SIZE_WH[0]  # x
    landmarks_input[:, 1] *= INPUT_SIZE_HW[0]  # y

    return landmarks_input, landmarks_norm_np, heatmaps_np


def compute_metrics(landmarks_pred, landmarks_gt, pixel_size):
    """Compute per-landmark and overall metrics.

    Args:
        landmarks_pred: (29, 2) in original image pixels
        landmarks_gt: (29, 2) in original image pixels
        pixel_size: mm per pixel

    Returns:
        metrics dict with MRE, SDR, per-landmark errors
    """
    # Euclidean distance per landmark (pixels)
    errors_px = np.sqrt(np.sum((landmarks_pred - landmarks_gt) ** 2, axis=1))  # (29,)

    # Convert to millimeters
    errors_mm = errors_px * pixel_size  # (29,)

    # Mean Radial Error (MRE) in mm
    mre_mm = np.mean(errors_mm)

    # Success Detection Rate (SDR) at various thresholds
    sdr_2mm = np.mean(errors_mm <= 2.0) * 100
    sdr_25mm = np.mean(errors_mm <= 2.5) * 100
    sdr_3mm = np.mean(errors_mm <= 3.0) * 100
    sdr_4mm = np.mean(errors_mm <= 4.0) * 100

    return {
        'mre_mm': mre_mm,
        'errors_px': errors_px,
        'errors_mm': errors_mm,
        'sdr_2mm': sdr_2mm,
        'sdr_25mm': sdr_25mm,
        'sdr_3mm': sdr_3mm,
        'sdr_4mm': sdr_4mm,
        'mean_error_px': np.mean(errors_px),
        'max_error_px': np.max(errors_px),
        'max_error_mm': np.max(errors_mm),
    }


def draw_landmarks_comparison(img_gray, landmarks_gt, landmarks_pred, filepath, title=""):
    """Draw ground truth (green) and predicted (red) landmarks side by side.

    Args:
        img_gray: (H, W) grayscale image (original size, uint8)
        landmarks_gt: (29, 2) in original pixels
        landmarks_pred: (29, 2) in original pixels
        filepath: output path
    """
    # Convert to 3-channel for color drawing
    img_vis = cv2.cvtColor(img_gray, cv2.COLOR_GRAY2BGR)
    img_vis = (img_vis * 255).clip(0, 255).astype(np.uint8) if img_vis.max() <= 1.0 else img_vis.astype(np.uint8)

    # Draw ground truth landmarks (green circles)
    for i, (x, y) in enumerate(landmarks_gt):
        x, y = int(round(x)), int(round(y))
        if 0 <= x < img_vis.shape[1] and 0 <= y < img_vis.shape[0]:
            cv2.circle(img_vis, (x, y), 3, (0, 255, 0), -1)  # Green filled
            cv2.circle(img_vis, (x, y), 5, (0, 255, 0), 1)   # Green outline
            # Small label
            if i < 10:  # Only label some to avoid clutter
                cv2.putText(img_vis, str(i), (x+4, y-4), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 255, 0), 1)

    # Draw predicted landmarks (red X)
    for i, (x, y) in enumerate(landmarks_pred):
        x, y = int(round(x)), int(round(y))
        if 0 <= x < img_vis.shape[1] and 0 <= y < img_vis.shape[0]:
            cv2.drawMarker(img_vis, (x, y), (0, 0, 255), cv2.MARKER_CROSS, 8, 1)

    # Add legend
    h, w = img_vis.shape[:2]
    legend_x = 10
    cv2.putText(img_vis, "GT: Verde (circulo)", (legend_x, 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    cv2.putText(img_vis, "Pred: Roja (X)", (legend_x, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

    if title:
        cv2.putText(img_vis, title, (legend_x, h - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

    cv2.imwrite(str(filepath), img_vis)


def main():
    print("=" * 70)
    print("AI-CEFALO - Evaluacion en Test Set")
    print("=" * 70)

    # Setup
    device = setup_device()
    base_dir = Path(__file__).parent.parent.parent
    model_path = base_dir / "models" / "best_model.pth"

    # Load model
    model = load_model(model_path, device)

    # Load TEST dataset
    dataset_path = base_dir / "data" / "raw" / "Aariz"
    print(f"\nCargando dataset TEST desde: {dataset_path}")

    test_dataset = AarizDataset(
        dataset_folder_path=str(dataset_path),
        mode="TEST",
    )

    test_loader = DataLoader(
        test_dataset,
        batch_size=1,
        shuffle=False,
        num_workers=0,
        pin_memory=True
    )

    print(f"Tamano del test set: {len(test_dataset)} imagenes")

    # Evaluation
    all_mre_mm = []
    all_errors_mm = []
    all_errors_px = []
    per_landmark_errors = np.zeros((len(test_dataset), NUM_LANDMARKS))  # [N, 29]
    pixel_sizes = []

    # Directory for visualizations
    viz_dir = base_dir / "logs" / "test_evaluation"
    viz_dir.mkdir(parents=True, exist_ok=True)
    print(f"Visualizaciones guardadas en: {viz_dir}")

    print("\n" + "-" * 70)
    print("Ejecutando inferencia...")
    print("-" * 70)

    # Load original sizes from preprocessed JSON
    original_sizes = load_original_sizes("TEST")

    with torch.no_grad():
        for batch_idx, (img_tensor, heatmaps_gt, landmarks_gt_norm, cvm_stage, pixel_size) in enumerate(test_loader):
            # Get original dimensions from preprocessed JSON
            img_path = test_dataset.image_files[batch_idx]
            stem = img_path.stem
            orig_dims = original_sizes.get(stem,
                {"orig_w": INPUT_SIZE_WH[0], "orig_h": INPUT_SIZE_HW[0]})
            orig_w = orig_dims["orig_w"]
            orig_h = orig_dims["orig_h"]
            pixel_size_val = pixel_size.item() if torch.is_tensor(pixel_size) else pixel_size
            pixel_sizes.append(pixel_size_val)

            # Scale factor: INPUT_SPACE -> original
            # Landmarks from model are in INPUT_SIZE_WH coordinates
            # Need to scale to original image coordinates
            scale_x = orig_w / INPUT_SIZE_WH[0]
            scale_y = orig_h / INPUT_SIZE_HW[0]

            # Predict in INPUT_SIZE space
            landmarks_pred_input, _, _ = predict_landmarks(model, img_tensor, device)

            # Convert to original image coords
            landmarks_pred_orig = landmarks_pred_input.copy()
            landmarks_pred_orig[:, 0] *= scale_x
            landmarks_pred_orig[:, 1] *= scale_y

            # Ground truth landmarks are normalized [0,1] relative to INPUT_SIZE
            landmarks_gt_norm_np = landmarks_gt_norm.squeeze(0).numpy()  # (29,2)
            # Denormalize to INPUT_SIZE coordinates first
            landmarks_gt_input = landmarks_gt_norm_np.copy()
            landmarks_gt_input[:, 0] *= INPUT_SIZE_WH[0]
            landmarks_gt_input[:, 1] *= INPUT_SIZE_HW[0]

            # Then scale to original
            landmarks_gt_orig = landmarks_gt_input.copy()
            landmarks_gt_orig[:, 0] *= scale_x
            landmarks_gt_orig[:, 1] *= scale_y

            # Compute metrics
            metrics = compute_metrics(landmarks_pred_orig, landmarks_gt_orig, pixel_size_val)

            all_mre_mm.append(metrics['mre_mm'])
            all_errors_mm.extend(metrics['errors_mm'])
            all_errors_px.extend(metrics['errors_px'])
            per_landmark_errors[batch_idx, :] = metrics['errors_mm']

            # Save visualization for first 5 images
            if batch_idx < 5:
                # Load original image for visualization
                orig_img_path = test_dataset.images_dir / f"{stem}.png"
                if not orig_img_path.exists():
                    orig_img_path = test_dataset.images_dir / f"{stem}.jpg"
                if orig_img_path.exists():
                    orig_img = cv2.imread(str(orig_img_path), cv2.IMREAD_GRAYSCALE)
                    if orig_img is not None:
                        title = f"MRE={metrics['mre_mm']:.2f}mm SDR2={metrics['sdr_2mm']:.0f}%"
                        out_path = viz_dir / f"{stem}_pred.png"
                        draw_landmarks_comparison(
                            orig_img, landmarks_gt_orig, landmarks_pred_orig,
                            out_path, title
                        )
                    else:
                        print(f"  WARN: Could not load original image {orig_img_path}")

            # Progress
            if (batch_idx + 1) % 20 == 0 or batch_idx == 0:
                print(f"  Batch {batch_idx+1}/{len(test_loader)} - "
                      f"MRE: {metrics['mre_mm']:.3f} mm, "
                      f"SDR@2mm: {metrics['sdr_2mm']:.1f}%")

    # Aggregate results
    print("\n" + "=" * 70)
    print("RESULTADOS FINALES - TEST SET")
    print("=" * 70)

    all_mre_mm = np.array(all_mre_mm)
    all_errors_mm = np.array(all_errors_mm)
    pixel_sizes = np.array(pixel_sizes)

    print(f"\nTamano del test set: {len(test_dataset)} imagenes")
    print(f"Total landmarks evaluados: {len(all_errors_mm)}")
    print(f"\nMRE (Mean Radial Error):")
    print(f"  Promedio: {np.mean(all_mre_mm):.4f} mm")
    print(f"  Std:      {np.std(all_mre_mm):.4f} mm")
    print(f"  Min:      {np.min(all_mre_mm):.4f} mm")
    print(f"  Max:      {np.max(all_mre_mm):.4f} mm")
    print(f"  Mediana:  {np.median(all_mre_mm):.4f} mm")

    print(f"\nErrores por landmark (en mm):")
    print(f"  Promedio por landmark: {np.mean(all_errors_mm):.4f} mm")
    print(f"  Max error por landmark: {np.max(all_errors_mm):.4f} mm")

    print(f"\nSuccess Detection Rate:")
    sdr2 = np.mean(all_errors_mm <= 2.0) * 100
    sdr25 = np.mean(all_errors_mm <= 2.5) * 100
    sdr3 = np.mean(all_errors_mm <= 3.0) * 100
    sdr4 = np.mean(all_errors_mm <= 4.0) * 100
    print(f"  SDR@2.0mm:  {sdr2:.2f}% (Baseline: >78.44%)")
    print(f"  SDR@2.5mm:  {sdr25:.2f}% (Baseline: >85.72%)")
    print(f"  SDR@3.0mm:  {sdr3:.2f}% (Baseline: >89.64%)")
    print(f"  SDR@4.0mm:  {sdr4:.2f}% (Baseline: >94.49%)")
    sdr1 = np.mean(all_errors_mm <= 1.0) * 100
    print(f"  SDR@1.0mm:  {sdr1:.2f}%")

    # Per-landmark analysis
    landmark_names = [
        "A", "ANS", "B", "Me", "N", "Or", "Pog",
        "PNS", "Pn", "R", "S", "Ar", "Co", "Gn",
        "Go", "Po", "LPM", "LIT", "LMT", "UPM",
        "UIA", "UIT", "UMT", "LIA", "Li", "Ls",
        "N'", "Pog'", "Sn"
    ]
    mean_per_lm = np.mean(per_landmark_errors, axis=0)
    sorted_idx = np.argsort(mean_per_lm)[::-1]  # worst first
    print(f"\nTop 5 landmarks con mayor error (mm):")
    for rank, idx in enumerate(sorted_idx[:5]):
        name = landmark_names[idx] if idx < len(landmark_names) else f"LM{idx}"
        print(f"  #{rank+1}: {name:20s} - {mean_per_lm[idx]:.3f} mm")

    print(f"\nTamano de pixel (calibracion) - estadisticas:")
    print(f"  Promedio: {np.mean(pixel_sizes):.4f} mm/px")
    print(f"  Min:      {np.min(pixel_sizes):.4f} mm/px")
    print(f"  Max:      {np.max(pixel_sizes):.4f} mm/px")

    # Compare with baselines
    print(f"\n" + "=" * 70)
    print("COMPARACION CON BASELINE (Paper Aariz)")
    print("=" * 70)
    baseline_mre = 1.789
    baseline_sdr2 = 78.44
    our_mre = np.mean(all_mre_mm)
    our_sdr2 = sdr2

    print(f"  MRE:     {our_mre:.3f} mm vs {baseline_mre} mm baseline - ", end="")
    if our_mre < baseline_mre:
        improvement = (baseline_mre - our_mre) / baseline_mre * 100
        print(f"MEJOR ({improvement:.1f}% mejor)")
    else:
        print(f"PEOR")

    print(f"  SDR@2mm: {our_sdr2:.1f}% vs {baseline_sdr2}% baseline - ", end="")
    if our_sdr2 > baseline_sdr2:
        improvement = our_sdr2 - baseline_sdr2
        print(f"MEJOR (+{improvement:.1f}%)")
    else:
        print(f"PEOR")

    # Check for systematic failures
    print(f"\n" + "=" * 70)
    print("ANALISIS DE FALLOS SISTEMATICOS")
    print("=" * 70)
    worst_images_idx = np.argsort(all_mre_mm)[-5:]  # 5 peores
    print(f"5 imagenes con peor MRE:")
    for rank, img_idx in enumerate(worst_images_idx[::-1]):
        img_path = test_dataset.image_files[img_idx]
        print(f"  {rank+1}. {img_path.name}: MRE = {all_mre_mm[img_idx]:.3f} mm")
        worst_lm_idx = np.argmax(per_landmark_errors[img_idx])
        lm_name = landmark_names[worst_lm_idx] if worst_lm_idx < len(landmark_names) else f"LM{worst_lm_idx}"
        print(f"     Landmark mas erroneo: {lm_name} ({per_landmark_errors[img_idx, worst_lm_idx]:.2f} mm)")

    overfitting_check = np.mean(all_mre_mm) > 1.0
    if overfitting_check:
        print(f"\n[WARNING] ADVERTENCIA: MRE test ({np.mean(all_mre_mm):.3f}mm) > 1.0mm")
        print(f"   Posible overfitting (val fue 0.7952mm)")
    else:
        print(f"\n[OK] Modelo generaliza bien (MRE test = {np.mean(all_mre_mm):.3f}mm)")

    # Save results JSON
    results = {
        "test_set_size": len(test_dataset),
        "mre_mm_mean": float(np.mean(all_mre_mm)),
        "mre_mm_std": float(np.std(all_mre_mm)),
        "sdr_1mm": float(sdr1),
        "sdr_2mm": float(sdr2),
        "sdr_25mm": float(sdr25),
        "sdr_3mm": float(sdr3),
        "sdr_4mm": float(sdr4),
        "baseline_mre": baseline_mre,
        "baseline_sdr2": baseline_sdr2,
        "better_than_baseline": bool(our_mre < baseline_mre and our_sdr2 > baseline_sdr2),
        "pixel_size_mean": float(np.mean(pixel_sizes)),
    }

    results_path = viz_dir.parent / "test_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResultados guardados en: {results_path}")

    print("\n" + "=" * 70)
    print("EVALUACION COMPLETADA")
    print("=" * 70)


if __name__ == "__main__":
    main()