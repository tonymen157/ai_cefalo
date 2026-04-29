FROM python:3.10-slim
WORKDIR /app
RUN apt-get update && apt-get install -y libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Crear las carpetas necesarias dentro del servidor
RUN mkdir -p ./models ./data/uploads/

# Copiar el archivo del modelo directamente a la carpeta interna
COPY best_model_v1_final.pth ./models/best_model.pth

# Copiar el código fuente
COPY src/ ./src/

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "7860"]
