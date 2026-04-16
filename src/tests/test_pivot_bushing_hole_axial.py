from playwright.sync_api import sync_playwright
import os

def test_pivot_bushing_hole_axial_form():
    with sync_playwright() as p:
        base_url = os.environ.get("DJANGO_URL", "http://django:8000")

        browser = p.chromium.launch()
        page = browser.new_page()

        # 1. Ir a la página del form
        page.goto(f"{base_url}/tolerances/pivot-bushing-hole-axial/")

        # 2. Rellenar datos de Wall distance
        page.fill('input[name="wall_distance_nominal"]', "50.0")
        page.fill('input[name="wall_distance_tol_sup"]', "0.2")
        page.fill('input[name="wall_distance_tol_inf"]', "-0.2")

        # 3. Rellenar datos de Bushing flange 1
        page.fill('input[name="bushing_flange_1_nominal"]', "2.5")
        page.fill('input[name="bushing_flange_1_tol_sup"]', "0.05")
        page.fill('input[name="bushing_flange_1_tol_inf"]', "-0.05")

        # 4. Rellenar datos de Bushing flange 2
        page.fill('input[name="bushing_flange_2_nominal"]', "2.5")
        page.fill('input[name="bushing_flange_2_tol_sup"]', "0.05")
        page.fill('input[name="bushing_flange_2_tol_inf"]', "-0.05")

        # 5. Rellenar datos de Tube Length
        page.fill('input[name="tube_length_nominal"]', "44.0")
        page.fill('input[name="tube_length_tol_sup"]', "0.1")
        page.fill('input[name="tube_length_tol_inf"]', "-0.1")

        # 6. Rellenar datos de Distribucion
        page.fill('input[name="cp"]', "1.33")
        page.fill('input[name="samples"]', "1000")

        # Comprobar si hay errores de validacion antes de enviar
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
                print("❌ Timeout esperando los resultados. Guardando captura en error_debug_axial.png...")
                page.screenshot(path="error_debug_axial.png", full_page=True)
            raise e

        # Validaciones de la respuesta
        assert "Distancia entre paredes" in page.content()
        assert "Longitud del Tubo" in page.content()

        print("✅ Test de Pivot Bushing Hole Axial completado con éxito!")
        browser.close()

if __name__ == "__main__":
    test_pivot_bushing_hole_axial_form()
