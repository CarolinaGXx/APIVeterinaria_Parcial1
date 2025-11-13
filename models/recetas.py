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


class RecetaCreate(BaseModel):
    """Modelo para crear receta. fecha_emision se genera automáticamente."""
    id_cita: UUID
    indicaciones: Optional[str] = None
    lineas: Optional[List[RecetaLinea]] = None


class RecetaUpdate(BaseModel):
    """Modelo para actualizar receta. fecha_emision no se puede modificar."""
    indicaciones: Optional[str] = None
    lineas: Optional[List[RecetaLinea]] = None


class Receta(RecetaBase):
    id_receta: UUID
    id_mascota: UUID
    mascota_nombre: Optional[str] = None
    mascota_tipo: Optional[str] = None
    veterinario: str
    veterinario_nombre: Optional[str] = None
    veterinario_telefono: Optional[str] = None
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
    veterinario_nombre: Optional[str] = None
    veterinario_telefono: Optional[str] = None
    propietario_username: Optional[str] = None
    propietario_nombre: Optional[str] = None
    propietario_telefono: Optional[str] = None
