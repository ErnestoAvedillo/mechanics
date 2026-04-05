from muelles.lineal.compresion import MuelleLineal
from muelles.pymodels.material import Material

# Crear material primero
material = Material(nombre_material="SL")

# Crear muelle con la clase correcta
muelle = MuelleLineal(material=material, diametro_hilo=2.5)

# Configurar propiedades del muelle (usando nombres correctos de métodos)
muelle.diametro_medio = muelle.calcular_diametro_medio(diametro_exterior=30, diametro_interior=None)
print(f"✅ Test básico de MuelleLineal")
print(f"Material: {muelle.material.nombre_material}")
print(f"Diámetro hilo: {muelle.diametro_hilo}")
print(f"Diámetro medio: {muelle.diametro_medio}")
print(f"Número espiras: {muelle.numero_espiras}")
print(f"Longitud libre: {muelle.longitud_libre}")

# Ejemplo básico de cálculos
if hasattr(muelle, 'calcular_indice_muelle'):
    indice = muelle.calcular_indice_muelle()
    print(f"Índice del muelle: {indice:.2f}")

if hasattr(muelle, 'calcular_factor_de_wahl'):
    factor_wahl = muelle.calcular_factor_de_wahl()
    if factor_wahl is not None:
        print(f"Factor de Wahl: {factor_wahl:.3f}")
    else:
        print(f"Factor de Wahl: No calculado (valor nulo)")

muelle.calculate_spring_properties(numero_espiras=10, pitch=None, longitud_libre=100)
posiciones = [30,40,50,60,70,80,90,100]
for pos in posiciones:
    muelle.add_posicion_carga(longitud=pos)

spring_data = muelle.get_spring_data()
for key, value in spring_data.items():
    print(f"{key}: {value}")

data_positions = muelle.get_data_positions()
for pc in data_positions:
    print(f"Posición: {pc.posicion}, Carga: {pc.carga}, Tensión: {pc.tension}, Diámetro Externo: {pc.diametro_externo}")

print("🎉 Test completado exitosamente!")