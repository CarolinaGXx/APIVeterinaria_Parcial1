"""
Vacuna routes (Controllers) - Layered Architecture.

This module handles HTTP requests/responses for vacuna endpoints.
All business logic is delegated to the VacunaService layer.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import Optional
from datetime import datetime, date
import logging

from models.vacunas import Vacuna, VacunaCreate, VacunaUpdate, TipoVacuna
from models.common import create_delete_response
from core.pagination import create_paginated_response
from core.exceptions import (
    AppException,
    NotFoundException,
    ForbiddenException,
    BusinessException,
    ValidationException,
)
from services.vacuna_service import VacunaService
from database.db import get_db
from sqlalchemy.orm import Session
from auth import get_current_user_dep, require_roles
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vacunas", tags=["vacunas"])


# ==================== Dependency Injection ====================

def get_vacuna_service(db: Session = Depends(get_db)) -> VacunaService:
    """Inject VacunaService with its dependencies."""
    from repositories.vacuna_repository import VacunaRepository
    from repositories.mascota_repository import MascotaRepository
    from repositories.usuario_repository import UsuarioRepository
    
    vacuna_repo = VacunaRepository(db)
    mascota_repo = MascotaRepository(db)
    usuario_repo = UsuarioRepository(db)
    
    return VacunaService(vacuna_repo, mascota_repo, usuario_repo)


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

@router.post("/", response_model=Vacuna, status_code=status.HTTP_201_CREATED)
async def registrar_vacuna(
    vacuna: VacunaCreate,
    current_user=Depends(require_roles("veterinario", "admin")),
    service: VacunaService = Depends(get_vacuna_service),
):
    """
    Register a new vacuna.
    
    Only veterinarios or admins can register vaccines.
    The veterinario field is automatically set to the current user.
    
    Args:
        vacuna: Vacuna creation data
        current_user: Current authenticated user (veterinario or admin)
        service: Injected VacunaService
        
    Returns:
        Created vacuna
    """
    try:
        return service.create_vacuna(vacuna, current_user)
    except AppException as e:
        raise handle_service_exception(e)
    except Exception as e:
        logger.error(f"Error creating vacuna: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al registrar vacuna"
        )


@router.get("/")
async def obtener_vacunas(
    page: int = Query(0, ge=0, description="Número de página (0-indexed)"),
    page_size: int = Query(
        settings.default_page_size,
        ge=1,
        le=settings.max_page_size,
        description="Tamaño de página"
    ),
    tipo_vacuna: Optional[TipoVacuna] = Query(None, description="Filtrar por tipo de vacuna"),
    veterinario: Optional[str] = Query(None, description="Filtrar por veterinario (búsqueda parcial)"),
    id_mascota: Optional[str] = Query(None, description="Filtrar por ID de mascota"),
    mascota_nombre: Optional[str] = Query(None, description="Filtrar por nombre de mascota (búsqueda parcial)"),
    include_deleted: bool = Query(False, description="Incluir vacunas eliminadas (solo admin)"),
    current_user=Depends(get_current_user_dep),
    service: VacunaService = Depends(get_vacuna_service),
):
    """
    List vacunas with pagination and filters.
    
    Filters are applied BEFORE pagination, so results span all pages.
    Results are ordered by fecha_aplicacion DESC (most recent first).
    
    Visibility rules:
    - admin: sees all vacunas, can include deleted
    - veterinario: sees all vacunas, cannot include deleted
    - cliente: sees only vacunas for their own pets
    
    Args:
        page: Page number (0-indexed)
        page_size: Items per page
        tipo_vacuna: Optional tipo_vacuna filter
        veterinario: Optional veterinario filter (partial match)
        id_mascota: Optional mascota ID filter
        mascota_nombre: Optional mascota name filter (partial match)
        include_deleted: Include soft-deleted vacunas (admin only)
        current_user: Current authenticated user
        service: Injected VacunaService
        
    Returns:
        Paginated list of vacunas
    """
    try:
        # Only admin can view deleted vacunas
        if include_deleted and current_user.role != "admin":
            include_deleted = False
        
        tipo_str = tipo_vacuna.value if tipo_vacuna else None
        items, total = service.get_vacunas(
            current_user=current_user,
            page=page,
            page_size=page_size,
            tipo_vacuna=tipo_str,
            veterinario=veterinario,
            id_mascota=id_mascota,
            mascota_nombre=mascota_nombre,
            include_deleted=include_deleted
        )
        return create_paginated_response(items, page, page_size, total)
    except AppException as e:
        raise handle_service_exception(e)
    except Exception as e:
        logger.error(f"Error listing vacunas: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al listar vacunas"
        )


@router.get("/proximas-dosis")
async def obtener_proximas_dosis(
    fecha_limite: Optional[date] = Query(None, description="Fecha límite"),
    current_user=Depends(get_current_user_dep),
    service: VacunaService = Depends(get_vacuna_service),
):
    """
    Get vacunas with upcoming next doses.
    
    Args:
        fecha_limite: Optional date limit
        current_user: Current authenticated user
        service: Injected VacunaService
        
    Returns:
        List of vacunas with upcoming doses
    """
    try:
        return service.get_proximas_dosis(current_user, fecha_limite)
    except AppException as e:
        raise handle_service_exception(e)
    except Exception as e:
        logger.error(f"Error getting proximas dosis: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener próximas dosis"
        )


@router.get("/{vacuna_id}", response_model=Vacuna)
async def obtener_vacuna(
    vacuna_id: str,
    current_user=Depends(get_current_user_dep),
    service: VacunaService = Depends(get_vacuna_service),
):
    """
    Get a vacuna by ID.
    
    Access allowed for admin, pet owner, or veterinarios.
    
    Args:
        vacuna_id: Vacuna ID
        current_user: Current authenticated user
        service: Injected VacunaService
        
    Returns:
        Vacuna data
    """
    try:
        return service.get_vacuna(vacuna_id, current_user)
    except AppException as e:
        raise handle_service_exception(e)
    except Exception as e:
        logger.error(f"Error getting vacuna {vacuna_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener vacuna"
        )


@router.put("/{vacuna_id}", response_model=Vacuna)
async def actualizar_vacuna(
    vacuna_id: str,
    vacuna_update: VacunaUpdate,
    current_user=Depends(require_roles("veterinario", "admin")),
    service: VacunaService = Depends(get_vacuna_service),
):
    """
    Update a vacuna.
    
    Only veterinarios or admins can update.
    
    Args:
        vacuna_id: Vacuna ID
        vacuna_update: Update data
        current_user: Current authenticated user
        service: Injected VacunaService
        
    Returns:
        Updated vacuna
    """
    try:
        return service.update_vacuna(vacuna_id, vacuna_update, current_user)
    except AppException as e:
        raise handle_service_exception(e)
    except Exception as e:
        logger.error(f"Error updating vacuna {vacuna_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar vacuna"
        )


@router.delete("/{vacuna_id}")
async def eliminar_vacuna(
    vacuna_id: str,
    current_user=Depends(require_roles("admin")),
    service: VacunaService = Depends(get_vacuna_service),
):
    """
    Delete a vacuna (soft delete).
    
    Only admins can delete vacunas.
    
    Args:
        vacuna_id: Vacuna ID
        current_user: Current authenticated user
        service: Injected VacunaService
        
    Returns:
        Delete confirmation
    """
    try:
        service.delete_vacuna(vacuna_id, current_user)
        return create_delete_response(
            message="Vacuna eliminada correctamente",
            deleted_id=vacuna_id,
            soft_delete=True
        )
    except AppException as e:
        raise handle_service_exception(e)
    except Exception as e:
        logger.error(f"Error deleting vacuna {vacuna_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar vacuna"
        )
