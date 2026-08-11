FROM eavedillo/django:latest


# Variables de entorno
ENV DJANGO_SETTINGS_MODULE=mechanics.settings
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DJANGO_DEBUG=True

WORKDIR /app


# Script para ejecutar runserver en desarrollo o gunicorn en producción
COPY ./start.sh /start.sh
RUN chmod +x /start.sh

# Cambiar a directorio src
WORKDIR /app/src

CMD ["/start.sh"]