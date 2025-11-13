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
    """ Modelo para registro de usuarios públicos (solo clientes).
    El rol se establece automáticamente como "cliente" en el servidor.
    Para crear veterinarios o administradores, utilice el punto de conexión de administración.
    """
    username: str = Field(..., min_length=1, max_length=100)
    nombre: str = Field(..., min_length=1, max_length=200)
    edad: int = Field(..., ge=0, le=150)
    telefono: str = Field(..., min_length=7, max_length=20)
    password: str = Field(..., min_length=6)


class Usuario(BaseModel):
    id_usuario: UUID
    username: str
    nombre: str
    edad: int
    telefono: str
    role: Role
    fecha_creacion: datetime
    is_deleted: bool = False
    
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

class UsuarioPrivilegedCreate(BaseModel):
    """Modelo para crear usuarios con roles privilegiados (veterinario o admin).
    Este endpoint solo debe ser accesible por admins.
    """
    username: str = Field(..., min_length=1, max_length=100)
    nombre: str = Field(..., min_length=1, max_length=200)
    edad: int = Field(..., ge=0, le=150)
    telefono: str = Field(..., min_length=7, max_length=20)
    password: str = Field(..., min_length=6)
    role: Role = Field(
        ..., description="Rol del usuario: veterinario o admin"
    )

class UsuarioRoleUpdate(BaseModel):
    """Modelo para actualizar el rol de un usuario.    
    Solo los admins pueden cambiar los roles de los usuarios.
    """
    role: Role = Field(..., description="Nuevo rol del usuario")