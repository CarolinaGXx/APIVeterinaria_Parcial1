from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class EstadoCita(str, Enum):
    pendiente = "pendiente"
    completada = "completada"
    cancelada = "cancelada"

class CitaBase(BaseModel):
    mascota_id: int
    fecha: datetime
    motivo: str = Field(..., min_length=1, max_length=200)
    veterinario: str = Field(..., min_length=1, max_length=100)

class CitaCreate(CitaBase):
    pass

class CitaUpdate(BaseModel):
    mascota_id: Optional[int] = None
    fecha: Optional[datetime] = None
    motivo: Optional[str] = Field(None, min_length=1, max_length=200)
    veterinario: Optional[str] = Field(None, min_length=1, max_length=100)
    estado: Optional[EstadoCita] = None

class Cita(CitaBase):
    id: int
    estado: EstadoCita = EstadoCita.pendiente
    fecha_creacion: datetime