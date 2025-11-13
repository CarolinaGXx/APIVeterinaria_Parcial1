"""
Usuario routes (Controllers) - Layered Architecture.

This module handles HTTP requests/responses for usuario endpoints.
All business logic is delegated to the UsuarioService layer.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import Optional
from datetime import datetime
import logging

from models.usuarios import (
    Usuario,
    UsuarioCreate,
    Role,
    UsuarioUpdateResponse,
    UsuarioUpdateRequest,
    UsuarioPrivilegedCreate,
    UsuarioRoleUpdate,
)
from models.common import create_delete_response
from core.pagination import create_paginated_response
from core.exceptions import (
    AppException,
    NotFoundException,
    ForbiddenException,
    BusinessException,
    ValidationException,
    DuplicateException,
)
from services.usuario_service import UsuarioService
from database.db import get_db
from sqlalchemy.orm import Session
from auth import get_current_user_dep, require_roles
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


# ==================== Dependency Injection ====================

def get_usuario_service(db: Session = Depends(get_db)) -> UsuarioService:
    """Inject UsuarioService with its dependencies."""
    from repositories.usuario_repository import UsuarioRepository
    repository = UsuarioRepository(db)
    return UsuarioService(repository)


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
    elif isinstance(e, DuplicateException):
        # Tests expect duplicate username to return 400 Bad Request
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
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


@router.post("/", response_model=Usuario, status_code=status.HTTP_201_CREATED)
async def crear_usuario(
    payload: UsuarioCreate,
    service: UsuarioService = Depends(get_usuario_service),
):
    """
    Create a new usuario (public endpoint - CLIENT ONLY).
    
    This endpoint is public and does not require authentication.
    IMPORTANT: Only allows creating 'cliente' role users.
    To create veterinarios or admins, use the /usuarios/admin/create endpoint.
    
    Args:
        payload: Usuario creation data
        service: Injected UsuarioService
        
    Returns:
        Created usuario
    """
    try:
        # SECURITY: Force role to be 'cliente' for public registration
        # The service defaults to 'cliente' if no role is provided
        return service.create_usuario(payload)
    except AppException as e:
        raise handle_service_exception(e)
    except Exception as e:
        logger.error(f"Error creating usuario: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear usuario"
        )


@router.post("/admin/create", response_model=Usuario, status_code=status.HTTP_201_CREATED)
async def crear_usuario_privilegiado(
    payload: UsuarioPrivilegedCreate,
    current_user=Depends(require_roles("admin")),
    service: UsuarioService = Depends(get_usuario_service),
):
    """
    Create a new usuario with privileged role (ADMIN ONLY).
    
    This endpoint allows admins to create veterinarios or other admins.
    Regular clients should use the public /usuarios/ endpoint.
    
    Args:
        payload: Usuario creation data with role
        current_user: Current authenticated admin user
        service: Injected UsuarioService
        
    Returns:
        Created usuario
    """
    try:
        # Validate that only veterinario or admin roles can be created here
        if payload.role not in [Role.veterinario, Role.admin]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este endpoint solo permite crear usuarios con rol 'veterinario' o 'admin'. Para clientes use /usuarios/"
            )
        
        # Convert to UsuarioCreate for service layer (without role field)
        usuario_data = UsuarioCreate(
            username=payload.username,
            nombre=payload.nombre,
            edad=payload.edad,
            telefono=payload.telefono,
            password=payload.password
        )
        # Pass the role explicitly to the service
        return service.create_usuario(usuario_data, role=payload.role.value)
    except AppException as e:
        raise handle_service_exception(e)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating privileged usuario: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear usuario privilegiado"
        )


@router.get("/")
async def listar_usuarios(
    page: int = Query(0, ge=0, description="Número de página (0-indexed)"),
    page_size: int = Query(
        settings.default_page_size,
        ge=1,
        le=settings.max_page_size,
        description="Tamaño de página"
    ),
    role: Optional[Role] = Query(None, description="Filtrar por rol"),
    include_deleted: bool = Query(False, description="Incluir usuarios eliminados"),
    current_user=Depends(require_roles("admin")),
    service: UsuarioService = Depends(get_usuario_service),
):
    """
    List usuarios with pagination (ADMIN ONLY).
    
    Requires admin authentication. Supports filtering by role.
    
    Args:
        page: Page number (0-indexed)
        page_size: Items per page
        role: Optional role filter
        include_deleted: Include soft-deleted usuarios
        current_user: Current authenticated admin user
        service: Injected UsuarioService
        
    Returns:
        Paginated list of usuarios
    """
    try:
        role_str = role.value if role else None
        items, total = service.get_usuarios(
            page=page,
            page_size=page_size,
            role=role_str,
            include_deleted=include_deleted
        )
        return create_paginated_response(items, page, page_size, total)
    except AppException as e:
        raise handle_service_exception(e)
    except Exception as e:
        logger.error(f"Error listing usuarios: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al listar usuarios"
        )


@router.get("/veterinarios")
async def listar_veterinarios(
    current_user=Depends(get_current_user_dep),
    service: UsuarioService = Depends(get_usuario_service),
):
    """
    Get a simple list of all veterinarios (for dropdowns).
    
    Args:
        current_user: Current authenticated user
        service: Injected UsuarioService
        
    Returns:
        List of veterinarios with username and nombre
    """
    try:
        items, _ = service.get_usuarios(
            page=0,
            page_size=1000,
            role="veterinario",
            include_deleted=False
        )
        # Return simplified list for dropdowns
        # items es una lista de diccionarios, no objetos
        return [
            {
                "username": vet["username"],
                "nombre": vet["nombre"] if vet.get("nombre") else vet["username"],
                "telefono": vet.get("telefono")
            }
            for vet in items
        ]
    except AppException as e:
        raise handle_service_exception(e)
    except Exception as e:
        logger.error(f"Error listing veterinarios: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al listar veterinarios"
        )


@router.get("/me", response_model=Usuario)
async def obtener_mi_usuario(
    current_user=Depends(get_current_user_dep),
    service: UsuarioService = Depends(get_usuario_service),
):
    """
    Get the authenticated usuario's data.
    
    Args:
        current_user: Current authenticated user
        service: Injected UsuarioService
        
    Returns:
        Current usuario data
    """
    try:
        return service.get_usuario(current_user.id)
    except AppException as e:
        raise handle_service_exception(e)
    except Exception as e:
        logger.error(f"Error getting current usuario: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener usuario actual"
        )


@router.get("/{usuario_id}", response_model=Usuario)
async def obtener_usuario(
    usuario_id: str,
    current_user=Depends(require_roles("admin")),
    service: UsuarioService = Depends(get_usuario_service),
):
    """
    Get a usuario by ID (ADMIN ONLY).
    
    Requires admin authentication.
    
    Args:
        usuario_id: Usuario ID
        current_user: Current authenticated admin user
        service: Injected UsuarioService
        
    Returns:
        Usuario data
    """
    try:
        return service.get_usuario(usuario_id)
    except AppException as e:
        raise handle_service_exception(e)
    except Exception as e:
        logger.error(f"Error getting usuario {usuario_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener usuario"
        )


@router.put("/me", response_model=UsuarioUpdateResponse)
async def actualizar_mi_usuario(
    payload: UsuarioUpdateRequest,
    current_user=Depends(get_current_user_dep),
    service: UsuarioService = Depends(get_usuario_service),
):
    """
    Update the authenticated usuario's data.
    
    Allows updating username, nombre, edad, and telefono.
    
    Args:
        payload: Update data
        current_user: Current authenticated user
        service: Injected UsuarioService
        
    Returns:
        Updated usuario fields
    """
    try:
        # The service requires the current_user as third parameter
        return service.update_usuario(current_user.id, payload, current_user)
    except AppException as e:
        raise handle_service_exception(e)
    except Exception as e:
        logger.error(f"Error updating current usuario: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar usuario"
        )


@router.delete("/me")
async def eliminar_mi_usuario(
    current_user=Depends(get_current_user_dep),
    service: UsuarioService = Depends(get_usuario_service),
):
    """
    Delete the authenticated usuario's account (soft delete).
    
    The usuario is marked as deleted but not removed from the database.
    
    Args:
        current_user: Current authenticated user
        service: Injected UsuarioService
        
    Returns:
        Delete confirmation
    """
    try:
        service.delete_usuario(current_user.id)
        return create_delete_response(
            message="Usuario eliminado correctamente",
            deleted_id=current_user.id,
            soft_delete=True
        )
    except AppException as e:
        raise handle_service_exception(e)
    except Exception as e:
        logger.error(f"Error deleting current usuario: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar usuario"
        )


@router.post("/me/restore")
async def restaurar_mi_usuario(
    current_user=Depends(get_current_user_dep),
    service: UsuarioService = Depends(get_usuario_service),
):
    """
    Restore the authenticated usuario's account.
    
    Only works if the usuario was soft-deleted.
    
    Args:
        current_user: Current authenticated user
        service: Injected UsuarioService
        
    Returns:
        Restore confirmation
    """
    try:
        service.restore_usuario(current_user.id)
        return {
            "success": True,
            "message": "Usuario restaurado correctamente",
            "id_usuario": current_user.id,
            "timestamp": datetime.utcnow()
        }
    except AppException as e:
        raise handle_service_exception(e)
    except Exception as e:
        logger.error(f"Error restoring current usuario: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al restaurar usuario"
        )


@router.delete("/{usuario_id}")
async def eliminar_usuario_admin(
    usuario_id: str,
    current_user=Depends(require_roles("admin")),
    service: UsuarioService = Depends(get_usuario_service),
):
    """
    Delete a user by ID (ADMIN ONLY - Soft Delete).
    
    This endpoint allows admins to soft-delete any user account.
    The user is marked as deleted but not removed from the database.
    
    Args:
        usuario_id: ID of the user to delete
        current_user: Current authenticated admin user
        service: Injected UsuarioService
        
    Returns:
        Delete confirmation
    """
    try:
        # Prevent admin from deleting their own account via this endpoint
        if usuario_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No puedes eliminar tu propia cuenta desde este endpoint. Usa /usuarios/me en su lugar."
            )
        
        # Verify user exists
        usuario = service.get_usuario(usuario_id)
        if not usuario:
            raise NotFoundException(f"Usuario con ID {usuario_id} no encontrado")
        
        # Delete user
        service.delete_usuario(usuario_id)
        return create_delete_response(
            message=f"Usuario {usuario.username} eliminado correctamente",
            deleted_id=usuario_id,
            soft_delete=True
        )
    except AppException as e:
        raise handle_service_exception(e)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting usuario {usuario_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar usuario"
        )


@router.post("/{usuario_id}/restore")
async def restaurar_usuario_admin(
    usuario_id: str,
    current_user=Depends(require_roles("admin")),
    service: UsuarioService = Depends(get_usuario_service),
):
    """
    Restore a deleted user by ID (ADMIN ONLY).
    
    This endpoint allows admins to restore any soft-deleted user account.
    
    Args:
        usuario_id: ID of the user to restore
        current_user: Current authenticated admin user
        service: Injected UsuarioService
        
    Returns:
        Restore confirmation
    """
    try:
        # Verify user exists
        usuario = service.get_usuario(usuario_id)
        if not usuario:
            raise NotFoundException(f"Usuario con ID {usuario_id} no encontrado")
        
        # Restore user
        service.restore_usuario(usuario_id)
        return {
            "success": True,
            "message": f"Usuario {usuario.username} restaurado correctamente",
            "id_usuario": usuario_id,
            "timestamp": datetime.utcnow()
        }
    except AppException as e:
        raise handle_service_exception(e)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restoring usuario {usuario_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al restaurar usuario"
        )


@router.patch("/{usuario_id}/role", response_model=Usuario)
async def cambiar_rol_usuario(
    usuario_id: str,
    payload: UsuarioRoleUpdate,
    current_user=Depends(require_roles("admin")),
    service: UsuarioService = Depends(get_usuario_service),
):
    """
    Change a user's role (ADMIN ONLY).
    
    This endpoint allows admins to change any user's role.
    
    Args:
        usuario_id: ID of the user whose role will be changed
        payload: New role data
        current_user: Current authenticated admin user
        service: Injected UsuarioService
        
    Returns:
        Updated usuario with new role
    """
    try:
        # Prevent admin from changing their own role
        if usuario_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No puedes cambiar tu propio rol. Pide a otro administrador que lo haga."
            )
        
        # Get the usuario ORM object using the repository
        usuario_orm = service.repository.get_by_id(usuario_id)
        if not usuario_orm:
            raise NotFoundException(f"Usuario con ID {usuario_id} no encontrado")
        
        # Update role
        usuario_orm.role = payload.role.value
        service.repository.commit()
        service.repository.db.refresh(usuario_orm)
        
        # Convert to response model
        return Usuario(
            id_usuario=usuario_orm.id,
            username=usuario_orm.username,
            nombre=usuario_orm.nombre,
            edad=usuario_orm.edad,
            telefono=usuario_orm.telefono,
            role=Role(usuario_orm.role),
            fecha_creacion=usuario_orm.fecha_creacion,
            is_deleted=usuario_orm.is_deleted
        )
    except AppException as e:
        raise handle_service_exception(e)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing usuario role: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al cambiar rol de usuario"
        )
