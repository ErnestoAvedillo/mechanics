FROM eavedillo/django:latest

WORKDIR /app

COPY . .

# Variables de entorno
ENV DJANGO_SETTINGS_MODULE=mechanics.settings
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DJANGO_DEBUG=True

# Cambiar a directorio src
WORKDIR /app/src

# Script para ejecutar runserver en desarrollo o gunicorn en producción
RUN echo '#!/bin/bash\nif [ "$DJANGO_DEBUG" = "True" ]; then\n  echo "Ejecutando Django en modo DESARROLLO (runserver)"\n  python manage.py runserver 0.0.0.0:8000\nelse\n  echo "Ejecutando Django en modo PRODUCCION (gunicorn)"\n  gunicorn mechanics.wsgi:application --bind 0.0.0.0:8000 --workers=4 --timeout=120\nfi' > /start.sh && chmod +x /start.sh

CMD ["/start.sh"]