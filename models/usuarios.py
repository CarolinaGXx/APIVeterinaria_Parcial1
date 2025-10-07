from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime
from enum import Enum


class Role(str, Enum):
    cliente = "cliente"
    veterinario = "veterinario"
    admin = "admin"


class UsuarioCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    nombre: str = Field(..., min_length=1, max_length=200)
    edad: int = Field(..., ge=0, le=150)
    telefono: str = Field(..., min_length=7, max_length=20)
    password: str = Field(..., min_length=6)
    role: Optional[Role] = Field(
        Role.cliente, description="Rol del usuario: cliente o veterinario"
    )


class Usuario(BaseModel):
    id_usuario: UUID
    username: str
    nombre: str
    edad: int
    telefono: str
    role: Role
    fecha_creacion: datetime


class UsuarioUpdateResponse(BaseModel):
    username: str
    nombre: str
    edad: int
    telefono: str


class UsuarioUpdateRequest(BaseModel):
    username: Optional[str] = Field(None, min_length=1, max_length=100)
    nombre: Optional[str] = Field(None, min_length=1, max_length=200)
    edad: Optional[int] = Field(None, ge=0, le=150)
    telefono: Optional[str] = Field(None, min_length=7, max_length=20)
