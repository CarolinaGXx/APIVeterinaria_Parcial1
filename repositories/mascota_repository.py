"""
Repositorio para la entidad Mascota.
Gestiona todas las operaciones de base de datos relacionadas con mascotas.
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from repositories.base_repository import BaseRepository
from database.models import MascotaORM
from core.exceptions import DatabaseException
import logging

logger = logging.getLogger(__name__)


class MascotaRepository(BaseRepository[MascotaORM]):
    """Repositorio para la entidad Mascota."""
    
    def __init__(self, db: Session):
        """
        Inicializa el repositorio de mascotas.
        
        Args:
            db: SQLAlchemy session
        """
        super().__init__(db, MascotaORM)
    
    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False,
        **kwargs
    ) -> List[MascotaORM]:
        """
        Obtiene todas las mascotas con ordenamiento personalizado.
        
        Sobrescribe el método base para aplicar el ordenamiento correcto:
        - Activas primero (is_deleted=False)
        - Luego eliminadas (is_deleted=True)
        - Ambos grupos alfabéticamente por nombre
        
        Args:
            omitir: Número de registros a omitir
            límite: Número máximo de registros a devolver
            incluir_eliminados: Indica si se deben incluir los registros eliminados lógicamente
            
        Returns:
            Lista de mascotas
        """
        try:
            query = self.db.query(MascotaORM)
            
            if not include_deleted:
                query = query.filter(MascotaORM.is_deleted == False)
            
            # Order by: activas primero, luego eliminadas (ambas alfabéticamente)
            query = query.order_by(MascotaORM.is_deleted.asc(), MascotaORM.nombre.asc())
            
            return query.offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting all mascotas: {e}")
            raise DatabaseException("Error al listar mascotas")
    
    def find_by_propietario(
        self,
        propietario_username: str,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> List[MascotaORM]:
        """
        Busca todas las mascotas pertenecientes a un propietario específico.
        
        Args:
            propietario_username: Nombre de usuario del propietario
            skip: Número de registros a omitir
            limit: Número máximo de registros a devolver
            include_deleted: Whether to include soft-deleted records
            
        Returns:
            List of mascotas
        """
        try:
            query = self.db.query(MascotaORM).filter(
                MascotaORM.propietario == propietario_username
            )
            
            if not include_deleted:
                query = query.filter(MascotaORM.is_deleted == False)
            
            # Order by: activas primero (is_deleted=False), luego eliminadas
            # Dentro de cada grupo, orden alfabético por nombre
            query = query.order_by(MascotaORM.is_deleted.asc(), MascotaORM.nombre.asc())
            
            return query.offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error finding mascotas by propietario {propietario_username}: {e}")
            raise DatabaseException("Error al buscar mascotas por propietario")
    
    def count_by_propietario(
        self,
        propietario_username: str,
        include_deleted: bool = False
    ) -> int:
        """
        Cuenta las mascotas pertenecientes a un propietario específico.
        
        Args:
            propietario_username: Nombre de usuario del propietario
            include_deleted: Whether to include soft-deleted records
            
        Returns:
            Count of mascotas
        """
        try:
            query = self.db.query(MascotaORM).filter(
                MascotaORM.propietario == propietario_username
            )
            
            if not include_deleted:
                query = query.filter(MascotaORM.is_deleted == False)
            
            return query.count()
        except Exception as e:
            logger.error(f"Error counting mascotas by propietario {propietario_username}: {e}")
            raise DatabaseException("Error al contar mascotas por propietario")
    
    def find_by_tipo(
        self,
        tipo: str,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> List[MascotaORM]:
        """
        Busca todas las mascotas de un tipo específico.
        
        Args:
            tipo: Tipo de mascota (perro, gato, ave, etc.)
            skip: Número de registros a omitir
            limit: Número máximo de registros a devolver
            include_deleted: Whether to include soft-deleted records
            
        Returns:
            List of mascotas
        """
        try:
            query = self.db.query(MascotaORM).filter(MascotaORM.tipo == tipo)
            
            if not include_deleted:
                query = query.filter(MascotaORM.is_deleted == False)
            
            # Order by: activas primero, luego eliminadas (ambas alfabéticamente)
            query = query.order_by(MascotaORM.is_deleted.asc(), MascotaORM.nombre.asc())
            
            return query.offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error finding mascotas by tipo {tipo}: {e}")
            raise DatabaseException("Error al buscar mascotas por tipo")
    
    def find_by_propietario_and_tipo(
        self,
        propietario_username: str,
        tipo: str,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> List[MascotaORM]:
        """
        Busca todas las mascotas de un propietario y tipo específico.
        
        Args:
            propietario_username: Nombre de usuario del propietario
            tipo: Tipo de mascota
            skip: Número de registros a omitir
            limit: Número máximo de registros a devolver
            include_deleted: Indica si se deben incluir los registros eliminados lógicamente
            
        Returns:
            Lista de mascotas
        """
        try:
            query = self.db.query(MascotaORM).filter(
                MascotaORM.propietario == propietario_username,
                MascotaORM.tipo == tipo
            )
            
            if not include_deleted:
                query = query.filter(MascotaORM.is_deleted == False)
            
            # Order by: activas primero, luego eliminadas (ambas alfabéticamente)
            query = query.order_by(MascotaORM.is_deleted.asc(), MascotaORM.nombre.asc())
            
            return query.offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error finding mascotas by propietario and tipo: {e}")
            raise DatabaseException("Error al buscar mascotas")
    
    def count_by_tipo(
        self,
        tipo: str,
        include_deleted: bool = False
    ) -> int:
        """
        Cuenta las mascotas de un tipo específico.
        
        Args:
            tipo: Tipo de mascota
            include_deleted: Indica si se deben incluir los registros eliminados lógicamente
            
        Returns:
            Count of mascotas
        """
        try:
            query = self.db.query(MascotaORM).filter(MascotaORM.tipo == tipo)
            
            if not include_deleted:
                query = query.filter(MascotaORM.is_deleted == False)
            
            return query.count()
        except Exception as e:
            logger.error(f"Error counting mascotas by tipo {tipo}: {e}")
            raise DatabaseException("Error al contar mascotas por tipo")
    
    def search_by_name(
        self,
        nombre: str,
        propietario_username: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> List[MascotaORM]:
        """
        Busca mascotas por nombre (coincidencia parcial insensible a mayúsculas y minúsculas).
        
        Args:
            nombre: Nombre a buscar
            propietario_username: Filtro opcional de propietario
            skip: Número de registros a omitir
            limit: Número máximo de registros a devolver
            include_deleted: Indica si se deben incluir los registros eliminados lógicamente
            
        Returns:
            Lista de mascotas que coinciden con la búsqueda
        """
        try:
            query = self.db.query(MascotaORM).filter(
                MascotaORM.nombre.ilike(f"%{nombre}%")
            )
            
            if propietario_username:
                query = query.filter(MascotaORM.propietario == propietario_username)
            
            if not include_deleted:
                query = query.filter(MascotaORM.is_deleted == False)
            
            query = query.order_by(MascotaORM.nombre)
            
            return query.offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error searching mascotas by nombre {nombre}: {e}")
            raise DatabaseException("Error al buscar mascotas por nombre")
    
    def search_mascotas(
        self,
        search_term: str,
        current_user_role: str,
        current_user_username: str,
        skip: int = 0,
        limit: int = 20,
        include_deleted: bool = False
    ) -> List[MascotaORM]:
        """
        Busca mascotas por nombre o propietario (para autocompletado).
        
        Busca en el nombre de la mascota y el nombre de usuario del propietario.
        Respetar los permisos basados en roles (los clientes solo pueden ver sus propias mascotas).
        
        Args:
            search_term: Search string (partial match)
            current_user_role: Role of current user
            current_user_username: Username of current user
            skip: Number of records to skip
            limit: Maximum results (default 20, optimized for autocomplete)
            include_deleted: Indica si se deben incluir los registros eliminados lógicamente
            
        Returns:
            Lista de mascotas que coinciden con el término de búsqueda
        """
        try:
            query = self.db.query(MascotaORM).filter(
                or_(
                    MascotaORM.nombre.ilike(f"%{search_term}%"),
                    MascotaORM.propietario.ilike(f"%{search_term}%")
                )
            )
            
            if current_user_role == "cliente":
                query = query.filter(MascotaORM.propietario == current_user_username)
                        
            if not include_deleted:
                query = query.filter(MascotaORM.is_deleted == False)
            
            query = query.order_by(
                MascotaORM.is_deleted.asc(),
                MascotaORM.nombre.asc()
            )
            
            return query.offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error searching mascotas with term '{search_term}': {e}")
            raise DatabaseException("Error al buscar mascotas")
