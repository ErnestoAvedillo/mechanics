FROM python:3.12-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*
# copiar requerimientros e instalar dependencias de python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt