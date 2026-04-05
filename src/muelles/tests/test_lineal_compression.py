from muelles.lineal.compresion import MuelleCompresion
from muelles.pymodels.material import Material

# Crear material primero
material = Material(nombre_material="SL")

# Crear muelle con la clase correcta
muelle = MuelleCompresion(material=material, diametro_hilo=2.5)
# Configurar propiedades del muelle (usando nombres correctos de métodos)
muelle.validate_diameters(diametro_exterior=30)
print(f"✅ Test básico de MuelleCompresion")
 
muelle.calculate_spring_properties(numero_espiras=None, pitch=20, longitud_libre=100)

posiciones = [30,40,50,60,70,80,90,100]
for pos in posiciones:
    try:
        muelle.add_posicion_carga(longitud=pos)
    except ValueError as e:
        print(f"Error al agregar posición de carga en longitud {pos}: {e}")

spring_data = muelle.get_spring_data()
for key, value in spring_data.items():
    print(f"{key}: {value}")

data_positions = muelle.get_data_positions()
for pc in data_positions:
    print(f"Posición: {pc.posicion}, Carga: {pc.carga}, Tensión: {pc.tension}, Diámetro Externo: {pc.diametro_externo}")

muelle.get_forces_vs_position_graph(show=True)
muelle.get_forces_vs_travel_graph(show=True)
muelle.get_diameter_graph(show=True)
muelle.get_diameter_vs_position_graph(show=True)
muelle.create_goodman_diagram(show=True)

muelle.calculate_spring_properties(numero_espiras=10, pitch=None, longitud_libre=100)

posiciones = [30,40,50,60,70,80,90,100]
for pos in posiciones:
    try:
        muelle.add_posicion_carga(longitud=pos)
    except ValueError as e:
        print(f"Error al agregar posición de carga en longitud {pos}: {e}")

spring_data = muelle.get_spring_data()
for key, value in spring_data.items():
    print(f"{key}: {value}")

data_positions = muelle.get_data_positions()
for pc in data_positions:
    print(f"Posición: {pc.posicion}, Carga: {pc.carga}, Tensión: {pc.tension}, Diámetro Externo: {pc.diametro_externo}")

muelle.get_forces_vs_position_graph(show=True)
muelle.get_forces_vs_travel_graph(show=True)
muelle.get_diameter_graph(show=True)
muelle.get_diameter_vs_position_graph(show=True)
muelle.create_goodman_diagram(show=True)



print("🎉 Test completado exitosamente!")