from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
from uuid import UUID

class TipoMascota(str, Enum):
    perro = "perro"
    gato = "gato"
    ave = "ave"

class MascotaBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=50)
    tipo: TipoMascota
    raza: str = Field(..., min_length=1, max_length=50)
    edad: int = Field(..., ge=0, le=30)
    peso: float = Field(..., gt=0)


class MascotaCreate(MascotaBase):
    """Modelo de entrada para crear mascota. No incluye `propietario` porque
    éste se infiere del usuario autenticado en el endpoint."""
    pass

class MascotaUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=50)
    tipo: Optional[TipoMascota] = None
    raza: Optional[str] = Field(None, min_length=1, max_length=50)
    edad: Optional[int] = Field(None, ge=0, le=30)
    peso: Optional[float] = Field(None, gt=0)

class Mascota(MascotaBase):
    id_mascota: UUID
    propietario: str
    telefono_propietario: Optional[str] = None