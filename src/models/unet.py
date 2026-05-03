import torch
import torch.nn as nn
import segmentation_models_pytorch as smp
from src.core.config import HEATMAP_SIZE_HW, NUM_LANDMARKS, INPUT_SIZE_HW


class UNetResNet50(nn.Module):
    """UNet with ResNet50 encoder for cephalometric landmark detection.

    Input: (N, 1, H, W) where (H, W) = INPUT_SIZE_HW from config.
    Output: (N, 29, H_hm, W_hm) where (H_hm, W_hm) = HEATMAP_SIZE_HW.
    """

    def __init__(self, num_landmarks=NUM_LANDMARKS, pretrained=True, dropout_p=0.1):
        super().__init__()
        self.num_landmarks = num_landmarks
        self.heatmap_size = HEATMAP_SIZE_HW  # (H, W) from config

        self.model = smp.Unet(
            encoder_name="resnet50",
            encoder_weights="imagenet" if pretrained else None,
            in_channels=1,
            classes=num_landmarks,
            activation=None,
        )
        # Dropout rate configurable, no hardcoded
        self.dropout = nn.Dropout2d(p=dropout_p)

    def forward(self, x):
        """Forward pass retornando heatmaps en [0,1].

        Args:
            x: (N, 1, H, W) - (N, C, H, W) con H,W desde config
        Returns:
            heatmaps: (N, 29, H_hm, W_hm) en rango [0, 1]
        """
        x = self.model(x)
        x = self.dropout(x)
        x = nn.functional.interpolate(
            x, size=self.heatmap_size, mode='bilinear', align_corners=False
        )
        x = torch.sigmoid(x)
        return x

    def predict_landmarks(self, x):
        """Predict landmarks from input image x usando argmax en heatmaps."""
        heatmaps = self.forward(x)
        return self.decode_heatmaps(heatmaps)

    def decode_heatmaps(self, heatmaps):
        """Decode heatmaps con refinamiento sub-píxel de segundo orden (ajuste parabólico).

        Tras encontrar el pico entero (px, py), extrae los vecinos inmediatos
        y aplica un ajuste cuadrático (Taylor de 2º orden) para obtener
        coordenadas sub-píxel con precisión teórica de ~0.25 píxeles.

        Args:
            heatmaps: (N, 29, H, W) - (N, C, H, W) con sigmoid aplicado
        Returns:
            landmarks: (N, 29, 2) en coordenadas normalizadas [0,1]
        """
        N, C, H, W = heatmaps.shape
        device = heatmaps.device

        # Encontrar posiciones de pico via argmax
        flat = heatmaps.view(N, C, -1)
        idx = flat.argmax(dim=-1)  # (N, C)

        px = (idx % W).float()
        py = (idx // W).float()

        # --- MEJORA V51.0: REFINAMIENTO SUB-PÍXEL ---
        # Ajuste parabólico de segundo orden (aproximación de Taylor)
        # H0 = pico, H1p = vecino derecha/abajo, H1m = vecino izquierda/arriba

        px_l = torch.clamp(px.long() - 1, 0, W - 1)
        px_r = torch.clamp(px.long() + 1, 0, W - 1)
        py_u = torch.clamp(py.long() - 1, 0, H - 1)
        py_d = torch.clamp(py.long() + 1, 0, H - 1)

        px_c = px.long().clamp(0, W - 1)
        py_c = py.long().clamp(0, H - 1)

        n_idx = torch.arange(N, device=device).view(N, 1).expand(N, C)
        c_idx = torch.arange(C, device=device).view(1, C).expand(N, C)

        H0 = heatmaps[n_idx, c_idx, py_c, px_c]       # (N, C) - pico central
        H1m_x = heatmaps[n_idx, c_idx, py_c, px_l]  # vecino izquierda
        H1p_x = heatmaps[n_idx, c_idx, py_c, px_r]  # vecino derecha
        H1m_y = heatmaps[n_idx, c_idx, py_u, px_c]  # vecino arriba
        H1p_y = heatmaps[n_idx, c_idx, py_d, px_c]  # vecino abajo

        # Refinamiento en X: dx = (H1p - H1m) / (2*(2*H0 - H1p - H1m) + eps)
        denom_x = (2.0 * H0 - H1p_x - H1m_x) * 2.0 + 1e-7
        dx = (H1p_x - H1m_x) / denom_x

        # Refinamiento en Y
        denom_y = (2.0 * H0 - H1p_y - H1m_y) * 2.0 + 1e-7
        dy = (H1p_y - H1m_y) / denom_y

        # Limitar el desplazamiento a +/- 0.5 píxeles para evitar divergencias
        dx = torch.clamp(dx, -0.5, 0.5)
        dy = torch.clamp(dy, -0.5, 0.5)

        x_refined = (px + dx) / W
        y_refined = (py + dy) / H

        return torch.stack([x_refined, y_refined], dim=-1)
