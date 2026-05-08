# Función para convertir cualquier entrada a objeto Pint
from pint import Quantity
from typing import Any, Annotated
from pint import  Quantity, UnitRegistry
from pydantic import BeforeValidator

ureg = UnitRegistry()


def as_quantity(v: Any) -> Quantity:
    if isinstance(v, Quantity):
        return v
    if isinstance(v, (int, float)):
        return v * ureg.mm  # Asume mm por defecto si es número
    if isinstance(v, str):
        return ureg(v)
    return v


# Tipo personalizado para reutilizar
PintQuantity = Annotated[Quantity, BeforeValidator(as_quantity)]