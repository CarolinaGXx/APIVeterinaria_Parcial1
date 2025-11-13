"""
Excepciones personalizadas para la aplicación.

Estas excepciones proporcionan una forma estructurada de manejar errores de lógica de negocio
y mapearlos a códigos de estado HTTP apropiados en la capa de API.
"""

from typing import Optional, Any


class AppException(Exception):
    """Excepción base para todos los errores de la aplicación."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: Optional[dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class BusinessException(AppException):
    """Excepción para errores de lógica de negocio."""

    def __init__(
        self,
        message: str,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message=message, status_code=400, details=details)


class NotFoundException(AppException):
    """Excepción cuando un recurso no se encuentra."""

    def __init__(
        self,
        resource: str,
        identifier: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        message = f"{resource} no encontrado"
        if identifier:
            message += f": {identifier}"
        super().__init__(message=message, status_code=404, details=details)


class UnauthorizedException(AppException):
    """Excepción cuando la autenticación es requerida o falla."""

    def __init__(
        self,
        message: str = "No autenticado",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message=message, status_code=401, details=details)


class ForbiddenException(AppException):
    """Excepción cuando el usuario carece de permisos para realizar una acción."""

    def __init__(
        self,
        message: str = "No autorizado para realizar esta acción",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message=message, status_code=403, details=details)


class ValidationException(AppException):
    """Excepción para errores de validación."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        if field:
            details = details or {}
            details["field"] = field
        super().__init__(message=message, status_code=422, details=details)


class DuplicateException(AppException):
    """Excepción cuando se intenta crear un recurso duplicado."""

    def __init__(
        self,
        resource: str,
        field: Optional[str] = None,
        value: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        #mensaje más descriptivo y compatible con tests que esperan la palabra 'existe'
        message = f"{resource} duplicado (ya existe)"
        if field and value:
            message += f": {field}='{value}'"
        #usamos 400 Bad Request por compatibilidad con la suite de tests y UX
        super().__init__(message=message, status_code=400, details=details)


class DatabaseException(AppException):
    """Excepción para errores de base de datos."""

    def __init__(
        self,
        message: str = "Error de base de datos",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message=message, status_code=500, details=details)
