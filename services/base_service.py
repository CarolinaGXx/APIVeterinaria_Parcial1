"""
Servicio base con operaciones de lógica de negocio comunes.
Esta clase proporciona una base para las clases de servicio que implementan
la lógica de negocio y coordinan las operaciones del repositorio.
"""

from typing import TypeVar, Generic, List, Optional, Type
import logging

from repositories.base_repository import BaseRepository
from core.exceptions import (
    NotFoundException,
    ValidationException,
    BusinessException,
)
from core.pagination import calculate_skip

logger = logging.getLogger(__name__)

# Type variables
T = TypeVar('T')  # ORM Model
R = TypeVar('R')  # Repository


class BaseService(Generic[T, R]):
    """
    Servicio base que proporciona operaciones lógicas de negocio comunes.
    Esta clase debe ser heredada por servicios de entidades específicas.
    """
    
    def __init__(self, repository: R):
        """
        Inicializa el servicio.
        
        Args:
            repository: The repository instance for data access
        """
        self.repository = repository
    
    def get_by_id(self, id: str) -> Optional[T]:
        """
        Obtiene una entidad por su ID.
        
        Args:
            id: ID de la entidad
            
        Returns:
            The entity or None if not found
        """
        return self.repository.get_by_id(id)
    
    def get_by_id_or_fail(self, id: str) -> T:
        """
        Obtiene una entidad por su ID o lanza una excepción si no se encuentra.
        
        Args:
            id: ID de la entidad
            
        Returns:
            The entity
            
        Raises:
            NotFoundException: If entity is not found
        """
        return self.repository.get_by_id_or_fail(id)
    
    def get_all(
        self,
        page: int = 0,
        page_size: int = 50,
        include_deleted: bool = False,
        order_by: Optional[str] = None,
        order_desc: bool = False
    ) -> tuple[List[T], int]:
        """
        Obtiene todas las entidades con paginación.
        
        Args:
            page: Número de página (0-indexed)
            page_size: Items por página
            include_deleted: Si se deben incluir los registros eliminados temporalmente
            order_by: Field name to order by
            order_desc: Si se debe ordenar en orden descendente
            
        Returns:
            Tuple of (list of entities, total count)
        """
        skip = calculate_skip(page, page_size)
        
        items = self.repository.get_all(
            skip=skip,
            limit=page_size,
            include_deleted=include_deleted,
            order_by=order_by,
            order_desc=order_desc
        )
        
        total_count = self.repository.count(include_deleted=include_deleted)
        
        return items, total_count
    
    def exists(self, id: str) -> bool:
        """
        Verifica si una entidad existe por su ID.
        
        Args:
            id: ID de la entidad
            
        Returns:
            True if entity exists, False otherwise
        """
        return self.repository.exists(id)
    
    def delete(
        self,
        id: str,
        user_id: Optional[str] = None,
        hard: bool = False
    ) -> None:
        """
        Elimina una entidad.
        
        Args:
            id: ID de la entidad
            user_id: ID del usuario que realiza la eliminación
            hard: Si True, realiza una eliminación física; de lo contrario, una eliminación suave
            
        Raises:
            NotFoundException: If entity is not found
        """
        entity = self.get_by_id_or_fail(id)
        
        # Check if already deleted (for soft delete)
        if not hard and hasattr(entity, 'is_deleted') and entity.is_deleted:
            raise BusinessException("El registro ya está eliminado")
        
        self.repository.delete(entity, user_id=user_id, hard=hard)
        self.repository.commit()
    
    def restore(self, id: str, user_id: Optional[str] = None) -> T:
        """
        Restaura una entidad eliminada temporalmente.
        
        Args:
            id: ID de la entidad
            user_id: ID del usuario que realiza la restauración
            
        Returns:
            The restored entity
            
        Raises:
            NotFoundException: If entity is not found
            BusinessException: If entity is not deleted
        """
        entity = self.get_by_id_or_fail(id)
        
        # Check if actually deleted
        if not hasattr(entity, 'is_deleted') or not entity.is_deleted:
            raise BusinessException("El registro no está eliminado")
        
        restored = self.repository.restore(entity, user_id=user_id)
        self.repository.commit()
        
        return restored
    
    def validate_not_deleted(self, entity: T) -> None:
        """
        Valida que una entidad no esté eliminada temporalmente.
        
        Args:
            entity: Entidad a verificar
            
        Raises:
            BusinessException: If entity is deleted
        """
        if hasattr(entity, 'is_deleted') and entity.is_deleted:
            raise BusinessException("El registro está eliminado y no puede ser utilizado")
