#!/bin/bash
# El Menú de Ernesto® - Servidor Optimizado

echo "🚀 Iniciando El Menú de Ernesto® - Versión Optimizada"

# Navegar al directorio del proyecto
cd /home/ernesto/Desktop/djmenu

# Verificar entorno virtual
if [ -d ".venv" ]; then
    echo "📦 Activando entorno virtual..."
    source .venv/bin/activate
fi

# Buscar puerto disponible
PORT=8000
while lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; do
    PORT=$((PORT + 1))
done

echo "🌐 Servidor disponible en http://127.0.0.1:$PORT"
echo "📝 Presiona Ctrl+C para detener"
echo ""

# Ejecutar servidor
python manage.py runserver $PORT
