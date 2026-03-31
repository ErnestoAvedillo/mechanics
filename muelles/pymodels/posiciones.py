from pydantic import BaseModel, field_validator, model_validator, ConfigDict
from typing import Optional, List
from pint import Quantity
from .units import ureg

class PosicionLineal(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True,
                              validate_assignment=True)

    posicion: Quantity
    recorrido: Quantity
    carga: Optional[Quantity] = None

    @field_validator('posicion', 'recorrido', mode='before')
    @classmethod
    def validate_positive_values(cls, v):
        if v is not None:
            try:
                if isinstance(v, Quantity):
                    quantity = v.to('mm')
                elif isinstance(v, (int, float)):
                    quantity = v * ureg.mm
                else:
                    quantity = ureg(v).to('mm')
            except Exception as e:
                raise ValueError(f"Valor '{v}' no es una cantidad válida con unidades. Error: {e}")
            return quantity
        return v
    
    @field_validator('carga', mode='before')
    @classmethod
    def validate_carga(cls, v):
        if v is not None:
            try:
                if isinstance(v, Quantity):
                    quantity = v.to('N')
                elif isinstance(v, (int, float)):
                    quantity = v * ureg.N
                else:
                    quantity = ureg(v).to('N')
            except Exception as e:
                raise ValueError(f"Valor '{v}' no es una cantidad válida con unidades. Error: {e}")
            return quantity
        return v
    
    def __str__(self):
        return (f"Posición: {self.posicion} mm, "
                f"Recorrido={self.recorrido} mm, "
                f"Carga={self.carga} N")

class PosicionAngular(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    posicion: Quantity
    recorrido: Quantity
    carga: Optional[Quantity] = None

    @field_validator('posicion', 'recorrido', mode='before')
    @classmethod
    def validate_positive_values(cls, v):
        if v is not None:
            try:
                if isinstance(v, Quantity):
                    quantity = v.to('degree')
                elif isinstance(v, (int, float)):
                    quantity = v * ureg.degree
                else:
                    quantity = ureg(v).to('degree')
            except Exception as e:
                raise ValueError(f"Valor '{v}' no es una cantidad válida con unidades. Error: {e}")
            return quantity
        return v
    
    @field_validator('carga', mode='before')
    @classmethod
    def validate_carga(cls, v):
        if v is not None:
            try:
                if isinstance(v, Quantity):
                    quantity = v
                elif isinstance(v, (int, float)):
                    quantity = v * ureg.N * ureg.mm
                else:
                    quantity = ureg(v)
            except Exception as e:
                raise ValueError(f"Valor '{v}' no es una cantidad válida con unidades. Error: {e}")
            return quantity
        return v
    
    def __str__(self):
        return (f"Posición={self.posicion} degrees, "
                f"Deformación={self.recorrido} degrees, "
                f"Carga={self.carga} Nmm")

class PosicionCargaLineal(PosicionLineal):
    tension: Optional[Quantity] = None
    diametro_externo: Optional[Quantity] = None
    diametro_interno: Optional[Quantity] = None

    @field_validator('diametro_externo', 'diametro_interno', mode='before')
    @classmethod
    def validate_positive_values(cls, v):
        if v is not None:
            try:
                if isinstance(v, Quantity):
                    quantity = v.to('mm')
                elif isinstance(v, (int, float)):
                    quantity = v * ureg.mm
                else:
                    quantity = ureg(v).to('mm')
            except Exception as e:
                raise ValueError(f"Valor '{v}' no es una cantidad válida con unidades. Error: {e}")
            return quantity
        return v

    @field_validator('tension', mode='before')
    @classmethod
    def validate_quantities(cls, v):
        if v is not None:
            try:
                if isinstance(v, Quantity):
                    quantity = v.to('MPa')
                elif isinstance(v, (int, float)):
                    quantity = v * ureg.MPa
                else:
                    quantity = ureg(v).to('MPa')
            except Exception as e:
                raise ValueError(f"Valor '{v}' no es una cantidad válida con unidades. Error: {e}")
            return quantity
        return v
    
    def __str__(self):
        return (f"Tensión={self.tension} MPa, "
                f"Diámetro Externo={self.diametro_externo} mm, "
                f"Diámetro Interno={self.diametro_interno} mm")

class PosicionCargaAngular(PosicionAngular):
    tension: Optional[Quantity] = None
    diametro_externo: Optional[Quantity] = None
    diametro_interno: Optional[Quantity] = None

    @field_validator('diametro_externo', 'diametro_interno', mode='before')
    @classmethod
    def validate_diameters(cls, v):
        if v is not None:
            try:
                if isinstance(v, Quantity):
                    quantity = v.to('mm')
                elif isinstance(v, (int, float)):
                    quantity = v * ureg.mm
                else:
                    quantity = ureg(v).to('mm')
            except Exception as e:
                raise ValueError(f"Valor '{v}' no es una cantidad válida con unidades. Error: {e}")
            return quantity
        return v

    @field_validator('tension', mode='before')
    @classmethod
    def validate_tension(cls, v):
        if v is not None:
            try:
                if isinstance(v, Quantity):
                    quantity = v.to('MPa')
                elif isinstance(v, (int, float)):
                    quantity = v * ureg.MPa
                else:
                    quantity = ureg(v).to('MPa')
            except Exception as e:
                raise ValueError(f"Valor '{v}' no es una cantidad válida con unidades. Error: {e}")
            return quantity
        return v
    
    def __str__(self):
        return (f"Tensión={self.tension} MPa, "
                f"Diámetro Externo={self.diametro_externo} mm, "
                f"Diámetro Interno={self.diametro_interno} mm")

class PosicionesTableLineal(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    posiciones: List[PosicionCargaLineal] = []

    def add_posicion_carga(self,
                           posicion: float,
                           recorrido: float,
                           carga: Optional[float] = None,
                           tension: Optional[float] = None,
                           diametro_externo: Optional[float] = None,
                           diametro_interno: Optional[float] = None):
        """Agrega una nueva posición con sus características a la tabla"""
        nueva_posicion = PosicionCargaLineal(
            posicion=posicion,
            recorrido=recorrido,
            carga=carga,
            tension=tension,
            diametro_externo=diametro_externo,
            diametro_interno=diametro_interno
        )
        self.posiciones.append(nueva_posicion)

    def clear_table(self):
        """Vacía la tabla de posiciones"""
        self.posiciones = []
    
    def __str__(self):
            """Devuelve una representación legible de la tabla de posiciones"""
            if not self.posiciones:
                return "No hay posiciones registradas."
            result = "Tabla de Posiciones:\n"
            for idx, pos in enumerate(self.posiciones, start=1):
                result += (f"Posición {idx}: Carga={pos.carga} N,\n"
                            f"  Tensión={pos.tension} MPa,\n"
                            f"  Deformación={pos.posicion} mm/mm,\n"
                            f"  Recorrido={pos.recorrido} mm/mm,\n"
                            f"  Diámetro Externo={pos.diametro_externo} mm,\n"
                            f"  Diámetro Interno={pos.diametro_interno} mm\n")
            return result

class PosicionesTableAngular(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    posiciones : List[PosicionCargaAngular] = []

    def add_posicion_carga(self,
                            posicion: float,
                            recorrido: float,
                            carga: Optional[float] = None,
                            tension: Optional[float] = None,
                            diametro_externo: Optional[float] = None,
                            diametro_interno: Optional[float] = None):
        """Agrega una nueva posición con sus características a la tabla"""
        nueva_posicion = PosicionCargaAngular(
            posicion=posicion,
            recorrido=recorrido,
            carga=carga,
            tension=tension,
            diametro_externo=diametro_externo,
            diametro_interno=diametro_interno
        )
        self.posiciones.append(nueva_posicion)

    def clear_table(self):
        """Vacía la tabla de posiciones"""
        self.posiciones = []
    
    def __str__(self):
        """Devuelve una representación legible de la tabla de posiciones"""
        if not self.posiciones:
            return "No hay posiciones registradas."
        result = "Tabla de Posiciones:\n"
        for idx, pos in enumerate(self.posiciones, start=1):
            result += (f"Posición {idx}: Carga={pos.carga} Nmm,\n"
                        f"  Tensión={pos.tension} MPa,\n"
                        f"  Deformación={pos.posicion} mm/mm,\n"
                        f"  Recorrido={pos.recorrido} mm/mm,\n"
                        f"  Diámetro Externo={pos.diametro_externo} mm,\n"
                        f"  Diámetro Interno={pos.diametro_interno} mm\n")
            
        return result