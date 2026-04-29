"""
Notebook: 03_unet_training.ipynb
Fase 3 - Entrenamiento UNet+ResNet50

Este notebook muestra el entrenamiento con wandb, visualización de heatmaps,
y métricas MRE en mm (usando calibración).
"""

# Celda 1: Instalar dependencias
"""
!pip install -q torch torchvision segmentation-models-pytorch opencv-python albumentations wandb
"""

# Celda 2: Imports
"""
import torch
import wandb
from src.data.dataset import AarizDataset
from src.models.unet import UNetResNet50
from src.models.losses import CombinedLoss
from src.training.train import create_dataloaders, train_one_epoch, evaluate
import matplotlib.pyplot as plt
import numpy as np
"""

# Celda 3: Inicializar wandb
"""
wandb.init(
    project="aicefalo",
    entity="steven",  # Cambiar por tu usuario wandb
    name="unet-resnet50-lr1e4-bs8",
    config={
        "model": "unet-resnet50",
        "lr": 1e-4,
        "batch_size": 8,
        "epochs": 200,
        "num_landmarks": 29,
        "loss": "mse+wing",
        "lambda_wing": 0.1,
        "sigma_heatmap": 5.0,
        "input_size": [576, 736],
        "heatmap_size": [144, 184],
    }
)
"""

# Celda 4: Cargar datasets
"""
from src.training.train import create_dataloaders

train_loader, val_loader = create_dataloaders(dataset_path="data/raw/Aariz")
print(f"Train batches: {len(train_loader)}")
print(f"Val batches: {len(val_loader)}")
"""

# Celda 5: Crear modelo
"""
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Device: {device}")

model = UNetResNet50(num_landmarks=29, pretrained=True)
model.to(device)
print(f"Model created: UNet+ResNet50")
print(f"Parameters: {sum(p.numel() for p in model.parameters()) / 1e6:.2f}M")
"""

# Celda 6: Optimizador y Loss
"""
import torch.optim as optim
from src.models.losses import CombinedLoss

optimizer = optim.AdamW(model.parameters(), lr=1e-4, weight_decay=1e-5)
scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=200)
criterion = CombinedLoss(lambda_wing=0.1)

print("Optimizer: AdamW, lr=1e-4")
print("Scheduler: CosineAnnealingLR")
print("Loss: MSE + WingLoss (lambda=0.1)")
"""

# Celda 7: Loop de entrenamiento (ejecutar)
"""
# Descomentar para entrenar
# for epoch in range(1, 201):
#     train_loss = train_one_epoch(model, train_loader, criterion, optimizer, device, epoch)
#     val_loss = evaluate(model, val_loader, criterion, device)
#
#     wandb.log({
#         "epoch": epoch,
#         "train/loss": train_loss,
#         "val/loss": val_loss,
#         "lr": optimizer.param_groups[0]['lr'],
#     })
#
#     if val_loss < best_val_loss:
#         torch.save(model.state_dict(), "models/best_model.pth")
#         wandb.save("models/best_model.pth")
#         best_val_loss = val_loss
#
#     scheduler.step()
#
# wandb.finish()
"""

# Celda 8: Visualizar un heatmap
"""
import numpy as np
import matplotlib.pyplot as plt

# Cargar modelo entrenado
checkpoint = torch.load("models/best_model.pth", map_location="cpu")
model.load_state_dict(checkpoint)
model.eval()

# Obtener una muestra
ds = AarizDataset("data/raw/Aariz", mode="VALID")
img, landmarks, cvm, pixel_size = ds[0]
print(f"Image shape: {img.shape}")
print(f"Landmarks shape: {landmarks.shape}")
print(f"Pixel size: {pixel_size} mm/pixel")

# Forward pass
with torch.no_grad():
    output = model(img.unsqueeze(0))  # (1, 29, 144, 184)
    heatmap = output[0, 0].numpy()  # Primer landmark

plt.figure(figsize=(6, 6))
plt.imshow(heatmap, cmap='hot')
plt.colorbar()
plt.title("Heatmap: Landmark 0 (Sella) - Predicción")
plt.show()

print(f"Heatmap shape: {heatmap.shape}")
print(f"Max value: {heatmap.max():.4f}")
"""

# Celda 9: Calcular MRE en mm para validación
"""
from src.api.services.steiner_calculator import pixels_to_mm

# Cargar modelo y evaluar
model.eval()
total_mre_mm = 0.0
num_samples = 50  # Subconjunto para prueba rápida

with torch.no_grad():
    for i in range(num_samples):
        img, landmarks_gt, cvm, pixel_size = ds[i]

        # Predicción
        pred_heatmaps = model(img.unsqueeze(0))  # (1, 29, 144, 184)

        # Decodificar landmarks (argmax)
        import numpy as np
        pred_landmarks = np.zeros((29, 2))
        for lm in range(29):
            hm = pred_heatmaps[0, lm].numpy()
            y, x = np.unravel_index(hm.argmax(), hm.shape)
            pred_landmarks[lm, 0] = x * (736.0 / 144.0)
            pred_landmarks[lm, 1] = y * (576.0 / 144.0)

        # Calcular MRE en pixels
        diff = pred_landmarks - landmarks_gt.numpy()
        mre_pixels = np.mean(np.sqrt(np.sum(diff**2, axis=1)))
        mre_mm = mre_pixels * pixel_size

        total_mre_mm += mre_mm

        if i % 10 == 0:
            print(f"Sample {i}: MRE = {mre_mm:.2f} mm")

avg_mre_mm = total_mre_mm / num_samples
print(f"\nAverage MRE on validation: {avg_mre_mm:.2f} mm")
print(f"Target: < 2.5 mm")
"""
