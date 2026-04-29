import csv
import json
from pathlib import Path

import cv2
import numpy as np
import torch
from torch.utils.data import Dataset

from src.core.config import (
    NUM_LANDMARKS,
    INPUT_SIZE_WH,
    INPUT_SIZE_HW,
    HEATMAP_SIZE_WH,
    HEATMAP_SIZE_HW,
    get_sigma_heatmap,
)
from src.core.geometry import generate_heatmap


class AarizDataset(Dataset):
    """Dataset Aariz para detección de 29 landmarks cefalométricos.

    Usa matrices de transformación afín rigurosas para data augmentation.
    Lee landmarks pre-escalados desde JSON (generado por precompute_images.py).

    Retorna: (imagen, heatmaps, landmarks, cvm_stage, pixel_size)
        - imagen: (1, H, W) preprocesada
        - heatmaps: (29, H_hm, W_hm) valores [0,1]
        - landmarks: (29, 2) normalizados a [0,1]
        - cvm_stage: int [0-6]
        - pixel_size: float (mm/pixel)
    """

    def __init__(self, dataset_folder_path: str, mode: str = "TRAIN"):
        super().__init__()
        self.dataset_path = Path(dataset_folder_path)
        self.mode = mode.upper()
        self.mode_lower = self.mode.lower()

        if self.mode not in ("TRAIN", "VALID", "TEST"):
            raise ValueError("mode must be 'TRAIN', 'VALID', or 'TEST'")

        self.mode_path = self._find_mode_dir()

        self.images_dir = self.mode_path / "Cephalograms"
        self.cvm_dir = self.mode_path / "Annotations" / "CVM Stages"

        self.preprocessed_dir = Path("data/preprocessed") / self.mode_lower
        self.heatmaps_dir = Path("data/heatmaps") / self.mode_lower

        self.sizes_json = Path("data/preprocessed") / f"{self.mode_lower}_sizes.json"
        self.sizes_dict = {}
        if self.sizes_json.exists():
            with open(self.sizes_json, "r") as f:
                self.sizes_dict = json.load(f)

        if not self.images_dir.exists():
            raise FileNotFoundError(
                f"Expected folder not found: {self.images_dir}\n"
                "Download from: https://doi.org/10.6084/m9.figshare.27986417.v1"
            )

        self._load_calibration()
        # Cargar configuración para augmentación
        try:
            config_path = Path(__file__).parent.parent / 'training' / 'config.yaml'
            import yaml
            with open(config_path, encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
        except Exception:
            self.config = {"data": {}}
        # Curriculum Learning: extraer épocas de curriculum y estado actual
        self.curriculum_epochs = self.config.get('training', {}).get('curriculum_epochs', 0)
        self.current_epoch = 0
        self.image_files = sorted(self._find_images())

    def set_epoch(self, epoch):
        """Establece la época actual para lógica de Curriculum Learning."""
        self.current_epoch = epoch

    def _find_mode_dir(self):
        """Encuentra directorio del split (train/valid/test)."""
        candidates = [
            self.dataset_path / self.mode,
            self.dataset_path / self.mode.capitalize(),
            self.dataset_path / self.mode_lower,
            self.dataset_path / self.mode_lower.replace("valid", "validation"),
        ]
        for c in candidates:
            if c.exists():
                return c
        return candidates[0]

    def _load_calibration(self):
        """Carga pixel_size (mm/pixel) desde CSV."""
        csv_path = self.dataset_path / "cephalogram_machine_mappings.csv"
        if not csv_path.exists():
            csv_path = self.dataset_path.parent / "cephalogram_machine_mappings.csv"
        if not csv_path.exists():
            self.calibration = {}
            return

        self.calibration = {}
        with open(csv_path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                pixel_size = float(row.get("pixel_size", 1.0))
                mode = row.get("mode", "").strip()
                if mode.upper() == self.mode:
                    self.calibration[row["cephalogram_id"].strip()] = pixel_size

    def _find_images(self):
        exts = ("*.jpg", "*.jpeg", "*.png", "*.bmp")
        files = []
        for ext in exts:
            files.extend(self.images_dir.glob(ext))
        return files

    def __len__(self):
        return len(self.image_files)

    def _build_affine_matrix(self, angle_deg, scale, tx, ty, cx, cy):
        """Construye matriz afín 2x3 para cv2.warpAffine con rotación sobre el centroide.

        CORRECCIÓN DE PIVOTE: Usa cv2.getRotationMatrix2D para rotar sobre
        el centro de la imagen (cx, cy), luego aplica escala y traslación.

        La matriz 2x3 resultante M garantiza:
            x' = M00*x + M01*y + M02
            y' = M10*x + M11*y + M12

        donde la rotación ocurre alrededor de (cx, cy), no en (0,0).
        """
        # cv2.getRotationMatrix2D rota sobre (cx, cy) — NO sobre origen
        M = cv2.getRotationMatrix2D((cx, cy), angle_deg, scale)  # (2, 3)

        # Sumar traslaciones adicionales (data augmentation aleatoria)
        M[0, 2] += tx
        M[1, 2] += ty

        return M.astype(np.float32)

    def _apply_affine_to_landmarks(self, landmarks, M):
        """Transforma landmarks usando multiplicación matricial rigurosa.

        Landmarks: (N, 2) en espacio de imagen
        M: matriz 2x3 de cv2.warpAffine

        Con coordenadas homogéneas:
            landmarks_homo = (N, 3)  # [x, y, 1]
            landmarks_transformed = landmarks_homo @ M.T  # (N, 2)

        Verificación matemática:
            x' = M00*x + M01*y + M02
            y' = M10*x + M11*y + M12
        """
        N = landmarks.shape[0]
        # Coordenadas homogéneas (N, 3): [x, y, 1]
        ones = np.ones((N, 1), dtype=np.float32)
        landmarks_homo = np.hstack([landmarks, ones])  # (N, 3)

        # M.T es (3, 2), resultado es (N, 2)
        landmarks_transformed = landmarks_homo @ M.T

        return landmarks_transformed.astype(np.float32)

    def __getitem__(self, idx):
        img_path = self.image_files[idx]
        stem = img_path.stem

        # 1. Cargar imagen preprocesada (tensor ya en espacio INPUT_SIZE_HW)
        img_path_pt = self.preprocessed_dir / f"{stem}.pt"
        if not img_path_pt.exists():
            raise FileNotFoundError(
                f"Preprocessed image not found: {img_path_pt}\n"
                "Run: python src/data/precompute_images.py"
            )
        img_tensor = torch.load(img_path_pt, weights_only=True)  # (1, H, W)

        # 2. Cargar landmarks ya escalados desde el JSON (NO recalcular)
        if stem not in self.sizes_dict or "landmarks_512" not in self.sizes_dict[stem]:
            raise KeyError(
                f"Landmarks not found in {self.sizes_json} for {stem}.\n"
                "Run: python src/data/precompute_images.py"
            )

        landmarks_scaled = np.array(
            self.sizes_dict[stem]["landmarks_512"], dtype=np.float32
        )  # (29, 2) en espacio INPUT_SIZE_WH

        cvm_stage = self._load_cvm(stem)
        pixel_size = self.calibration.get(stem, 1.0)

        # 3. DATA AUGMENTATION con matriz afín rigurosa (solo TRAIN)
        if self.mode == "TRAIN":
            img_np = img_tensor.squeeze(0).numpy()  # (H, W)
            H_img, W_img = img_np.shape

            if self.current_epoch >= self.curriculum_epochs:
                # FASE 2: Modo Difícil (Aumentación total)
                aug_cfg = self.config.get('data', {}).get('augmentation', {})
                ra = aug_cfg.get('random_affine', {})
                angle = np.random.uniform(-ra.get('degrees', 8.0), ra.get('degrees', 8.0))
                scale_aug = np.random.uniform(ra.get('scale', [0.9, 1.1])[0],
                                             ra.get('scale', [0.9, 1.1])[1])
                tx = np.random.uniform(-ra.get('translate', [0.06, 0.06])[0],
                                       ra.get('translate', [0.06, 0.06])[0]) * W_img
                ty = np.random.uniform(-ra.get('translate', [0.06, 0.06])[1],
                                       ra.get('translate', [0.06, 0.06])[1]) * H_img

                M = self._build_affine_matrix(
                    angle, scale_aug, tx, ty,
                    cx=W_img / 2.0, cy=H_img / 2.0,
                )

                img_aug_np = cv2.warpAffine(
                    img_np, M, (W_img, H_img),
                    flags=cv2.INTER_LINEAR,
                    borderMode=cv2.BORDER_CONSTANT,
                    borderValue=0,
                )

                landmarks_aug = self._apply_affine_to_landmarks(landmarks_scaled, M)
                landmarks_aug[:, 0] = np.clip(landmarks_aug[:, 0], 0, W_img - 1)
                landmarks_aug[:, 1] = np.clip(landmarks_aug[:, 1], 0, H_img - 1)

                img_tensor = torch.from_numpy(img_aug_np).unsqueeze(0).float()
                landmarks_scaled = landmarks_aug
            else:
                # FASE 1: Modo Fácil (Curriculum) - sin distorsión geométrica
                # La imagen y los landmarks permanecen en su estado original
                # (ya preprocesados a INPUT_SIZE)
                pass

        # 4. Normalizar landmarks a [0, 1] relativo a INPUT_SIZE_WH
        landmarks_normalized = landmarks_scaled.copy()
        landmarks_normalized[:, 0] /= INPUT_SIZE_WH[0]  # x / W
        landmarks_normalized[:, 1] /= INPUT_SIZE_WH[1]  # y / H

        # 5. Generar heatmaps dinámicos
        # Escalar landmarks de INPUT_SIZE_WH a HEATMAP_SIZE_WH
        landmarks_heatmap = landmarks_scaled.copy()
        landmarks_heatmap[:, 0] *= HEATMAP_SIZE_WH[0] / INPUT_SIZE_WH[0]
        landmarks_heatmap[:, 1] *= HEATMAP_SIZE_HW[0] / INPUT_SIZE_HW[1]

        heatmaps_tensor = generate_heatmap(
            landmarks_heatmap,
            H=HEATMAP_SIZE_HW[0],
            W=HEATMAP_SIZE_WH[1],
            sigma=get_sigma_heatmap(),
        )

        return img_tensor, heatmaps_tensor, landmarks_normalized, cvm_stage, pixel_size

    def _load_cvm(self, stem: str):
        """Carga etapa CVM (0 si no existe)."""
        cvm_path = self.cvm_dir / f"{stem}.json"
        if not cvm_path.exists():
            return 0
        with open(cvm_path, "r") as f:
            data = json.load(f)
        return int(data.get("cvm_stage", {}).get("value", 0))


def pixel_mre_to_mm(mre_pixels, pixel_size):
    """Convert MRE from pixels to millimeters using calibration."""
    return mre_pixels * pixel_size
