FROM python:3.12-slim

WORKDIR /app

# Evita que Python genere archivos .pyc que engordan la imagen un 30%
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instalar dependencias del sistema
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    git \
    gettext \
    && rm -rf /var/lib/apt/lists/*
# copiar requerimientros e instalar dependencias de python
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip
# Primero lo pesado (Rara vez cambia, caché de Docker intacta 99% del tiempo)
COPY requirements-core.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements-core.txt

# Luego lo ligero (Cambia más seguido, pero se instala en 3 segundos)
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt