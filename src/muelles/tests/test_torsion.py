from muelles.lineal.torsion import MuelleTorsion
from muelles.pymodels.material import Material
from math import pi

# Crear material primero
material = Material(nombre_material="SL")
# Crear muelle con la clase correcta
muelle = MuelleTorsion(material=material, wire_diameter=2.5)
# Configurar propiedades del muelle (usando nombres correctos de métodos)
muelle.configure_spring(
    diametro_medio=20.0,
    numero_espiras=10,
    pitch=5.0,
    angulo_libre=45.0,
    radious_leg_fija=10.0,
    radious_leg_movil=10.0
)
properties = muelle.get_spring_properties()
print("Propiedades del muelle después de la configuración:")
for key, item in properties.items():
    print(f"El valor de {key} = {item}")
muelle.add_position(angle_travel=10)
muelle.add_position(angle_travel=50)
posiciones = muelle.get_positions()
for pos in posiciones:
    print(f"Posición: Carga={pos.carga} N:")
    print(f"    Tensión={pos.tension:.2f} MPa")
    print(f"    Posición={pos.posicion * 180 / pi:.6f} degrees")
    print(f"    Recorrido={pos.recorrido * 180 / pi:.6f} degrees")
    print(f"    Diámetro Externo={pos.diametro_externo:.6f} mm")
    print(f"    Diámetro Interno={pos.diametro_interno:.6f} mm")
    print("-" * 40)
