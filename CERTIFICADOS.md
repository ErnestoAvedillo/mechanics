# 🔐 CONFIGURACIÓN DE CERTIFICADOS HTTPS

Este proyecto soporta dos tipos de certificados SSL/TLS:

## 1️⃣ CERTIFICADOS AUTOFIRMADOS (Desarrollo Local)

**Recomendado para:** Desarrollo local, testing, ambientes no públicos

### Generar certificados autofirmados:
```bash
make setup-selfsigned
```

**Qué hace:**
- Genera certificados autofirmados con validez de 365 días
- Coloca los certificados en: `./certs/live/ernestoavedillo.com/`
- Estructura compatible con Let's Encrypt
- Crea copias en `./selfsigned.crt` y `./selfsigned.key` para compatibilidad

**Advertencias del navegador:**
- Los navegadores mostrarán advertencia de "Conexión no segura"
- Esto es **normal** para certificados autofirmados
- Los datos siguen siendo encriptados

### Eliminar certificados autofirmados:
```bash
make rm-selfsigned
```

---

## 2️⃣ CERTIFICADOS LET'S ENCRYPT (Producción)

**Recomendado para:** Producción, sitios públicos, dominios válidos

### Requisitos previos:
- Dominio válido (ej: `ernestoavedillo.com`)
- Acceso DNS para validar el dominio
- Contenedores de nginx en ejecución
- Puertos 80 y 443 accesibles desde internet

### Generar certificados Let's Encrypt:
```bash
# Con parámetros por defecto
make setup-letsencrypt

# Con dominio y email personalizados
make setup-letsencrypt DOMAIN=tu-dominio.com EMAIL=tu-email@ejemplo.com
```

**Qué hace:**
- Inicia nginx si no está corriendo
- Ejecuta certbot para validar el dominio
- Genera certificados válidos (validez de 90 días)
- Configura renovación automática
- Los certificados se almacenan en: `./certs/live/tu-dominio.com/`

### Renovación automática:
El servicio `certbot` renovará automáticamente los certificados cada 12 horas (60 días antes de expiración).

Puedes forzar renovación manual:
```bash
docker compose run --rm certbot renew --force-renewal
```

### Eliminar certificados Let's Encrypt:
```bash
make rm-letsencrypt
```

---

## 🔄 CAMBIAR ENTRE TIPOS DE CERTIFICADOS

### De autofirmado a Let's Encrypt:
```bash
make rm-selfsigned
make setup-letsencrypt DOMAIN=ernestoavedillo.com EMAIL=admin@ernestoavedillo.com
docker compose restart nginx
```

### De Let's Encrypt a autofirmado:
```bash
make rm-letsencrypt
make setup-selfsigned
docker compose restart nginx
```

---

## 📁 ESTRUCTURA DE CERTIFICADOS

Ambos tipos generan la misma estructura:

```
./certs/
└── live/
    └── ernestoavedillo.com/
        ├── fullchain.pem    (certificado + cadena)
        ├── privkey.pem      (clave privada)
        ├── cert.pem         (solo certificado, generado por Let's Encrypt)
        └── chain.pem        (cadena de certificados, generado por Let's Encrypt)
```

Docker monta esta carpeta en nginx como: `/etc/letsencrypt/`

---

## 🔒 CONFIGURACIÓN HTTPS EN DJANGO

Los certificados se usan automáticamente en nginx. Para habilitar HTTPS en Django (producción):

Editar `.env`:
```env
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

O en `settings.py` (ya está configurado):
```python
SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'False') == 'True'
SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False') == 'True'
CSRF_COOKIE_SECURE = os.environ.get('CSRF_COOKIE_SECURE', 'False') == 'True'
```

---

## 🧪 VERIFICAR CERTIFICADOS

### Ver certificado actual:
```bash
# Dentro del contenedor nginx
docker compose exec nginx openssl x509 -in /etc/letsencrypt/live/ernestoavedillo.com/fullchain.pem -text -noout

# O con curl desde host
curl -vI https://localhost 2>&1 | grep -A20 "certificate"
```

### Ver fecha de expiración:
```bash
docker compose exec nginx openssl x509 -enddate -noout \
  -in /etc/letsencrypt/live/ernestoavedillo.com/fullchain.pem
```

---

## ⚠️ TROUBLESHOOTING

### Error: "certificados no encontrados"
```bash
# Asegúrese de que existe el directorio
ls -la ./certs/live/ernestoavedillo.com/

# Si está vacío, regenere:
make rm-selfsigned
make setup-selfsigned
```

### Error: Puerto 80 u 443 en uso
```bash
# Ver qué está usando los puertos
sudo netstat -tlnp | grep ":80\|:443"

# O con docker
docker ps -a | grep -E "80|443"
```

### Certificados Let's Encrypt no se renuevan
```bash
# Ver logs de certbot
docker compose logs certbot

# Forzar renovación
docker compose run --rm certbot renew --verbose
```

### Navegador sigue indicando conexión no segura
- **Para autofirmados:** Es normal, confía en el navegador
- **Para Let's Encrypt:** Espera 10-15 minutos después de generar
- Limpia caché del navegador: `Ctrl+Shift+Delete` (Chrome/Firefox)

---

## 📞 REFERENCIAS

- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [Certbot Documentation](https://certbot.eff.org/docs/)
- [OpenSSL Guide](https://wiki.openssl.org/)
