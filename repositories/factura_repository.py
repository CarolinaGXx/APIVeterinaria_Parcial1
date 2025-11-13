"""
Repositorio para la entidad Factura.
Gestiona todas las operaciones de base de datos relacionadas con las facturas.
"""

from typing import List, Optional
from sqlalchemy.orm import Session

from repositories.base_repository import BaseRepository
from database.models import FacturaORM, CitaORM, MascotaORM
from core.exceptions import DatabaseException
import logging

logger = logging.getLogger(__name__)


class FacturaRepository(BaseRepository[FacturaORM]):
    """Repositorio para la entidad Factura."""
    
    def __init__(self, db: Session):
        """
        Inicializa el repositorio de facturas.
        
        Args:
            db: SQLAlchemy session
        """
        super().__init__(db, FacturaORM)
    
    def find_by_cita(self, id_cita: str) -> Optional[FacturaORM]:
        """
        Busca una factura por el ID de la cita.
        
        Args:
            id_cita: ID de la cita
            
        Returns:
            Factura or None if not found
        """
        try:
            return self.db.query(FacturaORM).filter(
                FacturaORM.id_cita == id_cita
            ).one_or_none()
        except Exception as e:
            logger.error(f"Error finding factura by cita {id_cita}: {e}")
            raise DatabaseException("Error al buscar factura por cita")
    
    def find_by_vacuna(self, id_vacuna: str) -> Optional[FacturaORM]:
        """
        Busca una factura por el ID de la vacuna.
        
        Args:
            id_vacuna: ID de la vacuna
            
        Returns:
            Factura or None if not found
        """
        try:
            return self.db.query(FacturaORM).filter(
                FacturaORM.id_vacuna == id_vacuna
            ).one_or_none()
        except Exception as e:
            logger.error(f"Error finding factura by vacuna {id_vacuna}: {e}")
            raise DatabaseException("Error al buscar factura por vacuna")
    
    def find_by_mascota(
        self,
        id_mascota: str,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> List[FacturaORM]:
        """
        Busca todas las facturas para una mascota específica.
        
        Args:
            id_mascota: ID de la mascota
            skip: Número de registros a saltar
            limit: Número máximo de registros a devolver
            include_deleted: Whether to include soft-deleted records
            
        Returns:
            List of facturas
        """
        try:
            query = self.db.query(FacturaORM).filter(
                FacturaORM.id_mascota == id_mascota
            )
            
            if not include_deleted:
                query = query.filter(FacturaORM.is_deleted == False)
            
            query = query.order_by(FacturaORM.fecha_factura.desc())
            
            return query.offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error finding facturas by mascota {id_mascota}: {e}")
            raise DatabaseException("Error al buscar facturas por mascota")
    
    def find_by_estado(
        self,
        estado: str,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> List[FacturaORM]:
        """
        Busca todas las facturas con un estado específico.
        
        Args:
            estado: Estado (pendiente, pagada, anulada)
            skip: Número de registros a saltar
            limit: Número máximo de registros a devolver
            include_deleted: Whether to include soft-deleted records
            
        Returns:
            List of facturas
        """
        try:
            query = self.db.query(FacturaORM).filter(
                FacturaORM.estado == estado
            )
            
            if not include_deleted:
                query = query.filter(FacturaORM.is_deleted == False)
            
            query = query.order_by(FacturaORM.fecha_factura.desc())
            
            return query.offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error finding facturas by estado {estado}: {e}")
            raise DatabaseException("Error al buscar facturas por estado")
    
    def find_by_veterinario(
        self,
        veterinario: str,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> List[FacturaORM]:
        """
        Busca todas las facturas emitidas por un veterinario específico.
        
        Args:
            veterinario: nombre de usuario del veterinario
            skip: número de registros a saltar
            limit: número máximo de registros a devolver
            include_deleted: Whether to include soft-deleted records
            
        Returns:
            List of facturas
        """
        try:
            query = self.db.query(FacturaORM).filter(
                FacturaORM.veterinario.ilike(f"%{veterinario}%")
            )
            
            if not include_deleted:
                query = query.filter(FacturaORM.is_deleted == False)
            
            query = query.order_by(FacturaORM.fecha_factura.desc())
            
            return query.offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error finding facturas by veterinario {veterinario}: {e}")
            raise DatabaseException("Error al buscar facturas por veterinario")
    
    def find_by_veterinario_and_mascota(
        self,
        veterinario: str,
        mascota_id: str,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> List[FacturaORM]:
        """
        Busca todas las facturas emitidas por un veterinario específico para una mascota específica.
        
        Usado para la privacidad: los veterinarios solo pueden ver sus propias facturas
        cuando están viendo el historial clínico de un animal.
        
        Args:
            veterinario: nombre de usuario del veterinario
            mascota_id: ID de la mascota
            skip: número de registros a saltar
            limit: número máximo de registros a devolver
            include_deleted: Whether to include soft-deleted records
            
        Returns:
            lista de facturas
        """
        try:
            query = self.db.query(FacturaORM).filter(
                FacturaORM.veterinario.ilike(f"%{veterinario}%"),
                FacturaORM.id_mascota == mascota_id
            )
            
            if not include_deleted:
                query = query.filter(FacturaORM.is_deleted == False)
            
            query = query.order_by(FacturaORM.fecha_factura.desc())
            
            return query.offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error finding facturas by veterinario {veterinario} and mascota {mascota_id}: {e}")
            raise DatabaseException("Error al buscar facturas por veterinario y mascota")
    
    def find_by_propietario(
        self,
        propietario_username: str,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> List[FacturaORM]:
        """
        Busca todas las facturas para mascotas propiedad de un usuario específico.
        
        Args:
            propietario_username: nombre de usuario del propietario de la mascota
            skip: número de registros a saltar
            limit: número máximo de registros a devolver
            include_deleted: Whether to include soft-deleted records
            
        Returns:
            List of facturas
        """
        try:
            query = self.db.query(FacturaORM).join(
                MascotaORM, FacturaORM.id_mascota == MascotaORM.id
            ).filter(
                MascotaORM.propietario == propietario_username
            )
            
            if not include_deleted:
                query = query.filter(FacturaORM.is_deleted == False)
            
            query = query.order_by(FacturaORM.fecha_factura.desc())
            
            return query.offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error finding facturas by propietario {propietario_username}: {e}")
            raise DatabaseException("Error al buscar facturas por propietario")
    
    def find_by_veterinario_or_propietario(
        self,
        username: str,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> List[FacturaORM]:
        """
        Busca facturas donde el usuario sea el veterinario o el dueño de la mascota.
        Argumentos:
        username: Nombre de usuario a buscar
        skip: Número de registros a omitir
        limit: Número máximo de registros a devolver
        include_deleted: Indica si se deben incluir los registros eliminados lógicamente
        Devuelve:
        Lista de facturas
        """
        try:
            from sqlalchemy import or_
            
            query = self.db.query(FacturaORM).join(
                MascotaORM, FacturaORM.id_mascota == MascotaORM.id
            ).filter(
                or_(
                    FacturaORM.veterinario == username,
                    MascotaORM.propietario == username
                )
            )
            
            if not include_deleted:
                query = query.filter(FacturaORM.is_deleted == False)
            
            query = query.order_by(FacturaORM.fecha_factura.desc())
            
            return query.offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error finding facturas by veterinario or propietario {username}: {e}")
            raise DatabaseException("Error al buscar facturas")
    
    def count_by_filters(
        self,
        estado: Optional[str] = None,
        veterinario: Optional[str] = None,
        propietario_username: Optional[str] = None,
        include_deleted: bool = False
    ) -> int:
        """
        Cuenta facturas que coinciden con los filtros dados.
        
        Args:
            estado: Filtro opcional de estado
            veterinario: Filtro opcional de veterinario
            propietario_username: Filtro opcional de propietario
            include_deleted: Whether to include soft-deleted records
            
        Returns:
            Cantidad de facturas que coinciden con los filtros dados
        """
        try:
            query = self.db.query(FacturaORM)
            
            if propietario_username:
                query = query.join(
                    MascotaORM, FacturaORM.id_mascota == MascotaORM.id
                ).filter(
                    MascotaORM.propietario == propietario_username
                )
            
            if estado:
                query = query.filter(FacturaORM.estado == estado)
            
            if veterinario:
                query = query.filter(FacturaORM.veterinario.ilike(f"%{veterinario}%"))
            
            if not include_deleted:
                query = query.filter(FacturaORM.is_deleted == False)
            
            return query.count()
        except Exception as e:
            logger.error(f"Error counting facturas by filters: {e}")
            raise DatabaseException("Error al contar facturas")
