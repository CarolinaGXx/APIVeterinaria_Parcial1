from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class RecetaLinea(BaseModel):
    medicamento: str = Field(..., min_length=1, max_length=200)
    dosis: Optional[str] = None
    frecuencia: Optional[str] = None
    duracion: Optional[str] = None


class RecetaBase(BaseModel):
    id_cita: UUID
    fecha_emision: datetime
    indicaciones: Optional[str] = None
    lineas: Optional[List[RecetaLinea]] = None


class RecetaCreate(RecetaBase):
    pass


class RecetaUpdate(BaseModel):
    fecha_emision: Optional[datetime] = None
    indicaciones: Optional[str] = None
    lineas: Optional[List[RecetaLinea]] = None


class Receta(RecetaBase):
    id_receta: UUID
    id_mascota: UUID
    mascota_nombre: Optional[str] = None
    veterinario: str
    propietario_username: Optional[str] = None
    propietario_nombre: Optional[str] = None
    propietario_telefono: Optional[str] = None


class RecetaSummary(BaseModel):
    id_receta: UUID
    id_cita: UUID
    id_mascota: UUID
    mascota_nombre: Optional[str] = None
    fecha_emision: datetime
    veterinario: str
    propietario_username: Optional[str] = None
    propietario_nombre: Optional[str] = None
    propietario_telefono: Optional[str] = None

