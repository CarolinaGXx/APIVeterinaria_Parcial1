"""
Repositorio para la entidad Cita.
Gestiona todas las operaciones de base de datos relacionadas con las citas (preguntas).
"""

from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from repositories.base_repository import BaseRepository
from database.models import CitaORM, MascotaORM
from core.exceptions import DatabaseException
import logging

logger = logging.getLogger(__name__)


class CitaRepository(BaseRepository[CitaORM]):
    """Repositorio para la entidad Cita."""
    
    def __init__(self, db: Session):
        """
        Inicializa el repositorio de citas.
        
        Args:
            db: Sesión de SQLAlchemy
        """
        super().__init__(db, CitaORM)
    
    def find_by_mascota(
        self,
        id_mascota: str,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> List[CitaORM]:
        """
        Busca todas las citas para una mascota específica.
        
        Args:
            id_mascota: ID de la mascota
            skip: Número de registros a saltar
            limit: Número máximo de registros a devolver
            include_deleted: incluir los registros eliminados temporalmente
            
        Returns:
            lista de citas
        """
        try:
            query = self.db.query(CitaORM).filter(
                CitaORM.id_mascota == id_mascota
            )
            
            if not include_deleted:
                query = query.filter(CitaORM.is_deleted == False)
            
            # Order by: activas primero (por fecha ascendente = más cercanas primero),
            # luego canceladas (por fecha descendente = más recientes primero)
            query = query.order_by(CitaORM.is_deleted.asc(), CitaORM.fecha.asc())
            
            return query.offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error finding citas by mascota {id_mascota}: {e}")
            raise DatabaseException("Error al buscar citas por mascota")
    
    def find_by_veterinario(
        self,
        veterinario: str,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> List[CitaORM]:
        """
        Busca todas las citas para un veterinario específico.
        
        Args:
            veterinario: nombre de usuario del veterinario
            skip: número de registros a saltar
            limit: número máximo de registros a devolver
            include_deleted: incluir los registros eliminados temporalmente
            
        Returns:
            lista de citas
        """
        try:
            query = self.db.query(CitaORM).filter(
                CitaORM.veterinario.ilike(f"%{veterinario}%")
            )
            
            if not include_deleted:
                query = query.filter(CitaORM.is_deleted == False)
            
            # Order by: activas primero (más cercanas), canceladas al final
            query = query.order_by(CitaORM.is_deleted.asc(), CitaORM.fecha.asc())
            
            return query.offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error finding citas by veterinario {veterinario}: {e}")
            raise DatabaseException("Error al buscar citas por veterinario")
    
    def find_by_estado(
        self,
        estado: str,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> List[CitaORM]:
        """
        Busca todas las citas con un estado específico.
        
        Args:
            estado: Estado (pendiente, completada, cancelada)
            skip: número de registros a saltar
            limit: número máximo de registros a devolver
            include_deleted: incluir los registros eliminados temporalmente
            
        Returns:
            lista de citas
        """
        try:
            query = self.db.query(CitaORM).filter(
                CitaORM.estado == estado
            )
            
            if not include_deleted:
                query = query.filter(CitaORM.is_deleted == False)
            
            # Order by: activas primero (más cercanas), canceladas al final
            query = query.order_by(CitaORM.is_deleted.asc(), CitaORM.fecha.asc())
            
            return query.offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error finding citas by estado {estado}: {e}")
            raise DatabaseException("Error al buscar citas por estado")
    
    def find_by_propietario(
        self,
        propietario_username: str,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> List[CitaORM]:
        """
        Busca todas las citas para mascotas propiedad de un usuario específico.
        
        Args:
            propietario_username: nombre de usuario del propietario de la mascota
            skip: número de registros a saltar
            limit: número máximo de registros a devolver
            include_deleted: incluir los registros eliminados temporalmente
            
        Returns:
            lista de citas
        """
        try:
            query = self.db.query(CitaORM).join(
                MascotaORM, CitaORM.id_mascota == MascotaORM.id
            ).filter(
                MascotaORM.propietario == propietario_username
            )
            
            if not include_deleted:
                query = query.filter(CitaORM.is_deleted == False)
            
            # Order by: activas primero (más cercanas), canceladas al final
            query = query.order_by(CitaORM.is_deleted.asc(), CitaORM.fecha.asc())
            
            return query.offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error finding citas by propietario {propietario_username}: {e}")
            raise DatabaseException("Error al buscar citas por propietario")
    
    def find_by_veterinario_or_propietario(
        self,
        username: str,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> List[CitaORM]:
        """
        Busca todas las citas donde el usuario es el veterinario o el propietario de la mascota.
        
        Args:
            username: nombre de usuario a buscar
            skip: número de registros a saltar
            limit: número máximo de registros a devolver
            include_deleted: incluir los registros eliminados temporalmente
            
        Returns:
            lista de citas
        """
        try:
            query = self.db.query(CitaORM).join(
                MascotaORM, CitaORM.id_mascota == MascotaORM.id
            ).filter(
                or_(
                    CitaORM.veterinario == username,
                    MascotaORM.propietario == username
                )
            )
            
            if not include_deleted:
                query = query.filter(CitaORM.is_deleted == False)
            
            # Order by: activas primero (más cercanas), canceladas al final
            query = query.order_by(CitaORM.is_deleted.asc(), CitaORM.fecha.asc())
            
            return query.offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error finding citas by veterinario or propietario {username}: {e}")
            raise DatabaseException("Error al buscar citas")
    
    def count_by_filters(
        self,
        estado: Optional[str] = None,
        veterinario: Optional[str] = None,
        propietario_username: Optional[str] = None,
        include_deleted: bool = False
    ) -> int:
        """
        Cuenta las citas que coinciden con los filtros dados.
        
        Args:
            estado: filtro opcional de estado
            veterinario: filtro opcional de veterinario
            propietario_username: filtro opcional de propietario
            include_deleted: incluir los registros eliminados temporalmente
            
        Returns:
            conteo de citas que coinciden con los filtros dados
        """
        try:
            query = self.db.query(CitaORM)
            
            if propietario_username:
                query = query.join(
                    MascotaORM, CitaORM.id_mascota == MascotaORM.id
                ).filter(
                    MascotaORM.propietario == propietario_username
                )
            
            if estado:
                query = query.filter(CitaORM.estado == estado)
            
            if veterinario:
                query = query.filter(CitaORM.veterinario.ilike(f"%{veterinario}%"))
            
            if not include_deleted:
                query = query.filter(CitaORM.is_deleted == False)
            
            return query.count()
        except Exception as e:
            logger.error(f"Error counting citas by filters: {e}")
            raise DatabaseException("Error al contar citas")
