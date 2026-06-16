FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencias del sistema (mínimas). Descomenta si necesitas ffmpeg/opencv.
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     ffmpeg \
#  && rm -rf /var/lib/apt/lists/*

# Instala Python deps
COPY requirements.txt .
RUN python -m pip install --upgrade pip && pip install -r requirements.txt

# Copia el código
COPY . .

# Expone el puerto del servicio
EXPOSE 5000

# Arranque con Gunicorn (cambia "app:app" si tu módulo se llama distinto)
#CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "app:app"]
CMD ["python", "app.py"]