"""Training script for UNet+ResNet50 on Aariz dataset.

Usage:
    python src/training/train.py --config src/training/config.yaml

Optimizations applied:
    - CAPA 1: Heatmaps loaded from disk (pre-computed)
    - CAPA 2: DataLoader with num_workers=2, pin_memory, prefetch
    - CAPA 3: Automatic Mixed Precision (AMP) with GradScaler
    - CAPA 4: torch.compile() skipped on Windows (Triton unsupported)
"""

import argparse
import yaml
import sys
import os
import platform
import numpy as np

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torch.amp import autocast, GradScaler
import wandb

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.core.config import INPUT_SIZE_WH
from src.data.dataset import AarizDataset
from src.models.unet import UNetResNet50
from src.models.losses import CombinedLoss


def load_config(config_path):
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def create_dataloaders(config):
    """Create optimized train/val dataloaders."""
    dataset_path = config['data'].get('dataset_path', 'data/raw/Aariz')
    batch_size = config['training']['batch_size']
    num_workers = config['data'].get('num_workers', 2)

    train_ds = AarizDataset(dataset_path, mode='TRAIN')
    val_ds = AarizDataset(dataset_path, mode='VALID')

    train_loader = DataLoader(
        train_ds,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=True,
        prefetch_factor=2,
        persistent_workers=True
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True,
        prefetch_factor=2,
        persistent_workers=True
    )

    return train_loader, val_loader


def train_one_epoch(model, loader, criterion, optimizer, scaler, device, epoch, accumulation_steps=4):
    """Train one epoch with AMP and gradient accumulation."""
    model.train()
    total_loss = 0.0
    num_batches = len(loader)
    optimizer.zero_grad()

    for batch_idx, (images, target_heatmaps, landmarks, cvm_stages, pixel_sizes) in enumerate(loader):
        images = images.to(device, non_blocking=True)
        target_heatmaps = target_heatmaps.to(device, non_blocking=True)
        landmarks = landmarks.to(device, non_blocking=True)

        with autocast('cuda'):
            pred_heatmaps = model(images)
            pred_coords = model.decode_heatmaps(pred_heatmaps)
            loss = criterion(pred_heatmaps, target_heatmaps, pred_coords, landmarks) / accumulation_steps

        # 🛡️ Escudo Anti-NaN/Inf: Fail-fast para proteger hardware
        import math
        if math.isnan(loss.item()) or math.isinf(loss.item()):
            raise ValueError("🛑 ERROR CRÍTICO: El Loss explotó a NaN/Infinito. Entrenamiento abortado para proteger el hardware.")

        scaler.scale(loss).backward()

        if (batch_idx + 1) % accumulation_steps == 0 or (batch_idx + 1) == num_batches:
            scaler.step(optimizer)
            scaler.update()
            optimizer.zero_grad()

        total_loss += loss.item() * accumulation_steps

        if batch_idx % 10 == 0:
            print(f'Epoch {epoch}, Batch {batch_idx}/{num_batches}, Loss: {loss.item() * accumulation_steps:.4f}', flush=True)

    avg_loss = total_loss / num_batches
    return avg_loss


def evaluate(model, loader, criterion, device):
    """Evaluate model with clinical metrics: MRE (mm), SDR@2mm, etc."""
    model.eval()
    total_loss = 0.0
    num_batches = len(loader)

    sdr_2mm = 0
    sdr_25mm = 0
    sdr_3mm = 0
    sdr_4mm = 0
    total_landmarks = 0
    all_mre_px = []
    all_pixel_sizes = []

    with torch.no_grad():
        for images, target_heatmaps, landmarks, cvm_stages, pixel_sizes in loader:
            images = images.to(device, non_blocking=True)
            target_heatmaps = target_heatmaps.to(device, non_blocking=True)
            landmarks = landmarks.to(device, non_blocking=True)
            pixel_sizes_np = pixel_sizes.cpu().numpy() if isinstance(pixel_sizes, torch.Tensor) else np.array(pixel_sizes)

            with autocast('cuda'):
                pred_heatmaps = model(images)
                pred_coords = model.decode_heatmaps(pred_heatmaps)
                loss = criterion(pred_heatmaps, target_heatmaps, pred_coords, landmarks)
            total_loss += loss.item()

            # Denormalize coords from [0,1] to pixel space (512x512) for MRE
            pred_px = pred_coords.clone()
            pred_px[:, :, 0] *= INPUT_SIZE_WH[0]
            pred_px[:, :, 1] *= INPUT_SIZE_WH[1]

            target_px = landmarks.clone()
            target_px[:, :, 0] *= INPUT_SIZE_WH[0]
            target_px[:, :, 1] *= INPUT_SIZE_WH[1]

            # Calculate per-landmark distances using pixel-space coords
            for b in range(len(images)):
                ps = pixel_sizes_np[b] if not isinstance(pixel_sizes_np[b], torch.Tensor) else pixel_sizes_np[b].item()
                dists_px = torch.sqrt(((pred_px[b] - target_px[b]) ** 2).sum(dim=1))
                dists_mm = dists_px.cpu().numpy() * ps

                sdr_2mm += (dists_mm <= 2.0).sum()
                sdr_25mm += (dists_mm <= 2.5).sum()
                sdr_3mm += (dists_mm <= 3.0).sum()
                sdr_4mm += (dists_mm <= 4.0).sum()
                total_landmarks += len(dists_mm)

                mre_px = dists_px.mean().item()
                all_mre_px.append(mre_px)
                all_pixel_sizes.append(ps)

    # Calculate MRE in mm
    mre_mm = np.mean([mre_px * ps for mre_px, ps in zip(all_mre_px, all_pixel_sizes)])

    # Calculate SDR percentages
    sdr_2mm_pct = sdr_2mm / total_landmarks * 100 if total_landmarks > 0 else 0
    sdr_25mm_pct = sdr_25mm / total_landmarks * 100 if total_landmarks > 0 else 0
    sdr_3mm_pct = sdr_3mm / total_landmarks * 100 if total_landmarks > 0 else 0
    sdr_4mm_pct = sdr_4mm / total_landmarks * 100 if total_landmarks > 0 else 0

    avg_loss = total_loss / num_batches

    return avg_loss, mre_mm, sdr_2mm_pct, sdr_25mm_pct, sdr_3mm_pct, sdr_4mm_pct


def save_validation_debug(model, val_loader, device, epoch, output_dir="outputs"):
    """
    📸 Guarda una imagen de depuración con landmarks proyectados.
    Ejecuta una pasada de validación y guarda el primer batch con
    landmarks predichos vs ground truth dibujados.
    """
    import os
    import cv2
    import numpy as np
    from src.core.config import INPUT_SIZE_WH

    os.makedirs(output_dir, exist_ok=True)
    model.eval()

    with torch.no_grad():
        # Tomar primer batch de validación
        images, target_heatmaps, landmarks_gt, cvm_stages, pixel_sizes = next(iter(val_loader))
        images = images.to(device)

        # Predecir
        pred_heatmaps = model(images)
        pred_coords_norm = model.decode_heatmaps(pred_heatmaps)  # (N, 29, 2) en [0,1]

        # Desnormalizar para dibujar
        pred_coords = pred_coords_norm.clone()
        pred_coords[:, :, 0] *= INPUT_SIZE_WH[0]
        pred_coords[:, :, 1] *= INPUT_SIZE_WH[1]

        landmarks_gt_denorm = landmarks_gt.clone()
        landmarks_gt_denorm[:, :, 0] *= INPUT_SIZE_WH[0]
        landmarks_gt_denorm[:, :, 1] *= INPUT_SIZE_WH[1]

        # Tomar primera imagen del batch
        img = images[0].cpu().numpy().transpose(1, 2, 0)  # (H, W, 1) o (H, W, 3)

        # 🛠️ CORRECCIÓN: Normalización Min-Max dinámica para visualización perfecta
        img_min = img.min()
        img_max = img.max()
        img_norm = (img - img_min) / (img_max - img_min + 1e-8)  # Fuerza el rango a [0.0, 1.0]

        if img_norm.shape[2] == 1:
            img_norm = img_norm.squeeze(2)
            img_vis = cv2.cvtColor((img_norm * 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
        else:
            img_vis = (img_norm * 255).astype(np.uint8)
            # PyTorch usa RGB, OpenCV usa BGR para guardar
            img_vis = cv2.cvtColor(img_vis, cv2.COLOR_RGB2BGR)

        H, W = img_vis.shape[:2]

        # Dibujar landmarks GT (verdes) y Predichos (rojos)
        for i in range(landmarks_gt_denorm.shape[1]):
            # GT
            x_gt = int(landmarks_gt_denorm[0, i, 0].cpu().numpy())
            y_gt = int(landmarks_gt_denorm[0, i, 1].cpu().numpy())
            if 0 <= x_gt < W and 0 <= y_gt < H:
                cv2.circle(img_vis, (x_gt, y_gt), 2, (0, 255, 0), -1)

            # Predicho
            x_pred = int(pred_coords[0, i, 0].cpu().numpy())
            y_pred = int(pred_coords[0, i, 1].cpu().numpy())
            if 0 <= x_pred < W and 0 <= y_pred < H:
                cv2.circle(img_vis, (x_pred, y_pred), 2, (0, 0, 255), -1)

        # Etiqueta
        cv2.putText(img_vis, f"Epoch {epoch} | Verde=GT, Rojo=Pred",
                   (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

        out_path = os.path.join(output_dir, f"validation_debug_epoch_{epoch}.jpg")
        cv2.imwrite(out_path, img_vis)
        print(f"📸 Debug visual guardado: {out_path}")


def main():
    parser = argparse.ArgumentParser(description='Train UNet+ResNet50 for cephalometric landmarks')
    parser.add_argument(
        '--config', type=str, required=True, help='Path to config YAML'
    )
    parser.add_argument(
        '--resume', type=str, default=None, help='Checkpoint to resume from'
    )
    parser.add_argument(
        '--epochs', type=int, default=None, help='Number of epochs (overrides config)'
    )
    args = parser.parse_args()

    config = load_config(args.config)

    # Override epochs if provided
    if args.epochs is not None:
        config['training']['epochs'] = args.epochs

    # Setup wandb (configurable via environment or config)
    wandb_mode = config.get('wandb', {}).get('mode', os.environ.get('WANDB_MODE', 'disabled'))
    os.environ['WANDB_MODE'] = wandb_mode

    # Device
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f'Using device: {device}', flush=True)
    if device.type == 'cuda':
        print(f'GPU: {torch.cuda.get_device_name(0)}', flush=True)

    # Model
    print('Creating model...', flush=True)
    model = UNetResNet50(
        num_landmarks=config['model']['num_landmarks'],
        pretrained=config['model']['pretrained'],
    ).to(device)

    # torch.compile() skipped on Windows
    if platform.system() != 'Windows':
        print('Compiling model with torch.compile()...', flush=True)
        model = torch.compile(model)
    else:
        print('torch.compile() skipped (Windows - Triton not supported). Training in eager mode.', flush=True)

    # Carga de pesos pre-entrenados (Fine-tuning): intentar cargar best_model.pth
    best_model_path = 'models/best_model.pth'
    if os.path.exists(best_model_path):
        print(f'Loading pre-trained weights from {best_model_path}...', flush=True)
        try:
            checkpoint = torch.load(best_model_path, map_location=device, weights_only=False)
            if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
                model.load_state_dict(checkpoint['model_state_dict'])
            else:
                model.load_state_dict(checkpoint)
            print(f'Pre-trained weights loaded successfully.', flush=True)
        except Exception as e:
            print(f'Error loading {best_model_path}: {e}', flush=True)
            print('Starting from scratch.', flush=True)
    elif args.resume:
        print(f'Resuming from {args.resume}', flush=True)
        checkpoint = torch.load(args.resume, map_location=device, weights_only=False)
        if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
            model.load_state_dict(checkpoint['model_state_dict'])
        else:
            model.load_state_dict(checkpoint)
    else:
        print('No pre-trained weights found. Starting from scratch.', flush=True)

    # Optimizer
    optimizer = optim.AdamW(
        model.parameters(),
        lr=config['training']['lr'],
        weight_decay=config['training']['weight_decay'],
    )

    # AMP GradScaler
    scaler = GradScaler()

    # DataLoaders
    print('Loading data...', flush=True)
    train_loader, val_loader = create_dataloaders(config)

    # 🖥️ Telemetría RTX 4050 - Verificación de GPU
    if torch.cuda.is_available():
        print(f"✅ GPU detectada: {torch.cuda.get_device_name(0)}")
        print(f"✅ VRAM Total: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
    else:
        print("⚠️ ADVERTENCIA: Entrenando en CPU. Revisa tu instalación de CUDA.")

    # Loss (lambda_wing dinámico desde config; hard_mining_alpha eliminado)
    criterion = CombinedLoss(
        lambda_wing=config['loss'].get('lambda_wing', 0.1)
    )

    scheduler = optim.lr_scheduler.OneCycleLR(
        optimizer,
        max_lr=config['training']['lr'],
        epochs=config['training']['epochs'],
        steps_per_epoch=len(train_loader),
        pct_start=0.3,
        anneal_strategy='cos'
    )

    # Training loop
    best_val_mre = float('inf')
    epochs = config['training']['epochs']
    patience_counter = 0
    early_stop_patience = config['training'].get('early_stop_patience', 250)  # Configurable, default 250

    for epoch in range(1, epochs + 1):
        # Inyección de época actual para Curriculum Learning
        if hasattr(train_loader.dataset, 'set_epoch'):
            train_loader.dataset.set_epoch(epoch)
        elif hasattr(train_loader.dataset, 'dataset') and hasattr(train_loader.dataset.dataset, 'set_epoch'):
            train_loader.dataset.dataset.set_epoch(epoch)

        print(f"\n=== Epoch {epoch}/{epochs} ===", flush=True)

        train_loss = train_one_epoch(
            model, train_loader, criterion, optimizer, scaler, device, epoch, accumulation_steps=4
        )
        val_loss, val_mre_mm, val_sdr_2mm, val_sdr_25mm, val_sdr_3mm, val_sdr_4mm = evaluate(
            model, val_loader, criterion, device
        )

        # 📸 Debug visual en época 1 para verificar alineación geométrica
        if epoch == 1:
            save_validation_debug(model, val_loader, device, epoch)

        print(f"Train Loss: {train_loss:.4f}, Val Loss: {val_loss:.4f}", flush=True)
        print(f"Val MRE (mm): {val_mre_mm:.4f}, SDR@2mm: {val_sdr_2mm:.2f}%", flush=True)

        # Save best model
        if val_mre_mm < best_val_mre:
            best_val_mre = val_mre_mm
            checkpoint = {
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_loss': val_loss,
                'val_mre_mm': val_mre_mm,
                'val_sdr_2mm': val_sdr_2mm,
                'config': config,
            }
            os.makedirs('models', exist_ok=True)
            torch.save(checkpoint, 'models/best_model.pth')
            print(f'Saved best model at epoch {epoch}, val_MRE_mm: {val_mre_mm:.4f}, SDR@2mm: {val_sdr_2mm:.2f}%', flush=True)

        # Early stopping
        if val_mre_mm >= best_val_mre:
            patience_counter += 1
            if patience_counter >= early_stop_patience:
                print(f'Early stopping triggered at epoch {epoch}, best val MRE: {best_val_mre:.4f} mm', flush=True)
                break
        else:
            patience_counter = 0

    # Save final model
    os.makedirs('models', exist_ok=True)
    torch.save(model.state_dict(), 'models/unet_final.pth')

    print(f'\nTraining complete! Best val MRE (mm): {best_val_mre:.4f}', flush=True)


if __name__ == '__main__':
    main()
