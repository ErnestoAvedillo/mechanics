import pytest
import sys
import os

# Agregar el directorio padre al path para permitir importaciones
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, parent_dir)

from muelles.pymodels.wire_characteristics import WireCharacteristics
from muelles.pymodels.material import Material

def test_create_wire_characteristics()-> WireCharacteristics:
    # Test creating wire_characteristics with valid parameters
    material = Material(
        nombre_material="SL",
    )
    
    wire_char = WireCharacteristics(
        material=Material(
        nombre_material="SL",
        ),
        diametro_hilo=2.5
    )
    
    assert wire_char.diametro_hilo == 2.5
    assert wire_char.material.nombre_material == "SL"
    assert wire_char.tolerancia_diametro is not None
    assert wire_char.RMa_min is not None
    assert wire_char.RMa_max is not None
    print ("Material:", wire_char.material.nombre_material)

    return wire_char

def test_wire_characteristics_default_values()-> WireCharacteristics:
    # Test creating wire_characteristics with minimal parameters
    material = Material(
        nombre_material="SH",
    )
    
    wire_char = WireCharacteristics(
        material=material,
            diametro_hilo=1.0
    )
    
    assert wire_char.diametro_hilo == 1.0
    assert wire_char.material.nombre_material == "SH"
    assert hasattr(wire_char, 'tolerancia_diametro')
    assert hasattr(wire_char, 'RMa_min')
    assert hasattr(wire_char, 'RMa_max')
    
    return wire_char

if __name__ == "__main__":
    wire=test_create_wire_characteristics()
    print (f"características del material creado:")
    print (f"tipo: {wire.material.nombre_material}")
    print (f" diámetro hilo: {wire.diametro_hilo}")
    print (f" tolerancia diámetro: {wire.tolerancia_diametro}")
    print (f" RMa_min: {wire.RMa_min}")
    print (f" RMa_max: {wire.RMa_max }")
    wire = test_wire_characteristics_default_values()
    print (f"características del material creado:")
    print (f"tipo: {wire.material.nombre_material}")
    print (f" diámetro hilo: {wire.diametro_hilo}")
    print (f" tolerancia diámetro: {wire.tolerancia_diametro}")
    print (f" RMa_min: {wire.RMa_min}")
    print (f" RMa_max: {wire.RMa_max }")
    print("✅ Todos los tests pasaron correctamente!")