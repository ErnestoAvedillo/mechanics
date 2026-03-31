from muelles.regresiones.factor_f.usar_modelo_factor_f import ModeloFactorF
import numpy as np
from math import log10
from muelles.pymodels.material import Material
from muelles.pymodels.wire_characteristics import WireCharacteristics
from matplotlib import pyplot as plt
def test_factor_f():
    """Test del modelo de regresión para el factor f"""
    print("=== TEST DEL MODELO DE REGRESIÓN PARA EL FACTOR f ===")

    material = Material(nombre_material="DH")
    wire_char = WireCharacteristics(material=material, diametro_hilo=1.5)
    print(f"Material: {material.nombre_material}, RMa_min: {wire_char.RMa_min:.2f} MPa")
    
    # Cargar modelo
    modelo = ModeloFactorF()
    
    # Valores de Sut para probar (incluyendo casos fuera de rango)
    cycles_to_test = [950,1000, 1050, 10000, 100000, 1000000, 10000000]  # Ciclos para probar
    
    print("ciclos| Factor f predicho | Ssf")
    print("-------------------------------")
    SSf = []
    Sse_prime = wire_char.material.elastic_limit_factor * wire_char.RMa_min
    for cycle in cycles_to_test:
        f_predicho = modelo.predecir(wire_char.RMa_min)
        if cycle <= 1e3:
            Ssf_prime = cycle**(log10(f_predicho)/3)  # Aproximación para bajos ciclos
        else:
            if cycle > 1e6:
                cycle = 1e6  # Limitar a 1 millón de ciclos para la predicción
            a = f_predicho **2 / wire_char.material.elastic_limit_factor 
            b = -log10(f_predicho  * wire_char.RMa_min / Sse_prime) / 3
            Ssf_prime = a * cycle**b

        print(f"{cycle:8} | {f_predicho:.4f}")
        SSf.append(Ssf_prime)

    plt.figure(figsize=(8, 5))
    plt.plot(cycles_to_test, SSf, marker='o')
    plt.xscale('log')
    plt.title("Resistencia a la fatiga Ssf' vs Ciclos")
    plt.xlabel("Ciclos (log scale)")
    plt.ylabel("Resistencia a la fatiga Ssf' (MPa)")
    plt.grid(True)
    plt.show()

if __name__ == "__main__":
    test_factor_f()