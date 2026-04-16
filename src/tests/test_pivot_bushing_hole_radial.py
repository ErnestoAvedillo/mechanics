from playwright.sync_api import sync_playwright
import os

def test_pivot_bushing_hole_radial_form():
    with sync_playwright() as p:
        base_url = os.environ.get("DJANGO_URL", "http://django:8000")

        browser = p.chromium.launch()
        page = browser.new_page()

        # 1. Ir a la página del form
        page.goto(f"{base_url}/tolerances/pivot-bushing-hole-radial/")

        # 2. Rellenar datos de Inner Tube (Hole)
        page.fill('input[name="hole_nominal"]', "12.0")
        page.fill('input[name="hole_tol_sup"]', "0.1")
        page.fill('input[name="hole_tol_inf"]', "-0.05")

        # 3. Rellenar datos de Outer Bushing
        page.fill('input[name="outer_bushing_nominal"]', "12.2")
        page.fill('input[name="outer_bushing_tol_sup"]', "0.05")
        page.fill('input[name="outer_bushing_tol_inf"]', "-0.05")

        # 4. Rellenar datos de Inner Bushing
        page.fill('input[name="inner_bushing_nominal"]', "10.0")
        page.fill('input[name="inner_bushing_tol_sup"]', "0.05")
        page.fill('input[name="inner_bushing_tol_inf"]', "-0.05")

        # 5. Rellenar datos del Pin
        page.fill('input[name="pin_nominal"]', "9.8")
        page.fill('input[name="pin_tol_sup"]', "0.05")
        page.fill('input[name="pin_tol_inf"]', "-0.05")

        # 6. Rellenar datos de Distribucion
        page.fill('input[name="cp"]', "1.33")
        page.fill('input[name="samples"]', "1000")

        # Comprobar validaciones del navegador
        invalid_fields = page.evaluate('''() => {
            return Array.from(document.forms[0].elements)
                .filter(el => !el.validity.valid)
                .map(el => el.name + " (" + el.validationMessage + ")");
        }''')
        print(f"Campos inválidos antes de enviar: {invalid_fields}")

        # 7. Enviar formulario
        page.click('button:has-text("Calcular")')

        # 8. Verificar éxito (Se debe cargar la sección de Resultados)
        try:
            page.wait_for_selector('section.results h2:has-text("Resultados")', timeout=15000)
        except Exception as e:
            error_msg = page.locator('.error').first
            if error_msg.is_visible():
                print(f"❌ Falló el cálculo. Error en pantalla: {error_msg.inner_text()}")
            else:
                print("❌ Timeout esperando los resultados. Guardando captura en error_debug_radial.png...")
                page.screenshot(path="error_debug_radial.png", full_page=True)
            raise e

        # Validaciones del resultado
        assert "Pin" in page.content()
        assert "Tubo" in page.content()
        assert "Casquillo Exterior" in page.content()

        print("✅ Test de Pivot Bushing Hole Radial completado con éxito!")
        browser.close()

if __name__ == "__main__":
    test_pivot_bushing_hole_radial_form()
