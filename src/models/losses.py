import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np

from src.core.config import (
    INPUT_SIZE_WH,
    HEATMAP_SIZE_HW,
    HEATMAP_SIZE_WH,
    get_sigma_heatmap,
    NUM_LANDMARKS,
)


class WingLoss(nn.Module):
    """Wing Loss dinámico para coordenadas normalizadas [0,1].

    Los parámetros w y epsilon se derivan automáticamente del espacio de coordenadas.
    Si las coordenadas están en [0,1] (INPUT_SIZE_WH), los valores originales
    (w=10.0, epsilon=2.0 para 512px) se escalan a espacio normalizado.
    """

    def __init__(self, w=None, epsilon=None):
        super().__init__()
        # Valores para espacio normalizado [0,1] con heatmaps sigma=5.0
        # Leer desde config si no se pasan explícitamente
        if w is None or epsilon is None:
            try:
                from src.core.config import get_loss_config
                loss_cfg = get_loss_config()
                if w is None: w = loss_cfg.get('wing', {}).get('w', 0.05)
                if epsilon is None: epsilon = loss_cfg.get('wing', {}).get('epsilon', 0.01)
            except:
                if w is None: w = 0.05
                if epsilon is None: epsilon = 0.01
        self.w = w
        self.epsilon = epsilon
        self.C = self.w - self.w * (1.0 / (1.0 + self.w / self.epsilon))

    def forward(self, pred, target):
        """
        Args:
            pred: (N, num_landmarks, 2) en [0,1] normalizado
            target: (N, num_landmarks, 2) en [0,1] normalizado
        """
        diff = torch.abs(pred - target)
        loss = torch.where(
            diff < self.w,
            self.w * torch.log(1.0 + diff / self.epsilon),
            diff - self.C,
        )
        return loss.mean()


class CombinedLoss(nn.Module):
    """Combined Loss: Heatmap MSE + WingLoss con pesos dinámicos.

    El pos_weight para heatmaps se calcula dinámicamente como:
        pos_weight = (H * W) / (π * (3σ)²)
    donde (H, W) es el tamaño del heatmap y σ el sigma dinámico.
    Esto balancea foreground (Gaussiana) vs background (píxeles negativos).
    """

    def __init__(self, lambda_wing=None, foreground_threshold=None):
        super().__init__()
        self.mse = nn.MSELoss(reduction='none')
        self.wing = WingLoss()  # Parámetros dinámicos

        # pos_weight fijo para balancear foreground/background
        self.pos_weight_value = 100.0

        # lambda_wing dinámico: balancea MSE (~0.01-0.1) vs WingLoss (~0.01-0.05)
        # En espacio normalizado [0,1], MSE y WingLoss son comparables
        if lambda_wing is None:
            self.lambda_wing = 0.1  # Valor por defecto razonable
        else:
            self.lambda_wing = lambda_wing

        # Umbral para distinguir foreground/background en heatmaps
        if foreground_threshold is None:
            try:
                from src.core.config import get_loss_config
                loss_cfg = get_loss_config()
                self.foreground_threshold = loss_cfg.get('foreground_threshold', 0.01)
            except:
                self.foreground_threshold = 0.01
        else:
            self.foreground_threshold = foreground_threshold

        # Precálculo de pos_weight tensor (se inicializa en primer forward)
        self._pos_weight_tensor = None

    def _get_pos_weight(self, device):
        """Retorna pos_weight como tensor en el device correcto."""
        if self._pos_weight_tensor is None or self._pos_weight_tensor.device != device:
            self._pos_weight_tensor = torch.tensor(
                [self.pos_weight_value], device=device
            )
        return self._pos_weight_tensor

    def forward(
        self,
        pred_heatmaps,
        target_heatmaps,
        pred_coords=None,
        target_coords=None,
    ):
        """
        Args:
            pred_heatmaps: (N, C, H, W) heatmaps con sigmoid aplicado
            target_heatmaps: (N, C, H, W) Gaussianos [0,1]
            pred_coords: (N, 29, 2) en [0,1] para WingLoss
            target_coords: (N, 29, 2) en [0,1] para WingLoss
        """
        device = pred_heatmaps.device

        # MSE con peso espacial: foreground (Gaussiana) > background
        mse_per_pixel = self.mse(pred_heatmaps, target_heatmaps)  # (N, C, H, W)

        # Máscara: píxeles con Gaussiana (>0.01) reciben pos_weight,
        # píxeles de fondo (<=0.01) peso = 1.0
        pw = self._get_pos_weight(device)
        weight_mask = torch.where(target_heatmaps > self.foreground_threshold, pw, torch.tensor(1.0, device=device))
        mse_loss = (mse_per_pixel * weight_mask).mean()

        # WingLoss para coordenadas (si se proporcionan)
        if pred_coords is not None and target_coords is not None:
            wing_loss = self.wing(pred_coords, target_coords)
            return mse_loss + self.lambda_wing * wing_loss

        return mse_loss

    @property
    def pos_weight(self):
        """Getter para el pos_weight calculado dinámicamente."""
        return self.pos_weight_value
