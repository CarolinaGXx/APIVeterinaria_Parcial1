from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime

from models import Factura, FacturaCreate, FacturaUpdate, EstadoFactura, TipoServicio, EstadoCita
from database.db import (
    facturas_db, encontrar_mascota, encontrar_cita, encontrar_factura,
    obtener_proximo_id_factura, generar_numero_factura, calcular_total_factura
)

router = APIRouter(prefix="/facturas", tags=["facturas"])

@router.post("/", response_model=Factura, status_code=201)
async def crear_factura(factura: FacturaCreate):
    """Crear una nueva factura"""
    # Verificar que la mascota existe
    mascota = encontrar_mascota(factura.mascota_id)
    if not mascota:
        raise HTTPException(status_code=400, detail="La mascota especificada no existe")
    
    # Si se especifica cita_id, verificar que existe
    if factura.cita_id:
        cita = encontrar_cita(factura.cita_id)
        if not cita:
            raise HTTPException(status_code=400, detail="La cita especificada no existe")
        # Actualizar estado de la cita a completada al facturar
        cita.estado = EstadoCita.completada
    
    # Obtener el próximo ID
    factura_id = obtener_proximo_id_factura()
    
    # Calcular el total
    total = calcular_total_factura(factura.valor_servicio, factura.iva, factura.descuento)
    
    nueva_factura = Factura(
        id=factura_id,
        numero_factura=generar_numero_factura(factura_id),
        **factura.model_dump(),
        fecha_factura=datetime.now(),
        estado=EstadoFactura.pendiente,
        total=total,
        fecha_creacion=datetime.now()
    )
    facturas_db.append(nueva_factura)
    return nueva_factura

@router.get("/", response_model=List[Factura])
async def obtener_facturas(
    estado: Optional[EstadoFactura] = Query(None, description="Filtrar por estado de factura"),
    tipo_servicio: Optional[TipoServicio] = Query(None, description="Filtrar por tipo de servicio"),
    veterinario: Optional[str] = Query(None, description="Filtrar por veterinario")
):
    """Obtener lista de facturas con filtros opcionales"""
    facturas_filtradas = facturas_db
    
    if estado:
        facturas_filtradas = [f for f in facturas_filtradas if f.estado == estado]
    
    if tipo_servicio:
        facturas_filtradas = [f for f in facturas_filtradas if f.tipo_servicio == tipo_servicio]
        
    if veterinario:
        facturas_filtradas = [f for f in facturas_filtradas if veterinario.lower() in f.veterinario.lower()]
    
    return facturas_filtradas

@router.get("/{factura_id}", response_model=Factura)
async def obtener_factura(factura_id: int):
    """Obtener una factura específica por ID"""
    factura = encontrar_factura(factura_id)
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    return factura

# Endpoint adicional para obtener facturas por mascota
from fastapi import APIRouter as _APIRouter
mascotas_facturas_router = _APIRouter(prefix="/mascotas", tags=["mascotas-facturas"])

@mascotas_facturas_router.get("/{mascota_id}/facturas", response_model=List[Factura])
async def obtener_facturas_mascota(mascota_id: int):
    """Obtener todas las facturas de una mascota específica"""
    mascota = encontrar_mascota(mascota_id)
    if not mascota:
        raise HTTPException(status_code=404, detail="Mascota no encontrada")
    
    facturas_mascota = [f for f in facturas_db if f.mascota_id == mascota_id]
    return facturas_mascota

@router.put("/{factura_id}", response_model=Factura)
async def actualizar_factura(factura_id: int, factura_update: FacturaUpdate):
    """Actualizar información de una factura"""
    factura = encontrar_factura(factura_id)
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    
    # No permitir actualizar facturas pagadas
    if factura.estado == EstadoFactura.pagada:
        raise HTTPException(status_code=400, detail="No se puede modificar una factura pagada")
    
    # Verificar mascota si se actualiza
    if factura_update.mascota_id and not encontrar_mascota(factura_update.mascota_id):
        raise HTTPException(status_code=400, detail="La mascota especificada no existe")
    
    # Verificar cita si se actualiza
    if factura_update.cita_id and not encontrar_cita(factura_update.cita_id):
        raise HTTPException(status_code=400, detail="La cita especificada no existe")
    
    update_data = factura_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(factura, field, value)
    
    # Recalcular total si se actualizaron valores monetarios
    if any(field in update_data for field in ['valor_servicio', 'iva', 'descuento']):
        factura.total = calcular_total_factura(factura.valor_servicio, factura.iva, factura.descuento)
    
    return factura

@router.patch("/{factura_id}/pagar")
async def marcar_factura_pagada(factura_id: int):
    """Marcar una factura como pagada"""
    factura = encontrar_factura(factura_id)
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    
    if factura.estado == EstadoFactura.pagada:
        raise HTTPException(status_code=400, detail="La factura ya está pagada")
    
    if factura.estado == EstadoFactura.anulada:
        raise HTTPException(status_code=400, detail="No se puede pagar una factura anulada")
    
    factura.estado = EstadoFactura.pagada
    return {"message": f"Factura {factura.numero_factura} marcada como pagada", "factura": factura}

@router.patch("/{factura_id}/anular")
async def anular_factura(factura_id: int):
    """Anular una factura"""
    factura = encontrar_factura(factura_id)
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    
    if factura.estado == EstadoFactura.pagada:
        raise HTTPException(status_code=400, detail="No se puede anular una factura pagada")
    
    factura.estado = EstadoFactura.anulada
    return {"message": f"Factura {factura.numero_factura} anulada", "factura": factura}

@router.delete("/{factura_id}")
async def eliminar_factura(factura_id: int):
    """Eliminar una factura"""
    for i, factura in enumerate(facturas_db):
        if factura.id == factura_id:
            if factura.estado == EstadoFactura.pagada:
                raise HTTPException(status_code=400, detail="No se puede eliminar una factura pagada")
            
            del facturas_db[i]
            return {"message": "Factura eliminada exitosamente"}
    
    raise HTTPException(status_code=404, detail="Factura no encontrada")