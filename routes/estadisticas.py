"""
Rutas para endpoints de estadísticas del dashboard.

Proporciona estadísticas personalizadas según el rol del usuario autenticado.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from auth import get_current_user_dep
from dependencies import get_estadistica_service
from services.estadistica_service import EstadisticaService
from models.estadisticas import EstadisticasResponse
import logging

logger = logging.getLogger(__name__)

# Router con prefijo /estadisticas
router = APIRouter(prefix="/estadisticas", tags=["estadisticas"])


@router.get("/dashboard", response_model=EstadisticasResponse)
async def obtener_estadisticas_dashboard(
    current_user=Depends(get_current_user_dep),
    service: EstadisticaService = Depends(get_estadistica_service),
):
    """
    Obtener estadísticas del dashboard según el rol del usuario.
    
    Retorna diferentes conjuntos de estadísticas basados en el rol:
    - **Cliente**: Estadísticas de sus mascotas, citas y facturas
    - **Veterinario**: Estadísticas de citas asignadas, vacunas aplicadas, facturas emitidas
    - **Admin**: Estadísticas globales del sistema
    
    Args:
        current_user: Usuario autenticado
        service: Servicio de estadísticas inyectado
        
    Returns:
        EstadisticasResponse con datos según el rol
        
    Raises:
        HTTPException: Si ocurre un error al calcular estadísticas
    """
    try:
        data = service.get_estadisticas(current_user)
        
        return EstadisticasResponse(
            success=True,
            role=current_user.role,
            data=data
        )
    except Exception as e:
        logger.error(f"Error getting dashboard statistics for {current_user.username}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener estadísticas del dashboard"
        )
