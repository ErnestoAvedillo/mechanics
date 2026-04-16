from playwright.sync_api import sync_playwright
import os

def test_calculadora_compresion_form():
    with sync_playwright() as p:
        base_url = os.environ.get("DJANGO_URL", "http://django:8000")

        browser = p.chromium.launch()
        page = browser.new_page()

        # 1. Ir a la página del form
        page.goto(f"{base_url}/muelles/calculadora/compresion/")

        # 2. Material
        page.select_option('select[name="material"]', 'SM')
        page.fill('input[name="diametro_hilo"]', "1.5")
        page.select_option('select[name="numero_ciclos"]', '1e5')

        # 3. Geometría
        # Como hay un sistema JS sincronizando los campos y puede sobreescribir al teclear, forzamos su asignación
        page.fill('input[name="diametro_interior"]', "7.0")
        page.keyboard.press('Tab')
        page.wait_for_timeout(500)
        page.fill('input[name="diametro_exterior"]', "10.0")
        page.keyboard.press('Tab')
        page.wait_for_timeout(500)
        page.fill('input[name="diametro_medio"]', "8.5")
        page.keyboard.press('Tab')
        page.wait_for_timeout(500)
        page.fill('input[name="numero_espiras"]', "8.5")
        page.fill('input[name="longitud_libre"]', "30.0")
        
        # Estas pueden ser calculadas automáticamente por JS pero por si acaso rellenamos
        page.fill('input[name="longitud_inicial"]', "25.0")
        page.fill('input[name="longitud_final"]', "20.0")

        # 4. Extremos
        # Hacemos click en el div end-option que corresponda y por JS asignará el input hidden "tipo_final"
        page.locator('.compresion-end-option[data-value="cerrado"]').click()

        # Comprobar validaciones del navegador
        invalid_fields = page.evaluate('''() => {
            return Array.from(document.forms[0].elements)
                .filter(el => !el.validity.valid)
                .map(el => el.name + " (" + el.validationMessage + ")");
        }''')
        print(f"Campos inválidos antes de enviar: {invalid_fields}")

        # Enviar formulario forzadamente si hiciera falta o usando click
        # Usamos locator específico
        page.click('button:has-text("Calcular")')

        # Esperar la recarga y la renderización de los resultados
        try:
            page.wait_for_selector('h3:has-text("Resultados del Cálculo")', timeout=15000)
        except Exception as e:
            error_msg = page.locator('.error').first
            if error_msg.is_visible():
                print(f"❌ Falló el cálculo. Error en pantalla: {error_msg.inner_text()}")
            else:
                print("❌ Timeout esperando los resultados. Guardando captura en error_muelles_compresion.png...")
                page.screenshot(path="error_muelles_compresion.png", full_page=True)
            raise e

        print("✅ Test de Calculadora de Compresión completado con éxito!")
        browser.close()

if __name__ == "__main__":
    test_calculadora_compresion_form()