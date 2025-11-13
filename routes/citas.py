"""
Cita routes (Controllers) - Layered Architecture.

This module handles HTTP requests/responses for cita endpoints.
All business logic is delegated to the CitaService layer.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import Optional
from datetime import datetime
import logging

from models.citas import Cita, CitaCreate, CitaUpdate, EstadoCita
from models.common import create_delete_response
from core.pagination import create_paginated_response
from core.exceptions import (
    AppException,
    NotFoundException,
    ForbiddenException,
    BusinessException,
    ValidationException,
)
from services.cita_service import CitaService
from database.db import get_db
from sqlalchemy.orm import Session
from auth import get_current_user_dep, require_roles
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/citas", tags=["citas"])


# ==================== Dependency Injection ====================

def get_cita_service(db: Session = Depends(get_db)) -> CitaService:
    """Inject CitaService with its dependencies."""
    from repositories.cita_repository import CitaRepository
    from repositories.mascota_repository import MascotaRepository
    from repositories.usuario_repository import UsuarioRepository
    
    cita_repo = CitaRepository(db)
    mascota_repo = MascotaRepository(db)
    usuario_repo = UsuarioRepository(db)
    
    return CitaService(cita_repo, mascota_repo, usuario_repo)


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

@router.post("/", response_model=Cita, status_code=status.HTTP_201_CREATED)
async def agendar_cita(
    cita: CitaCreate,
    current_user=Depends(require_roles("veterinario", "cliente", "admin")),
    service: CitaService = Depends(get_cita_service),
):
    """
    Schedule a new cita (appointment).
    
    Only the pet owner or admin can create appointments for a pet.
    Veterinario must exist and have the 'veterinario' role.
    
    Args:
        cita: Cita creation data
        current_user: Current authenticated user
        service: Injected CitaService
        
    Returns:
        Created cita
    """
    try:
        return service.create_cita(cita, current_user)
    except AppException as e:
        raise handle_service_exception(e)
    except Exception as e:
        logger.error(f"Error creating cita: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear cita"
        )


@router.get("/")
async def obtener_citas(
    page: int = Query(0, ge=0, description="Número de página (0-indexed)"),
    page_size: int = Query(
        settings.default_page_size,
        ge=1,
        le=settings.max_page_size,
        description="Tamaño de página"
    ),
    estado: Optional[EstadoCita] = Query(None, description="Filtrar por estado"),
    veterinario: Optional[str] = Query(None, description="Filtrar por veterinario"),
    include_deleted: bool = Query(False, description="Incluir citas eliminadas"),
    current_user=Depends(get_current_user_dep),
    service: CitaService = Depends(get_cita_service),
):
    """
    List citas with pagination and filters.
    
    Visibility rules:
    - admin: sees all citas
    - veterinario: sees citas assigned to them or for their own pets
    - cliente: sees only citas for their own pets
    
    Args:
        page: Page number (0-indexed)
        page_size: Items per page
        estado: Optional estado filter
        veterinario: Optional veterinario filter
        include_deleted: Include soft-deleted citas
        current_user: Current authenticated user
        service: Injected CitaService
        
    Returns:
        Paginated list of citas
    """
    try:
        estado_str = estado.value if estado else None
        items, total = service.get_citas(
            current_user=current_user,
            page=page,
            page_size=page_size,
            estado=estado_str,
            veterinario=veterinario,
            include_deleted=include_deleted
        )
        return create_paginated_response(items, page, page_size, total)
    except AppException as e:
        raise handle_service_exception(e)
    except Exception as e:
        logger.error(f"Error listing citas: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al listar citas"
        )


@router.get("/{cita_id}", response_model=Cita)
async def obtener_cita(
    cita_id: str,
    current_user=Depends(get_current_user_dep),
    service: CitaService = Depends(get_cita_service),
):
    """
    Get a cita by ID.
    
    Access allowed for admin, pet owner, or assigned veterinario.
    
    Args:
        cita_id: Cita ID
        current_user: Current authenticated user
        service: Injected CitaService
        
    Returns:
        Cita data
    """
    try:
        return service.get_cita(cita_id, current_user)
    except AppException as e:
        raise handle_service_exception(e)
    except Exception as e:
        logger.error(f"Error getting cita {cita_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener cita"
        )


@router.put("/{cita_id}", response_model=Cita)
async def actualizar_cita(
    cita_id: str,
    cita_update: CitaUpdate,
    current_user=Depends(get_current_user_dep),
    service: CitaService = Depends(get_cita_service),
):
    """
    Update a cita.
    
    Only pet owner or admin can update.
    
    Args:
        cita_id: Cita ID
        cita_update: Update data
        current_user: Current authenticated user
        service: Injected CitaService
        
    Returns:
        Updated cita
    """
    try:
        return service.update_cita(cita_id, cita_update, current_user)
    except AppException as e:
        raise handle_service_exception(e)
    except Exception as e:
        logger.error(f"Error updating cita {cita_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar cita"
        )


@router.delete("/{cita_id}")
async def cancelar_cita(
    cita_id: str,
    current_user=Depends(get_current_user_dep),
    service: CitaService = Depends(get_cita_service),
):
    """
    Cancel a cita (changes estado to 'cancelada').
    
    Only pet owner or admin can cancel.
    
    Args:
        cita_id: Cita ID
        current_user: Current authenticated user
        service: Injected CitaService
        
    Returns:
        Cancellation confirmation
    """
    try:
        service.cancel_cita(cita_id, current_user)
        return {
            "success": True,
            "message": "Cita cancelada correctamente",
            "id_cita": cita_id,
            "timestamp": datetime.utcnow()
        }
    except AppException as e:
        raise handle_service_exception(e)
    except Exception as e:
        logger.error(f"Error cancelling cita {cita_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al cancelar cita"
        )
