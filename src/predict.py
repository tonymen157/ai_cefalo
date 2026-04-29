"""
Pipeline de Inferencia Dinámico (Cero Hardcoding).
Procesa radiografías de producción para detección de 29 landmarks cefalométricos.

Reglas:
- Cero hardcoding de resoluciones (usa INPUT_SIZE_WH del config).
- Cero hardcoding de número de landmarks (usa num_landmarks del config).
- Coordenadas sub-píxel preservadas hasta el último escalado afín.

Uso:
    python src/predict.py --image data/raw/Aariz/Train/Cephalograms/cks2ip8fq29yq0yufc4scftj8.png
"""

import argparse
import sys
import os
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn.functional as F
import yaml

# Añadir src al path para importaciones locales
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import INPUT_SIZE_WH, INPUT_SIZE_HW, HEATMAP_SIZE_HW, HEATMAP_SIZE_WH, get_sigma_heatmap
from src.models.unet import UNetResNet50


def load_config(config_path="src/training/config.yaml"):
    """Carga config.yaml dinámicamente."""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def preprocess_image(img_path, target_size):
    """
    Pre-procesamiento geométrico dinámico.

    Args:
        img_path: Ruta a la radiografía en escala de grises.
        target_size: Tupla (W, H) desde INPUT_SIZE_WH.

    Returns:
        img_tensor: (1, 1, H, W) float32 en [0, 1].
        img_bgr: Copia BGR de la imagen original para dibujar.
        (H_real, W_real): Topología original.
    """
    # Leer imagen original
    img_raw = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
    if img_raw is None:
        raise FileNotFoundError(f"No se pudo leer la imagen: {img_path}")

    H_real, W_real = img_raw.shape

    # Resize dinámico usando INPUT_SIZE_WH (preserva aspecto con letterboxing implícito)
    # Nota: para inferencia consistente con el entrenamiento, usamos letterboxing.
    target_w, target_h = target_size
    scale = min(target_w / W_real, target_h / H_real)
    new_w = int(W_real * scale)
    new_h = int(H_real * scale)

    img_resized = cv2.resize(img_raw, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

    # Letterboxing (padding negro) para completar target_size
    canvas = np.zeros((target_h, target_w), dtype=np.float32)
    y_offset = (target_h - new_h) // 2
    x_offset = (target_w - new_w) // 2
    canvas[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = img_resized

    # Normalizar a [0, 1] (flotante)
    if canvas.max() > 1.0:
        canvas = canvas / 255.0

    # Expandir dimensiones: (1, 1, H, W) para PyTorch (batch, channel, height, width)
    img_tensor = torch.from_numpy(canvas).unsqueeze(0).unsqueeze(0).float()

    # Convertir original a BGR para dibujar puntos después
    img_bgr = cv2.cvtColor(img_raw, cv2.COLOR_GRAY2BGR)

    return img_tensor, img_bgr, (H_real, W_real), (x_offset, y_offset, scale)


def main():
    parser = argparse.ArgumentParser(description="Inferencia de landmarks cefalométricos (cero hardcoding).")
    parser.add_argument("--image", type=str, required=True, help="Ruta de la radiografía de entrada.")
    parser.add_argument("--config", type=str, default="src/training/config.yaml", help="Ruta al config YAML.")
    parser.add_argument("--model", type=str, default="models/best_model.pth", help="Ruta al modelo entrenado.")
    parser.add_argument("--output", type=str, default="outputs/prediction.jpg", help="Ruta de salida.")
    args = parser.parse_args()

    # 1. Importaciones dinámicas desde config
    cfg = load_config(args.config)
    num_landmarks = cfg["model"]["num_landmarks"]
    print(f"[INFO] num_landmarks desde config: {num_landmarks}")
    print(f"[INFO] INPUT_SIZE_WH desde config: {INPUT_SIZE_WH}")

    # Device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[INFO] Usando device: {device}")

    # 2. Inicialización del motor
    model = UNetResNet50(num_landmarks=num_landmarks, pretrained=False).to(device)
    model.eval()

    # Cargar pesos (sin map_location en state_dict directamente por simplicidad)
    checkpoint = torch.load(args.model, map_location=device, weights_only=False)
    if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
        model.load_state_dict(checkpoint["model_state_dict"])
    else:
        model.load_state_dict(checkpoint)
    print(f"[INFO] Modelo cargado desde: {args.model}")

    # 3. Pre-procesamiento geométrico
    img_tensor, img_bgr, (H_real, W_real), (x_off, y_off, scale) = preprocess_image(
        args.image, target_size=INPUT_SIZE_WH
    )
    img_tensor = img_tensor.to(device)

    # 4. Forward pass y centro de masa (decode_heatmaps ya implementa soft-argmax sub-píxel)
    with torch.no_grad():
        heatmaps = model(img_tensor)  # (1, C, H_hm, W_hm)
        coords_norm = model.decode_heatmaps(heatmaps)  # (1, C, 2) en [0, 1]

    # Llevar a espacio de INPUT_SIZE_WH (antes de recorte/padding)
    coords_input = coords_norm.clone()
    coords_input[:, :, 0] *= INPUT_SIZE_WH[0]  # X
    coords_input[:, :, 1] *= INPUT_SIZE_HW[1]  # Y

    # 5. Transformación afín inversa: quitar padding y escalar a espacio real
    # Restar padding
    coords_input[:, :, 0] -= x_off
    coords_input[:, :, 1] -= y_off

    # Dividir por scale para llevar al tamaño original (sin redondear aún)
    coords_real = coords_input.clone()
    coords_real[:, :, 0] /= scale
    coords_real[:, :, 1] /= scale

    # Convertir a numpy (mantener precisión sub-píxel hasta aquí)
    coords_np = coords_real.squeeze(0).cpu().numpy()  # (C, 2)

    # Solo para dibujar: redondear a enteros
    coords_draw = np.round(coords_np).astype(np.int32)

    # 6. I/O y exportación
    # Dibujar puntos y etiquetas
    for i, (x, y) in enumerate(coords_draw):
        cv2.circle(img_bgr, (x, y), 3, (0, 0, 255), -1)           # punto rojo
        cv2.circle(img_bgr, (x, y), 5, (0, 255, 255), 1)         # círculo amarillo
        cv2.putText(img_bgr, str(i), (x + 4, y - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

    # Asegurar directorio de salida
    os.makedirs(os.path.dirname(args.output) if os.path.dirname(args.output) else ".", exist_ok=True)
    cv2.imwrite(args.output, img_bgr)
    print(f"[INFO] Predicción guardada en: {args.output}")

    # Imprimir coordenadas reales (preservando precisión sub-píxel)
    print("\n[COORDENADAS REALES (sub-píxel)]:")
    print(coords_np)


if __name__ == "__main__":
    main()
