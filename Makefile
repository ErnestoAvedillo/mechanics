COMPOSE = docker-compose

LIST_VOLUMES = $(shell $(COMPOSE) config --volumes ls -q)
DANGLING_IMAGES = $(shell docker images -f "dangling=true" -q)
DOCKER_COMPOSE_FILE = ./docker-compose.yml
CERTS_SELFSIGNED = selfsigned.crt selfsigned.key
DOMAIN ?= ernestoavedillo.com
EMAIL ?= admin@ernestoavedillo.com

all: build

build: build_certs
	$(COMPOSE) -f $(DOCKER_COMPOSE_FILE) build --no-cache
	$(COMPOSE) -f $(DOCKER_COMPOSE_FILE) up -d

down:
	$(COMPOSE) -f $(DOCKER_COMPOSE_FILE) down

restart: down
	$(COMPOSE) -f $(DOCKER_COMPOSE_FILE) up -d

logs:
	$(COMPOSE) -f $(DOCKER_COMPOSE_FILE) logs -f $(ARGS)

stop:
	$(COMPOSE) -f $(DOCKER_COMPOSE_FILE) stop

start: 
	$(COMPOSE) -f $(DOCKER_COMPOSE_FILE) start

# Certificados autofirmados (DESARROLLO LOCAL)
build_certs: $(CERTS_SELFSIGNED)

setup-selfsigned: $(CERTS_SELFSIGNED)
	@echo "✓ Certificados autofirmados generados para desarrollo local"
	@echo "  Ubicación: ./selfsigned.crt y ./selfsigned.key"

rm-selfsigned:
	@echo "Eliminando certificados autofirmados..."
	@rm -f selfsigned.crt selfsigned.key
	
$(CERTS_SELFSIGNED):
	@echo "Generating self-signed certificates..."
	./certs.sh

# Certificados Let's Encrypt (PRODUCCIÓN)
setup-letsencrypt:
	@echo "Generando certificados Let's Encrypt para $(DOMAIN)..."
	@mkdir -p certs certs-www
	@$(COMPOSE) -f $(DOCKER_COMPOSE_FILE) up -d nginx
	@sleep 5
	@$(COMPOSE) -f $(DOCKER_COMPOSE_FILE) run --rm certbot certonly \
		--webroot \
		-w /var/www/certbot \
		-d $(DOMAIN) \
		--email $(EMAIL) \
		--agree-tos \
		--no-eff-email
	@echo "✓ Certificados Let's Encrypt generados para $(DOMAIN)"
	@$(COMPOSE) -f $(DOCKER_COMPOSE_FILE) restart nginx

rm-letsencrypt:
	@echo "Eliminando certificados Let's Encrypt..."
	@$(COMPOSE) -f $(DOCKER_COMPOSE_FILE) down certbot
	@rm -rf ./certs ./certs-www

# Configuración nginx (DESARROLLO / PRODUCCIÓN)
switch-dev:
	@echo "🔄 Cambiando a configuración de DESARROLLO (HTTP)..."
	@cp ./config/nginx/nginx.conf.dev ./config/nginx/nginx.conf
	@$(COMPOSE) -f $(DOCKER_COMPOSE_FILE) restart nginx
	@echo "✓ Sirviendo HTTP sin HTTPS (desarrollo)"
	@echo "  Accede a: http://localhost"

switch-prod:
	@echo "🔄 Cambiando a configuración de PRODUCCIÓN (HTTPS)..."
	@if [ ! -d "./certs/live/ernestoavedillo.com" ]; then \
		echo "⚠️  CERTIFICADOS NO ENCONTRADOS"; \
		echo "  Primero ejecuta: make setup-letsencrypt DOMAIN=ernestoavedillo.com EMAIL=tu@email.com"; \
		exit 1; \
	fi
	@cp ./config/nginx/nginx.conf.prod ./config/nginx/nginx.conf
	@$(COMPOSE) -f $(DOCKER_COMPOSE_FILE) restart nginx
	@echo "✓ Sirviendo HTTPS con certificados"
	@echo "  Accede a: https://ernestoavedillo.com"

show-nginx-config:
	@echo "=== CONFIGURACIONES DISPONIBLES ==="
	@echo "VERSION ACTUAL:"
	@ls -la ./config/nginx/nginx.conf | awk '{print $$NF}'
	@echo ""
	@echo "VERSIONES DISPONIBLES:"
	@echo "  • nginx.conf.dev  (HTTP - Desarrollo)"
	@echo "  • nginx.conf.prod (HTTPS - Producción)"
	@echo ""
	@echo "CAMBIAR:"
	@echo "  make switch-dev   (volver a HTTP)"
	@echo "  make switch-prod  (activar HTTPS con certificados)"

rebuild: down setup-selfsigned build

re: clean build

status:
	@echo "Checking the status of the containers..."
	@$(COMPOSE) -f $(DOCKER_COMPOSE_FILE) ps
	@echo "Checking the status of the images..."
	@$(COMPOSE) -f $(DOCKER_COMPOSE_FILE) config --images
	@echo "Checking the status of the volumes..."
	@$(COMPOSE) -f $(DOCKER_COMPOSE_FILE) config --volumes
	@echo "Checking the status of the networks..."
	@$(COMPOSE) -f $(DOCKER_COMPOSE_FILE) config --networks


rm_none:
	@echo "Removing images not used..."
	@echo "Dangling images: $(DANGLING_IMAGES)"
	@docker image rm "$(DANGLING_IMAGES)" || true

clean: stop 
	@echo "Cleaning up..."
	@docker rm -f $$(docker ps -a -q) || true
	@docker rmi -f $$(docker images -q) || true
	@docker volume rm $$(docker volume ls -q) || true
	@docker network rm $$(docker network ls -q) || true
	@docker system prune -f

in_nginx:
	@echo "Starting interactive shell in the nginx container..."
	$(COMPOSE) -f $(DOCKER_COMPOSE_FILE) exec nginx -it bash

in_django:
	@echo "Starting interactive shell in the django container..."
	$(COMPOSE) -f $(DOCKER_COMPOSE_FILE) exec django -it bash

help:
	@echo "═══════════════════════════════════════════════════════════════"
	@echo "CONTENEDORES"
	@echo "═══════════════════════════════════════════════════════════════"
	@echo "  build              - Build and start the containers"
	@echo "  down               - Stop and remove the containers"
	@echo "  restart            - Restart the containers"
	@echo "  rebuild            - Rebuild the containers without cache"
	@echo "  re                 - Clean and rebuild the containers"
	@echo "  start              - Start the containers"
	@echo "  stop               - Stop the containers"
	@echo ""
	@echo "CERTIFICADOS (elige uno)"
	@echo "═══════════════════════════════════════════════════════════════"
	@echo "  setup-selfsigned   - Generar certificados autofirmados (DEV)"
	@echo "  setup-letsencrypt  - Generar certificados Let's Encrypt (PROD)"
	@echo "                       make setup-letsencrypt DOMAIN=tu.com EMAIL=tu@email.com"
	@echo "  switch-dev         - Cambiar a HTTP (desarrollo)"
	@echo "  switch-prod        - Cambiar a HTTPS (producción)"
	@echo "  show-nginx-config  - Ver configuración actual"
	@echo "  rm-selfsigned      - Eliminar certificados autofirmados"
	@echo "  rm-letsencrypt     - Eliminar certificados Let's Encrypt"
	@echo ""
	@echo "LOGS Y DEBUGGING"
	@echo "═══════════════════════════════════════════════════════════════"
	@echo "  logs               - Ver logs (opcionalmente: make logs -f)"
	@echo "  status             - Ver estado de contenedores/imágenes/volúmenes"
	@echo "  in_nginx           - Shell interactivo en contenedor nginx"
	@echo "  in_django          - Shell interactivo en contenedor django"
	@echo ""
	@echo "LIMPIEZA"
	@echo "═══════════════════════════════════════════════════════════════"
	@echo "  clean              - Eliminar todos los contenedores/imágenes/volúmenes"
	@echo "  rm_none            - Eliminar imágenes huérfanas"
	@echo "  help               - Mostrar esta ayuda"
	@echo ""
	@echo "FLUJO RECOMENDADO (DESARROLLO)"
	@echo "═══════════════════════════════════════════════════════════════"
	@echo "  1. make build              (primera vez)"
	@echo "  2. make switch-dev         (HTTP, sin certificados)"
	@echo "  3. docker ps               (verificar que todo está bien)"
	@echo ""
	@echo "FLUJO PARA PRODUCCIÓN"
	@echo "═══════════════════════════════════════════════════════════════"
	@echo "  1. make build"
	@echo "  2. make setup-letsencrypt DOMAIN=tu.com EMAIL=tu@email.com"
	@echo "  3. make switch-prod        (HTTPS con certificados válidos)"
	@echo ""

.PHONY: all build down restart logs stop start rebuild re status rm_none clean in_nginx in_django help setup-selfsigned setup-letsencrypt rm-selfsigned rm-letsencrypt switch-dev switch-prod show-nginx-config