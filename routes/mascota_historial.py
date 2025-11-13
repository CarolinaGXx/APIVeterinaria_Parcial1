"""
Mascota Historial routes - Endpoints for complete clinical history.

These endpoints return ALL clinical records for a specific pet,
regardless of which veterinarian created them.
"""

from fastapi import APIRouter, HTTPException, Query, Depends, status
from typing import Optional
import logging
from sqlalchemy.orm import Session

from core.pagination import create_paginated_response
from core.exceptions import AppException, NotFoundException, ForbiddenException
from database.db import get_db
from auth import get_current_user_dep
from config import settings

# Import services
from services.vacuna_service import VacunaService
from services.cita_service import CitaService
from services.receta_service import RecetaService
from services.factura_service import FacturaService
from services.mascota_service import MascotaService

# Import repositories
from repositories.vacuna_repository import VacunaRepository
from repositories.cita_repository import CitaRepository
from repositories.receta_repository import RecetaRepository
from repositories.factura_repository import FacturaRepository
from repositories.mascota_repository import MascotaRepository
from repositories.usuario_repository import UsuarioRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mascotas", tags=["mascota-historial"])


# ==================== Dependency Injection ====================

def get_vacuna_service_dep(db: Session = Depends(get_db)) -> VacunaService:
    """Inject VacunaService."""
    vacuna_repo = VacunaRepository(db)
    mascota_repo = MascotaRepository(db)
    usuario_repo = UsuarioRepository(db)
    return VacunaService(vacuna_repo, mascota_repo, usuario_repo)

def get_cita_service_dep(db: Session = Depends(get_db)) -> CitaService:
    """Inject CitaService."""
    cita_repo = CitaRepository(db)
    mascota_repo = MascotaRepository(db)
    usuario_repo = UsuarioRepository(db)
    return CitaService(cita_repo, mascota_repo, usuario_repo)

def get_receta_service_dep(db: Session = Depends(get_db)) -> RecetaService:
    """Inject RecetaService."""
    receta_repo = RecetaRepository(db)
    cita_repo = CitaRepository(db)
    mascota_repo = MascotaRepository(db)
    usuario_repo = UsuarioRepository(db)
    return RecetaService(receta_repo, cita_repo, mascota_repo, usuario_repo)

def get_factura_service_dep(db: Session = Depends(get_db)) -> FacturaService:
    """Inject FacturaService."""
    factura_repo = FacturaRepository(db)
    cita_repo = CitaRepository(db)
    vacuna_repo = VacunaRepository(db)
    mascota_repo = MascotaRepository(db)
    usuario_repo = UsuarioRepository(db)
    return FacturaService(factura_repo, cita_repo, vacuna_repo, mascota_repo, usuario_repo)

def get_mascota_service_dep(db: Session = Depends(get_db)) -> MascotaService:
    """Inject MascotaService."""
    mascota_repo = MascotaRepository(db)
    usuario_repo = UsuarioRepository(db)
    return MascotaService(mascota_repo, usuario_repo)


# ==================== Vacunas de una Mascota ====================

@router.get("/{mascota_id}/vacunas")
async def obtener_vacunas_mascota(
    mascota_id: str,
    page: int = Query(0, ge=0, description="Número de página (0-indexed)"),
    page_size: int = Query(
        settings.default_page_size,
        ge=1,
        le=settings.max_page_size,
        description="Tamaño de página"
    ),
    include_deleted: bool = Query(False, description="Incluir vacunas eliminadas"),
    current_user=Depends(get_current_user_dep),
    vacuna_service: VacunaService = Depends(get_vacuna_service_dep),
    mascota_service: MascotaService = Depends(get_mascota_service_dep),
):
    """
    Get ALL vacunas for a specific mascota (complete clinical history).
    
    Returns all vaccines regardless of which veterinarian applied them.
    Access is granted to:
    - Pet owner
    - Any veterinarian (for clinical necessity)
    - Administrators
    
    Args:
        mascota_id: Mascota ID
        page: Page number
        page_size: Items per page
        include_deleted: Include deleted vacunas
        
    Returns:
        Paginated list of ALL vacunas for this mascota
    """
    try:
        # Verify user has access to this mascota
        mascota = mascota_service.get_mascota(mascota_id, current_user)
        
        # Get ALL vacunas for this mascota
        items, total = vacuna_service.get_vacunas_by_mascota(
            mascota_id=mascota_id,
            page=page,
            page_size=page_size,
            include_deleted=include_deleted
        )
        
        return create_paginated_response(items, page, page_size, total)
        
    except (NotFoundException, ForbiddenException) as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if isinstance(e, NotFoundException) else status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting vacunas for mascota {mascota_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener vacunas"
        )


# ==================== Citas de una Mascota ====================

@router.get("/{mascota_id}/citas")
async def obtener_citas_mascota(
    mascota_id: str,
    page: int = Query(0, ge=0, description="Número de página (0-indexed)"),
    page_size: int = Query(
        settings.default_page_size,
        ge=1,
        le=settings.max_page_size,
        description="Tamaño de página"
    ),
    include_deleted: bool = Query(False, description="Incluir citas canceladas"),
    current_user=Depends(get_current_user_dep),
    cita_service: CitaService = Depends(get_cita_service_dep),
    mascota_service: MascotaService = Depends(get_mascota_service_dep),
):
    """
    Get ALL citas for a specific mascota (complete clinical history).
    
    Returns all appointments regardless of which veterinarian attended them.
    """
    try:
        # Verify user has access to this mascota
        mascota = mascota_service.get_mascota(mascota_id, current_user)
        
        # Get ALL citas for this mascota
        items, total = cita_service.get_citas_by_mascota(
            mascota_id=mascota_id,
            page=page,
            page_size=page_size,
            include_deleted=include_deleted
        )
        
        return create_paginated_response(items, page, page_size, total)
        
    except (NotFoundException, ForbiddenException) as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if isinstance(e, NotFoundException) else status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting citas for mascota {mascota_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener citas"
        )


# ==================== Recetas de una Mascota ====================

@router.get("/{mascota_id}/recetas")
async def obtener_recetas_mascota(
    mascota_id: str,
    page: int = Query(0, ge=0, description="Número de página (0-indexed)"),
    page_size: int = Query(
        settings.default_page_size,
        ge=1,
        le=settings.max_page_size,
        description="Tamaño de página"
    ),
    include_deleted: bool = Query(False, description="Incluir recetas eliminadas"),
    current_user=Depends(get_current_user_dep),
    receta_service: RecetaService = Depends(get_receta_service_dep),
    mascota_service: MascotaService = Depends(get_mascota_service_dep),
):
    """
    Get ALL recetas for a specific mascota (complete clinical history).
    
    Returns all prescriptions regardless of which veterinarian issued them.
    """
    try:
        # Verify user has access to this mascota
        mascota = mascota_service.get_mascota(mascota_id, current_user)
        
        # Get ALL recetas for this mascota
        items, total = receta_service.get_recetas_by_mascota(
            mascota_id=mascota_id,
            page=page,
            page_size=page_size,
            include_deleted=include_deleted
        )
        
        return create_paginated_response(items, page, page_size, total)
        
    except (NotFoundException, ForbiddenException) as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if isinstance(e, NotFoundException) else status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting recetas for mascota {mascota_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener recetas"
        )


# ==================== Facturas de una Mascota ====================

@router.get("/{mascota_id}/facturas")
async def obtener_facturas_mascota(
    mascota_id: str,
    page: int = Query(0, ge=0, description="Número de página (0-indexed)"),
    page_size: int = Query(
        settings.default_page_size,
        ge=1,
        le=settings.max_page_size,
        description="Tamaño de página"
    ),
    include_deleted: bool = Query(False, description="Incluir facturas anuladas"),
    current_user=Depends(get_current_user_dep),
    factura_service: FacturaService = Depends(get_factura_service_dep),
    mascota_service: MascotaService = Depends(get_mascota_service_dep),
):
    """
    Get ALL facturas for a specific mascota.
    
    Returns all invoices for the pet. Access is more restricted:
    - Pet owner can see all their pet's invoices
    - Veterinarians can see invoices they issued for this pet
    - Administrators can see all
    """
    try:
        # Verify user has access to this mascota
        mascota = mascota_service.get_mascota(mascota_id, current_user)
        
        # Get facturas for this mascota (with role-based filtering)
        items, total = factura_service.get_facturas_by_mascota(
            mascota_id=mascota_id,
            current_user=current_user,
            page=page,
            page_size=page_size,
            include_deleted=include_deleted
        )
        
        return create_paginated_response(items, page, page_size, total)
        
    except (NotFoundException, ForbiddenException) as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if isinstance(e, NotFoundException) else status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting facturas for mascota {mascota_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener facturas"
        )
