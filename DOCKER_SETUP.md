# Docker Setup para Django + Nginx

Este proyecto está configurado para ejecutarse con Docker y Docker Compose, con Django servido por Gunicorn y Nginx como proxy inverso.

## Archivos creados

- **Dockerfile**: Imagen Docker con Python 3.13, Django y Gunicorn (multi-stage build)
- **docker-compose.yml**: Orquestación de servicios Django + Nginx
- **nginx/nginx.conf**: Configuración de Nginx como proxy inverso
- **.dockerignore**: Archivos ignorados al construir la imagen

## Requisitos

- Docker
- Docker Compose

## Instrucciones de uso

### 1. Construir e iniciar los contenedores

```bash
docker-compose up --build
```

Esto:
- Construirá la imagen Docker de la aplicación Django
- Iniciará los servicios de Django y Nginx
- Expondrá la aplicación en `http://localhost`

### 2. En el primer inicio (migraciones)

```bash
# En otra terminal, ejecuta las migraciones de Django
docker-compose exec django python manage.py migrate
```

### 3. Crear un superusuario (opcional)

```bash
docker-compose exec django python manage.py createsuperuser
```

### 4. Detener los contenedores

```bash
docker-compose down
```

### 5. Detener y eliminar volúmenes

```bash
docker-compose down -v
```

## Notas de Producción

Antes de desplegar a producción, asegúrate de:

1. **SECRET_KEY**: Cambiar la clave secreta en `settings.py`
2. **ALLOWED_HOSTS**: Actualizar con tus dominios reales en `settings.py`
3. **Variables de entorno**: Usar variables de entorno para credenciales sensibles
4. **HTTPS**: Configurar certificados SSL/TLS en Nginx (usar Let's Encrypt)
5. **Base de datos**: Cambiar de SQLite a PostgreSQL o MySQL para producción
6. **DEBUG = False**: Ya está configurado en `settings.py`

## Estructura de volúmenes

- `static_volume`: Archivos estáticos servidos por Nginx
- `media_volume`: Archivos media (uploads)
- `django_socket`: Socket Unix para comunicación entre Django y Nginx

## Puertos

- **Nginx**: Puerto 80 (HTTP) - `http://localhost`
- **Django**: Puerto 8000 (interno, NO expuesto)
- **Nginx-Django**: Comunicación vía socket Unix

## Logs

Ver logs de los contenedores:

```bash
# Logs de Django
docker-compose logs -f django

# Logs de Nginx
docker-compose logs -f nginx

# Todos los logs
docker-compose logs -f
```

## Ejecutar comandos en el contenedor

```bash
# Comandos de Django
docker-compose exec django python manage.py <comando>

# Shell de Python/Django
docker-compose exec django python manage.py shell

# Crear paquete de migración
docker-compose exec django python manage.py makemigrations
```
