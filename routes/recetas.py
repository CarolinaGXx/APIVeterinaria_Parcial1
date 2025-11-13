"""
Receta routes (Controllers) - Layered Architecture.

This module handles HTTP requests/responses for receta endpoints.
All business logic is delegated to the RecetaService layer.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import Optional
from datetime import datetime
import logging

from models.recetas import Receta, RecetaCreate, RecetaUpdate, RecetaSummary
from models.common import create_delete_response
from core.pagination import create_paginated_response
from core.exceptions import (
    AppException,
    NotFoundException,
    ForbiddenException,
    BusinessException,
    ValidationException,
)
from services.receta_service import RecetaService
from database.db import get_db
from sqlalchemy.orm import Session
from auth import get_current_user_dep, require_roles
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recetas", tags=["recetas"])


# ==================== Dependency Injection ====================

def get_receta_service(db: Session = Depends(get_db)) -> RecetaService:
    """Inject RecetaService with its dependencies."""
    from repositories.receta_repository import RecetaRepository
    from repositories.cita_repository import CitaRepository
    from repositories.mascota_repository import MascotaRepository
    from repositories.usuario_repository import UsuarioRepository
    
    receta_repo = RecetaRepository(db)
    cita_repo = CitaRepository(db)
    mascota_repo = MascotaRepository(db)
    usuario_repo = UsuarioRepository(db)
    
    return RecetaService(receta_repo, cita_repo, mascota_repo, usuario_repo)


# ==================== Exception Handler ====================

def handle_service_exception(e: Exception) -> HTTPException:
    """Convert service layer exceptions to HTTP exceptions."""
    if isinstance(e, NotFoundException):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    elif isinstance(e, ForbiddenException):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.message)
    elif isinstance(e, ValidationException):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.message)
    elif isinstance(e, BusinessException):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    elif isinstance(e, AppException):
        return HTTPException(status_code=e.status_code, detail=e.message)
    else:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor")


# ==================== Endpoints ====================

@router.post("/", response_model=Receta, status_code=status.HTTP_201_CREATED)
async def crear_receta(
    receta: RecetaCreate,
    current_user=Depends(require_roles("veterinario", "admin")),
    service: RecetaService = Depends(get_receta_service),
):
    """
    Create a new receta (prescription) with medication lines.
    
    Only veterinarios or admins can create recetas.
    fecha_emision is auto-generated.
    
    Args:
        receta: Receta creation data with lineas
        current_user: Current authenticated user (veterinario or admin)
        service: Injected RecetaService
        
    Returns:
        Created receta with lineas
    """
    try:
        return service.create_receta(receta, current_user)
    except AppException as e:
        raise handle_service_exception(e)
    except Exception as e:
        logger.error(f"Error creating receta: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al crear receta")


@router.get("/")
async def obtener_recetas(
    page: int = Query(0, ge=0, description="Número de página (0-indexed)"),
    page_size: int = Query(settings.default_page_size, ge=1, le=settings.max_page_size, description="Tamaño de página"),
    veterinario: Optional[str] = Query(None, description="Filtrar por veterinario"),
    include_deleted: bool = Query(False, description="Incluir recetas eliminadas"),
    current_user=Depends(get_current_user_dep),
    service: RecetaService = Depends(get_receta_service),
):
    """
    List recetas with pagination (summary without lineas).
    
    Visibility rules:
    - admin/veterinario: sees all recetas
    - cliente: sees only recetas for their own pets
    
    Args:
        page, page_size, veterinario, include_deleted, current_user, service
        
    Returns:
        Paginated list of receta summaries
    """
    try:
        items, total = service.get_recetas(current_user, page, page_size, veterinario, include_deleted)
        return create_paginated_response(items, page, page_size, total)
    except AppException as e:
        raise handle_service_exception(e)
    except Exception as e:
        logger.error(f"Error listing recetas: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al listar recetas")


@router.get("/cita/{cita_id}", response_model=Receta)
async def obtener_receta_por_cita(
    cita_id: str,
    current_user=Depends(get_current_user_dep),
    service: RecetaService = Depends(get_receta_service),
):
    """
    Get receta for a specific cita (with lineas).
    
    Args:
        cita_id: Cita ID
        current_user: Current authenticated user
        service: Injected RecetaService
        
    Returns:
        Receta with lineas or 404 if not found
    """
    try:
        receta = service.get_receta_by_cita(cita_id, current_user)
        if not receta:
            raise HTTPException(status_code=404, detail="No se encontró receta para esta cita")
        return receta
    except AppException as e:
        raise handle_service_exception(e)
    except Exception as e:
        logger.error(f"Error getting receta by cita {cita_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al obtener receta")


@router.get("/{receta_id}", response_model=Receta)
async def obtener_receta(
    receta_id: str,
    current_user=Depends(get_current_user_dep),
    service: RecetaService = Depends(get_receta_service),
):
    """Get a receta by ID (with lineas)."""
    try:
        return service.get_receta(receta_id, current_user)
    except AppException as e:
        raise handle_service_exception(e)
    except Exception as e:
        logger.error(f"Error getting receta {receta_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al obtener receta")


@router.put("/{receta_id}", response_model=Receta)
async def actualizar_receta(
    receta_id: str,
    receta_update: RecetaUpdate,
    current_user=Depends(require_roles("veterinario", "admin")),
    service: RecetaService = Depends(get_receta_service),
):
    """
    Update a receta (including lineas replacement).
    
    Only veterinarios or admins can update.
    If lineas are provided, they replace all existing lineas.
    """
    try:
        return service.update_receta(receta_id, receta_update, current_user)
    except AppException as e:
        raise handle_service_exception(e)
    except Exception as e:
        logger.error(f"Error updating receta {receta_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al actualizar receta")


@router.delete("/{receta_id}")
async def eliminar_receta(
    receta_id: str,
    current_user=Depends(require_roles("admin")),
    service: RecetaService = Depends(get_receta_service),
):
    """Delete a receta (soft delete). Only admins can delete."""
    try:
        service.delete(receta_id, user_id=current_user.id, hard=False)
        return create_delete_response(message="Receta eliminada correctamente", deleted_id=receta_id, soft_delete=True)
    except AppException as e:
        raise handle_service_exception(e)
    except Exception as e:
        logger.error(f"Error deleting receta {receta_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al eliminar receta")
