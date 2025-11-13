"""
Repositorio base con operaciones CRUD comunes:
Este repositorio genérico proporciona operaciones de base de datos estándar
que se pueden reutilizar en todos los repositorios de entidades
"""

from typing import TypeVar, Generic, List, Optional, Type, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
from datetime import datetime
import logging

from core.exceptions import NotFoundException, DatabaseException
from database.db import soft_delete, restore_deleted, set_audit_fields

logger = logging.getLogger(__name__)

T = TypeVar('T')


class BaseRepository(Generic[T]):
    """
    Repositorio genérico proporciona operaciones CRUD estándar
    
    Esta clase debe ser heredada por repositorios de entidades específicos.
    """
    
    def __init__(self, db: Session, model_class: Type[T]):
        """
        Inicializa el repositorio.
        
        Args:
            db: Sesión SQLAlchemy
            model_class: Clase del modelo ORM para este repositorio
        """
        self.db = db
        self.model_class = model_class
    
    def get_by_id(self, id: str) -> Optional[T]:
        """
        Obtiene una entidad por su ID.
        
        Args:
            id: ID de la entidad
            
        Returns:
            The entity or None if not found
        """
        try:
            return self.db.get(self.model_class, str(id))
        except Exception as e:
            logger.error(f"Error getting {self.model_class.__name__} by id {id}: {e}")
            raise DatabaseException(f"Error al obtener {self.model_class.__name__}")
    
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
        entity = self.get_by_id(id)
        if not entity:
            raise NotFoundException(
                resource=self.model_class.__name__,
                identifier=str(id)
            )
        return entity
    
    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False,
        order_by: Optional[str] = None,
        order_desc: bool = False
    ) -> List[T]:
        """
        Obtiene todas las entidades con paginación.
        
        Args:
            skip: Número de registros a saltar
            limit: Número máximo de registros a devolver
            include_deleted: Si se incluyen los registros eliminados
            order_by: Field name to order by
            order_desc: Whether to order descending
            
        Returns:
            List of entities
        """
        try:
            query = self.db.query(self.model_class)
            
            # Filter soft-deleted records
            if not include_deleted and hasattr(self.model_class, 'is_deleted'):
                query = query.filter(self.model_class.is_deleted == False)
            
            # Apply ordering
            if order_by and hasattr(self.model_class, order_by):
                order_field = getattr(self.model_class, order_by)
                if order_desc:
                    query = query.order_by(desc(order_field))
                else:
                    query = query.order_by(asc(order_field))
            
            return query.offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting all {self.model_class.__name__}: {e}")
            raise DatabaseException(f"Error al listar {self.model_class.__name__}")
    
    def count(self, include_deleted: bool = False, **filters) -> int:
        """
        Cuenta las entidades que coinciden con los filtros.
        
        Args:
            include_deleted: Whether to include soft-deleted records
            **filters: Additional filters as keyword arguments
            
        Returns:
            Count of matching entities
        """
        try:
            query = self.db.query(self.model_class)
            
            # Filter soft-deleted records
            if not include_deleted and hasattr(self.model_class, 'is_deleted'):
                query = query.filter(self.model_class.is_deleted == False)
            
            # Apply additional filters
            for field, value in filters.items():
                if hasattr(self.model_class, field) and value is not None:
                    query = query.filter(getattr(self.model_class, field) == value)
            
            return query.count()
        except Exception as e:
            logger.error(f"Error counting {self.model_class.__name__}: {e}")
            raise DatabaseException(f"Error al contar {self.model_class.__name__}")
    
    def create(self, entity: T, user_id: Optional[str] = None) -> T:
        """
        Crea una nueva entidad.
        
        Args:
            entity: La entidad a crear
            user_id: ID del usuario que crea la entidad (para auditoría)
            
        Returns:
            The created entity
        """
        try:
            # Set audit fields
            if user_id:
                set_audit_fields(entity, user_id, creating=True)
            
            self.db.add(entity)
            self.db.flush()
            self.db.refresh(entity)
            return entity
        except Exception as e:
            logger.error(f"Error creating {self.model_class.__name__}: {e}")
            self.db.rollback()
            raise DatabaseException(f"Error al crear {self.model_class.__name__}")
    
    def update(self, entity: T, user_id: Optional[str] = None) -> T:
        """
        Actualiza una entidad existente.
        
        Args:
            entity: La entidad a actualizar
            user_id: ID del usuario que actualiza la entidad (para auditoría)
            
        Returns:
            The updated entity
        """
        try:
            # Set audit fields
            if user_id:
                set_audit_fields(entity, user_id, creating=False)
            
            self.db.add(entity)
            self.db.flush()
            self.db.refresh(entity)
            return entity
        except Exception as e:
            logger.error(f"Error updating {self.model_class.__name__}: {e}")
            self.db.rollback()
            raise DatabaseException(f"Error al actualizar {self.model_class.__name__}")
    
    def delete(self, entity: T, user_id: Optional[str] = None, hard: bool = False) -> None:
        """
        Elimina una entidad (eliminación suave por defecto).
        
        Args:
            entity: La entidad a eliminar
            user_id: ID del usuario que elimina la entidad
            hard: Si True, realizar eliminación dura; de lo contrario, eliminación suave
        """
        try:
            if hard:
                self.db.delete(entity)
            else:
                soft_delete(entity, user_id)
                self.db.add(entity)
            
            self.db.flush()
        except Exception as e:
            logger.error(f"Error deleting {self.model_class.__name__}: {e}")
            self.db.rollback()
            raise DatabaseException(f"Error al eliminar {self.model_class.__name__}")
    
    def restore(self, entity: T, user_id: Optional[str] = None) -> T:
        """
        Restaura una entidad eliminada (eliminación suave).
        
        Args:   
            entity: La entidad a restaurar
            user_id: ID del usuario que restaura la entidad
            
        Returns:
            La entidad restaurada
        """
        try:
            restore_deleted(entity, user_id)
            self.db.add(entity)
            self.db.flush()
            self.db.refresh(entity)
            return entity
        except Exception as e:
            logger.error(f"Error restoring {self.model_class.__name__}: {e}")
            self.db.rollback()
            raise DatabaseException(f"Error al restaurar {self.model_class.__name__}")
    
    def exists(self, id: str) -> bool:
        """
        Verifica si una entidad existe por su ID.
        
        Args:
            id: ID de la entidad
            
        Returns:
            True si la entidad existe, False en caso contrario
        """
        try:
            return self.get_by_id(id) is not None
        except Exception:
            return False
    
    def commit(self) -> None:
        """Realiza el commit de la transacción actual."""
        try:
            self.db.commit()
        except Exception as e:
            logger.error(f"Error committing transaction: {e}")
            self.db.rollback()
            raise DatabaseException("Error al guardar cambios en la base de datos")
    
    def rollback(self) -> None:
        """Realiza el rollback de la transacción actual."""
        self.db.rollback()
    
    def refresh(self, entity: T) -> T:
        """
        Refresca una entidad desde la base de datos.
        
        Args:
            entity: La entidad a refrescar
            
        Returns:
            La entidad refrescada
        """
        self.db.refresh(entity)
        return entity
