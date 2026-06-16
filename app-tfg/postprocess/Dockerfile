FROM python:3.8-slim
# Si usas 3.8 en tu proyecto, cambia a python:3.8-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Herramientas de build básicas (a veces las pide numpy/torch)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# PIP actualizado
RUN python -m pip install --upgrade pip setuptools wheel

# 1) Dependencias de tu servicio
COPY requirements.txt .
RUN pip install -r requirements.txt

# 2) Forzamos OpenCV sin GUI para evitar libGL
RUN pip install --no-cache-dir opencv-python-headless

# (si 'reid' o tus deps necesitan torch, instala aquí antes de 'reid')
# CPU (ejemplo):
RUN pip install --no-cache-dir torch torchvision torchaudio
# GPU (CUDA) -> depende de tu host/driver (consúltame y lo adaptamos)

# 3) Copiamos el paquete reid DENTRO de postprocess y lo instalamos en editable
COPY reid/ ./reid/
RUN pip install -e ./reid   # equivalente a "cd reid && python setup.py develop"

# 4) Copiamos el resto del código de postprocess
COPY . .

EXPOSE 5002
# CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5002", "app:app"]
CMD ["python", "app.py"]