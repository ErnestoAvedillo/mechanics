# El Menú de Ernesto® - Versión Django Optimizada

Sistema de gestión de menús y enlaces desarrollado en Django. Permite editar archivos CSV y JSON de forma visual e intuitiva.

## Características ✨
- 📊 **Editor CSV Interactivo**: Vista tabla y texto con drag & drop
- 🔧 **Editor JSON Visual**: Edición de estructuras JSON complejas  
- 📱 **Interfaz Responsive**: Optimizado para móvil, tablet y escritorio
- 📁 **Gestión de Enlaces**: Organización de carpetas y URLs
- ⚡ **Código Optimizado**: Reducción de dependencias y archivos innecesarios

## Tecnologías 🛠️
- Django 6.0.1 (minimalista)
- JavaScript ES6+ modular
- CSS Grid y Flexbox
- HTML5 semántico

## Instalación 🚀

### Estructura del Proyecto

- **mechanics/**: Configuración principal del proyecto Django
- **menuapp/**: Aplicación Django con las vistas y lógica de negocio
- **templates/**: Plantillas HTML (ahora usando sintaxis Django)
- **static/**: Archivos estáticos (CSS, JS, datos)

### Cambios Realizados

1. **Vistas (menuapp/views.py)**:
   - Convertidas de Flask a Django
   - Uso de `render()` en lugar de `render_template()`
   - Uso de `redirect()` con `reverse()`
   - `request.GET` en lugar de `request.args`
   - `request.POST` para formularios

2. **URLs (menuapp/urls.py)**:
   - Configuración de rutas Django
   - Soporte para parámetros en URLs

3. **Plantillas**:
   - `{% load static %}` y `{% load menu_filters %}`
   - `{% static 'path' %}` en lugar de `url_for('static', filename='path')`
   - `{% url 'view_name' %}` en lugar de `url_for('view_name')`
   - `{% csrf_token %}` en formularios POST

4. **Filtros Personalizados (menuapp/templatetags/menu_filters.py)**:
   - `is_url`: Verifica si una cadena es una URL

### Configuración

La configuración principal está en `mechanics/settings.py`:

- **INSTALLED_APPS**: Incluye 'menuapp'
- **TEMPLATES**: Configurado para usar el directorio 'templates'
- **STATICFILES_DIRS**: Apunta al directorio 'static'

## Cómo Ejecutar

### Opción 1: Usando el script

```bash
./run_server.sh
```

### Opción 2: Comando directo

```bash
uv run python manage.py runserver
```

### Opción 3: Con comando corregido

```bash
uv run python manage.py runserver
```

El servidor estará disponible en: `http://127.0.0.1:8000/`

## Comandos Útiles

### Crear migraciones
```bash
uv run python manage.py makemigrations
```

### Aplicar migraciones
```bash
uv run python manage.py migrate
```

### Verificar el proyecto
```bash
uv run python manage.py check
```

### Crear superusuario
```bash
uv run python manage.py createsuperuser
```

## Errores Corregidos

1. ✅ Configuración de INSTALLED_APPS (añadido 'menuapp')
2. ✅ Configuración de directorios de templates y static
3. ✅ Conversión de sintaxis Flask a Django en templates
4. ✅ Creación de filtros personalizados para templates
5. ✅ Configuración de URLs
6. ✅ Añadido CSRF token en formularios
7. ✅ Migraciones aplicadas

## Notas

- El proyecto usa `uv` para gestionar el entorno Python
- Django 6.0.1 está instalado
- La base de datos SQLite se crea automáticamente
- Los archivos estáticos se sirven desde el directorio `static/`
