from playwright.sync_api import sync_playwright
import os

def test_insert_support_form():
    with sync_playwright() as p:
        base_url = os.environ.get("DJANGO_URL", "http://django:8000")

        browser = p.chromium.launch()
        # Puedes cambiar headless a False y agregar un slow_mo si quieres ver visualmente cómo se rellena
        # browser = p.chromium.launch(headless=False, slow_mo=100)
        
        page = browser.new_page()

        # 1. Ir a la página del form
        page.goto(f"{base_url}/tolerances/insert-support/")

        # 2. Rellenar datos de Altura soporte
        page.fill('input[name="support_height_nominal"]', "20.0")
        page.fill('input[name="support_height_tol_sup"]', "0.1")
        page.fill('input[name="support_height_tol_inf"]', "-0.1")

        # 3. Rellenar datos de Altura inserto
        page.fill('input[name="spacer_height_nominal"]', "18.0")
        page.fill('input[name="spacer_height_tol_sup"]', "0.05")
        page.fill('input[name="spacer_height_tol_inf"]', "-0.05")

        # 4. Rellenar datos de Diametro soporte
        page.fill('input[name="support_diameter_nominal"]', "10.0")
        page.fill('input[name="support_diameter_tol_sup"]', "0.2")
        page.fill('input[name="support_diameter_tol_inf"]', "-0.2")

        # 5. Rellenar datos de Diametro inserto
        page.fill('input[name="spacer_diameter_nominal"]', "9.8")
        page.fill('input[name="spacer_diameter_tol_sup"]', "0.1")
        page.fill('input[name="spacer_diameter_tol_inf"]', "0.0")

        # 6. Rellenar datos de Distribucion
        page.fill('input[name="cp"]', "1.33")
        page.fill('input[name="samples"]', "100000")

        # 7. Enviar formulario
        page.click('button:has-text("Calcular")')

        # 8. Verificar éxito (Se debe cargar la sección de Resultados)
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

        # Opcional: Validar que los resultados aparezcan
        assert "Diametro del Inserto" in page.content()
        assert "Clearance system" in page.content()

        print("✅ Test de Insert Support completado con éxito!")
        browser.close()

if __name__ == "__main__":
    test_insert_support_form()
