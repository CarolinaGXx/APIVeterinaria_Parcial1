"""
Service for Usuario business logic.

Handles all business operations related to usuarios (users).
"""

from typing import List, Optional, Dict, Any
from uuid import uuid4
import logging

from services.base_service import BaseService
from repositories.usuario_repository import UsuarioRepository
from database.models import UsuarioORM
from database.db import hash_password, verify_password
from models.usuarios import UsuarioCreate, UsuarioUpdateRequest, Usuario, UsuarioUpdateResponse
from core.exceptions import (
    BusinessException,
    ValidationException,
    NotFoundException,
    DuplicateException,
    DatabaseException,
)
from core.security import validate_uuid
from core.pagination import calculate_skip

logger = logging.getLogger(__name__)


class UsuarioService(BaseService[UsuarioORM, UsuarioRepository]):
    """Service for managing usuario business logic."""
    
    def __init__(self, repository: UsuarioRepository):
        """
        Initialize usuario service.
        
        Args:
            repository: UsuarioRepository instance
        """
        super().__init__(repository)
    
    def create_usuario(self, usuario_data: UsuarioCreate, role: str = "cliente") -> Usuario:
        """
        Create a new usuario.
        
        Args:
            usuario_data: Usuario creation data
            role: Role to assign to the user (default: "cliente")
            
        Returns:
            Created usuario
            
        Raises:
            DuplicateException: If username already exists
            ValidationException: If data is invalid
        """
        # Check if username already exists
        if self.repository.exists_username(usuario_data.username):
            raise DuplicateException(
                resource="Usuario",
                field="username",
                value=usuario_data.username
            )
        
        # Hash password
        salt_hex, hash_hex = hash_password(usuario_data.password)
        
        # Create ORM instance
        usuario_orm = UsuarioORM(
            id=str(uuid4()),
            username=usuario_data.username,
            nombre=usuario_data.nombre,
            edad=usuario_data.edad,
            telefono=usuario_data.telefono,
            role=role,
            password_salt=salt_hex,
            password_hash=hash_hex,
        )
        
        # Save to database
        created = self.repository.create(usuario_orm)
        self.repository.commit()
        
        logger.info(f"Usuario {created.id} ({created.username}) created")
        
        return self._to_response_model(created)
    
    def get_usuario(self, usuario_id: str) -> Usuario:
        """
        Get a usuario by ID.
        
        Args:
            usuario_id: Usuario ID
            
        Returns:
            Usuario data
            
        Raises:
            NotFoundException: If usuario not found
        """
        validate_uuid(usuario_id, "usuario_id")
        usuario = self.repository.get_by_id_or_fail(usuario_id)
        return self._to_response_model(usuario)
    
    def get_usuarios(
        self,
        page: int = 0,
        page_size: int = 50,
        role: Optional[str] = None,
        include_deleted: bool = False
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        Get list of usuarios with filters.
        
        Args:
            page: Page number (0-indexed)
            page_size: Items per page
            role: Filter by role (optional)
            include_deleted: Include soft-deleted records
            
        Returns:
            Tuple of (list of usuarios, total count)
        """
        skip = calculate_skip(page, page_size)
        
        if role:
            usuarios = self.repository.find_by_role(
                role=role,
                skip=skip,
                limit=page_size,
                include_deleted=include_deleted
            )
            total_count = self.repository.count_by_role(
                role=role,
                include_deleted=include_deleted
            )
        else:
            usuarios = self.repository.get_all(
                skip=skip,
                limit=page_size,
                include_deleted=include_deleted,
                order_by="username"
            )
            total_count = self.repository.count(include_deleted=include_deleted)
        
        # Convert to response dicts (include is_deleted for admin views)
        response_list = [self._to_response_dict(u) for u in usuarios]
        
        return response_list, total_count
    
    def update_usuario(
        self,
        usuario_id: str,
        usuario_update: UsuarioUpdateRequest,
        current_user: UsuarioORM
    ) -> Usuario:
        """
        Update a usuario.
        
        Args:
            usuario_id: Usuario ID
            usuario_update: Update data
            current_user: Current authenticated user
            
        Returns:
            Updated usuario
            
        Raises:
            NotFoundException: If usuario not found
            ForbiddenException: If user doesn't have permission
            ValidationException: If username already exists
            BusinessException: If usuario is deleted
        """
        validate_uuid(usuario_id, "usuario_id")
        usuario = self.repository.get_by_id_or_fail(usuario_id)
        
        # Validate not deleted
        self.validate_not_deleted(usuario)
        
        update_data = usuario_update.model_dump(exclude_unset=True)
        
        # Check username uniqueness and update references if being updated
        if "username" in update_data:
            new_username = update_data["username"]
            old_username = usuario.username
            
            if self.repository.exists_username(
                new_username,
                exclude_id=usuario_id
            ):
                raise DuplicateException(
                    resource="Usuario",
                    field="username",
                    value=new_username
                )
            
            # Update username in related tables (cascade update)
            self._update_username_references(old_username, new_username)
            
            usuario.username = new_username
            logger.info(f"Username updated from '{old_username}' to '{new_username}'")
        
        # Update other fields
        if "nombre" in update_data:
            usuario.nombre = update_data["nombre"]
        if "edad" in update_data:
            usuario.edad = update_data["edad"]
        if "telefono" in update_data:
            usuario.telefono = update_data["telefono"]
        
        # Save changes
        updated = self.repository.update(usuario, user_id=usuario_id)
        self.repository.commit()
        
        logger.info(f"Usuario {usuario_id} updated")
        
        return UsuarioUpdateResponse(
            username=updated.username,
            nombre=updated.nombre,
            edad=updated.edad,
            telefono=updated.telefono
        )
    
    def delete_usuario(self, usuario_id: str) -> None:
        """
        Delete a usuario (soft delete).
        
        Args:
            usuario_id: Usuario ID
            
        Raises:
            NotFoundException: If usuario not found
            BusinessException: If usuario is already deleted
        """
        validate_uuid(usuario_id, "usuario_id")
        usuario = self.repository.get_by_id_or_fail(usuario_id)
        
        if usuario.is_deleted:
            raise BusinessException("El usuario ya está eliminado")
        
        self.repository.delete(usuario, user_id=usuario_id, hard=False)
        self.repository.commit()
        
        logger.info(f"Usuario {usuario_id} deleted")
    
    def restore_usuario(self, usuario_id: str) -> Usuario:
        """
        Restore a soft-deleted usuario.
        
        Args:
            usuario_id: Usuario ID
            
        Returns:
            Restored usuario
            
        Raises:
            NotFoundException: If usuario not found
            BusinessException: If usuario is not deleted
        """
        validate_uuid(usuario_id, "usuario_id")
        usuario = self.repository.get_by_id_or_fail(usuario_id)
        
        if not usuario.is_deleted:
            raise BusinessException("El usuario no está eliminado")
        
        restored = self.repository.restore(usuario, user_id=usuario_id)
        self.repository.commit()
        
        logger.info(f"Usuario {usuario_id} restored")
        
        return self._to_response_model(restored)
    
    def change_password(
        self,
        usuario_id: str,
        current_password: str,
        new_password: str
    ) -> None:
        """
        Change a usuario's password.
        
        Args:
            usuario_id: Usuario ID
            current_password: Current password for verification
            new_password: New password to set
            
        Raises:
            NotFoundException: If usuario not found
            ValidationException: If current password is incorrect
        """
        validate_uuid(usuario_id, "usuario_id")
        usuario = self.repository.get_by_id_or_fail(usuario_id)
        
        # Verify current password
        if not verify_password(
            usuario.password_salt,
            usuario.password_hash,
            current_password
        ):
            raise ValidationException(
                message="Contraseña actual incorrecta",
                field="current_password"
            )
        
        # Hash new password
        salt_hex, hash_hex = hash_password(new_password)
        usuario.password_salt = salt_hex
        usuario.password_hash = hash_hex
        
        # Save changes
        self.repository.update(usuario, user_id=usuario_id)
        self.repository.commit()
        
        logger.info(f"Password changed for usuario {usuario_id}")
    
    def _update_username_references(self, old_username: str, new_username: str) -> None:
        """
        Update username references in all related tables (cascade update).
        
        This ensures data integrity when a username changes by updating:
        - mascotas.propietario (for clients)
        - citas.veterinario (for veterinarians)
        - vacunas.veterinario (for veterinarians)
        - facturas.veterinario (for veterinarians)
        - recetas.veterinario (for veterinarians)
        
        Args:
            old_username: The username to be replaced
            new_username: The new username to use
        """
        from database.models import MascotaORM, CitaORM, VacunaORM, FacturaORM, RecetaORM
        
        db = self.repository.db
        
        try:
            # Update mascotas.propietario (clients)
            mascotas_updated = db.query(MascotaORM).filter(
                MascotaORM.propietario == old_username
            ).update({MascotaORM.propietario: new_username}, synchronize_session=False)
            
            # Update citas.veterinario (veterinarians)
            citas_updated = db.query(CitaORM).filter(
                CitaORM.veterinario == old_username
            ).update({CitaORM.veterinario: new_username}, synchronize_session=False)
            
            # Update vacunas.veterinario (veterinarians)
            vacunas_updated = db.query(VacunaORM).filter(
                VacunaORM.veterinario == old_username
            ).update({VacunaORM.veterinario: new_username}, synchronize_session=False)
            
            # Update facturas.veterinario (veterinarians)
            facturas_updated = db.query(FacturaORM).filter(
                FacturaORM.veterinario == old_username
            ).update({FacturaORM.veterinario: new_username}, synchronize_session=False)
            
            # Update recetas.veterinario (veterinarians)
            recetas_updated = db.query(RecetaORM).filter(
                RecetaORM.veterinario == old_username
            ).update({RecetaORM.veterinario: new_username}, synchronize_session=False)
            
            db.flush()
            
            logger.info(
                f"Username references updated: "
                f"{mascotas_updated} mascotas, "
                f"{citas_updated} citas, "
                f"{vacunas_updated} vacunas, "
                f"{facturas_updated} facturas, "
                f"{recetas_updated} recetas"
            )
        except Exception as e:
            logger.error(f"Error updating username references: {e}")
            raise DatabaseException(f"Error actualizando referencias del usuario: {str(e)}")
    
    def _to_response_model(self, usuario: UsuarioORM) -> Usuario:
        """
        Convert ORM model to Pydantic response model.
        
        Args:
            usuario: ORM instance
            
        Returns:
            Pydantic Usuario model
        """
        return Usuario(
            id_usuario=usuario.id,
            username=usuario.username,
            nombre=usuario.nombre,
            edad=usuario.edad,
            telefono=usuario.telefono,
            role=usuario.role,
            fecha_creacion=usuario.fecha_creacion,
            is_deleted=usuario.is_deleted
        )
    
    def _to_response_dict(self, usuario: UsuarioORM) -> Dict[str, Any]:
        """
        Convert ORM model to dictionary for response.
        
        Args:
            usuario: ORM instance
            
        Returns:
            Dictionary with usuario data
        """
        return {
            "id_usuario": usuario.id,
            "username": usuario.username,
            "nombre": usuario.nombre,
            "edad": usuario.edad,
            "telefono": usuario.telefono,
            "role": usuario.role,
            "fecha_creacion": usuario.fecha_creacion,
            "is_deleted": usuario.is_deleted,
        }
