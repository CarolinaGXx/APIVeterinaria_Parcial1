from pydantic import BaseModel, Field
from typing import Optional
from datetime import date
from enum import Enum
from uuid import UUID


class TipoVacuna(str, Enum):
    rabia = "rabia"
    parvovirus = "parvovirus"
    moquillo = "moquillo"
    leucemia_felina = "leucemia_felina"
    triple_felina = "triple_felina"
    newcastle = "newcastle"


class VacunaBase(BaseModel):
    id_mascota: UUID
    tipo_vacuna: TipoVacuna
    fecha_aplicacion: date
    lote_vacuna: str = Field(..., min_length=1, max_length=20)
    proxima_dosis: Optional[date] = None


class VacunaCreate(VacunaBase):
    pass


class VacunaUpdate(BaseModel):
    tipo_vacuna: Optional[TipoVacuna] = None
    fecha_aplicacion: Optional[date] = None
    lote_vacuna: Optional[str] = Field(None, min_length=1, max_length=20)
    proxima_dosis: Optional[date] = None


class Vacuna(VacunaBase):
    id_vacuna: UUID
    mascota_nombre: str
    propietario_username: Optional[str] = None
    propietario_nombre: Optional[str] = None
    propietario_telefono: Optional[str] = None
