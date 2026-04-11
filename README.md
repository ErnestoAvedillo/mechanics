# Página web de Ernesto Avedillo

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

### Para iniciar el proyecto
``` bash
make build
```

### Para renovar certificados:
``` bash
make renew-certificates
```
en make help están todas las opciones
