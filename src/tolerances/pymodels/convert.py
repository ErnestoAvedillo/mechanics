# Function to convert any input to a Pint object
from pint import Quantity
from typing import Any, Annotated
from pint import  Quantity, UnitRegistry
from pydantic import BeforeValidator

ureg = UnitRegistry()


def as_quantity(v: Any) -> Quantity:
    if isinstance(v, Quantity):
        return v
    if isinstance(v, (int, float)):
        return v * ureg.mm  # Assumes mm by default if it's a number
    if isinstance(v, str):
        return ureg(v)
    return v


# Custom type for reuse
PintQuantity = Annotated[Quantity, BeforeValidator(as_quantity)]