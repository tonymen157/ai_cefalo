# AI-Cefalo: Plan Técnico Completo
### Sistema de Detección Automática de Puntos Cefalométricos

---

## Índice

1. [Visión General del Proyecto](#1-visión-general-del-proyecto)
2. [Fuentes de Datos](#2-fuentes-de-datos)
3. [Arquitectura del Sistema](#3-arquitectura-del-sistema)
4. [Modelos de AA Recomendados](#4-modelos-de-aa-recomendados)
5. [Pipeline de Entrenamiento](#5-pipeline-de-entrenamiento)
6. [Plan de Evaluación y Métricas](#6-plan-de-evaluación-y-métricas)
7. [Plan de Pruebas (Testing)](#7-plan-de-pruebas-testing)
8. [Planificación por Fases](#8-planificación-por-fases)
9. [Stack Tecnológico](#9-stack-tecnológico)
10. [Estructura del Repositorio](#10-estructura-del-repositorio)
11. [Consideraciones Legales y Éticas](#11-consideraciones-legales-y-éticas)

---

## 1. Visión General del Proyecto

### ¿Qué es la Cefalometría?
El análisis cefalométrico consiste en marcar entre **19 y 21 puntos anatómicos** (landmarks) sobre una radiografía lateral de cráneo para calcular ángulos y medidas que determinan el diagnóstico ortodóncico de un paciente.

### Problema que Resuelve AI-Cefalo
- Los estudiantes tardan **30–60 minutos** por radiografía marcando puntos manualmente.
- El margen de error humano en landmarks es de **2–4 mm**, afectando el diagnóstico.
- Es la tarea más repetida y odiada en los primeros años de ortodoncia.

### Propuesta de Valor
> "El estudiante sube su radiografía lateral, la IA coloca los 19 puntos anatómicos, calcula los ángulos del análisis de Steiner/Ricketts, y genera un reporte PDF imprimible en 15 segundos."

### Puntos a Detectar (estándar Aariz — 29 landmarks)
```
ÓSEOS CRANEALES:
1.  Sella (S)              6.  Nasion (N)
2.  Articular (Ar)         7.  Orbitale (Or)
3.  Porion (Po)            8.  Espina Nasal Ant. (ANS)
4.  Espina Nasal Post.     5.  Punto A

ÓSEOS MANDIBULARES:
9.  Punto B               12.  Pogonion (Pog)
10. Menton (Me)           13.  Gnathion (Gn)
11. Gonion (Go)

DENTALES:
14. Incisivo sup. borde   17.  Incisivo inf. borde
15. Incisivo sup. ápice   18.  Incisivo inf. ápice
16. Molar sup. cúspide    19.  Molar inf. cúspide

TEJIDOS BLANDOS (exclusivos de Aariz vs ISBI):
20. Punta nariz           25.  Labio sup. (Ls)
21. Subnasal (Sn)         26.  Labio inf. (Li)
22. Pogonion blando       27.  Menton blando
23. Glabela               28.  Stomion sup.
24. Stomion inf.          29.  Punto Cervical (C)
```

> **Nota para el agente de programación:** El dataset usa 29 landmarks. El modelo debe tener `num_landmarks = 29` y generar 29 heatmaps en el output. No confundir con versiones antiguas del plan que decían 19 landmarks (eso era ISBI 2015). Todos los configs, loss functions y métricas deben usar `NUM_LANDMARKS = 29`.

---

## 2. Fuentes de Datos

### Dataset Principal — Aariz ⭐ USAR ESTE

| Atributo | Detalle |
|---|---|
| **Nombre** | Aariz Cephalometric Landmark Dataset |
| **Imágenes** | 1000 radiografías laterales (700 train / 150 val / 150 test) |
| **Resolución** | Variable (7 dispositivos distintos) |
| **Anotaciones** | 29 landmarks por imagen + etiqueta CVM stage |
| **Formato** | PNG/JPG + JSON con coordenadas |
| **Acceso** | 100% público, descarga directa sin email |
| **GitHub** | https://github.com/manwaarkhd/aariz-cephalometric-dataset |
| **Paper** | Nature Scientific Data, 2025 |

**Cómo descargarlo (3 pasos):**
```bash
# Opción 1 — Git clone directo
git clone https://github.com/manwaarkhd/aariz-cephalometric-dataset.git

# Opción 2 — Solo el dataset sin el código
# Ir a la pestaña "Releases" del repositorio y descargar el .zip

# Verificar que tienes la estructura correcta
ls aariz-cephalometric-dataset/
# → images/  annotations/  README.md  dataset.py
```

**Cómo cargar el dataset (código oficial del repo):**
```python
from dataset import AarizDataset

train_dataset = AarizDataset(
    dataset_folder_path="./aariz-cephalometric-dataset",
    mode="TRAIN"  # opciones: TRAIN, VALID, TEST
)

# Cada item retorna:
image, landmarks, cvm_stage = train_dataset[0]
# image:     tensor (C, H, W)
# landmarks: tensor (29, 2) → coordenadas (x, y) de cada punto
# cvm_stage: int (1-6) → etapa de maduración cervical
```

### Dataset Secundario — ISBI 2015 (Referencia Histórica)

| Atributo | Detalle |
|---|---|
| **Nombre** | IEEE ISBI 2015 Grand Challenge |
| **Imágenes** | 400 radiografías (150 train / 250 test) |
| **Landmarks** | 19 (subconjunto de los 29 de Aariz) |
| **Acceso** | Requiere email al Dr. Chia-Wei Chen (NTUST, Taiwan) |
| **Cuándo usarlo** | Solo para comparar métricas con papers antiguos |

> **Decisión:** No pierdas tiempo pidiendo el ISBI por email. Aariz tiene 2.5x más imágenes, más landmarks, es público, y fue publicado en Nature 2025. Es estrictamente mejor.

### Dataset Complementario — CEPHMark-Net (Solo el Modelo, NO los Datos)

> **IMPORTANTE para el agente:** El repositorio `manwaarkhd/CEPHMark-Net` en GitHub **NO contiene datos**. Es únicamente la implementación del modelo CNN. Sirve como referencia de arquitectura, pero los datos deben venir de Aariz. No intentar extraer imágenes de ese repo.

### Datos de la Universidad (Canal Privilegiado)
Solicitar al departamento de Ortodoncia casos anonimizados (sin nombre ni fecha del paciente). Cada caso = 1 radiografía + trazado corregido por el profesor.

```
Meta: Recolectar 100–200 casos locales en 3 meses
Valor agregado: Morfología craneofacial latinoamericana/andina,
subrepresentada en todos los datasets existentes (asiáticos y europeos)
Formato a pedir: JPEG o BMP + archivo con coordenadas de los 19 puntos mínimos
```

---

## 3. Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND (Web App)                    │
│  Sube RX → Visualiza landmarks → Descarga reporte PDF   │
└───────────────────────┬─────────────────────────────────┘
                        │ REST API (FastAPI)
┌───────────────────────▼─────────────────────────────────┐
│                  BACKEND (Python)                        │
│  Preprocesamiento → Inferencia → Cálculo de ángulos     │
└───────────────────────┬─────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
   Modelo AA      Base de Datos    Generador PDF
  (PyTorch)       (PostgreSQL)    (ReportLab)
```

### Flujo de Datos
```
RX JPEG/PNG → Normalización → Resize 512×512 → 
→ Modelo CNN → 19 coordenadas (x,y) → 
→ Escalar a resolución original → 
→ Calcular ángulos (SNA, SNB, ANB...) → 
→ Clasificar patrón esquelético → Reporte PDF
```

---

## 4. Modelos de AA Recomendados

### Opción A — UNet con Heatmap Regression ⭐ RECOMENDADO

**¿Por qué?** Es el estado del arte para detección de landmarks médicos. Genera un mapa de calor por cada punto, lo que da incertidumbre visual y es interpretable.

```
Arquitectura: UNet modificada con ResNet-50 como encoder
Input:  1 imagen grayscale (512×512)
Output: 19 heatmaps (uno por landmark) de 128×128
Landmark final: argmax del heatmap + refinamiento subpixel
```

**Papers de referencia:**
- "Automatic cephalometric landmark detection by AttentionU-Net" — 2020
- "Cephalometric Landmark Detection by AttentionU-Net with Heatmap Supervision" — ISBI 2021

### Opción B — Vision Transformer (ViT) + Regression Head

```
Arquitectura: ViT-Base pretrained en ImageNet
Fine-tuning: Dataset ISBI
Output: Vector de 38 valores (19 puntos × 2 coordenadas)
Ventaja: Captura contexto global (relaciones entre puntos distantes)
Desventaja: Necesita más datos para fine-tuning (~500+ imágenes)
```

### Opción C — HRNet (High-Resolution Network)

```
Arquitectura: HRNet-W32 pretrained en COCO keypoints
Output: 19 heatmaps de alta resolución
Ventaja: Mantiene alta resolución en todo el forward pass
Uso ideal: Si tienes GPU con >8GB VRAM
```

### Comparativa de Modelos

| Modelo | MRE (mm) esperado | Datos mínimos | GPU necesaria | Complejidad |
|---|---|---|---|---|
| **UNet + ResNet50** | 1.5–2.0 mm | 150 imgs | 4GB | Media |
| **ViT Fine-tuning** | 1.3–1.8 mm | 400+ imgs | 8GB | Alta |
| **HRNet** | 1.2–1.6 mm | 200 imgs | 8GB | Alta |
| CNN simple (baseline) | 3.0–4.5 mm | 100 imgs | 2GB | Baja |

> **MRE = Mean Radial Error** (error promedio en mm entre landmark predicho y real)

### Decisión Recomendada
Empieza con **UNet + ResNet50** preentrenado. Es el balance perfecto entre precisión, cantidad de datos disponible (150 imágenes de ISBI) y hardware accesible. Puedes correrlo en Google Colab Pro ($10/mes) sin comprar GPU.

---

## 5. Pipeline de Entrenamiento

### 5.1 Preprocesamiento de Imágenes

```python
# Pasos de preprocesamiento para cada radiografía
def preprocess_xray(image_path):
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    
    # 1. CLAHE (mejora contraste sin saturar)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    img = clahe.apply(img)
    
    # 2. Normalización Z-score
    img = (img - img.mean()) / img.std()
    
    # 3. Resize manteniendo aspect ratio
    img = cv2.resize(img, (512, 512))
    
    # 4. Convertir a tensor PyTorch
    return torch.tensor(img).unsqueeze(0).float()
```

### 5.2 Data Augmentation

```python
augmentation = A.Compose([
    A.HorizontalFlip(p=0.0),        # NO flip (asimétrico izq/der)
    A.Rotate(limit=10, p=0.5),       # Rotación leve
    A.RandomBrightnessContrast(p=0.5),
    A.GaussNoise(p=0.3),
    A.ElasticTransform(p=0.2),       # Deformación anatómica simulada
    A.RandomScale(scale_limit=0.1, p=0.3),
], keypoint_params=A.KeypointParams(format='xy'))
```

> **Importante:** Toda augmentación debe transformar también las coordenadas de los landmarks.

### 5.3 Generación de Heatmaps

```python
def generate_heatmap(landmark_x, landmark_y, img_size=128, sigma=3):
    """Genera mapa de calor Gaussiano centrado en el landmark."""
    x = np.arange(0, img_size)
    y = np.arange(0, img_size)
    xx, yy = np.meshgrid(x, y)
    heatmap = np.exp(-((xx - landmark_x)**2 + (yy - landmark_y)**2) / (2 * sigma**2))
    return heatmap
```

### 5.4 Configuración de Entrenamiento

```yaml
# config/training.yaml
model:
  encoder: resnet50
  pretrained: true
  in_channels: 1
  num_landmarks: 19

training:
  epochs: 200
  batch_size: 8
  optimizer: AdamW
  lr: 1e-4
  lr_scheduler: CosineAnnealingLR
  weight_decay: 1e-5

loss:
  primary: MSELoss (heatmaps)
  auxiliary: WingLoss (coordenadas)  # Mejor para outliers
  lambda_wing: 0.1

data:
  train_split: 0.70
  val_split: 0.15
  test_split: 0.15
  augmentation: true
```

### 5.5 Loss Function — Wing Loss

```python
class WingLoss(nn.Module):
    """Más robusta que MSE para landmarks médicos."""
    def __init__(self, w=10, epsilon=2):
        super().__init__()
        self.w = w
        self.epsilon = epsilon
        self.C = w - w * math.log(1 + w / epsilon)

    def forward(self, pred, target):
        diff = torch.abs(pred - target)
        loss = torch.where(
            diff < self.w,
            self.w * torch.log(1 + diff / self.epsilon),
            diff - self.C
        )
        return loss.mean()
```

### 5.6 Entrenamiento en Google Colab

```python
# Instalar dependencias
!pip install segmentation-models-pytorch albumentations

# Estructura de carpetas esperada
/content/drive/MyDrive/aicefalo/
├── data/
│   ├── images/          # .bmp o .png
│   └── landmarks/       # .txt con coordenadas
├── models/              # Checkpoints guardados
└── results/             # Métricas y gráficas
```

---

## 6. Plan de Evaluación y Métricas

### 6.1 Métricas Principales

**Mean Radial Error (MRE)** — Métrica estándar del ISBI Challenge
```
MRE = (1/N) × Σ √((x_pred - x_real)² + (y_pred - y_real)²)
Unidad: milímetros (convertir pixels con DPI de la imagen)
Objetivo: MRE < 2.0 mm (precisión clínica aceptable)
Excelente: MRE < 1.5 mm
```

**Success Detection Rate (SDR)**
```
SDR@2mm: % de landmarks detectados dentro de 2mm del real
SDR@2.5mm: % dentro de 2.5mm
SDR@3mm: % dentro de 3mm
SDR@4mm: % dentro de 4mm
Objetivo mínimo: SDR@2mm > 75%
```

### 6.2 Métricas por Landmark

Algunos landmarks son más difíciles de detectar que otros. Evaluar individualmente:

| Landmark | Dificultad esperada | Causa |
|---|---|---|
| Sella (S) | Baja | Alta densidad ósea, claro en RX |
| Orbitale (Or) | Alta | Superposición de estructuras |
| Gonion (Go) | Media | Variabilidad morfológica |
| Incisivos | Alta | Calidad de imagen variable |

### 6.3 Comparativa con Baseline

| Método | MRE (mm) | SDR@2mm |
|---|---|---|
| Marcado manual estudiante | 2.5–4.0 | ~50% |
| CNN simple (baseline) | 3.0–4.5 | ~40% |
| **AI-Cefalo (objetivo)** | **1.5–2.0** | **>75%** |
| Estado del arte (2024) | 1.1–1.4 | >90% |

### 6.4 Ángulos Cefalométricos a Calcular

Una vez detectados los landmarks, calcular automáticamente:

```python
def calcular_angulos_steiner(landmarks):
    """
    Análisis de Steiner - Ángulos principales
    landmarks: dict con nombre → (x, y)
    """
    S, N, A, B, Pog = landmarks['S'], landmarks['N'], landmarks['A'], landmarks['B'], landmarks['Pog']
    
    SNA  = angulo_entre_puntos(S, N, A)     # Normal: 82° ± 2°
    SNB  = angulo_entre_puntos(S, N, B)     # Normal: 80° ± 2°
    ANB  = SNA - SNB                         # Normal: 2° ± 2°
    
    return {
        'SNA': round(SNA, 1),
        'SNB': round(SNB, 1),
        'ANB': round(ANB, 1),
        'clasificacion': clasificar_esqueletico(ANB)
    }

def clasificar_esqueletico(ANB):
    if ANB > 4:   return "Clase II (prognatismo maxilar)"
    elif ANB < 0: return "Clase III (prognatismo mandibular)"
    else:         return "Clase I (normo-oclusión)"
```

---

## 7. Plan de Pruebas (Testing)

### 7.1 Pruebas Unitarias (Código)

```bash
tests/
├── test_preprocessing.py    # CLAHE, resize, normalización
├── test_heatmap_gen.py      # Generación de Gaussianas
├── test_model_forward.py    # Shape de inputs/outputs
├── test_angle_calc.py       # Cálculo de ángulos SNA, SNB, ANB
├── test_pdf_generation.py   # Reporte generado correctamente
└── test_api_endpoints.py    # FastAPI endpoints responden
```

Ejecutar con:
```bash
pytest tests/ --cov=src --cov-report=html
```

### 7.2 Pruebas del Modelo

**Test Set Holdout (no tocar hasta el final)**
- 15% del dataset = ~22-30 imágenes
- Evaluar UNA SOLA VEZ al final
- Nunca usar para ajustar hiperparámetros

**Cross-Validation durante desarrollo**
```
K-Fold con K=5 sobre el training set
Detecta overfitting y estabilidad del modelo
```

**Prueba de Robustez**
```python
# Simular condiciones reales del local
pruebas_robustez = [
    "imagen_foto_celular",    # RX fotografiada con celular (no escaneada)
    "imagen_baja_calidad",    # Radiografía antigua, manchada
    "imagen_rotada_15grados", # Mala posición del paciente
    "imagen_con_artefactos",  # Tornillos, brackets metálicos
    "imagen_pediatrica",      # Paciente menor (morfología diferente)
]
```

### 7.3 Pruebas con Usuarios Reales (Beta)

**Fase 1 — Prueba cerrada (Semana 1-2)**
```
Participantes: 5 estudiantes de 4to año
Protocolo:
  1. Marcan la radiografía manualmente (tiempo cronometrado)
  2. Usan AI-Cefalo en la misma radiografía
  3. Comparan resultados con el "gold standard" del profesor
  4. Llenan encuesta de UX (escala 1-10)
Métricas: Tiempo ahorrado, diferencia de error, NPS
```

**Fase 2 — Beta abierta (Mes 2)**
```
Participantes: 20-30 estudiantes del local
Protocolo: Uso libre con código de acceso gratuito
Métricas: Retención (usan más de 3 veces), casos de error reportados
```

**Encuesta de Validación (post-beta)**
```
1. ¿Usarías esto en tus tareas reales? (1-10)
2. ¿Qué tan confiable fue el resultado? (1-10)
3. ¿Pagarías $5 por 10 análisis? (Sí/No/Tal vez)
4. ¿Qué le agregarías o quitarías?
```

---

## 8. Planificación por Fases

### Fase 0 — Preparación (Semanas 1-2)
- [ ] Solicitar dataset ISBI 2015 por email
- [ ] Crear repositorio GitHub privado
- [ ] Configurar Google Colab Pro + Google Drive
- [ ] Explorar y visualizar el dataset completo
- [ ] Revisar 10 papers de cefalometría con IA (ver sección papers)
- [ ] Instalar y testear stack tecnológico localmente

**Entregable:** Notebook de exploración con 20 radiografías visualizadas y landmarks superpuestos.

---

### Fase 1 — Baseline y Datos (Semanas 3-4)
- [ ] Escribir pipeline de carga de datos
- [ ] Implementar preprocesamiento (CLAHE, normalización)
- [ ] Implementar data augmentation
- [ ] Entrenar CNN simple como baseline
- [ ] Alcanzar MRE < 4.0 mm (superar marcado manual malo)

**Entregable:** Modelo baseline corriendo, métricas documentadas.

---

### Fase 2 — Modelo Principal (Semanas 5-8)
- [ ] Implementar UNet con encoder ResNet50
- [ ] Implementar generación y decodificación de heatmaps
- [ ] Implementar Wing Loss
- [ ] Ajuste de hiperparámetros (lr, sigma de heatmap, batch size)
- [ ] Alcanzar MRE < 2.5 mm en validación

**Entregable:** Modelo guardado (.pth), notebook de entrenamiento documentado.

---

### Fase 3 — Refinamiento del Modelo (Semanas 9-11)
- [ ] Análisis de errores por landmark (¿cuáles fallan más?)
- [ ] Data augmentation específica para landmarks difíciles
- [ ] Ensemble de 2-3 modelos si hay tiempo
- [ ] Alcanzar MRE < 2.0 mm y SDR@2mm > 75%
- [ ] Evaluación final en test set holdout

**Entregable:** Modelo final, tabla de métricas completa, análisis visual de errores.

---

### Fase 4 — Backend y API (Semanas 12-13)
- [ ] Crear API FastAPI con endpoint `/predict`
- [ ] Implementar cálculo automático de ángulos (Steiner mínimo)
- [ ] Implementar generador de reporte PDF
- [ ] Dockerizar la aplicación
- [ ] Deploy en servidor (Railway, Render, o VPS económico)

**Entregable:** API funcionando en URL pública, documentación Swagger.

---

### Fase 5 — Frontend (Semana 14-15)
- [ ] Interfaz web (React o simple HTML/JS)
- [ ] Upload de imagen → visualización con landmarks superpuestos
- [ ] Tabla de ángulos calculados con rangos normales
- [ ] Botón de descarga de reporte PDF
- [ ] Sistema de créditos (código → usos)

**Entregable:** App web deployada, accesible desde celular.

---

### Fase 6 — Beta y Lanzamiento (Semanas 16-18)
- [ ] Beta cerrada con 5 estudiantes
- [ ] Correcciones basadas en feedback
- [ ] Beta abierta con 20-30 estudiantes
- [ ] Preparar material de venta para el local del padre
- [ ] Definir precio y sistema de tarjetas de crédito

**Entregable:** Producto lanzado, primeros ingresos.

---

### Cronograma Resumen

```
Semana:  1  2  3  4  5  6  7  8  9  10 11 12 13 14 15 16 17 18
         [Fase 0 ]
                  [  Fase 1   ]
                           [      Fase 2        ]
                                             [ F3  ]
                                                      [F4]
                                                            [F5]
                                                               [Beta + Launch]
```

---

## 9. Stack Tecnológico

### Machine Learning
```
PyTorch 2.x                 — Framework principal
segmentation-models-pytorch — UNet prebuilt con encoders
albumentations              — Data augmentation médica
OpenCV                      — Preprocesamiento de imágenes
scikit-learn                — Métricas y validación
Weights & Biases (wandb)    — Logging de experimentos (gratis)
```

### Backend
```
Python 3.11
FastAPI           — API REST
Uvicorn           — Servidor ASGI
ReportLab         — Generación de PDF
Pillow            — Manipulación de imágenes
PostgreSQL        — Base de datos
SQLAlchemy        — ORM
```

### Frontend
```
React + Vite      — App web
Konva.js          — Canvas para dibujar landmarks sobre imagen
TailwindCSS       — Estilos
```

### Infraestructura
```
RTX 4050 local    — Entrenamiento principal (sin costo)
Railway.app       — Deploy del backend (~$5/mes)
Vercel            — Deploy del frontend (gratis)
GitHub Actions    — CI/CD básico
```

### Herramientas de Desarrollo
```
VS Code o Cursor  — Editor principal (ver sección 9.1)
Jupyter Notebooks — Exploración y entrenamiento
Docker + Docker Compose — Reproducibilidad
pytest            — Testing
black + flake8    — Formato de código
```

---

## 9.1 Guía de Weights & Biases (wandb) con VS Code / Cursor

### ¿Qué es wandb en una oración?
Es un sitio web (wandb.ai) que recibe métricas de tu entrenamiento en tiempo real y las muestra como gráficas interactivas. Tu código le "habla" a ese sitio mientras entrena.

### Setup inicial (una sola vez)
```bash
# 1. Instalar
pip install wandb

# 2. Crear cuenta gratis en https://wandb.ai/signup
# 3. Obtener tu API key desde https://wandb.ai/authorize
# 4. Loguear desde la terminal (VS Code o Cursor tienen terminal integrada)
wandb login
# → pega tu API key cuando la pida
```

### Cómo integrarlo en el código de entrenamiento
```python
import wandb

# Al inicio del script de entrenamiento
wandb.init(
    project="aicefalo",          # Nombre del proyecto en wandb.ai
    name="unet-resnet50-lr1e4",  # Nombre de ESTE experimento
    config={                      # Hiperparámetros que quieres recordar
        "model": "unet-resnet50",
        "lr": 1e-4,
        "batch_size": 8,
        "epochs": 200,
        "num_landmarks": 29,
        "dataset": "aariz-v1",
        "loss": "wing+mse",
        "sigma_heatmap": 3
    }
)

# Dentro del loop de entrenamiento, en cada época:
for epoch in range(NUM_EPOCHS):
    train_loss = train_one_epoch(model, dataloader)
    val_mre, val_sdr = evaluate(model, val_dataloader)
    
    # Esta línea sola envía todo a wandb.ai
    wandb.log({
        "epoch": epoch,
        "train/loss": train_loss,
        "val/MRE_mm": val_mre,
        "val/SDR_2mm": val_sdr,
        "val/SDR_2.5mm": val_sdr_25,
        "lr": optimizer.param_groups[0]['lr']
    })
    
    # Guardar el mejor modelo automáticamente
    if val_mre < best_mre:
        best_mre = val_mre
        torch.save(model.state_dict(), "models/best_model.pth")
        wandb.save("models/best_model.pth")  # También lo guarda en la nube

# Al terminar el entrenamiento
wandb.finish()
```

### Lo que ves en wandb.ai mientras entrena
```
Dashboard en tiempo real:
┌─────────────────────────────────────────────────┐
│  Experimento: unet-resnet50-lr1e4               │
│  Estado: ▶ Corriendo (época 45/200)             │
├─────────────────┬───────────────────────────────┤
│  train/loss     │  📉 bajando de 0.48 → 0.12    │
│  val/MRE_mm     │  📉 bajando de 4.2 → 2.1 mm   │
│  val/SDR_2mm    │  📈 subiendo de 38% → 71%      │
│  lr             │  📉 cosine decay               │
└─────────────────┴───────────────────────────────┘

Comparación de experimentos:
  Exp A (lr=1e-4):   MRE = 2.1mm  ← MEJOR
  Exp B (lr=1e-3):   MRE = 3.4mm
  Exp C (lr=5e-5):   MRE = 2.6mm
```

### Uso con VS Code
```
1. Abre el proyecto en VS Code
2. Abre la terminal integrada (Ctrl + `)
3. Corre: python src/training/train.py
4. Abre tu navegador en https://wandb.ai/tu-usuario/aicefalo
5. Las gráficas aparecen automáticamente mientras el código corre
6. Puedes cerrar la terminal y las métricas siguen llegando
```

### Uso con Cursor (el VS Code con IA integrada)
Cursor es un editor basado en VS Code que tiene un agente de IA integrado (similar a GitHub Copilot pero más potente). **Sí son 100% compatibles**, wandb funciona exactamente igual porque Cursor es VS Code por dentro.

**Flujo recomendado con Cursor:**
```
1. Abres Cursor
2. Usas Ctrl+K o el chat lateral para pedirle al agente:
   "Agrega wandb logging a mi función train_one_epoch"
   "Analiza mi gráfica de MRE y dime si hay overfitting"
   "El MRE se estancó en 2.8mm después de la época 60, ¿qué cambio?"
3. El agente ve tu código y sugiere cambios directamente
4. Las métricas de wandb puedes pegarlas en el chat para que el agente las analice
```

**Nota:** Si usas Cursor, puedes pedirle al agente que consulte este mismo archivo `.md` como contexto. Arrastra el archivo al chat de Cursor con `@AI-Cefalo_Plan_Completo.md` y el agente tendrá todo el contexto del proyecto.

### Instalación de Cursor
```
1. Descargar desde https://cursor.sh (gratis, tier gratuito funciona bien)
2. Instalar igual que VS Code
3. Importa tus extensiones de VS Code: Ctrl+Shift+P → "Import VS Code settings"
4. Todas tus extensiones de Python, Git, etc. quedan instaladas automáticamente
```

---

## 10. Estructura del Repositorio

```
aicefalo/
├── README.md
├── docker-compose.yml
├── requirements.txt
│
├── data/
│   ├── raw/                    # Dataset Aariz sin modificar (git clone)
│   │   ├── images/             # 1000 radiografías
│   │   └── annotations/        # 29 landmarks por imagen en JSON
│   ├── processed/              # Datos preprocesados (heatmaps generados)
│   └── external/              # Casos donados por la universidad (anónimos)
│
├── notebooks/
│   ├── 01_exploracion_datos.ipynb
│   ├── 02_baseline_model.ipynb
│   ├── 03_unet_training.ipynb
│   ├── 04_evaluacion_metricas.ipynb
│   └── 05_analisis_errores.ipynb
│
├── src/
│   ├── data/
│   │   ├── dataset.py          # PyTorch Dataset class
│   │   ├── preprocessing.py    # CLAHE, normalización
│   │   └── augmentation.py     # Albumentations pipeline
│   │
│   ├── models/
│   │   ├── unet.py             # Arquitectura UNet
│   │   ├── losses.py           # WingLoss, MSELoss
│   │   └── metrics.py          # MRE, SDR
│   │
│   ├── training/
│   │   ├── train.py            # Loop de entrenamiento
│   │   ├── evaluate.py         # Evaluación
│   │   └── config.yaml         # Hiperparámetros
│   │
│   └── api/
│       ├── main.py             # FastAPI app
│       ├── predict.py          # Inferencia
│       ├── angles.py           # Cálculo ángulos Steiner
│       └── report.py           # Generador PDF
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── ImageUploader.jsx
│   │   │   ├── LandmarkViewer.jsx  # Canvas con Konva
│   │   │   └── AngleTable.jsx
│   │   └── services/
│   │       └── api.js
│   └── package.json
│
├── tests/
│   ├── test_preprocessing.py
│   ├── test_model.py
│   ├── test_angles.py
│   └── test_api.py
│
└── models/
    ├── baseline_cnn.pth
    ├── unet_v1.pth
    └── unet_final.pth
```

---

## 11. Consideraciones Legales y Éticas

### Datos de Pacientes
```
- NUNCA almacenar radiografías con datos identificables del paciente
- Solicitar al usuario que borre nombre/fecha antes de subir
- Agregar disclaimer claro en la interfaz
- Las radiografías procesadas se eliminan del servidor en 1 hora
```

### Disclaimer Obligatorio en la App
```
⚠️ AI-Cefalo es una herramienta educativa de apoyo.
Los resultados NO reemplazan el diagnóstico de un profesional
certificado. Esta herramienta está diseñada para ayudar a
estudiantes a verificar su propio análisis, no para emitir
diagnósticos clínicos.
```

### Por Qué Esto te Protege Legalmente
Al posicionarlo como "verificador educativo" (el estudiante hace su análisis primero, luego compara con la IA), evitas cualquier responsabilidad clínica. El producto es de aprendizaje, no diagnóstico.

### Uso del Dataset ISBI
El dataset ISBI 2015 está disponible para uso académico e investigación. Si el producto genera dinero, considera contactar a los autores originales para citar su trabajo correctamente en la app.

---

## Papers Recomendados para Leer

1. **Wang et al. (2016)** — "Benchmark and comparison of landmark detection methods for cephalometric X-Ray images" — el paper base del ISBI Challenge
2. **Lindner et al. (2015)** — "Fully automatic cephalometric evaluation using random forest regression-voting" 
3. **Zhang et al. (2023)** — "CephaloNet: Attention-based landmark detection in cephalometric radiographs"
4. **Lee et al. (2020)** — "Automated cephalometric landmark detection with confidence regions using Bayesian convolutional neural networks"

Buscarlos en **Google Scholar** o **Semantic Scholar** — todos tienen versión gratuita en arXiv o ResearchGate.

---

*Documento generado para el proyecto AI-Cefalo — Riobamba, Ecuador*
*Versión 1.0*
