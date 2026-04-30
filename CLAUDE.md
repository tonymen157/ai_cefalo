# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-Cefalo is an automatic cephalometric landmark detection system for dental radiographs. Users upload a lateral skull X-ray, the AI detects 29 anatomical landmarks, calculates orthodontic angles (Steiner/Ricketts analysis), and generates a printable PDF report.

**Current state:** Fase 4 (Backend API + Frontend) implemented, pending integration testing and deployment.

## Critical Technical Decisions

- **29 landmarks** (Aariz standard), NOT 19 (ISBI 2015). All configs, models, loss functions, and metrics MUST use `NUM_LANDMARKS = 29`. No exceptions.
- **Dataset:** Aariz Cephalometric Landmark Dataset. Public, 1000 images (700/150/150 split). Clone from GitHub + download actual data from Figshare: https://doi.org/10.6084/m9.figshare.27986417.v1
- **Ground truth:** Average of BOTH Senior Orthodontists AND Junior Orthodontists annotations:
  ```python
  gt_x = (senior_x + junior_x) / 2
  gt_y = (senior_y + junior_y) / 2
  ```
  NEVER use only Senior as ground truth.
- **Splits:** Use the provided TRAIN/VALID/TEST folders. NO manual `train_test_split()`. The dataset splits are already done.

## Calibration (CRITICAL)

The dataset includes `cephalogram_machine_mappings.csv` with `pixel_size` (mm/pixel) per imaging device. **MRE must be converted from pixels to millimeters using this calibration** — without it, metrics have NO clinical value.

```python
# pixel_size loaded per image from cephalogram_machine_mappings.csv
mre_mm = mre_pixels * pixel_size
```

The `AarizDataset` class returns `pixel_size` as the 4th element of each sample for this purpose.

## Preprocessing Pipeline (EXACT ORDER — NO EXCEPTIONS)

```python
# Paso 1: CLAHE (clipLimit=2.0, tileGridSize=(8,8))
clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
img = clahe.apply(image)

# Paso 2: NLM denoising (h=10)
img = cv2.fastNlMeansDenoising(img, None, h=10, templateWindowSize=7, searchWindowSize=21)

# Paso 3: Z-score normalization
img = (img - img.mean()) / (img.std() + 1e-8)

# Paso 4: Resize to INPUT_SIZE with landmark scaling
img = cv2.resize(img, (INPUT_SIZE_WH[0], INPUT_SIZE_WH[1]))
landmarks[:, 0] = orig_landmarks[:, 0] * (INPUT_SIZE_WH[1] / orig_w)
landmarks[:, 1] = orig_landmarks[:, 1] * (INPUT_SIZE_WH[0] / orig_h)
```

**NO HorizontalFlip** in augmentation (anatomical left/right asymmetry).

## Image & Heatmap Sizes

| Parameter | Value | Notes |
|---|---|---|
| **INPUT_SIZE_WH** | (512, 512) | (W, H) - standard resolution |
| **INPUT_SIZE_HW** | (512, 512) | (H, W) - for PyTorch ops |
| **HEATMAP_SIZE_WH** | (128, 128) | 1/4 of INPUT_SIZE |
| **HEATMAP_SIZE_HW** | (128, 128) | (H, W) for PyTorch |
| **SIGMA_HEATMAP** | 5.0 | sigma for 128px heatmaps |
| **NUM_LANDMARKS** | 29 | Everywhere, no exceptions |

Landmark coordinates MUST be scaled when transforming to original image space using per-image `scale_x = orig_w / INPUT_SIZE_WH[0]` and `scale_y = orig_h / INPUT_SIZE_HW[0]`. This non-uniform scaling is essential for clinical accuracy with real X-ray aspect ratios.

## Benchmarks (Official Aariz Baseline)

| Metric | Target (AI-Cefalo) | Baseline (Aariz) | SOTA (2025) |
|---|---|---|---|
| **MRE (mm)** | < 1.789 mm | 1.789 mm | < 1.23 mm |
| **SDR@2mm** | > 78.44% | 78.44% | > 81.18% |
| **SDR@2.5mm** | > 85.72% | 85.72% | > 87.28% |
| **SDR@3.0mm** | > 89.64% | 89.64% | > 90.82% |
| **SDR@4.0mm** | > 94.49% | 94.49% | > 94.82% |

## Trained Model Results

- **Model:** `best_model_v1_final.pth` (UNet + ResNet50 encoder)
- **Val MRE:** 0.7952 mm (época 174/200)
- **Test MRE:** 1.2670 mm (29.2% better than baseline)
- **Test SDR@2mm:** 82.99% (4.55% better than baseline)
- **Config:** Input 512×512, Heatmap 128×128, Batch 8, LR 1e-4, Combined Loss (MSE + WingLoss)

## Tech Stack

**ML/Data:** PyTorch 2.x, segmentation-models-pytorch, albumentations, OpenCV, scikit-learn, Weights & Biases (wandb)

**Backend:** Python 3.11, FastAPI + Uvicorn, ReportLab (PDF), Pillow, PostgreSQL + SQLAlchemy

**Frontend:** React + Vite, Konva.js (canvas rendering), TailwindCSS

**Infrastructure:** Docker, Hugging Face Spaces (deployment), GitHub Actions (CI/CD)

## Repository Structure

```
aicefalo/
├── data/
│   ├── raw/Aariz/              # Aariz dataset (in .gitignore)
│   │   ├── train/              # 700 images + annotations
│   │   ├── valid/              # 150 images + annotations
│   │   ├── test/               # 150 images + annotations
│   │   └── cephalogram_machine_mappings.csv  # CRITICAL: pixel_size per image
│   └── preprocessed/           # Pre-computed images + heatmaps
├── src/
│   ├── api/                    # FastAPI backend
│   │   ├── main.py             # FastAPI app, CORS, router registration
│   │   ├── database.py         # SQLAlchemy setup, PostgreSQL
│   │   ├── models.py           # DB models (User, CreditCode, Analysis)
│   │   ├── dependencies.py     # Auth dependencies
│   │   ├── routers/            # API routes (upload, calibrate, analyze, steiner, credit, admin)
│   │   └── services/           # Business logic (detectors, PDF gen, credit service)
│   ├── data/                   # AarizDataset, preprocessing
│   ├── models/                 # UNet, losses (WingLoss), metrics
│   ├── training/               # Train loop, evaluation, config
│   ├── inference/              # Inference pipeline
│   └── core/                   # Core utilities
├── frontend/                   # React + Vite app
│   └── src/
│       ├── components/         # UI components (UploadStep, CalibrationStep, LandmarkCanvas, ResultsStep, etc.)
│       ├── services/            # API client calls
│       ├── context/             # React context (state management)
│       ├── hooks/               # Custom hooks
│       └── constants/           # Landmark definitions, Steiner angles
├── models/                     # Saved checkpoints (in .gitignore)
├── tests/                      # pytest
└── outputs/                    # Generated PDFs (in .gitignore)
```

## Key Architecture

```
Frontend (React) → FastAPI Backend → UNet Model (PyTorch)
                                   → Angle Calculator (Steiner: SNA, SNB, ANB)
                                   → PDF Report Generator
                                   → PostgreSQL (user credits, history)
```

**Image pipeline:** X-ray → CLAHE → NLM Denoising → Z-score → Resize 512×512 (scale landmarks!) → UNet → 29 heatmaps (128×128, sigma=5.0) → argmax + subpixel → Scale to original → Convert MRE to mm using pixel_size → Calculate angles → PDF

## API Endpoints

| Method | Endpoint | Description |
|--------|-----------|-------------|
| POST | `/api/upload-image` | Upload X-ray image |
| POST | `/api/calibrate` | Detect calibration coin (10mm) |
| POST | `/api/analyze` | Run landmark detection + angle calculation |
| GET | `/api/steiner` | Get Steiner analysis results |
| POST | `/api/credit/verify` | Verify credit code |
| GET | `/api/admin/stats` | Admin statistics (protected) |

## Commands

```bash
# Setup (Windows)
python -m venv venv
venv\Scripts\activate
pip install --no-cache-dir -r requirements.txt

# Activate venv (Windows)
venv\Scripts\activate

# Train model
python src/training/train.py --config src/training/config.yaml

# Evaluate on test set
python -m src.training.evaluate --model-path models/best_model.pth

# Run backend API locally
cd D:/Proyectos\ Personales/aicefalo/aicefalo
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Run frontend locally
cd frontend
npm install
npm run dev

# Tests
pytest tests/ --cov=src --cov-report=html

# Docker (full stack)
docker-compose up --build

# Docker (backend only for HF Spaces)
docker build -t aicefalo .
docker run -p 7860:7860 aicefalo
```

## Frontend Key Components

- **App.jsx** - Main app with step-based flow (Upload → Calibrate → Processing → Results → Download)
- **LandmarkCanvas.jsx** - Konva.js canvas for displaying X-ray with detected landmarks
- **ToolPanel.jsx** - Zoom, pan, landmark toggle controls
- **SteinerTable.jsx** - Displays calculated orthodontic angles
- **ResultsStep.jsx** - Shows detection results and PDF download
- **CalibrationStep.jsx** - Coin detection for mm/pixel calibration

## Legal/Ethical

- Position as "educational verification tool" (students verify their own analysis), NOT clinical diagnostic tool
- Delete uploaded radiographs after 1 hour
- Never store patient-identifiable data
- Required disclaimer: "AI-Cefalo is an educational support tool. Results do NOT replace certified professional diagnosis."

## Reference

Full technical plan: `AI-Cefalo_Plan_Completo.md`
Dataset paper: https://doi.org/10.1038/s41597-025-05542-3
