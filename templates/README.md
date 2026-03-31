# Menú de Cabecera Reutilizable

## ✅ Configuración Completada

Se ha creado un **menú de cabecera moderno** que se reutiliza en todas las páginas:

### Archivos Creados:

1. **`templates/base.html`** - Template base que heredan todas las páginas
2. **`templates/includes/header.html`** - Componente del header (navegación + imagen)
3. **`static/css/header.css`** - Estilos completos del header
4. **`static/images/header-background.jpg`** - Imagen de fondo del header (placeholder SVG)

---

## 🔧 Cómo Usar en tus Páginas

### Opción 1: Usar el Template Base (RECOMENDADO)

Hereda de `base.html` en tus templates:

```html
{% extends 'base.html' %}
{% load static %}

{% block title %}Tu Título de Página{% endblock %}

{% block extra_css %}
  <link rel="stylesheet" href="{% static 'tu-app/css/estilo.css' %}">
{% endblock %}

{% block content %}
  <!-- Tu contenido aquí -->
{% endblock %}

{% block extra_js %}
  <!-- Scripts adicionales -->
{% endblock %}
```

### Opción 2: Incluir Header en Otros Templates

Si prefieres no usar template base, puedes incluir solo el header:

```html
{% include 'includes/header.html' %}
```

---

## 🖼️ Agregar tu Propia Imagen de Header

1. Prepara una imagen (recomendado 1920x380px o similar)
2. Guárdala en: **`static/images/header-background.jpg`**
3. El header la usará automáticamente

**Formato recomendado:**
- Ancho: 1920px o superior
- Alto: 380px
- Formato: JPG, PNG o WebP
- Compatibilidad: Imagen que se vea bien con overlay oscuro (25-35% de opacidad)

---

## 📱 Características del Header

✨ **Responsive:**
- Desktop: navegación horizontal
- Mobile: menú desplegable (hamburguesa)

✨ **Características:**
- Imagen de fondo con efecto parallax
- Navegación superpuesta (overlay con transparencia)
- Logo/Branding a la izquierda
- Botón "Contacto" destacado
- Animaciones suaves en los enlaces

✨ **Navegación Actual:**
- Inicio (/)
- Muelles (/muelles/)
- Tolerancias (/tolerances/)
- Contacto (#contact)

---

## 📝 Personalizar el Menú

Edita `templates/includes/header.html`:

```html
<ul class="nav-menu" id="navMenu">
  <li><a href="/" class="nav-link">Inicio</a></li>
  <li><a href="/muelles/" class="nav-link">Muelles</a></li>
  <li><a href="/tolerances/" class="nav-link">Tolerancias</a></li>
  <li><a href="/tu-nueva-pagina/" class="nav-link">Nueva Página</a></li>
  <!-- Agregá más enlaces aquí -->
</ul>
```

---

## 🎨 Personalizar Colores

En `static/css/header.css`, modifica las variables CSS:

```css
:root {
  --nav-bg: rgba(11, 31, 51, 0.92);        /* Color fondo navegación */
  --nav-text: #ffffff;                      /* Color texto */
  --accent: #0f4c81;                        /* Color acento (botón contacto) */
  --accent-light: #dbe8f5;                  /* Subrayado hover */
}
```

---

## 🔄 Próximos Pasos

1. **Actualiza otras páginas** para que usen `{% extends 'base.html' %}`
2. **Reemplaza la imagen placeholder** con tu propia imagen de header
3. **Personaliza los enlaces** del menú según tus necesidades

¡Listo! El menú reutilizable está funcional en todas partes 🚀
