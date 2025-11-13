"""
Service for Mascota business logic.

Handles all business operations related to mascotas (pets).
"""

from typing import List, Optional, Dict, Any
import logging

from services.base_service import BaseService
from repositories.mascota_repository import MascotaRepository
from repositories.usuario_repository import UsuarioRepository
from database.models import MascotaORM, UsuarioORM
from models.mascotas import MascotaCreate, MascotaUpdate, Mascota
from core.exceptions import (
    BusinessException,
    ValidationException,
    NotFoundException,
    ForbiddenException,
)
from core.security import (
    validate_uuid,
    check_ownership_by_username,
)
from core.utils import enum_to_value, normalize_stored_enum
from core.pagination import calculate_skip
from database.db import SessionLocal

logger = logging.getLogger(__name__)


class MascotaService(BaseService[MascotaORM, MascotaRepository]):
    """Service for managing mascota business logic."""
    
    def __init__(self, repository: MascotaRepository, usuario_repository: UsuarioRepository):
        """
        Initialize mascota service.
        
        Args:
            repository: MascotaRepository instance
            usuario_repository: UsuarioRepository instance
        """
        super().__init__(repository)
        self.usuario_repo = usuario_repository
    
    def create_mascota(
        self,
        mascota_data: MascotaCreate,
        current_user: UsuarioORM
    ) -> Mascota:
        """
        Create a new mascota.
        
        Args:
            mascota_data: Mascota creation data
            current_user: Current authenticated user (will be the owner)
            
        Returns:
            Created mascota with response data
            
        Raises:
            ValidationException: If data is invalid
        """
        # Convert Pydantic model to dict
        data = mascota_data.model_dump()
        
        # Create ORM instance
        mascota_orm = MascotaORM(
            nombre=data["nombre"],
            tipo=enum_to_value(data["tipo"]),
            raza=data.get("raza"),
            edad=data.get("edad"),
            peso=data.get("peso"),
            propietario=current_user.username,
        )
        
        # Save to database
        created = self.repository.create(mascota_orm, user_id=current_user.id)
        self.repository.commit()
        
        logger.info(f"Mascota {created.id} created by user {current_user.username}")
        
        # Convert to response model
        return self._to_response_model(created, current_user.telefono)
    
    def get_mascota(
        self,
        mascota_id: str,
        current_user: UsuarioORM
    ) -> Mascota:
        """
        Get a mascota by ID.
        
        Args:
            mascota_id: Mascota ID
            current_user: Current authenticated user
            
        Returns:
            Mascota data
            
        Raises:
            NotFoundException: If mascota not found
            ForbiddenException: If user doesn't have access
        """
        # Validate UUID
        validate_uuid(mascota_id, "mascota_id")
        
        # Get mascota
        mascota = self.repository.get_by_id_or_fail(mascota_id)
        
        # Admin y veterinarios pueden ver cualquier mascota
        # Clientes solo pueden ver sus propias mascotas
        if current_user.role not in ["admin", "veterinario"]:
            check_ownership_by_username(
                current_username=current_user.username,
                owner_username=mascota.propietario,
                user_role=current_user.role,
                resource_name="mascota"
            )
        
        # Get owner phone
        telefono = self._get_telefono_for_username(mascota.propietario)
        
        return self._to_response_model(mascota, telefono)
    
    def get_mascotas(
        self,
        current_user: UsuarioORM,
        page: int = 0,
        page_size: int = 50,
        tipo: Optional[str] = None,
        propietario: Optional[str] = None,
        search_term: Optional[str] = None,
        include_deleted: bool = False
    ) -> tuple[List[Mascota], int]:
        """
        Get list of mascotas with filters.
        
        Args:
            current_user: Current authenticated user
            page: Page number (0-indexed)
            page_size: Items per page
            tipo: Filter by tipo
            propietario: Filter by propietario username (admin only)
            search_term: Search term for name/owner (partial match)
            include_deleted: Include soft-deleted records
            
        Returns:
            Tuple of (list of mascotas, total count)
        """
        skip = calculate_skip(page, page_size)
        
        # If search_term is provided, use search method
        if search_term:
            mascotas = self.repository.search_mascotas(
                search_term=search_term,
                current_user_role=current_user.role,
                current_user_username=current_user.username,
                skip=skip,
                limit=page_size,
                include_deleted=include_deleted
            )
            total_count = len(mascotas)  # For search, we return the actual count
            
            # Convert to response models
            response_list = []
            for mascota in mascotas:
                telefono = self._get_telefono_for_username(mascota.propietario)
                response_list.append(self._to_response_model(mascota, telefono))
            
            return response_list, total_count
        
        # Determine filter based on user role
        if current_user.role in ["admin", "veterinario"]:
            # Admin y veterinarios pueden ver todas las mascotas o filtrar por propietario
            if propietario:
                mascotas = self.repository.find_by_propietario(
                    propietario_username=propietario,
                    skip=skip,
                    limit=page_size,
                    include_deleted=include_deleted
                )
                total_count = self.repository.count_by_propietario(
                    propietario_username=propietario,
                    include_deleted=include_deleted
                )
            elif tipo:
                mascotas = self.repository.find_by_tipo(
                    tipo=tipo,
                    skip=skip,
                    limit=page_size,
                    include_deleted=include_deleted
                )
                total_count = self.repository.count_by_tipo(
                    tipo=tipo,
                    include_deleted=include_deleted
                )
            else:
                mascotas = self.repository.get_all(
                    skip=skip,
                    limit=page_size,
                    include_deleted=include_deleted
                )
                total_count = self.repository.count(include_deleted=include_deleted)
        else:
            # Clientes solo pueden ver sus propias mascotas
            if tipo:
                mascotas = self.repository.find_by_propietario_and_tipo(
                    propietario_username=current_user.username,
                    tipo=tipo,
                    skip=skip,
                    limit=page_size,
                    include_deleted=include_deleted
                )
                # Count with same filters
                total_count = len(self.repository.find_by_propietario_and_tipo(
                    propietario_username=current_user.username,
                    tipo=tipo,
                    skip=0,
                    limit=100000,
                    include_deleted=include_deleted
                ))
            else:
                mascotas = self.repository.find_by_propietario(
                    propietario_username=current_user.username,
                    skip=skip,
                    limit=page_size,
                    include_deleted=include_deleted
                )
                total_count = self.repository.count_by_propietario(
                    propietario_username=current_user.username,
                    include_deleted=include_deleted
                )
        
        # Convert to response models
        response_list = []
        for mascota in mascotas:
            telefono = self._get_telefono_for_username(mascota.propietario)
            response_list.append(self._to_response_model(mascota, telefono))
        
        return response_list, total_count
    
    def update_mascota(
        self,
        mascota_id: str,
        mascota_update: MascotaUpdate,
        current_user: UsuarioORM
    ) -> Mascota:
        """
        Update a mascota.
        
        Args:
            mascota_id: Mascota ID
            mascota_update: Update data
            current_user: Current authenticated user
            
        Returns:
            Updated mascota
            
        Raises:
            NotFoundException: If mascota not found
            ForbiddenException: If user doesn't have access
            BusinessException: If mascota is deleted
        """
        # Validate UUID
        validate_uuid(mascota_id, "mascota_id")
        
        # Get mascota
        mascota = self.repository.get_by_id_or_fail(mascota_id)
        
        # Validate not deleted
        self.validate_not_deleted(mascota)
        
        # Check ownership
        check_ownership_by_username(
            current_username=current_user.username,
            owner_username=mascota.propietario,
            user_role=current_user.role,
            resource_name="mascota"
        )
        
        # Apply updates
        update_data = mascota_update.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            if value is not None:
                setattr(mascota, field, enum_to_value(value))
        
        # Save changes
        updated = self.repository.update(mascota, user_id=current_user.id)
        self.repository.commit()
        
        logger.info(f"Mascota {mascota_id} updated by user {current_user.username}")
        
        # Get owner phone
        telefono = self._get_telefono_for_username(mascota.propietario)
        
        return self._to_response_model(updated, telefono)
    
    def delete_mascota(
        self,
        mascota_id: str,
        current_user: UsuarioORM
    ) -> None:
        """
        Delete a mascota (soft delete).
        
        Args:
            mascota_id: Mascota ID
            current_user: Current authenticated user
            
        Raises:
            NotFoundException: If mascota not found
            ForbiddenException: If user doesn't have access
            BusinessException: If mascota is already deleted
        """
        # Validate UUID
        validate_uuid(mascota_id, "mascota_id")
        
        # Get mascota
        mascota = self.repository.get_by_id_or_fail(mascota_id)
        
        # Check if already deleted
        if mascota.is_deleted:
            raise BusinessException("La mascota ya está eliminada")
        
        # Check ownership
        check_ownership_by_username(
            current_username=current_user.username,
            owner_username=mascota.propietario,
            user_role=current_user.role,
            resource_name="mascota"
        )
        
        # Soft delete
        self.repository.delete(mascota, user_id=current_user.id, hard=False)
        self.repository.commit()
        
        logger.info(f"Mascota {mascota_id} deleted by user {current_user.username}")
    
    def restore_mascota(
        self,
        mascota_id: str,
        current_user: UsuarioORM
    ) -> Mascota:
        """
        Restore a soft-deleted mascota.
        
        Args:
            mascota_id: Mascota ID
            current_user: Current authenticated user
            
        Returns:
            Restored mascota
            
        Raises:
            NotFoundException: If mascota not found
            ForbiddenException: If user doesn't have access
            BusinessException: If mascota is not deleted
        """
        # Validate UUID
        validate_uuid(mascota_id, "mascota_id")
        
        # Get mascota
        mascota = self.repository.get_by_id_or_fail(mascota_id)
        
        # Check if not deleted
        if not mascota.is_deleted:
            raise BusinessException("La mascota no está eliminada")
        
        # Check ownership
        check_ownership_by_username(
            current_username=current_user.username,
            owner_username=mascota.propietario,
            user_role=current_user.role,
            resource_name="mascota"
        )
        
        # Restore
        restored = self.repository.restore(mascota, user_id=current_user.id)
        self.repository.commit()
        
        logger.info(f"Mascota {mascota_id} restored by user {current_user.username}")
        
        # Get owner phone
        telefono = self._get_telefono_for_username(restored.propietario)
        
        return self._to_response_model(restored, telefono)
    
    def _get_telefono_for_username(self, username: Optional[str]) -> Optional[str]:
        """
        Get phone number for a username.
        
        Args:
            username: Username to look up
            
        Returns:
            Phone number or None if not found
        """
        if not username:
            return None
        
        try:
            db = SessionLocal()
            try:
                from database.models import UsuarioORM
                usuario = db.query(UsuarioORM).filter(
                    UsuarioORM.username == username
                ).one_or_none()
                return usuario.telefono if usuario else None
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Error getting telefono for username {username}: {e}")
            return None
    
    def _to_response_model(
        self,
        mascota: MascotaORM,
        telefono: Optional[str] = None
    ) -> Mascota:
        """
        Convert ORM model to Pydantic response model.
        
        Args:
            mascota: ORM instance
            telefono: Owner's phone number
            
        Returns:
            Pydantic Mascota model
        """
        # Get propietario name and phone from username
        owner = self.usuario_repo.find_by_username(mascota.propietario) if mascota.propietario else None
        propietario_nombre = owner.nombre if owner else None
        propietario_telefono = owner.telefono if owner else None
        
        return Mascota(
            id_mascota=mascota.id,
            nombre=mascota.nombre,
            tipo=normalize_stored_enum(mascota.tipo),
            raza=mascota.raza,
            edad=mascota.edad,
            peso=mascota.peso,
            propietario=mascota.propietario,
            propietario_nombre=propietario_nombre,
            propietario_telefono=propietario_telefono,
            telefono_propietario=telefono if telefono else propietario_telefono,  # deprecated
            is_deleted=mascota.is_deleted
        )
    
    def _to_response_dict(
        self,
        mascota: MascotaORM,
        telefono: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Convert ORM model to dictionary for response.
        
        Args:
            mascota: ORM instance
            telefono: Owner's phone number
            
        Returns:
            Dictionary with mascota data
        """
        # Get propietario name and phone from username
        owner = self.usuario_repo.find_by_username(mascota.propietario) if mascota.propietario else None
        propietario_nombre = owner.nombre if owner else None
        propietario_telefono = owner.telefono if owner else None
        
        return {
            "id_mascota": mascota.id,
            "nombre": mascota.nombre,
            "tipo": normalize_stored_enum(mascota.tipo),
            "raza": mascota.raza,
            "edad": mascota.edad,
            "peso": mascota.peso,
            "propietario": mascota.propietario,
            "propietario_nombre": propietario_nombre,
            "propietario_telefono": propietario_telefono,
            "telefono_propietario": telefono if telefono else propietario_telefono,  # deprecated
            "is_deleted": mascota.is_deleted,
        }
