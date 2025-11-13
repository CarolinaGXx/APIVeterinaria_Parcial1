from pydantic import BaseModel, Field, model_validator
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
    id_vacuna: Optional[UUID] = None
    fecha_factura: datetime
    tipo_servicio: TipoServicio
    descripcion: str = Field(..., min_length=1, max_length=500)
    veterinario: str = Field(..., min_length=1, max_length=100)
    valor_servicio: float = Field(..., gt=0)
    iva: float = Field(..., ge=0)
    descuento: float = Field(0, ge=0)

class FacturaCreate(BaseModel):
    id_cita: Optional[UUID] = None
    id_vacuna: Optional[UUID] = None
    tipo_servicio: TipoServicio
    descripcion: str = Field(..., min_length=1, max_length=500)
    valor_servicio: float = Field(..., gt=0)
    iva: float = Field(..., ge=0)
    descuento: float = Field(0, ge=0)
    
    @model_validator(mode='after')
    def validate_cita_or_vacuna(self):
        """Validar que al menos id_cita o id_vacuna esté presente."""
        if not self.id_cita and not self.id_vacuna:
            raise ValueError('Debe proporcionar id_cita o id_vacuna')
        if self.id_cita and self.id_vacuna:
            raise ValueError('No puede proporcionar ambos id_cita e id_vacuna')
        return self

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
    veterinario_nombre: Optional[str] = None
    veterinario_telefono: Optional[str] = None
    mascota_nombre: Optional[str] = None
    mascota_tipo: Optional[str] = None
    propietario_username: Optional[str] = None
    propietario_nombre: Optional[str] = None
    propietario_telefono: Optional[str] = None