from playwright.sync_api import sync_playwright
import os

def test_pin_hole_form():
    with sync_playwright() as p:
        base_url = os.environ.get("DJANGO_URL", "http://django:8000")

        browser = p.chromium.launch()
        # Puedes cambiar headless a False y agregar un slow_mo si quieres ver visualmente cómo se rellena
        # browser = p.chromium.launch(headless=False, slow_mo=100)
        
        page = browser.new_page()

        # 1. Ir a la página del form de pin-hole
        page.goto(f"{base_url}/tolerances/pin-hole/")

        # 2. Rellenar datos del Pin
        page.fill('input[name="pin_nominal"]', "10.0")
        page.fill('input[name="pin_tol_sup"]', "0.05")
        page.fill('input[name="pin_tol_inf"]', "-0.05")

        # 3. Rellenar datos del Agujero (Hole)
        page.fill('input[name="hole_nominal"]', "10.2")
        page.fill('input[name="hole_tol_sup"]', "0.1")
        page.fill('input[name="hole_tol_inf"]', "-0.1")

        # 4. Rellenar datos de Distribucion
        page.fill('input[name="cp"]', "1.33")
        page.fill('input[name="samples"]', "100000")

        # 5. Enviar formulario
        invalid_fields = page.evaluate('''() => {
            return Array.from(document.forms[0].elements)
                .filter(el => !el.validity.valid)
                .map(el => el.name + " (" + el.validationMessage + ")");
        }''')
        print(f"Campos inválidos antes de enviar: {invalid_fields}")

        page.click('button:has-text("Calcular")')

        # 6. Verificar éxito (Se debe cargar la sección de Resultados)
        try:
            # Aumentamos el timeout a 15s por si el cálculo tarda en responder
            page.wait_for_selector('section.results h2:has-text("Resultados")', timeout=15000)
        except Exception as e:
            # Si falla, vamos a capturar si hay un mensaje de error y sacar una captura
            error_msg = page.locator('.error').first
            if error_msg.is_visible():
                print(f"❌ Falló el cálculo. Error en pantalla: {error_msg.inner_text()}")
            else:
                print("❌ Timeout esperando los resultados. Guardando captura en error_debug.png...")
                page.screenshot(path="error_debug.png", full_page=True)
            raise e

        # Opcional: Validar que los resultados aparezcan correctamente según el HTML
        assert "Pin" in page.content()
        assert "Agujero" in page.content()
        assert "Ajuste" in page.content()

        print("✅ Test de Pin-Hole completado con éxito!")
        browser.close()

if __name__ == "__main__":
    test_pin_hole_form()
