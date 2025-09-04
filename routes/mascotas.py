from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from models import Mascota, MascotaCreate, MascotaUpdate, TipoMascota
from database.db import (
    mascotas_db, citas_db, vacunas_db,
    encontrar_mascota, obtener_proximo_id_mascota
)

router = APIRouter(prefix="/mascotas", tags=["mascotas"])

@router.post("/", response_model=Mascota, status_code=201)
async def crear_mascota(mascota: MascotaCreate):
    """Crear una nueva mascota"""
    nueva_mascota = Mascota(id=obtener_proximo_id_mascota(), **mascota.model_dump())
    mascotas_db.append(nueva_mascota)
    return nueva_mascota

@router.get("/", response_model=List[Mascota])
async def obtener_mascotas(
    tipo: Optional[TipoMascota] = Query(None, description="Filtrar por tipo de mascota"),
    propietario: Optional[str] = Query(None, description="Filtrar por propietario")
):
    """Obtener lista de mascotas con filtros opcionales"""
    mascotas_filtradas = mascotas_db
    
    if tipo:
        mascotas_filtradas = [m for m in mascotas_filtradas if m.tipo == tipo]
    
    if propietario:
        mascotas_filtradas = [m for m in mascotas_filtradas if propietario.lower() in m.propietario.lower()]
    
    return mascotas_filtradas

@router.get("/{mascota_id}", response_model=Mascota)
async def obtener_mascota(mascota_id: int):
    """Obtener una mascota específica por ID"""
    mascota = encontrar_mascota(mascota_id)
    if not mascota:
        raise HTTPException(status_code=404, detail="Mascota no encontrada")
    return mascota

# Endpoint adicional para obtener vacunas por mascota
from fastapi import APIRouter as _APIRouter
mascotas_vacunas_router = _APIRouter(prefix="/mascotas", tags=["mascotas-vacunas"])

@mascotas_vacunas_router.get("/{mascota_id}/vacunas")
async def obtener_vacunas_mascota(mascota_id: int):
    """Obtener todas las vacunas de una mascota específica"""
    from models import Vacuna
    mascota = encontrar_mascota(mascota_id)
    if not mascota:
        raise HTTPException(status_code=404, detail="Mascota no encontrada")
    
    vacunas_mascota = [v for v in vacunas_db if v.mascota_id == mascota_id]
    return vacunas_mascota

@router.put("/{mascota_id}", response_model=Mascota)
async def actualizar_mascota(mascota_id: int, mascota_update: MascotaUpdate):
    """Actualizar información de una mascota"""
    mascota = encontrar_mascota(mascota_id)
    if not mascota:
        raise HTTPException(status_code=404, detail="Mascota no encontrada")
    
    # Actualizar solo los campos proporcionados
    update_data = mascota_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(mascota, field, value)
    
    return mascota

@router.delete("/{mascota_id}")
async def eliminar_mascota(mascota_id: int):
    """Eliminar una mascota"""
    for i, mascota in enumerate(mascotas_db):
        if mascota.id == mascota_id:
            # Verificar si hay citas o vacunas asociadas
            citas_asociadas = [c for c in citas_db if c.mascota_id == mascota_id]
            vacunas_asociadas = [v for v in vacunas_db if v.mascota_id == mascota_id]
            
            if citas_asociadas or vacunas_asociadas:
                raise HTTPException(
                    status_code=400, 
                    detail="No se puede eliminar la mascota porque tiene citas o vacunas asociadas"
                )
            
            del mascotas_db[i]
            return {"message": "Mascota eliminada exitosamente"}
    
    raise HTTPException(status_code=404, detail="Mascota no encontrada")