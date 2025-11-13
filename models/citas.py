from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum
from uuid import UUID

class EstadoCita(str, Enum):
    pendiente = "pendiente"
    completada = "completada"
    cancelada = "cancelada"
    confirmada = "confirmada"

class CitaBase(BaseModel):
    id_mascota: UUID
    fecha: datetime
    motivo: str = Field(..., min_length=1, max_length=200)
    veterinario: str = Field(..., min_length=1, max_length=100)

class CitaCreate(CitaBase):
    """Crear una nueva cita."""
    pass

class CitaUpdate(BaseModel):
    """Actualizar una cita existente."""
    fecha: Optional[datetime] = None
    motivo: Optional[str] = Field(None, min_length=1, max_length=200)
    veterinario: Optional[str] = Field(None, min_length=1, max_length=100)
    estado: Optional[str] = None
    diagnostico: Optional[str] = Field(None, max_length=500)
    tratamiento: Optional[str] = Field(None, max_length=500)

class Cita(CitaBase):
    """
    Modelo de respuesta de Cita.
    
    El campo 'veterinario' contiene el USERNAME.
    El campo 'veterinario_nombre' contiene el nombre completo para mostrar.
    """
    id_cita: UUID
    estado: EstadoCita = EstadoCita.pendiente
    diagnostico: Optional[str] = None
    tratamiento: Optional[str] = None
    veterinario_nombre: Optional[str] = None
    veterinario_telefono: Optional[str] = None
    mascota_nombre: str
    propietario_username: Optional[str] = None
    propietario_nombre: Optional[str] = None
    propietario_telefono: Optional[str] = None
    is_deleted: bool = False