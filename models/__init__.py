from .mascotas import Mascota, MascotaCreate, MascotaUpdate, TipoMascota
from .citas import Cita, CitaCreate, CitaUpdate, EstadoCita
from .vacunas import Vacuna, VacunaCreate, VacunaUpdate, TipoVacuna
from .facturas import Factura, FacturaCreate, FacturaUpdate, EstadoFactura, TipoServicio
from .usuarios import (
    Usuario, 
    UsuarioCreate, 
    Role, 
    UsuarioUpdateResponse, 
    UsuarioUpdateRequest,
    UsuarioPrivilegedCreate,
    UsuarioRoleUpdate
)
from .recetas import Receta, RecetaCreate, RecetaSummary, RecetaUpdate
from .estadisticas import (
    EstadisticasCliente,
    EstadisticasVeterinario,
    EstadisticasAdmin,
    EstadisticasResponse
)
from .common import (
    SuccessResponse,
    ErrorResponse,
    DeleteResponse,
    PaginatedResponse,
    PaginationMeta,
    HealthCheckResponse,
    create_success_response,
    create_error_response,
    create_delete_response,
    create_paginated_response
)

__all__ = [
    # Mascotas
    "Mascota", "MascotaCreate", "MascotaUpdate", "TipoMascota",
    # Citas
    "Cita", "CitaCreate", "CitaUpdate", "EstadoCita",
    # Vacunas
    "Vacuna", "VacunaCreate", "VacunaUpdate", "TipoVacuna",
    # Facturas
    "Factura", "FacturaCreate", "FacturaUpdate", "EstadoFactura", "TipoServicio",
    # Usuarios
    "Usuario", "UsuarioCreate", "Role", "UsuarioUpdateResponse", "UsuarioUpdateRequest",
    "UsuarioPrivilegedCreate", "UsuarioRoleUpdate",
    # Recetas
    "Receta", "RecetaCreate", "RecetaSummary", "RecetaUpdate",
    # Estadísticas
    "EstadisticasCliente", "EstadisticasVeterinario", "EstadisticasAdmin", "EstadisticasResponse",
    # Common responses
    "SuccessResponse", "ErrorResponse", "DeleteResponse", "PaginatedResponse",
    "PaginationMeta", "HealthCheckResponse",
    "create_success_response", "create_error_response", "create_delete_response",
    "create_paginated_response"
]