from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime

from models import Cita, CitaCreate, CitaUpdate, EstadoCita
from database.db import (
    citas_db, encontrar_mascota, encontrar_cita, 
    obtener_proximo_id_cita
)

router = APIRouter(prefix="/citas", tags=["citas"])

@router.post("/", response_model=Cita, status_code=201)
async def agendar_cita(cita: CitaCreate):
    """Agendar una nueva cita"""
    # Verificar que la mascota existe
    mascota = encontrar_mascota(cita.mascota_id)
    if not mascota:
        raise HTTPException(status_code=400, detail="La mascota especificada no existe")
    
    nueva_cita = Cita(
        id=obtener_proximo_id_cita(),
        **cita.dict(),
        estado=EstadoCita.pendiente,
        fecha_creacion=datetime.now()
    )
    citas_db.append(nueva_cita)
    return nueva_cita

@router.get("/", response_model=List[Cita])
async def obtener_citas(
    estado: Optional[EstadoCita] = Query(None, description="Filtrar por estado de cita"),
    veterinario: Optional[str] = Query(None, description="Filtrar por veterinario")
):
    """Obtener lista de citas con filtros opcionales"""
    citas_filtradas = citas_db
    
    if estado:
        citas_filtradas = [c for c in citas_filtradas if c.estado == estado]
    
    if veterinario:
        citas_filtradas = [c for c in citas_filtradas if veterinario.lower() in c.veterinario.lower()]
    
    return citas_filtradas

@router.get("/{cita_id}", response_model=Cita)
async def obtener_cita(cita_id: int):
    """Obtener una cita específica por ID"""
    cita = encontrar_cita(cita_id)
    if not cita:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    return cita

@router.put("/{cita_id}", response_model=Cita)
async def actualizar_cita(cita_id: int, cita_update: CitaUpdate):
    """Actualizar información de una cita"""
    cita = encontrar_cita(cita_id)
    if not cita:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    
    # Si se actualiza mascota_id, verificar que existe
    if cita_update.mascota_id and not encontrar_mascota(cita_update.mascota_id):
        raise HTTPException(status_code=400, detail="La mascota especificada no existe")
    
    update_data = cita_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(cita, field, value)
    
    return cita

@router.delete("/{cita_id}")
async def cancelar_cita(cita_id: int):
    """Cancelar/eliminar una cita"""
    for i, cita in enumerate(citas_db):
        if cita.id == cita_id:
            del citas_db[i]
            return {"message": "Cita cancelada exitosamente"}
    
    raise HTTPException(status_code=404, detail="Cita no encontrada")