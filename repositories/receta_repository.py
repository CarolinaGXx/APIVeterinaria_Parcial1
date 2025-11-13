"""
Repositorio para la entidad Receta.
Gestiona todas las operaciones de base de datos relacionadas con las recetas (prescripciones).
"""

from typing import List, Optional
from sqlalchemy.orm import Session, joinedload

from repositories.base_repository import BaseRepository
from database.models import RecetaORM, RecetaLineaORM, CitaORM, MascotaORM
from core.exceptions import DatabaseException
import logging

logger = logging.getLogger(__name__)


class RecetaRepository(BaseRepository[RecetaORM]):
    """Repositorio para la gestión de entidades de recetas."""
    
    def __init__(self, db: Session):
        """
        Inicializa el repositorio de recetas.
        
        Args:
            db: Sesión de SQLAlchemy
        """
        super().__init__(db, RecetaORM)
    
    def find_by_cita(self, id_cita: str) -> Optional[RecetaORM]:
        """
        Busca una receta por ID de cita (con carga pre-cargada de lineas).
        
        Args:
            id_cita: ID de la cita
            
        Returns:
            Receta with lineas loaded or None if not found
        """
        try:
            return self.db.query(RecetaORM).options(
                joinedload(RecetaORM.lineas)
            ).filter(
                RecetaORM.id_cita == id_cita
            ).one_or_none()
        except Exception as e:
            logger.error(f"Error finding receta by cita {id_cita}: {e}")
            raise DatabaseException("Error al buscar receta por cita")
    
    def get_by_id_with_lineas(self, id: str) -> Optional[RecetaORM]:
        """
        Obtiene una receta por ID con carga pre-cargada de lineas.
        
        Args:
            id: ID de la receta
            
        Returns:
            Receta with lineas loaded or None if not found
        """
        try:
            return self.db.query(RecetaORM).options(
                joinedload(RecetaORM.lineas)
            ).filter(
                RecetaORM.id == str(id)
            ).one_or_none()
        except Exception as e:
            logger.error(f"Error getting receta with lineas {id}: {e}")
            raise DatabaseException("Error al obtener receta")
    
    def find_by_veterinario(
        self,
        veterinario: str,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> List[RecetaORM]:
        """
        Busca todas las recetas por veterinario.
        
        Args:
            veterinario: Nombre de usuario del veterinario
            skip: Número de registros a omitir
            limit: Número máximo de registros a devolver
            include_deleted: Whether to include soft-deleted records
            
        Returns:
            List of recetas (without lineas)
        """
        try:
            query = self.db.query(RecetaORM).filter(
                RecetaORM.veterinario.ilike(f"%{veterinario}%")
            )
            
            if not include_deleted:
                query = query.filter(RecetaORM.is_deleted == False)
            
            query = query.order_by(RecetaORM.fecha_emision.desc())
            
            return query.offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error finding recetas by veterinario {veterinario}: {e}")
            raise DatabaseException("Error al buscar recetas por veterinario")
    
    def find_by_propietario(
        self,
        propietario_username: str,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> List[RecetaORM]:
        """
        Busca todas las recetas para mascotas propiedad de un usuario específico.
        
        Args:
            propietario_username: Nombre de usuario del propietario
            skip: Número de registros a omitir
            limit: Número máximo de registros a devolver
            include_deleted: Whether to include soft-deleted records
            
        Returns:
            List of recetas (without lineas)
        """
        try:
            query = self.db.query(RecetaORM).join(
                CitaORM, RecetaORM.id_cita == CitaORM.id
            ).join(
                MascotaORM, CitaORM.id_mascota == MascotaORM.id
            ).filter(
                MascotaORM.propietario == propietario_username
            )
            
            if not include_deleted:
                query = query.filter(RecetaORM.is_deleted == False)
            
            query = query.order_by(RecetaORM.fecha_emision.desc())
            
            return query.offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error finding recetas by propietario {propietario_username}: {e}")
            raise DatabaseException("Error al buscar recetas por propietario")
    
    def find_by_mascota(
        self,
        mascota_id: str,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> List[RecetaORM]:
        """
        Busca todas las recetas para una mascota específica (historial clínico completo).
        
        Args:
            mascota_id: ID de la mascota
            skip: Número de registros a omitir
            limit: Número máximo de registros a devolver
            include_deleted: Whether to include soft-deleted records
            
        Returns:
            List de recetas (sin lineas)
        """
        try:
            query = self.db.query(RecetaORM).join(
                CitaORM, RecetaORM.id_cita == CitaORM.id
            ).filter(
                CitaORM.id_mascota == mascota_id
            )
            
            if not include_deleted:
                query = query.filter(RecetaORM.is_deleted == False)
            
            query = query.order_by(RecetaORM.fecha_emision.desc())
            
            return query.offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error finding recetas by mascota {mascota_id}: {e}")
            raise DatabaseException("Error al buscar recetas por mascota")
    
    def find_by_veterinario_or_propietario(
        self,
        username: str,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> List[RecetaORM]:
        """
        Busca todas las recetas donde el usuario es el veterinario o el propietario de la mascota.
        
        Args:
            username: Nombre de usuario a buscar
            skip: Número de registros a omitir
            limit: Número máximo de registros a devolver
            include_deleted: incluir registros eliminados
            
        Returns:
            List de recetas (sin lineas)
        """
        try:
            from sqlalchemy import or_
            
            query = self.db.query(RecetaORM).join(
                CitaORM, RecetaORM.id_cita == CitaORM.id
            ).join(
                MascotaORM, CitaORM.id_mascota == MascotaORM.id
            ).filter(
                or_(
                    RecetaORM.veterinario == username,
                    MascotaORM.propietario == username
                )
            )
            
            if not include_deleted:
                query = query.filter(RecetaORM.is_deleted == False)
            
            query = query.order_by(RecetaORM.fecha_emision.desc())
            
            return query.offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error finding recetas by veterinario or propietario {username}: {e}")
            raise DatabaseException("Error al buscar recetas")
    
    def count_by_filters(
        self,
        veterinario: Optional[str] = None,
        propietario_username: Optional[str] = None,
        include_deleted: bool = False
    ) -> int:
        """
        Cuenta las recetas que coinciden con los filtros dados.
        
        Args:
            veterinario: Filtro opcional de veterinario
            propietario_username: Filtro opcional de propietario
            include_deleted: incluir registros eliminados
            
        Returns:
            Cantidad de recetas que coinciden con los filtros
        """
        try:
            query = self.db.query(RecetaORM)
            
            if propietario_username:
                query = query.join(
                    CitaORM, RecetaORM.id_cita == CitaORM.id
                ).join(
                    MascotaORM, CitaORM.id_mascota == MascotaORM.id
                ).filter(
                    MascotaORM.propietario == propietario_username
                )
            
            if veterinario:
                query = query.filter(RecetaORM.veterinario.ilike(f"%{veterinario}%"))
            
            if not include_deleted:
                query = query.filter(RecetaORM.is_deleted == False)
            
            return query.count()
        except Exception as e:
            logger.error(f"Error counting recetas by filters: {e}")
            raise DatabaseException("Error al contar recetas")
    
    def create_with_lineas(
        self,
        receta: RecetaORM,
        lineas: List[RecetaLineaORM],
        user_id: Optional[str] = None
    ) -> RecetaORM:
        """
        Crea una receta con sus líneas en una sola transacción.
        Argumentos:
        receta: Instancia de Receta ORM
        lineas: Lista de instancias de RecetaLinea ORM
        user_id: ID del usuario que crea la receta
        Retorno:
        Receta creada con sus líneas adjuntas
        """
        try:
            created = self.create(receta, user_id=user_id)
            
            # agregar lineas
            for linea in lineas:
                linea.id_receta = created.id
                self.db.add(linea)
            
            self.db.flush()
            self.db.refresh(created)
            
            return created
        except Exception as e:
            logger.error(f"Error creating receta with lineas: {e}")
            self.db.rollback()
            raise DatabaseException("Error al crear receta con líneas")
    
    def update_lineas(
        self,
        receta_id: str,
        new_lineas: List[RecetaLineaORM]
    ) -> None:
        """
        Reemplaza todas las lineas para una receta.
        Argumentos:
            receta_id: ID de la receta
            new_lineas: Nueva lista de lineas para reemplazar las existentes
        """
        try:
            # eliminar lineas existentes
            self.db.query(RecetaLineaORM).filter(
                RecetaLineaORM.id_receta == receta_id
            ).delete(synchronize_session=False)
            
            self.db.flush()
            
            # agregar nuevas líneas
            for linea in new_lineas:
                linea.id_receta = receta_id
                self.db.add(linea)
            
            self.db.flush()
            
            logger.info(f"Updated {len(new_lineas)} lineas for receta {receta_id}")
        except Exception as e:
            logger.error(f"Error updating lineas for receta {receta_id}: {e}")
            self.db.rollback()
            raise DatabaseException("Error al actualizar líneas de receta")
