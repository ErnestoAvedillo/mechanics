#!/bin/bash

# Habilitar buildx (por si acaso no está activo)
docker buildx create --use --name mybuilder || docker buildx use mybuilder

# Construir y empujar en UN SOLO PASO usando caché remota eficiente
docker buildx build \
  --provenance=false \
  --cache-from=type=registry,ref=eavedillo/django:buildcache \
  --cache-to=type=registry,ref=eavedillo/django:buildcache,mode=max,image-manifest=true,oci-mediatypes=true \
  -t eavedillo/django:latest \
  --push .
