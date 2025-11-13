""" Utilidades principales y componentes compartidos para la aplicación.

Este paquete contiene:

- Excepciones personalizadas
- Utilidades de seguridad
- Funciones auxiliares de paginación
- Utilidades de validación
"""

from .exceptions import (
    AppException,
    BusinessException,
    NotFoundException,
    UnauthorizedException,
    ValidationException,
    DuplicateException,
    ForbiddenException,
    DatabaseException,
)
from .security import (
    validate_uuid,
    check_ownership,
    check_ownership_by_username,
    require_role,
)
from .pagination import (
    PaginationParams,
    PaginationMeta,
    PaginatedResponse,
    calculate_pagination_meta,
    create_paginated_response,
    calculate_skip,
)
from .utils import (
    enum_to_value,
    normalize_stored_enum,
    uuid_to_str,
)

__all__ = [
    # Excepciones
    "AppException",
    "BusinessException",
    "NotFoundException",
    "UnauthorizedException",
    "ValidationException",
    "DuplicateException",
    "ForbiddenException",
    "DatabaseException",
    # seguridad
    "validate_uuid",
    "check_ownership",
    "check_ownership_by_username",
    "require_role",
    # paginacion
    "PaginationParams",
    "PaginationMeta",
    "PaginatedResponse",
    "calculate_pagination_meta",
    "create_paginated_response",
    "calculate_skip",
    # utils
    "enum_to_value",
    "normalize_stored_enum",
    "uuid_to_str",
]
