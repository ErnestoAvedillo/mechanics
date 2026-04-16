from playwright.sync_api import sync_playwright
import os


def test_rellenar_formulario():
    with sync_playwright() as p:
        # Usamos el nombre del servicio de docker "django" en lugar de localhost
        base_url = os.environ.get("DJANGO_URL", "http://django:8000")

        browser = p.chromium.launch()
        page = browser.new_page()

        # 1. Ir a la página del formulario
        page.goto(f"{base_url}/tu-formulario/")

        # 2. Rellenar datos
        page.fill('input[name="username"]', "usuario_test")
        page.fill('input[name="email"]', "test@example.com")
        # Si tienes términos y condiciones
        page.check('input[type="checkbox"]')

        # 3. Enviar
        page.click('button[type="submit"]')

        # 4. Verificar éxito (por ejemplo, buscando un texto de confirmación)
        assert "Gracias por tu mensaje" in page.content()

        print("✅ Test completado con éxito!")
        browser.close()


if __name__ == "__main__":
    test_rellenar_formulario()

    """crea tambien tests de prueba en diferentes scripts para la s siguientes páginas:
/home/eavedillo/Desktop/mechanics2/src/templates/muelles/calculadora_compresion.html
/home/eavedillo/Desktop/mechanics2/src/templates/muelles/calculadora_torsion.html
/home/eavedillo/Desktop/mechanics2/src/templates/muelles/calculadora_torsion.html"""