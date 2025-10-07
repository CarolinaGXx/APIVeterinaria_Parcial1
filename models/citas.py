from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum
from uuid import UUID

class EstadoCita(str, Enum):
    pendiente = "pendiente"
    completada = "completada"
    cancelada = "cancelada"

class CitaBase(BaseModel):
    id_mascota: UUID
    fecha: datetime
    motivo: str = Field(..., min_length=1, max_length=200)
    veterinario: str = Field(..., min_length=1, max_length=100)

class CitaCreate(CitaBase):
    pass

class CitaUpdate(BaseModel):
    fecha: Optional[datetime] = None
    motivo: Optional[str] = Field(None, min_length=1, max_length=200)
    veterinario: Optional[str] = Field(None, min_length=1, max_length=100)

class Cita(CitaBase):
    id_cita: UUID
    estado: EstadoCita = EstadoCita.pendiente
    mascota_nombre: str
    propietario_username: Optional[str] = None
    propietario_nombre: Optional[str] = None
    propietario_telefono: Optional[str] = None