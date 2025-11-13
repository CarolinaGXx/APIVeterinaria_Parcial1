"""
Utilidades de paginación para una paginación consistente en toda la aplicación.
"""

from typing import TypeVar, Generic, List, Any
from pydantic import BaseModel, Field
from datetime import datetime

T = TypeVar('T')


class PaginationParams(BaseModel):
    """Parametros para la paginacion."""
    page: int = Field(0, ge=0, description="Page number (0-indexed)")
    page_size: int = Field(50, ge=1, le=100, description="Items per page")


class PaginationMeta(BaseModel):
    """Metadata para la paginacion."""
    page: int = Field(..., ge=0, description="Current page number (0-indexed)")
    page_size: int = Field(..., ge=1, description="Page size")
    total_items: int = Field(..., ge=0, description="Total items available")
    total_pages: int = Field(..., ge=0, description="Total pages")
    has_next: bool = Field(..., description="Has next page")
    has_previous: bool = Field(..., description="Has previous page")


class PaginatedResponse(BaseModel, Generic[T]):
    """Respuesta paginada genérica."""
    success: bool = Field(True, description="Operation success")
    data: List[T] = Field(..., description="List of items")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        arbitrary_types_allowed = True


def calculate_pagination_meta(
    page: int,
    page_size: int,
    total_items: int
) -> PaginationMeta:
    """
    Calcula la metadata de la paginación.
    
    Args:
        page: Número de página actual (0-indexed)
        page_size: Items por página
        total_items: Total number of items
        
    Returns:
        paginationmeta objeto con valores calculados
    """
    total_pages = (total_items + page_size - 1) // page_size if page_size > 0 else 0
    
    return PaginationMeta(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
        has_next=page < total_pages - 1,
        has_previous=page > 0
    )


def create_paginated_response(
    items: List[Any],
    page: int,
    page_size: int,
    total_items: int
) -> dict:
    """
    Crea un diccionario de respuesta paginado.
    Argumentos:
    items: Lista de elementos de la página actual
    page: Número de página actual (indexado desde 0)
    page_size: Número de elementos por página
    total_items: Número total de elementos
    Devuelve:
    Diccionario con la respuesta paginada
    """
    pagination_meta = calculate_pagination_meta(page, page_size, total_items)
    
    return {
        "success": True,
        "data": items,
        "pagination": pagination_meta.model_dump(),
        "timestamp": datetime.utcnow()
    }


def calculate_skip(page: int, page_size: int) -> int:
    """
    Calcula el valor de skip/offset para las consultas de la base de datos.
    
    Args:
        page: Número de página actual (indexado desde 0)
        page_size: Número de elementos por página
        
    Returns:
        Número de elementos a saltar
    """
    return page * page_size
