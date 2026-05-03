
#!/usr/bin/env python3
"""
Predict Module - AI-Cefalo Landmark Detection
Inferencia profesional con preprocesamiento CLAHE y escala no-uniforme.

Uso:
    python src/inference/predict.py --image path/to/imagen.jpg

Requisitos:
    - models/best_model.pth
    - data/preprocessed/{train,valid,test}_sizes.json
"""

import argparse
import json
import os
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn.functional as F
import yaml

# Rutas base
BASE_DIR = Path(__file__).parent.parent.parent
import sys
sys.path.insert(0, str(BASE_DIR))

# Configuraciones de red
from src.core.config import INPUT_SIZE_WH, INPUT_SIZE_HW, NUM_LANDMARKS, FALLBACK_SCALE
from src.models.unet import UNetResNet50


def load_config():
    """Carga configuración de entrenamiento."""
    cfg_path = BASE_DIR / "src" / "training" / "config.yaml"
    with open(cfg_path, "r") as f:
        return yaml.safe_load(f)


def preprocess_clahe_nlm(img_raw):
    """
    Preprocesamiento CLAHE + NLM + Z-score (SSOT).
    Mantiene tamaño original para escalado posterior.
    """
    # CLAHE (SSOT from config)
    from src.core.config import CLAHE_CLIP_LIMIT, CLAHE_TILE_GRID_SIZE
    clahe = cv2.createCLAHE(clipLimit=CLAHE_CLIP_LIMIT, tileGridSize=CLAHE_TILE_GRID_SIZE)
    img_clahe = clahe.apply(img_raw)

    # NLM Denoising
    img_nlm = cv2.fastNlMeansDenoising(
        img_clahe, None, h=10, templateWindowSize=7, searchWindowSize=21
    )

    # Z-score
    img_norm = (img_nlm.astype(np.float32) - img_nlm.mean()) / (img_nlm.std() + 1e-8)
    return img_norm


def load_original_sizes(mode="TEST"):
    """Carga tamaños originales desde JSON preprocesado."""
    sizes_path = BASE_DIR / "data" / "preprocessed" / f"{mode.lower()}_sizes.json"
    if not sizes_path.exists():
        # Si no existe (imagen externa), se calculará dinámicamente
        return {}
    with open(sizes_path, "r") as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(
        description="Detección de 29 landmarks cefalométricos (IA-Cefalo)"
    )
    parser.add_argument(
        "--image", "-i", type=str, required=True, help="Imagen de entrada (.jpg/.png)"
    )
    parser.add_argument(
        "--model",
        "-m",
        type=str,
        default=str(BASE_DIR / "models" / "best_model.pth"),
        help="Modelo entrenado",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="outputs/predictions/prediction.jpg",
        help="Imagen de salida",
    )
    parser.add_argument(
        "--json",
        "-j",
        type=str,
        default="outputs/predictions/landmarks.json",
        help="JSON de coordenadas",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("AI-CEFALO - Predicción de Landmarks")
    print("=" * 60)

    # 1. Cargar configuración
    cfg = load_config()
    print(f"[Config] Landmarks: {NUM_LANDMARKS}")
    print(f"[Config] Input size: {INPUT_SIZE_WH}")

    # 2. Cargar modelo
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = UNetResNet50(num_landmarks=NUM_LANDMARKS).to(device)
    model.eval()

    ckpt = torch.load(args.model, map_location=device, weights_only=False)
    model.load_state_dict(ckpt.get("model_state_dict", ckpt))
    print(f"[Modelo] Cargado desde: {args.model}")
    print(f"[Device] {device}")

    # 3. Leer imagen original
    img_path = Path(args.image)
    if not img_path.exists():
        raise FileNotFoundError(f"Imagen no encontrada: {img_path}")

    img_raw = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
    if img_raw is None:
        raise ValueError(f"No se pudo leer la imagen: {img_path}")

    H_orig, W_orig = img_raw.shape
    print(f"\n[Imagen] {img_path.name}")
    print(f"  Tamaño original: {W_orig}x{H_orig} px")

    # 4. Preprocesamiento (CLAHE + NLM + Z-score) en tamaño ORIGINAL
    img_processed = preprocess_clahe_nlm(img_raw)

    # 5. Redimensionar a INPUT_SIZE_WH (512x512) para el modelo
    # Usamos letterboxing para preservar aspect ratio
    target_w, target_h = INPUT_SIZE_WH
    if W_orig <= 0 or H_orig <= 0:
        scale_model = FALLBACK_SCALE  # Fallback si W_orig/H_orig <= 0
    else:
        scale_model = min(target_w / W_orig, target_h / H_orig)
    new_w = int(W_orig * scale_model)
    new_h = int(H_orig * scale_model)

    img_resized = cv2.resize(
        img_processed, (new_w, new_h), interpolation=cv2.INTER_LINEAR
    )

    # Padding a 512x512
    canvas = np.zeros((target_h, target_w), dtype=np.float32)
    y_pad = (target_h - new_h) // 2
    x_pad = (target_w - new_w) // 2
    canvas[y_pad : y_pad + new_h, x_pad : x_pad + new_w] = img_resized

    # Expandir dimensiones para PyTorch: (1, 1, 512, 512)
    img_tensor = torch.from_numpy(canvas).unsqueeze(0).unsqueeze(0).float().to(device)

    print(f"  Preprocesamiento: CLAHE + NLM + Z-score OK")
    print(f"  Redimensionado: {W_orig}x{H_orig} -> 512x512")
    print(f"  Padding: x={x_pad}, y={y_pad}, scale={scale_model:.4f}")

    # 6. INFERENCIA
    with torch.no_grad():
        heatmaps = model(img_tensor)
        coords_norm = model.decode_heatmaps(heatmaps)  # (1, 29, 2) en [0,1]

    # 7. Transformada inversa a COORDENADAS ORIGINALES
    # 7a. Llevar a espacio 512x512 (eliminar normalización)
    coords_512 = coords_norm.clone()
    coords_512[:, :, 0] *= INPUT_SIZE_WH[0]  # W
    coords_512[:, :, 1] *= INPUT_SIZE_HW[0]  # H

    # 7b. Eliminar padding del letterboxing
    coords_512[:, :, 0] -= x_pad
    coords_512[:, :, 1] -= y_pad

    # 7c. ESCALA NO-UNIFORME: llevar a tamaño original
    if new_w <= 0:
        scale_x_true = FALLBACK_SCALE
    else:
        scale_x_true = W_orig / new_w
    if new_h <= 0:
        scale_y_true = FALLBACK_SCALE
    else:
        scale_y_true = H_orig / new_h

    coords_orig = coords_512.clone()
    coords_orig[:, :, 0] *= scale_x_true  # Escala X
    coords_orig[:, :, 1] *= scale_y_true  # Escala Y

    # 8. Calcular errores (si hay ground truth disponible)
    #    En producción con imagen nueva, no hay GT
    pixel_size = None
    try:
        # Buscar en CSV de calibración si la imagen está
        csv_path = BASE_DIR / "data" / "raw" / "Aariz" / "cephalogram_machine_mappings.csv"
        if csv_path.exists():
            import csv
            with open(csv_path) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row["cephalogram_id"] == img_path.stem:
                        pixel_size = float(row["pixel_size"])
                        break
    except Exception:
        pass

    # Coordenadas finales (numpy)
    coords_np = coords_orig.squeeze(0).cpu().numpy()  # (29, 2)

    # 9. Visualización
    img_vis = cv2.cvtColor(img_raw, cv2.COLOR_GRAY2BGR)

    # Colores para landmarks
    colors = [
        (0, 0, 255),      # Rojo
        (0, 255, 0),      # Verde
        (255, 0, 0),      # Azul
        (0, 255, 255),    # Amarillo
        (255, 0, 255),    # Magenta
        (255, 128, 0),    # Naranja
    ]

    landmark_names = [
        "A", "ANS", "B", "Me", "N", "Or", "Pog",
        "PNS", "Pn", "R", "S", "Ar", "Co", "Gn",
        "Go", "Po", "LPM", "LIT", "LMT", "UPM",
        "UIA", "UIT", "UMT", "LIA", "Li", "Ls",
        "N'", "Pog'", "Sn"
    ]

    for i, (x, y) in enumerate(coords_np):
        x_int, y_int = int(round(x)), int(round(y))
        color = colors[i % len(colors)]

        # Punto
        cv2.circle(img_vis, (x_int, y_int), 4, color, -1)
        cv2.circle(img_vis, (x_int, y_int), 6, (255, 255, 255), 1)

        # Etiqueta
        label = f"{i}"
        cv2.putText(
            img_vis,
            label,
            (x_int + 6, y_int - 6),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            1,
            cv2.LINE_AA,
        )

    # Info en imagen
    info_text = f"AI-Cefalo | 29 landmarks"
    cv2.putText(
        img_vis,
        info_text,
        (10, 25),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 0),
        2,
        cv2.LINE_AA,
    )

    if pixel_size:
        # Calcular estadísticas si hay GT (solo test set)
        pass

    # 10. ANÁLISIS CEFALOMÉTRICO (Fase 2 - Motor Completo)
    from src.analysis.geometry import CephalometricAnalysis

    analisis = CephalometricAnalysis(
        coords_np,
        nombre_imagen=str(img_path.name),
        escala_mm=pixel_size,
    )
    full_analysis = analisis.reporte_json()

    # 11. Guardar resultados
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    os.makedirs(os.path.dirname(args.json), exist_ok=True)

    cv2.imwrite(args.output, img_vis)
    print(f"\n[Output] Imagen guardada: {args.output}")

    # Determinar clase esquelética basado en ANB
    # ANB > 4: Clase II (maxilar adelantado o mandíbula retraída)
    # ANB < 0: Clase III (mandíbula adelantada o maxilar retraído)
    # 0 <= ANB <= 4: Clase I (normal)
    anb = full_analysis.get("ANB")
    if anb is not None:
        if anb > 4:
            clase = "Clase II"
        elif anb < 0:
            clase = "Clase III"
        else:
            clase = "Clase I"
    else:
        clase = "N/A"

    # JSON
    landmarks_dict = {
        "image": str(img_path.name),
        "image_size": {"width": int(W_orig), "height": int(H_orig)},
        "model_input_size": list(INPUT_SIZE_WH),
        "landmarks": [],
        "landmark_names": landmark_names,
        "num_landmarks": NUM_LANDMARKS,
        "cephalometric_analysis": full_analysis,
        "skeletal_class": clase,
    }

    for i, (x, y) in enumerate(coords_np):
        landmarks_dict["landmarks"].append(
            {
                "id": i,
                "name": landmark_names[i] if i < len(landmark_names) else f"LM{i}",
                "x": float(x),
                "y": float(y),
            }
        )

    with open(args.json, "w") as f:
        json.dump(landmarks_dict, f, indent=2)

    print(f"[Output] JSON guardado: {args.json}")

    # 12. Resumen
    print("\n" + "=" * 60)
    print("COORDENADAS DETECTADAS (sub-píxel):")
    print("=" * 60)
    for i, (x, y) in enumerate(coords_np):
        name = landmark_names[i] if i < len(landmark_names) else f"LM{i}"
        print(f"  {name:3s} ({i:2d}): x={x:8.3f}, y={y:8.3f}")

    # 13. Reporte Steinert
    print(analisis.reporte_texto())

    if pixel_size:
        print(f"\n[Calibración] Pixel size: {pixel_size} mm/px")
        dist_mm = np.sqrt(
            np.sum((coords_np[1:] - coords_np[0]) ** 2, axis=1)
        ) * pixel_size
        print(f"[Distancias] Media: {dist_mm.mean():.3f} mm")

    print("\nOK Predicción completada exitosamente.")


if __name__ == "__main__":
    main()

