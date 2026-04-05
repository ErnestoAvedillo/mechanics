FROM nginx:alpine

RUN apk update && apk add --no-cache vim openssl

# Remover configuración por defecto
RUN rm /etc/nginx/conf.d/default.conf

# Copiar configuración personalizada
COPY nginx.conf /etc/nginx/nginx.conf
COPY init-certs.sh /docker-entrypoint.sh

# Hacer el script ejecutable
RUN chmod +x /docker-entrypoint.sh

EXPOSE 80 443
#ENTRYPOINT [ "sh", "-c", "while true; do sleep 3306; done"]

ENTRYPOINT ["/docker-entrypoint.sh"]