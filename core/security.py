"""
Utilidades de seguridad para validación y permisos.
"""

from typing import Optional
from uuid import UUID
from core.exceptions import ValidationException, ForbiddenException


def validate_uuid(value: str, field_name: str = "id") -> str:
    """
    Valida que una cadena sea un UUID válido.
    
    Args:
        value: Cadena a validar
        field_name: Nombre del campo para mensajes de error
        
    Returns:
        El UUID validado como cadena
        
    Raises:
        ValidationException: Si el valor no es un UUID válido
    """
    try:
        UUID(str(value))
        return str(value)
    except (ValueError, AttributeError, TypeError):
        raise ValidationException(
            message=f"{field_name} debe ser un UUID válido",
            field=field_name,
            details={"value": str(value)}
        )


def check_ownership(
    user_id: str,
    owner_id: str,
    user_role: str,
    resource_name: str = "recurso"
) -> None:
    """
    Verifica si un usuario tiene el permiso de acceder a un recurso o es un administrador.
    
    Args:
        user_id: ID del usuario actual
        owner_id: ID del propietario del recurso
        user_role: Rol del usuario actual
        resource_name: Nombre del recurso para mensajes de error
        
    Raises:
        ForbiddenException: Si el usuario no es el propietario y no es un administrador
    """
    if user_role != "admin" and user_id != owner_id:
        raise ForbiddenException(
            message=f"No autorizado para acceder a este {resource_name}",
            details={
                "resource": resource_name,
                "user_id": user_id,
                "required_owner_id": owner_id
            }
        )


def check_ownership_by_username(
    current_username: str,
    owner_username: str,
    user_role: str,
    resource_name: str = "recurso"
) -> None:
    """
    Check if a user owns a resource by username or is an admin.
    
    Args:
        current_username: Username of the current user
        owner_username: Username of the resource owner
        user_role: Role of the current user
        resource_name: Name of the resource for error messages
        
    Raises:
        ForbiddenException: If user is not the owner and not an admin
    """
    if user_role != "admin" and current_username != owner_username:
        raise ForbiddenException(
            message=f"No autorizado para acceder a este {resource_name}",
            details={
                "resource": resource_name,
                "current_user": current_username,
                "required_owner": owner_username
            }
        )


def require_role(user_role: str, *allowed_roles: str) -> None:
    """
    Check if user has one of the allowed roles.
    
    Args:
        user_role: Role of the current user
        allowed_roles: Tuple of allowed roles
        
    Raises:
        ForbiddenException: If user role is not in allowed roles
    """
    if user_role not in allowed_roles:
        raise ForbiddenException(
            message="Permisos insuficientes",
            details={
                "user_role": user_role,
                "required_roles": list(allowed_roles)
            }
        )
