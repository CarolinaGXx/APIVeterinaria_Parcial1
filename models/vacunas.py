from pydantic import BaseModel, Field
from typing import Optional
from datetime import date
from enum import Enum

class TipoVacuna(str, Enum):
    rabia = "rabia"
    parvovirus = "parvovirus"
    moquillo = "moquillo"
    leucemia_felina = "leucemia_felina"
    triple_felina = "triple_felina"
    newcastle = "newcastle"

class VacunaBase(BaseModel):
    mascota_id: int
    tipo_vacuna: TipoVacuna
    fecha_aplicacion: date
    veterinario: str = Field(..., min_length=1, max_length=100)
    lote_vacuna: str = Field(..., min_length=1, max_length=20)
    proxima_dosis: Optional[date] = None

class VacunaCreate(VacunaBase):
    pass

class VacunaUpdate(BaseModel):
    mascota_id: Optional[int] = None
    tipo_vacuna: Optional[TipoVacuna] = None
    fecha_aplicacion: Optional[date] = None
    veterinario: Optional[str] = Field(None, min_length=1, max_length=100)
    lote_vacuna: Optional[str] = Field(None, min_length=1, max_length=20)
    proxima_dosis: Optional[date] = None

class Vacuna(VacunaBase):
    id: int