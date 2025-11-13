"""
Modelos comunes de respuesta para la API.

Estos modelos proporcionan respuestas consistentes y estandarizadas
para todos los endpoints de la API
"""
from typing import Generic, TypeVar, Optional, List, Any
from pydantic import BaseModel, Field
from datetime import datetime

#generic type para datos paginados
T = TypeVar('T')


class SuccessResponse(BaseModel):
    """Respuesta estándar exitosa."""
    success: bool = Field(True, description="Indica si la operación fue exitosa")
    message: str = Field(..., description="Mensaje descriptivo de la operación")
    data: Optional[Any] = Field(None, description="Datos de respuesta")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp de la respuesta")


class ErrorResponse(BaseModel):
    """Respuesta estándar de error."""
    success: bool = Field(False, description="Indica que la operación falló")
    error: str = Field(..., description="Tipo de error")
    message: str = Field(..., description="Mensaje descriptivo del error")
    details: Optional[dict] = Field(None, description="Detalles adicionales del error")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp de la respuesta")


class DeleteResponse(BaseModel):
    """Respuesta estándar para operaciones de eliminación."""
    success: bool = Field(True, description="Indica si la eliminación fue exitosa")
    message: str = Field(..., description="Mensaje descriptivo")
    deleted_id: str = Field(..., description="ID del registro eliminado")
    soft_delete: bool = Field(True, description="Indica si fue soft delete (true) o hard delete (false)")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PaginationMeta(BaseModel):
    """Metadata de paginación."""
    page: int = Field(..., ge=0, description="Número de página actual (0-indexed)")
    page_size: int = Field(..., ge=1, description="Tamaño de página")
    total_items: int = Field(..., ge=0, description="Total de items disponibles")
    total_pages: int = Field(..., ge=0, description="Total de páginas")
    has_next: bool = Field(..., description="Indica si hay página siguiente")
    has_previous: bool = Field(..., description="Indica si hay página anterior")


class PaginatedResponse(BaseModel, Generic[T]):
    """Respuesta paginada genérica."""
    success: bool = Field(True, description="Indica si la operación fue exitosa")
    data: List[T] = Field(..., description="Lista de items de la página actual")
    pagination: PaginationMeta = Field(..., description="Metadata de paginación")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        #Permite usar tipos genéricos
        arbitrary_types_allowed = True


class HealthCheckResponse(BaseModel):
    """Respuesta del health check."""
    status: str = Field(..., description="Estado general (healthy/unhealthy)")
    service: str = Field(..., description="Nombre del servicio")
    version: str = Field(..., description="Versión de la API")
    database: str = Field(..., description="Estado de la base de datos")
    environment: str = Field(..., description="Entorno (production/development)")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


def create_success_response(message: str, data: Any = None) -> dict:
    """Helper para crear respuestas exitosas."""
    return SuccessResponse(message=message, data=data).model_dump()


def create_error_response(error: str, message: str, details: Optional[dict] = None) -> dict:
    """Helper para crear respuestas de error."""
    return ErrorResponse(error=error, message=message, details=details).model_dump()


def create_delete_response(message: str, deleted_id: str, soft_delete: bool = True) -> dict:
    """Helper para crear respuestas de eliminación."""
    return DeleteResponse(
        message=message,
        deleted_id=deleted_id,
        soft_delete=soft_delete
    ).model_dump()


def create_paginated_response(
    items: List[Any],
    page: int,
    page_size: int,
    total_items: int
) -> dict:
    """Helper para crear respuestas paginadas."""
    total_pages = (total_items + page_size - 1) // page_size if page_size > 0 else 0
    
    pagination = PaginationMeta(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
        has_next=page < total_pages - 1,
        has_previous=page > 0
    )
    
    return {
        "success": True,
        "data": items,
        "pagination": pagination.model_dump(),
        "timestamp": datetime.utcnow()
    }
