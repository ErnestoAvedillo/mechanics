# Stage 1: Builder
FROM python:3.13-slim as builder

WORKDIR /app

# Instalar dependencias del sistema necesarias para compilar
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiar archivo de dependencias
COPY pyproject.toml uv.lock* ./

# Instalar uv e instalar dependencias
RUN pip install uv && uv venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
RUN uv pip install -r <(uv pip compile pyproject.toml)

# Stage 2: Runtime
FROM python:3.13-slim

WORKDIR /app

# Instalar dependencias de runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copiar environment virtual desde builder
COPY --from=builder /app/.venv /app/.venv

# Copiar código de la aplicación
COPY . /app/

# Establecer PATH
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=mechanics.settings

# Crear directorio para socket de gunicorn y colectar estáticos
RUN mkdir -p /app/run /app/static_files /app/media

# Usuario no root
RUN useradd -m -u 1000 django && chown -R django:django /app
USER django

# Exponer puerto
EXPOSE 8000

# Comando por defecto
CMD ["gunicorn", "--workers", "4", "--bind", "unix:/app/run/gunicorn.sock", "--timeout", "120", "mechanics.wsgi"]
