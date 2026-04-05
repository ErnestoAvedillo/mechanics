#!/bin/bash

export COUNTRY="SP"
export STATE="Barcelona"
export LOCATION="Viladecans"
export ORG="ernestoavedillo.com"
export ORGUNIT="Mechanics"
export NAME="Ernesto Avedillo"
export DOMAIN="ernestoavedillo.com"

# Crear directorio de estructura Let's Encrypt
mkdir -p ./certs/live/$DOMAIN

# Generar certificados autofirmados
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
 -keyout ./certs/live/$DOMAIN/privkey.pem \
 -out ./certs/live/$DOMAIN/fullchain.pem \
 -subj "/C=$COUNTRY/ST=$STATE/L=$LOCATION/O=$ORG/OU=$ORGUNIT/CN=$DOMAIN"

# Crear enlaces simbólicos para compatibilidad (opcional)
cp ./certs/live/$DOMAIN/fullchain.pem ./selfsigned.crt 2>/dev/null || true
cp ./certs/live/$DOMAIN/privkey.pem ./selfsigned.key 2>/dev/null || true

echo "✓ Certificados autofirmados generados exitosamente"
echo "  Ubicación: ./certs/live/$DOMAIN/"