"""
Repositorio para la entidad Usuario.
Gestiona todas las operaciones de base de datos relacionadas con los usuarios.
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from repositories.base_repository import BaseRepository
from database.models import UsuarioORM
from core.exceptions import DatabaseException
import logging

logger = logging.getLogger(__name__)


class UsuarioRepository(BaseRepository[UsuarioORM]):
    """Repositorio para la gestión de entidades de usuario."""
    
    def __init__(self, db: Session):
        """
        Inicializa el repositorio de usuarios.
        
        Args:
            db: SQLAlchemy session
        """
        super().__init__(db, UsuarioORM)
    
    def find_by_username(self, username: str) -> Optional[UsuarioORM]:
        """
        Busca un usuario por username.
        
        Args:
            username: para buscar usuario
            
        Returns:
            Usuario ORM instance or None si no se encuentra
        """
        try:
            return self.db.query(UsuarioORM).filter(
                UsuarioORM.username == username
            ).one_or_none()
        except Exception as e:
            logger.error(f"Error finding usuario by username {username}: {e}")
            raise DatabaseException("Error al buscar usuario por username")
    
    def find_by_role(
        self,
        role: str,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> List[UsuarioORM]:
        """
        Busca todos los usuarios con un rol específico.
        
        Args:
            role: Rol a filtrar (cliente, veterinario, admin)
            skip: Número de registros a omitir
            limit: Número máximo de registros a devolver
            include_deleted: Whether to include soft-deleted records
            
        Returns:
            Lista de usuarios con el rol especificado
        """
        try:
            query = self.db.query(UsuarioORM).filter(
                UsuarioORM.role == role
            )
            
            if not include_deleted:
                query = query.filter(UsuarioORM.is_deleted == False)
            
            query = query.order_by(UsuarioORM.username)
            
            return query.offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error finding usuarios by role {role}: {e}")
            raise DatabaseException("Error al buscar usuarios por rol")
    
    def count_by_role(
        self,
        role: str,
        include_deleted: bool = False
    ) -> int:
        """
        Cuenta los usuarios con un rol específico.
        
        Args:
            role: Rol a filtrar (cliente, veterinario, admin)
            include_deleted: Si se deben incluir los registros eliminados temporalmente
            
        Returns:
            Cantidad de usuarios con el rol especificado
        """
        try:
            query = self.db.query(UsuarioORM).filter(
                UsuarioORM.role == role
            )
            
            if not include_deleted:
                query = query.filter(UsuarioORM.is_deleted == False)
            
            return query.count()
        except Exception as e:
            logger.error(f"Error counting usuarios by role {role}: {e}")
            raise DatabaseException("Error al contar usuarios por rol")
    
    def exists_username(
        self,
        username: str,
        exclude_id: Optional[str] = None
    ) -> bool:
        """
        Verifica si un username ya existe.
        
        Args:
            username: Username a verificar
            exclude_id: ID de usuario opcional para excluir de la verificación (para actualizaciones)
            
        Returns:
            True si el username existe, False en caso contrario
        """
        try:
            query = self.db.query(UsuarioORM).filter(
                UsuarioORM.username == username
            )
            
            if exclude_id:
                query = query.filter(UsuarioORM.id != exclude_id)
            
            return query.first() is not None
        except Exception as e:
            logger.error(f"Error checking if username exists {username}: {e}")
            raise DatabaseException("Error al verificar username")
    
    def search_by_name(
        self,
        nombre: str,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> List[UsuarioORM]:
        """
        Busca usuarios por nombre (coincidencia parcial insensible a mayúsculas y minúsculas).
        
        Args:
            nombre: Nombre a buscar
            skip: Número de registros a omitir
            limit: Número máximo de registros a devolver
            include_deleted: Si se deben incluir los registros eliminados temporalmente
            
        Returns:
            Lista de usuarios que coinciden con la búsqueda
        """
        try:
            query = self.db.query(UsuarioORM).filter(
                UsuarioORM.nombre.ilike(f"%{nombre}%")
            )
            
            if not include_deleted:
                query = query.filter(UsuarioORM.is_deleted == False)
            
            query = query.order_by(UsuarioORM.nombre)
            
            return query.offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error searching usuarios by nombre {nombre}: {e}")
            raise DatabaseException("Error al buscar usuarios por nombre")
