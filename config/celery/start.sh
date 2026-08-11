#!/bin/bash

# Terminar la ejecución si hay algún error
set -e

echo "Iniciando el worker de Celery..."

# Ejecutar el worker de Celery apuntando a la configuración en "mechanics"
# Asegúrate de que este comando se ejecuta dentro del directorio donde está manage.py o en PYTHONPATH
celery -A mechanics worker --loglevel=info -E