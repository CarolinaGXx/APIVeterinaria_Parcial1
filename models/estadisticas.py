"""
Modelos para estadísticas del dashboard.

Proporciona diferentes vistas de estadísticas según el rol del usuario.
"""
from pydantic import BaseModel, Field
from typing import Optional


class EstadisticasCliente(BaseModel):
    """Estadísticas para usuarios con rol cliente."""
    mis_mascotas: int = Field(..., description="Número de mascotas propias")
    citas_pendientes: int = Field(..., description="Número de citas pendientes")
    citas_completadas: int = Field(..., description="Número de citas completadas")
    vacunas_aplicadas: int = Field(..., description="Total de vacunas aplicadas a mis mascotas")
    facturas_pendientes: int = Field(..., description="Número de facturas pendientes")
    facturas_pagadas: int = Field(..., description="Número de facturas pagadas")


class EstadisticasVeterinario(BaseModel):
    """Estadísticas para usuarios con rol veterinario."""
    mis_mascotas: int = Field(..., description="Número de mascotas propias como propietario")
    citas_asignadas: int = Field(..., description="Citas asignadas a mí (pendientes)")
    citas_completadas: int = Field(..., description="Citas que he completado")
    vacunas_aplicadas: int = Field(..., description="Vacunas que yo he aplicado")
    facturas_emitidas: int = Field(..., description="Facturas que yo he emitido (pendientes)")
    facturas_cobradas: int = Field(..., description="Facturas que yo he cobrado")


class EstadisticasAdmin(BaseModel):
    """Estadísticas para usuarios con rol administrador."""
    total_mascotas: int = Field(..., description="Total de mascotas en el sistema")
    total_usuarios: int = Field(..., description="Total de usuarios registrados")
    citas_pendientes: int = Field(..., description="Total de citas pendientes")
    citas_hoy: int = Field(..., description="Citas programadas para hoy")
    vacunas_mes: int = Field(..., description="Vacunas aplicadas este mes")
    facturas_pendientes: int = Field(..., description="Total de facturas pendientes")
    ingresos_mes: float = Field(..., description="Ingresos del mes actual")


class EstadisticasResponse(BaseModel):
    """Respuesta unificada de estadísticas."""
    success: bool = Field(True, description="Indica si la operación fue exitosa")
    role: str = Field(..., description="Rol del usuario")
    data: EstadisticasCliente | EstadisticasVeterinario | EstadisticasAdmin = Field(
        ..., description="Estadísticas según el rol"
    )
