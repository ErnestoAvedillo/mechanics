from muelles.lineal.goodman import Goodman, GoodmanData, GoodmanAnalyzer
from muelles.regresiones.factor_f.usar_modelo_factor_f import ModeloFactorF
from muelles.pymodels.material import Material
import matplotlib.pyplot as plt
from pandas import read_csv
import json

def test_goodman():
    """Test completo de la funcionalidad de Goodman usando la nueva arquitectura"""
    
    # Configurar matplotlib para mostrar gráficos
    plt.ion()  # Activa el modo interactivo
    
    print("=== ANÁLISIS DE GOODMAN ===")
    print("Probando nueva arquitectura separada...")
    
    # 1. Crear datos del material
    material = Material(nombre_material="DH")
    diameter = 1.0
    carga = "torsion"
    
    # 2. Opción A: Usar la nueva arquitectura (recomendada)
    print("\n--- Método 1: Nueva arquitectura ---")
    data = GoodmanData(material=material, diameter=diameter, carga=carga, cycles=1e3)
    analyzer = GoodmanAnalyzer(data)
    
    # Definir punto de operación
    sigma_max = 400  # MPa
    sigma_min = 100  # MPa
    
    # Mostrar información del análisis
    summary = analyzer.get_analysis_summary(sigma_max, sigma_min)
    print(f"Material: {summary['material']}")
    print(f"Diámetro: {summary['diameter']} mm")
    print(f"Tipo de carga: {summary['load_type']}")
    print(f"Factor de seguridad: {summary['safety_factor']:.2f}")
    print(f"RMa min: {summary['strengths']['RMa_min_MPa']:.1f} MPa")
    print(f"Se: {summary['strengths']['Se_MPa']:.1f} MPa")
    print(f"Sf: {summary['strengths']['Sf_MPa']:.1f} MPa")
    
    # Mostrar diagrama mejorado
    print("\nMostrando diagrama de Goodman mejorado...")
    fig1 = analyzer.plot_diagram(sigma_max, sigma_min, show_plot=True)
    
    # 3. Opción B: Usar la clase de retrocompatibilidad
    print("\n--- Método 2: Retrocompatibilidad ---")
    goodman_legacy = Goodman(material=material, diameter=diameter, carga=carga)
    print("Probando método legacy plot_diagramm...")
    goodman_legacy.plot_diagramm(sigma_max, sigma_min)
    
    # 4. Análisis adicional con el nuevo sistema
    print("\n--- Análisis adicional ---")
    print(f"Factor kₐ (superficie): {analyzer.k_a:.4f}")
    print(f"Factor k_b (tamaño): {analyzer.k_b:.4f}")
    print(f"Factor k_c (carga): {analyzer.k_c:.4f}")
    
    # Test con diferentes puntos de operación
    test_points = [
        (300, 50),   # Punto seguro
        (500, 200),  # Punto crítico
        (200, 0),    # Solo tensión media
    ]
    
    print("\n--- Análisis de múltiples puntos ---")
    for i, (s_max, s_min) in enumerate(test_points):
        sf = analyzer.calculate_safety_factor(s_max, s_min)
        status = "SEGURO" if sf > 1.5 else "CRÍTICO" if sf > 1.0 else "PELIGROSO"
        print(f"Punto {i+1}: σmax={s_max}, σmin={s_min} → FS={sf:.2f} [{status}]")
    
    # Guardar resumen en JSON para análisis posterior
    with open('/tmp/goodman_analysis.json', 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"\nResumen guardado en: /tmp/goodman_analysis.json")
    
    # Mantener la ventana abierta
    plt.ioff()  # Desactiva el modo interactivo
    input("Presiona Enter para cerrar los gráficos...")  # Pausa para ver el gráfico

def test_comparacion_materiales():
    """Test adicional: comparar diferentes materiales"""
    print("\n=== COMPARACIÓN DE MATERIALES ===")
    
    materiales = ["DH", "DM"]  # Agregar más si están disponibles
    diameter = 1.5
    carga = "torsion"
    sigma_max, sigma_min = 350, 80
    
    for mat_name in materiales:
        try:
            material = Material(nombre_material=mat_name)
            data = GoodmanData(material=material, diameter=diameter, carga=carga, cycles=1e3)
            analyzer = GoodmanAnalyzer(data)
            sf = analyzer.calculate_safety_factor(sigma_max, sigma_min)
            
            print(f"{mat_name}: FS = {sf:.2f}, RMa = {analyzer.wire_char.RMa_min:.0f} MPa")
            
        except Exception as e:
            print(f"Error con material {mat_name}: {e}")

def test_factorf():
    """Test específico para el modelo de factor f"""
    print("\n=== TEST MODELO FACTOR F ===")
    material = Material(nombre_material="DH")
    carga = "torsion"
    pd = read_csv("/home/ernesto/Desktop/djmenu/muelles/material/DIAMETRO_TOLERANCIAS.csv")
    diameters = pd['diameter'].values
    valores_sf =[]
    for diameter in diameters:
        data = GoodmanData(material=material, diameter=diameter, carga=carga, cycles=1001)
        analyzer = GoodmanAnalyzer(data)
        valores_sf.append(analyzer.Ssf)
        print(f"Diámetro: {diameter:.2f} mm → Sf: {analyzer.Ssf:.1f} MPa")
    plt.figure(figsize=(8, 5))
    plt.plot(diameters, valores_sf, marker='o')
    plt.title("Resistencia a la fatiga Sf vs Diámetro del hilo")
    plt.xlabel("Diámetro del hilo (mm)")
    plt.ylabel("Resistencia a la fatiga Sf (MPa)")
    plt.grid(True)
    plt.show()

    material = Material(nombre_material="DH")
    carga = "torsion"
    diameters = [0.5, 1.0, 1.5, 2.0]
    cycles = [1e3, 1e4, 1e5, 1e6]
    markers = ['o', 's', 'D', '^']
    for diameter in diameters:
        valores_sf = []
        valores_se = []
        for cycle in cycles:
            data = GoodmanData(material=material, diameter=diameter, carga=carga, cycles=cycle)
            analyzer = GoodmanAnalyzer(data)
            print(f"Diámetro: {diameter:.2f} mm, Ciclos: {cycle:.0f} → Sf: {analyzer.Ssf:.1f} MPa")
            valores_sf.append(analyzer.Ssf)
            valores_se.append(analyzer.Sse)
        plt.figure(figsize=(8, 5))
        plt.plot(cycles, valores_sf, marker=markers[diameters.index(diameter)], label=f'Diámetro: {diameter:.2f} mm')
        plt.plot(cycles, valores_se, marker=markers[diameters.index(diameter)], label=f'Diámetro: {diameter:.2f} mm')
        plt.xscale('log')
        plt.title(f"Resistencia a la fatiga Sf vs Ciclos (Diámetro: {diameter:.2f} mm)")
        plt.xlabel("Ciclos (log scale)")
        plt.ylabel("Resistencia a la fatiga Sf (MPa)")
        plt.grid(True)
        plt.legend()  
    plt.show()

if __name__ == "__main__":
    test_goodman()
    # test_comparacion_materiales()
    # test_factorf()
