from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from models import Vacuna, VacunaCreate, VacunaUpdate, TipoVacuna
from database.db import (
    vacunas_db, encontrar_mascota, encontrar_vacuna,
    obtener_proximo_id_vacuna
)

router = APIRouter(prefix="/vacunas", tags=["vacunas"])

@router.post("/", response_model=Vacuna, status_code=201)
async def registrar_vacuna(vacuna: VacunaCreate):
    """Registrar una nueva vacuna"""
    # Verificar que la mascota existe
    mascota = encontrar_mascota(vacuna.mascota_id)
    if not mascota:
        raise HTTPException(status_code=400, detail="La mascota especificada no existe")
    
    nueva_vacuna = Vacuna(id=obtener_proximo_id_vacuna(), **vacuna.dict())
    vacunas_db.append(nueva_vacuna)
    return nueva_vacuna

@router.get("/", response_model=List[Vacuna])
async def obtener_vacunas(
    tipo_vacuna: Optional[TipoVacuna] = Query(None, description="Filtrar por tipo de vacuna"),
    veterinario: Optional[str] = Query(None, description="Filtrar por veterinario")
):
    """Obtener lista de vacunas con filtros opcionales"""
    vacunas_filtradas = vacunas_db
    
    if tipo_vacuna:
        vacunas_filtradas = [v for v in vacunas_filtradas if v.tipo_vacuna == tipo_vacuna]
    
    if veterinario:
        vacunas_filtradas = [v for v in vacunas_filtradas if veterinario.lower() in v.veterinario.lower()]
    
    return vacunas_filtradas

@router.get("/{vacuna_id}", response_model=Vacuna)
async def obtener_vacuna(vacuna_id: int):
    """Obtener una vacuna específica por ID"""
    vacuna = encontrar_vacuna(vacuna_id)
    if not vacuna:
        raise HTTPException(status_code=404, detail="Vacuna no encontrada")
    return vacuna

@router.put("/{vacuna_id}", response_model=Vacuna)
async def actualizar_vacuna(vacuna_id: int, vacuna_update: VacunaUpdate):
    """Actualizar información de una vacuna"""
    vacuna = encontrar_vacuna(vacuna_id)
    if not vacuna:
        raise HTTPException(status_code=404, detail="Vacuna no encontrada")
    
    # Si se actualiza mascota_id, verificar que existe
    if vacuna_update.mascota_id and not encontrar_mascota(vacuna_update.mascota_id):
        raise HTTPException(status_code=400, detail="La mascota especificada no existe")
    
    update_data = vacuna_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(vacuna, field, value)
    
    return vacuna

@router.delete("/{vacuna_id}")
async def eliminar_vacuna(vacuna_id: int):
    """Eliminar registro de vacuna"""
    for i, vacuna in enumerate(vacunas_db):
        if vacuna.id == vacuna_id:
            del vacunas_db[i]
            return {"message": "Registro de vacuna eliminado exitosamente"}
    
    raise HTTPException(status_code=404, detail="Vacuna no encontrada")