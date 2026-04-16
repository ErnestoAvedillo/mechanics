from playwright.sync_api import sync_playwright
import os
import pytest

@pytest.mark.django_db
def test_full_auth_flow_playwright():
    """
    Test de flujo completo: Registro -> Verificación -> Login usando Playwright.
    """
    with sync_playwright() as p:
        base_url = os.environ.get("DJANGO_URL", "http://django:8000")
        browser = p.chromium.launch()
        context = browser.new_context()
        page = context.new_page()

        # 1. Registro
        page.goto(f"{base_url}/signup/")
        page.fill('input[name="username"]', "pw_user")
        page.fill('input[name="email"]', "pw@example.com")
        page.fill('input[name="password"]', "Playwright123!")
        page.fill('input[name="confirm_password"]', "Playwright123!")
        page.click('button:has-text("Registrarse")')

        # 2. Verificar que estamos en la página de código
        assert "/verify-email/" in page.url
        
        # Como no podemos leer el email fácilmente en el test, 
        # forzamos la obtención del código desde la DB de Django (esto requiere acceso a la DB)
        # En un test puramente E2E usaríamos una API de correos, aquí simplificamos:
        from menuapp.models import EmailVerification
        from django.contrib.auth.models import User
        user = User.objects.get(username="pw_user")
        verification = EmailVerification.objects.get(user=user)
        
        page.fill('input[name="code"]', verification.code)
        page.click('button:has-text("Verificar")')

        # 3. Tras verificar, debería estar en el home e identificado
        # Según los cambios pedidos, el home ahora solo debería mostrar Login/Registro o nada si está logueado
        # Pero según la lógica de Django, tras login redirige a index
        assert page.url == f"{base_url}/" or page.url == f"{base_url}/home/"

        print("✅ Test de flujo de autenticación con Playwright completado.")
        browser.close()

def test_login_logout_playwright():
    with sync_playwright() as p:
        base_url = os.environ.get("DJANGO_URL", "http://django:8000")
        browser = p.chromium.launch()
        page = browser.new_page()

        # Crear usuario previo
        from django.contrib.auth.models import User
        if not User.objects.filter(username="login_test").exists():
            u = User.objects.create_user(username="login_test", password="password123")
            u.is_active = True
            u.save()

        page.goto(f"{base_url}/login/")
        page.fill('input[name="username"]', "login_test")
        page.fill('input[name="password"]', "password123")
        page.click('button[type="submit"]')

        # Verificar redirección
        assert page.url == f"{base_url}/"
        
        print("✅ Test de Login con Playwright completado.")
        browser.close()
