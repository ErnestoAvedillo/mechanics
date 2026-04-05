FROM eavedillo/django:latest

WORKDIR /app

COPY . .

# Variables de entorno
ENV DJANGO_SETTINGS_MODULE=mechanics.settings
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Cambiar a directorio src
WORKDIR /app/src

# Ejecutar servidor desde src/
CMD ["gunicorn", "mechanics.wsgi:application", "--bind", "0.0.0.0:8000"]