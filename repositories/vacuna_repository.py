"""
Repositorio para la entidad Vacuna.
Gestiona todas las operaciones de base de datos relacionadas con vacunas.
"""
from typing import List, Optional
from datetime import date
from sqlalchemy.orm import Session

from repositories.base_repository import BaseRepository
from database.models import VacunaORM, MascotaORM
from core.exceptions import DatabaseException
import logging

logger = logging.getLogger(__name__)


class VacunaRepository(BaseRepository[VacunaORM]):
    """Repositorio para la gestión de entidades de vacuna."""
    
    def __init__(self, db: Session):
        """
        Inicializa el repositorio de vacunas.
        
        Args:
            db: SQLAlchemy session
        """
        super().__init__(db, VacunaORM)
    
    def find_by_mascota(
        self,
        id_mascota: str,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> List[VacunaORM]:
        """
        Busca todas las vacunas para una mascota específica.
        
        Args:
            id_mascota: ID de la mascota
            skip: Número de registros a omitir
            limit: Número máximo de registros a devolver
            include_deleted: Si se deben incluir los registros eliminados temporalmente
            
        Returns:
            Lista de vacunas
        """
        try:
            query = self.db.query(VacunaORM).filter(
                VacunaORM.id_mascota == id_mascota
            )
            
            if not include_deleted:
                query = query.filter(VacunaORM.is_deleted == False)
            
            query = query.order_by(VacunaORM.fecha_aplicacion.desc())
            
            return query.offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error finding vacunas by mascota {id_mascota}: {e}")
            raise DatabaseException("Error al buscar vacunas por mascota")
    
    def find_by_veterinario(
        self,
        veterinario: str,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> List[VacunaORM]:
        """
        Busca todas las vacunas administradas por un veterinario específico.
        
        Args:
            veterinario: Username del veterinario
            skip: Número de registros a omitir
            limit: Número máximo de registros a devolver
            include_deleted: Si se deben incluir los registros eliminados temporalmente
            
        Returns:
            Lista de vacunas
        """
        try:
            query = self.db.query(VacunaORM).filter(
                VacunaORM.veterinario.ilike(f"%{veterinario}%")
            )
            
            if not include_deleted:
                query = query.filter(VacunaORM.is_deleted == False)
            
            query = query.order_by(VacunaORM.fecha_aplicacion.desc())
            
            return query.offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error finding vacunas by veterinario {veterinario}: {e}")
            raise DatabaseException("Error al buscar vacunas por veterinario")
    
    def find_by_tipo(
        self,
        tipo_vacuna: str,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> List[VacunaORM]:
        """
        Busca todas las vacunas de un tipo específico.
        
        Args:
            tipo_vacuna: Tipo de vacuna
            skip: Número de registros a omitir
            limit: Número máximo de registros a devolver
            include_deleted: Si se deben incluir los registros eliminados temporalmente
            
        Returns:
            Lista de vacunas
        """
        try:
            query = self.db.query(VacunaORM).filter(
                VacunaORM.tipo_vacuna == tipo_vacuna
            )
            
            if not include_deleted:
                query = query.filter(VacunaORM.is_deleted == False)
            
            query = query.order_by(VacunaORM.fecha_aplicacion.desc())
            
            return query.offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error finding vacunas by tipo {tipo_vacuna}: {e}")
            raise DatabaseException("Error al buscar vacunas por tipo")
    
    def find_proximas_dosis(
        self,
        fecha_limite: Optional[date] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[VacunaORM]:
        """
        Busca vacunas con próximas dosis pendientes.
        
        Args:
            fecha_limite: Fecha límite opcional (por defecto None - todas las dosis futuras)
            skip: Número de registros a omitir
            limit: Número máximo de registros a devolver
            
        Returns:
            Lista de vacunas con próximas dosis
        """
        try:
            today = date.today()
            query = self.db.query(VacunaORM).filter(
                VacunaORM.proxima_dosis != None,
                VacunaORM.proxima_dosis >= today,
                VacunaORM.is_deleted == False
            )
            
            if fecha_limite:
                query = query.filter(VacunaORM.proxima_dosis <= fecha_limite)
            
            query = query.order_by(VacunaORM.proxima_dosis)
            
            return query.offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error finding proximas dosis: {e}")
            raise DatabaseException("Error al buscar próximas dosis")
    
    def find_by_propietario(
        self,
        propietario_username: str,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> List[VacunaORM]:
        """
        Busca todas las vacunas para mascotas propiedad de un usuario específico.
        
        Args:
            propietario_username: Username del propietario de la mascota
            skip: Número de registros a omitir
            limit: Número máximo de registros a devolver
            include_deleted: Si se deben incluir los registros eliminados temporalmente
            
        Returns:
            Lista de vacunas
        """
        try:
            query = self.db.query(VacunaORM).join(
                MascotaORM, VacunaORM.id_mascota == MascotaORM.id
            ).filter(
                MascotaORM.propietario == propietario_username
            )
            
            if not include_deleted:
                query = query.filter(VacunaORM.is_deleted == False)
            
            query = query.order_by(VacunaORM.fecha_aplicacion.desc())
            
            return query.offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error finding vacunas by propietario {propietario_username}: {e}")
            raise DatabaseException("Error al buscar vacunas por propietario")
    
    def find_by_veterinario_or_propietario(
        self,
        username: str,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> List[VacunaORM]:
        """
        Busca vacunas donde el usuario es el veterinario o el propietario de la mascota.
        
        Args:
            username: Username a buscar
            skip: Número de registros a omitir
            limit: Número máximo de registros a devolver
            include_deleted: Si se deben incluir los registros eliminados temporalmente
            
        Returns:
            Lista de vacunas
        """
        try:
            from sqlalchemy import or_
            
            query = self.db.query(VacunaORM).join(
                MascotaORM, VacunaORM.id_mascota == MascotaORM.id
            ).filter(
                or_(
                    VacunaORM.veterinario == username,
                    MascotaORM.propietario == username
                )
            )
            
            if not include_deleted:
                query = query.filter(VacunaORM.is_deleted == False)
            
            query = query.order_by(VacunaORM.fecha_aplicacion.desc())
            
            return query.offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error finding vacunas by veterinario or propietario {username}: {e}")
            raise DatabaseException("Error al buscar vacunas")
    
    def find_by_multiple_filters(
        self,
        tipo_vacuna: Optional[str] = None,
        veterinario: Optional[str] = None,
        id_mascota: Optional[str] = None,
        propietario_username: Optional[str] = None,
        search_term: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> List[VacunaORM]:
        """
        Busca vacunas que coincidan con múltiples filtros con paginación.
        Los filtros se combinan con lógica AND.
        
        Args:
            tipo_vacuna: Optional tipo_vacuna filter
            veterinario: Optional veterinario filter
            id_mascota: Optional mascota ID filter
            propietario_username: Optional propietario filter (exact match on username)
            search_term: Optional search in mascota nombre OR propietario nombre (partial match)
            skip: Número de registros a omitir
            limit: Número máximo de registros a devolver
            include_deleted: Si se deben incluir los registros eliminados temporalmente
            
        Returns:
            Lista de vacunas
        """
        try:
            query = self.db.query(VacunaORM)
            
            #Join with MascotaORM if we need to filter/search by mascota data
            if propietario_username or search_term:
                query = query.join(
                    MascotaORM, VacunaORM.id_mascota == MascotaORM.id
                )
            
            if tipo_vacuna:
                query = query.filter(VacunaORM.tipo_vacuna == tipo_vacuna)
            
            if veterinario:
                query = query.filter(VacunaORM.veterinario.ilike(f"%{veterinario}%"))
            
            if id_mascota:
                query = query.filter(VacunaORM.id_mascota == id_mascota)
            
            #Filtro exacto por propietario (para clientes)
            if propietario_username:
                query = query.filter(MascotaORM.propietario == propietario_username)
            
            #Búsqueda libre: nombre de mascota OR nombre de propietario
            if search_term:
                from sqlalchemy import or_
                query = query.filter(
                    or_(
                        MascotaORM.nombre.ilike(f"%{search_term}%"),
                        MascotaORM.propietario.ilike(f"%{search_term}%")
                    )
                )
            
            if not include_deleted:
                query = query.filter(VacunaORM.is_deleted == False)
            
            #Order by fecha_aplicacion descending (most recent first)
            query = query.order_by(VacunaORM.fecha_aplicacion.desc())
            
            return query.offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error finding vacunas by multiple filters: {e}")
            raise DatabaseException("Error al buscar vacunas con filtros")

    def count_by_filters(
        self,
        tipo_vacuna: Optional[str] = None,
        veterinario: Optional[str] = None,
        id_mascota: Optional[str] = None,
        propietario_username: Optional[str] = None,
        search_term: Optional[str] = None,
        include_deleted: bool = False
    ) -> int:
        """
        Cuenta las vacunas que coinciden con los filtros dados.
        
        Args:
            tipo_vacuna: Optional tipo_vacuna filter
            veterinario: Optional veterinario filter
            id_mascota: Optional mascota ID filter
            propietario_username: Optional propietario filter (exact match on username)
            search_term: Optional search in mascota nombre OR propietario nombre
            include_deleted: Si se deben incluir los registros eliminados temporalmente
            
        Returns:
            Cantidad de vacunas que coinciden con los filtros
        """
        try:
            query = self.db.query(VacunaORM)
            
            #join with mascota if needed
            if propietario_username or search_term:
                query = query.join(
                    MascotaORM, VacunaORM.id_mascota == MascotaORM.id
                )
            
            if tipo_vacuna:
                query = query.filter(VacunaORM.tipo_vacuna == tipo_vacuna)
            
            if veterinario:
                query = query.filter(VacunaORM.veterinario.ilike(f"%{veterinario}%"))
            
            if id_mascota:
                query = query.filter(VacunaORM.id_mascota == id_mascota)
            
            if propietario_username:
                query = query.filter(MascotaORM.propietario == propietario_username)
            
            #busqueda libre
            if search_term:
                from sqlalchemy import or_
                query = query.filter(
                    or_(
                        MascotaORM.nombre.ilike(f"%{search_term}%"),
                        MascotaORM.propietario.ilike(f"%{search_term}%")
                    )
                )
            
            if not include_deleted:
                query = query.filter(VacunaORM.is_deleted == False)
            
            return query.count()
        except Exception as e:
            logger.error(f"Error counting vacunas by filters: {e}")
            raise DatabaseException("Error al contar vacunas")
