from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum
from uuid import UUID

class EstadoFactura(str, Enum):
    pendiente = "pendiente"
    pagada = "pagada"
    anulada = "anulada"

class TipoServicio(str, Enum):
    consulta_general = "consulta_general"
    vacunacion = "vacunacion"
    cirugia = "cirugia"
    emergencia = "emergencia"
    control = "control"
    desparasitacion = "desparasitacion"

class FacturaBase(BaseModel):
    id_mascota: UUID
    id_cita: Optional[UUID] = None
    fecha_factura: datetime
    tipo_servicio: TipoServicio
    descripcion: str = Field(..., min_length=1, max_length=500)
    veterinario: str = Field(..., min_length=1, max_length=100)
    valor_servicio: float = Field(..., gt=0)
    iva: float = Field(..., ge=0)
    descuento: float = Field(0, ge=0)

class FacturaCreate(BaseModel):
    # id_mascota is intentionally omitted: it will be inferred from the cita (appointment)
    id_cita: UUID
    tipo_servicio: TipoServicio
    descripcion: str = Field(..., min_length=1, max_length=500)
    # veterinarian is inferred from the authenticated user; do not accept in the request
    valor_servicio: float = Field(..., gt=0)
    iva: float = Field(..., ge=0)
    descuento: float = Field(0, ge=0)

class FacturaUpdate(BaseModel):
    tipo_servicio: Optional[TipoServicio] = None
    descripcion: Optional[str] = Field(None, min_length=1, max_length=500)
    valor_servicio: Optional[float] = Field(None, gt=0)
    iva: Optional[float] = Field(None, ge=0)
    descuento: Optional[float] = Field(None, ge=0)
    estado: Optional[EstadoFactura] = None

class Factura(FacturaBase):
    id_factura: UUID
    numero_factura: str
    estado: EstadoFactura = EstadoFactura.pendiente
    total: float
    mascota_nombre: Optional[str] = None
    propietario_username: Optional[str] = None
    propietario_nombre: Optional[str] = None
    propietario_telefono: Optional[str] = None