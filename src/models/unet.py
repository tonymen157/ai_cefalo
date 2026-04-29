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
        """Soft-argmax decoding con ventana 3x3 para sub-pixel.

        Usa cálculo de centroide local en ventana 3x3 alrededor del pico
        para obtener coordenadas fraccionales (sub-píxel), eliminando
        errores de discretización del argmax estándar.

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

        # Soft-argmax en ventana 3x3 para precisión sub-píxel
        py_c = torch.clamp(py, 1, H - 2).long()
        px_c = torch.clamp(px, 1, W - 2).long()

        offs = torch.tensor([-1, 0, 1], dtype=torch.long, device=device)
        yyi, xxi = torch.meshgrid(offs, offs, indexing='ij')

        n_idx = torch.arange(N, device=device).view(N, 1, 1, 1).expand(N, C, 3, 3)
        c_idx = torch.arange(C, device=device).view(1, C, 1, 1).expand(N, C, 3, 3)
        py_3d = py_c.view(N, C, 1, 1).expand(N, C, 3, 3)
        px_3d = px_c.view(N, C, 1, 1).expand(N, C, 3, 3)
        yyi_3d = yyi.view(1, 1, 3, 3).expand(N, C, 3, 3)
        xxi_3d = xxi.view(1, 1, 3, 3).expand(N, C, 3, 3)

        patches = heatmaps[n_idx, c_idx, py_3d + yyi_3d, px_3d + xxi_3d]

        w = torch.softmax(patches.view(N, C, 9), dim=-1).view(N, C, 3, 3)

        off_f = torch.tensor([-1.0, 0.0, 1.0], dtype=torch.float32, device=device)
        yyf, xxf = torch.meshgrid(off_f, off_f, indexing='ij')
        yyf_3d = yyf.view(1, 1, 3, 3).expand(N, C, 3, 3)
        xxf_3d = xxf.view(1, 1, 3, 3).expand(N, C, 3, 3)

        eps = 1e-8
        sum_w = w.sum(dim=(2, 3)) + eps
        dy = (w * yyf_3d).sum(dim=(2, 3)) / sum_w
        dx = (w * xxf_3d).sum(dim=(2, 3)) / sum_w

        # Normalizar a [0,1] usando dimensiones dinámicas del heatmap
        x_sp = torch.clamp((px + dx) / W, 0.0, 1.0)
        y_sp = torch.clamp((py + dy) / H, 0.0, 1.0)

        return torch.stack([x_sp, y_sp], dim=-1)
