# Stage 1: Builder
FROM nginx:latest as builder
WORKDIR /app
# Copiar configuración personalizada de nginx
COPY nginx.conf /etc/nginx/nginx.conf
# Copiar archivos estáticos generados por Django    
COPY . /app/

CMD [ "executable" ]