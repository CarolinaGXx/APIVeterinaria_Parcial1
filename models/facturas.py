from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

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
    mascota_id: int
    cita_id: Optional[int] = None  # Opcional porque puede ser una consulta sin cita previa
    fecha_factura: datetime
    tipo_servicio: TipoServicio
    descripcion: str = Field(..., min_length=1, max_length=500)
    veterinario: str = Field(..., min_length=1, max_length=100)
    valor_servicio: float = Field(..., gt=0)
    iva: float = Field(..., ge=0)
    descuento: float = Field(0, ge=0)

class FacturaCreate(BaseModel):
    mascota_id: int
    cita_id: Optional[int] = None
    tipo_servicio: TipoServicio
    descripcion: str = Field(..., min_length=1, max_length=500)
    veterinario: str = Field(..., min_length=1, max_length=100)
    valor_servicio: float = Field(..., gt=0)
    iva: float = Field(..., ge=0)
    descuento: float = Field(0, ge=0)

class FacturaUpdate(BaseModel):
    mascota_id: Optional[int] = None
    cita_id: Optional[int] = None
    tipo_servicio: Optional[TipoServicio] = None
    descripcion: Optional[str] = Field(None, min_length=1, max_length=500)
    veterinario: Optional[str] = Field(None, min_length=1, max_length=100)
    valor_servicio: Optional[float] = Field(None, gt=0)
    iva: Optional[float] = Field(None, ge=0)
    descuento: Optional[float] = Field(None, ge=0)
    estado: Optional[EstadoFactura] = None

class Factura(FacturaBase):
    id: int
    numero_factura: str
    estado: EstadoFactura = EstadoFactura.pendiente
    total: float
    fecha_creacion: datetime