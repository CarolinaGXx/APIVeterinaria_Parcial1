"""
Mascota routes (Controllers) - Layered Architecture.

This module handles HTTP requests/responses for mascota endpoints.
All business logic is delegated to the MascotaService layer.

Responsibilities:
- Parse HTTP requests
- Validate authentication/authorization
- Delegate to service layer
- Format HTTP responses
- Handle errors and status codes
"""

from fastapi import APIRouter, HTTPException, Query, Depends, status
from typing import Optional
from datetime import datetime
import logging

from models.mascotas import Mascota, MascotaCreate, MascotaUpdate, TipoMascota
from models.common import create_delete_response
from core.pagination import create_paginated_response
from core.exceptions import (
    AppException,
    NotFoundException,
    ForbiddenException,
    BusinessException,
    ValidationException,
)
from services.mascota_service import MascotaService
from database.db import get_db
from sqlalchemy.orm import Session
from auth import get_current_user_dep, require_roles
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mascotas", tags=["mascotas"])


# ==================== Dependency Injection ====================

def get_mascota_service(db: Session = Depends(get_db)) -> MascotaService:
    """Inject MascotaService with its dependencies."""
    from repositories.mascota_repository import MascotaRepository
    from repositories.usuario_repository import UsuarioRepository
    repository = MascotaRepository(db)
    usuario_repository = UsuarioRepository(db)
    return MascotaService(repository, usuario_repository)


# ==================== Exception Handler ====================

def handle_service_exception(e: Exception) -> HTTPException:
    """Convert service layer exceptions to HTTP exceptions."""
    if isinstance(e, NotFoundException):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )
    elif isinstance(e, ForbiddenException):
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message
        )
    elif isinstance(e, ValidationException):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.message
        )
    elif isinstance(e, BusinessException):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
    elif isinstance(e, AppException):
        return HTTPException(
            status_code=e.status_code,
            detail=e.message
        )
    else:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )


# ==================== Endpoints ====================

@router.post("/", response_model=Mascota, status_code=status.HTTP_201_CREATED)
async def crear_mascota(
    mascota: MascotaCreate,
    current_user=Depends(require_roles("veterinario", "cliente", "admin")),
    service: MascotaService = Depends(get_mascota_service),
):
    """
    Create a new mascota.
    
    The owner is inferred from the authenticated user.
    
    Args:
        mascota: Mascota data
        current_user: Current authenticated user
        service: Injected MascotaService
        
    Returns:
        Created mascota with owner phone number
    """
    try:
        return service.create_mascota(mascota, current_user)
    except AppException as e:
        raise handle_service_exception(e)
    except Exception as e:
        logger.error(f"Error creating mascota: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear mascota"
        )


@router.get("/search")
async def buscar_mascotas(
    q: str = Query(..., min_length=1, description="Término de búsqueda (nombre de mascota o propietario)"),
    limit: int = Query(20, ge=1, le=50, description="Máximo de resultados"),
    include_deleted: bool = Query(False, description="Incluir mascotas eliminadas"),
    current_user=Depends(get_current_user_dep),
    service: MascotaService = Depends(get_mascota_service),
):
    """
    Search mascotas by name or owner (for autocomplete/quick search).
    
    Returns a simplified list of mascotas matching the search term.
    Designed for real-time search while creating vaccines/appointments.
    
    Args:
        q: Search term (searches in mascota name and owner name)
        limit: Maximum results to return (default 20, max 50)
        include_deleted: Include soft-deleted mascotas
        current_user: Current authenticated user
        service: Injected MascotaService
        
    Returns:
        List of mascotas (not paginated, simple array)
    """
    try:
        items, _ = service.get_mascotas(
            current_user=current_user,
            page=0,
            page_size=limit,
            tipo=None,
            propietario=None,
            search_term=q,  # New parameter for search
            include_deleted=include_deleted
        )
        return items
    except AppException as e:
        raise handle_service_exception(e)
    except Exception as e:
        logger.error(f"Error searching mascotas: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al buscar mascotas"
        )


@router.get("/")
async def obtener_mascotas(
    page: int = Query(0, ge=0, description="Número de página (0-indexed)"),
    page_size: int = Query(
        settings.default_page_size,
        ge=1,
        le=settings.max_page_size,
        description="Tamaño de página"
    ),
    tipo: Optional[TipoMascota] = Query(
        None, description="Filtrar por tipo de mascota"
    ),
    propietario: Optional[str] = Query(
        None, description="Filtrar por propietario (admin only)"
    ),
    include_deleted: bool = Query(False, description="Incluir mascotas eliminadas"),
    current_user=Depends(get_current_user_dep),
    service: MascotaService = Depends(get_mascota_service),
):
    """
    Get list of mascotas with pagination.
    
    By default returns mascotas belonging to the authenticated user.
    Administrators can optionally filter by owner.
    
    Args:
        page: Page number (0-indexed)
        page_size: Items per page
        tipo: Filter by mascota type
        propietario: Filter by owner username (admin only)
        include_deleted: Include soft-deleted mascotas
        current_user: Current authenticated user
        service: Injected MascotaService
        
    Returns:
        Paginated list of mascotas
    """
    try:
        tipo_str = tipo.value if tipo else None
        items, total = service.get_mascotas(
            current_user=current_user,
            page=page,
            page_size=page_size,
            tipo=tipo_str,
            propietario=propietario,
            include_deleted=include_deleted
        )
        return create_paginated_response(items, page, page_size, total)
    except AppException as e:
        raise handle_service_exception(e)
    except Exception as e:
        logger.error(f"Error getting mascotas: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener mascotas"
        )


@router.get("/{mascota_id}", response_model=Mascota)
async def obtener_mascota(
    mascota_id: str,
    current_user=Depends(get_current_user_dep),
    service: MascotaService = Depends(get_mascota_service),
):
    """
    Get a mascota by ID.
    
    Only the owner or an administrator can view the mascota.
    
    Args:
        mascota_id: Mascota ID
        current_user: Current authenticated user
        service: Injected MascotaService
        
    Returns:
        Mascota with owner phone number
    """
    try:
        return service.get_mascota(mascota_id, current_user)
    except AppException as e:
        raise handle_service_exception(e)
    except Exception as e:
        logger.error(f"Error getting mascota {mascota_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener mascota"
        )


@router.put("/{mascota_id}", response_model=Mascota)
async def actualizar_mascota(
    mascota_id: str,
    mascota_update: MascotaUpdate,
    current_user=Depends(get_current_user_dep),
    service: MascotaService = Depends(get_mascota_service),
):
    """
    Update an existing mascota.
    
    Only the owner or an administrator can update.
    
    Args:
        mascota_id: Mascota ID
        mascota_update: Update data
        current_user: Current authenticated user
        service: Injected MascotaService
        
    Returns:
        Updated mascota
    """
    try:
        return service.update_mascota(mascota_id, mascota_update, current_user)
    except AppException as e:
        raise handle_service_exception(e)
    except Exception as e:
        logger.error(f"Error updating mascota {mascota_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar mascota"
        )


@router.delete("/{mascota_id}")
async def eliminar_mascota(
    mascota_id: str,
    current_user=Depends(get_current_user_dep),
    service: MascotaService = Depends(get_mascota_service),
):
    """
    Delete a mascota (soft delete).
    
    The mascota is marked as deleted but not removed from the database.
    Only the owner or an administrator can delete.
    
    Args:
        mascota_id: Mascota ID
        current_user: Current authenticated user
        service: Injected MascotaService
        
    Returns:
        Delete confirmation
    """
    try:
        service.delete_mascota(mascota_id, current_user)
        return create_delete_response(
            message="Mascota eliminada correctamente",
            deleted_id=mascota_id,
            soft_delete=True
        )
    except AppException as e:
        raise handle_service_exception(e)
    except Exception as e:
        logger.error(f"Error deleting mascota {mascota_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar mascota"
        )


@router.post("/{mascota_id}/restore")
async def restaurar_mascota(
    mascota_id: str,
    current_user=Depends(get_current_user_dep),
    service: MascotaService = Depends(get_mascota_service),
):
    """
    Restore a soft-deleted mascota.
    
    Only the owner or an administrator can restore.
    
    Args:
        mascota_id: Mascota ID
        current_user: Current authenticated user
        service: Injected MascotaService
        
    Returns:
        Restore confirmation
    """
    try:
        service.restore_mascota(mascota_id, current_user)
        return {
            "success": True,
            "message": "Mascota restaurada correctamente",
            "id_mascota": mascota_id,
            "timestamp": datetime.utcnow()
        }
    except AppException as e:
        raise handle_service_exception(e)
    except Exception as e:
        logger.error(f"Error restoring mascota {mascota_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al restaurar mascota"
        )
