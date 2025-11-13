"""
Factura routes (Controllers) - Layered Architecture.

This module handles HTTP requests/responses for factura endpoints.
All business logic is delegated to the FacturaService layer.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import Optional
from datetime import datetime
import logging

from models.facturas import Factura, FacturaCreate, FacturaUpdate, EstadoFactura, TipoServicio
from models.common import create_delete_response
from core.pagination import create_paginated_response
from core.exceptions import (
    AppException,
    NotFoundException,
    ForbiddenException,
    BusinessException,
    ValidationException,
)
from services.factura_service import FacturaService
from database.db import get_db
from sqlalchemy.orm import Session
from auth import get_current_user_dep, require_roles
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/facturas", tags=["facturas"])


# ==================== Dependency Injection ====================

def get_factura_service(db: Session = Depends(get_db)) -> FacturaService:
    """Inject FacturaService with its dependencies."""
    from repositories.factura_repository import FacturaRepository
    from repositories.cita_repository import CitaRepository
    from repositories.vacuna_repository import VacunaRepository
    from repositories.mascota_repository import MascotaRepository
    from repositories.usuario_repository import UsuarioRepository
    
    factura_repo = FacturaRepository(db)
    cita_repo = CitaRepository(db)
    vacuna_repo = VacunaRepository(db)
    mascota_repo = MascotaRepository(db)
    usuario_repo = UsuarioRepository(db)
    
    return FacturaService(factura_repo, cita_repo, vacuna_repo, mascota_repo, usuario_repo)


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

@router.post("/", response_model=Factura, status_code=status.HTTP_201_CREATED)
async def crear_factura(
    factura: FacturaCreate,
    current_user=Depends(require_roles("veterinario", "admin")),
    service: FacturaService = Depends(get_factura_service),
):
    """
    Create a new factura (invoice).
    
    Only veterinarios or admins can create facturas.
    Creates factura for a cita and marks it as completada.
    
    Args:
        factura: Factura creation data
        current_user: Current authenticated user (veterinario or admin)
        service: Injected FacturaService
        
    Returns:
        Created factura with calculated total
    """
    try:
        return service.create_factura(factura, current_user)
    except AppException as e:
        raise handle_service_exception(e)
    except Exception as e:
        logger.error(f"Error creating factura: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al crear factura")


@router.get("/")
async def obtener_facturas(
    page: int = Query(0, ge=0, description="Número de página (0-indexed)"),
    page_size: int = Query(settings.default_page_size, ge=1, le=settings.max_page_size, description="Tamaño de página"),
    estado: Optional[EstadoFactura] = Query(None, description="Filtrar por estado"),
    veterinario: Optional[str] = Query(None, description="Filtrar por veterinario"),
    include_deleted: bool = Query(False, description="Incluir facturas eliminadas"),
    current_user=Depends(get_current_user_dep),
    service: FacturaService = Depends(get_factura_service),
):
    """
    List facturas with pagination and filters.
    
    Visibility rules:
    - admin: sees all facturas
    - veterinario: sees all facturas
    - cliente: sees only facturas for their own pets
    
    Args:
        page, page_size, estado, veterinario, include_deleted, current_user, service
        
    Returns:
        Paginated list of facturas
    """
    try:
        estado_str = estado.value if estado else None
        items, total = service.get_facturas(current_user, page, page_size, estado_str, veterinario, include_deleted)
        return create_paginated_response(items, page, page_size, total)
    except AppException as e:
        raise handle_service_exception(e)
    except Exception as e:
        logger.error(f"Error listing facturas: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al listar facturas")


@router.get("/{factura_id}", response_model=Factura)
async def obtener_factura(
    factura_id: str,
    current_user=Depends(get_current_user_dep),
    service: FacturaService = Depends(get_factura_service),
):
    """Get a factura by ID."""
    try:
        return service.get_factura(factura_id, current_user)
    except AppException as e:
        raise handle_service_exception(e)
    except Exception as e:
        logger.error(f"Error getting factura {factura_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al obtener factura")


@router.put("/{factura_id}", response_model=Factura)
async def actualizar_factura(
    factura_id: str,
    factura_update: FacturaUpdate,
    current_user=Depends(require_roles("veterinario", "admin")),
    service: FacturaService = Depends(get_factura_service),
):
    """Update a factura. Only veterinarios or admins can update."""
    try:
        return service.update_factura(factura_id, factura_update, current_user)
    except AppException as e:
        raise handle_service_exception(e)
    except Exception as e:
        logger.error(f"Error updating factura {factura_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al actualizar factura")


@router.post("/{factura_id}/pagar", response_model=Factura)
async def marcar_como_pagada(
    factura_id: str,
    current_user=Depends(get_current_user_dep),
    service: FacturaService = Depends(get_factura_service),
):
    """Mark factura as paid."""
    try:
        return service.mark_as_paid(factura_id, current_user)
    except AppException as e:
        raise handle_service_exception(e)
    except Exception as e:
        logger.error(f"Error marking factura as paid {factura_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al marcar factura como pagada")


@router.post("/{factura_id}/anular")
async def anular_factura(
    factura_id: str,
    current_user=Depends(require_roles("admin")),
    service: FacturaService = Depends(get_factura_service),
):
    """Anular (cancel) a factura. Only admins can anular."""
    try:
        service.anular_factura(factura_id, current_user)
        return {"success": True, "message": "Factura anulada correctamente", "id_factura": factura_id, "timestamp": datetime.utcnow()}
    except AppException as e:
        raise handle_service_exception(e)
    except Exception as e:
        logger.error(f"Error anulando factura {factura_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al anular factura")


@router.delete("/{factura_id}")
async def eliminar_factura(
    factura_id: str,
    current_user=Depends(require_roles("admin")),
    service: FacturaService = Depends(get_factura_service),
):
    """Delete a factura (soft delete). Only admins can delete."""
    try:
        service.delete(factura_id, user_id=current_user.id, hard=False)
        return create_delete_response(message="Factura eliminada correctamente", deleted_id=factura_id, soft_delete=True)
    except AppException as e:
        raise handle_service_exception(e)
    except Exception as e:
        logger.error(f"Error deleting factura {factura_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al eliminar factura")
