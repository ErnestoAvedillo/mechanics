#!/bin/sh

# Script de inicialización para generar certificados si no existen

CERT_DIR="/etc/letsencrypt/live/ernestoavedillo.com"
CERT_FILE="$CERT_DIR/fullchain.pem"
KEY_FILE="$CERT_DIR/privkey.pem"

# Crear directorio si no existe
mkdir -p "$CERT_DIR"

# Verificar si los certificados existen
if [ ! -f "$CERT_FILE" ] || [ ! -f "$KEY_FILE" ]; then
    echo "⚠️  Certificados no encontrados. Generando certificados autofirmados..."
    
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$KEY_FILE" \
        -out "$CERT_FILE" \
        -subj "/C=SP/ST=Barcelona/L=Viladecans/O=ernestoavedillo.com/OU=Mechanics/CN=ernestoavedillo.com"
    
    echo "✓ Certificados autofirmados generados en: $CERT_DIR"
    echo "  💡 Para certificados válidos en producción, ejecuta:"
    echo "     make setup-letsencrypt DOMAIN=ernestoavedillo.com EMAIL=tu@email.com"
else
    echo "✓ Certificados encontrados en: $CERT_DIR"
fi

# Verificar que nginx puede leer los archivos
if [ ! -r "$CERT_FILE" ] || [ ! -r "$KEY_FILE" ]; then
    echo "⚠️  Los certificados existen pero no son legibles. Ajustando permisos..."
    chmod 644 "$CERT_FILE"
    chmod 600 "$KEY_FILE"
fi

echo "✓ Iniciando nginx..."
exec nginx -g "daemon off;"
