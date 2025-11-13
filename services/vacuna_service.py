"""
Service for Vacuna business logic.

Handles all business operations related to vacunas (vaccines).
"""

from typing import List, Optional, Dict, Any
from datetime import date
import logging

from services.base_service import BaseService
from repositories.vacuna_repository import VacunaRepository
from repositories.mascota_repository import MascotaRepository
from repositories.usuario_repository import UsuarioRepository
from database.models import VacunaORM, MascotaORM, UsuarioORM
from models.vacunas import VacunaCreate, VacunaUpdate, Vacuna
from core.exceptions import (
    BusinessException,
    ValidationException,
    NotFoundException,
    ForbiddenException,
)
from core.security import validate_uuid, check_ownership_by_username
from core.utils import enum_to_value, normalize_stored_enum
from core.pagination import calculate_skip

logger = logging.getLogger(__name__)


class VacunaService(BaseService[VacunaORM, VacunaRepository]):
    """Service for managing vacuna business logic."""
    
    def __init__(
        self,
        vacuna_repository: VacunaRepository,
        mascota_repository: MascotaRepository,
        usuario_repository: UsuarioRepository
    ):
        """
        Initialize vacuna service.
        
        Args:
            vacuna_repository: VacunaRepository instance
            mascota_repository: MascotaRepository instance
            usuario_repository: UsuarioRepository instance
        """
        super().__init__(vacuna_repository)
        self.mascota_repo = mascota_repository
        self.usuario_repo = usuario_repository
    
    def create_vacuna(
        self,
        vacuna_data: VacunaCreate,
        current_user: UsuarioORM
    ) -> Vacuna:
        """
        Register a new vacuna.
        
        Args:
            vacuna_data: Vacuna creation data
            current_user: Current authenticated user (must be veterinario or admin)
            
        Returns:
            Created vacuna
            
        Raises:
            ValidationException: If data is invalid
            NotFoundException: If mascota not found
            ForbiddenException: If user doesn't have permission
        """
        # Validate mascota exists and is not deleted
        mascota = self.mascota_repo.get_by_id_or_fail(str(vacuna_data.id_mascota))
        
        if mascota.is_deleted:
            raise BusinessException(
                "No se puede registrar una vacuna para una mascota inactiva (eliminada)"
            )
        
        # Auto-generate fecha_aplicacion with today's date
        fecha_aplicacion = date.today()
        
        # Validate proxima_dosis if provided
        if vacuna_data.proxima_dosis:
            if vacuna_data.proxima_dosis <= fecha_aplicacion:
                raise ValidationException(
                    message="La próxima dosis debe ser posterior a la fecha de aplicación",
                    field="proxima_dosis"
                )
        
        # Create vacuna ORM
        vacuna_orm = VacunaORM(
            id_mascota=str(vacuna_data.id_mascota),
            tipo_vacuna=enum_to_value(vacuna_data.tipo_vacuna),
            fecha_aplicacion=fecha_aplicacion,
            veterinario=current_user.username,  # Guardar username
            lote_vacuna=vacuna_data.lote_vacuna,
            proxima_dosis=vacuna_data.proxima_dosis,
        )
        
        created = self.repository.create(vacuna_orm, user_id=current_user.id)
        self.repository.commit()
        
        logger.info(f"Vacuna {created.id} registered for mascota {mascota.id} by {current_user.username}")
        
        return self._to_response_model(created, mascota)
    
    def get_vacuna(
        self,
        vacuna_id: str,
        current_user: UsuarioORM
    ) -> Vacuna:
        """
        Get a vacuna by ID.
        
        Args:
            vacuna_id: Vacuna ID
            current_user: Current authenticated user
            
        Returns:
            Vacuna data
            
        Raises:
            NotFoundException: If vacuna not found
            ForbiddenException: If user doesn't have access
        """
        validate_uuid(vacuna_id, "vacuna_id")
        vacuna = self.repository.get_by_id_or_fail(vacuna_id)
        
        # Check permissions
        mascota = self.mascota_repo.get_by_id_or_fail(vacuna.id_mascota)
        
        if current_user.role == "cliente":
            # Clientes can only view vacunas for their own pets
            if mascota.propietario != current_user.username:
                raise ForbiddenException("No autorizado para ver esta vacuna")
        # Admin and veterinarios can view any vacuna (needed for clinical history)
        
        return self._to_response_model(vacuna, mascota)
    
    def get_vacunas(
        self,
        current_user: UsuarioORM,
        page: int = 0,
        page_size: int = 50,
        tipo_vacuna: Optional[str] = None,
        veterinario: Optional[str] = None,
        id_mascota: Optional[str] = None,
        mascota_nombre: Optional[str] = None,
        include_deleted: bool = False
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        Get list of vacunas with filters based on user permissions.
        
        Filters are applied BEFORE pagination, so search results span all pages.
        Results are ordered by fecha_aplicacion ASC (closest date first).
        
        Args:
            current_user: Current authenticated user
            page: Page number (0-indexed)
            page_size: Items per page
            tipo_vacuna: Optional tipo_vacuna filter
            veterinario: Optional veterinario filter (partial match)
            id_mascota: Optional mascota ID filter
            mascota_nombre: Optional mascota name filter (partial match)
            include_deleted: Include soft-deleted vacunas
            
        Returns:
            Tuple of (list of vacunas, total count)
        """
        skip = calculate_skip(page, page_size)
        
        # Apply role-based filtering
        if current_user.role == "admin" or current_user.role == "veterinario":
            # Admin and Veterinario see all vacunas with filters
            # mascota_nombre puede ser búsqueda libre (nombre mascota o propietario)
            vacunas = self.repository.find_by_multiple_filters(
                tipo_vacuna=tipo_vacuna,
                veterinario=veterinario,
                id_mascota=id_mascota,
                search_term=mascota_nombre,  # Búsqueda libre
                skip=skip,
                limit=page_size,
                include_deleted=include_deleted
            )
            
            total_count = self.repository.count_by_filters(
                tipo_vacuna=tipo_vacuna,
                veterinario=veterinario,
                id_mascota=id_mascota,
                search_term=mascota_nombre,
                include_deleted=include_deleted
            )
        else:
            # Cliente sees only vacunas for their own pets
            # Si hay búsqueda, aplicar sobre sus mascotas; sino, mostrar todas sus mascotas
            vacunas = self.repository.find_by_multiple_filters(
                tipo_vacuna=tipo_vacuna,
                veterinario=veterinario,
                id_mascota=id_mascota,
                propietario_username=current_user.username,  # Siempre filtrar por propietario
                search_term=mascota_nombre,  # Búsqueda adicional dentro de sus mascotas
                skip=skip,
                limit=page_size,
                include_deleted=include_deleted
            )
            total_count = self.repository.count_by_filters(
                tipo_vacuna=tipo_vacuna,
                veterinario=veterinario,
                id_mascota=id_mascota,
                propietario_username=current_user.username,
                search_term=mascota_nombre,
                include_deleted=include_deleted
            )
        
        # Enrich with mascota and owner data
        response_list = []
        for vacuna in vacunas:
            mascota = self.mascota_repo.get_by_id(vacuna.id_mascota)
            response_list.append(self._to_response_dict(vacuna, mascota))
        
        return response_list, total_count
    
    def get_vacunas_by_mascota(
        self,
        mascota_id: str,
        page: int = 0,
        page_size: int = 50,
        include_deleted: bool = False
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        Get ALL vacunas for a specific mascota (complete clinical history).
        
        This method returns ALL vaccines for a pet, regardless of which
        veterinarian applied them. Used for viewing complete clinical history.
        
        Args:
            mascota_id: Mascota ID
            page: Page number (0-indexed)
            page_size: Items per page
            include_deleted: Include deleted vacunas
            
        Returns:
            Tuple of (list of vacunas, total count)
        """
        validate_uuid(mascota_id, "mascota_id")
        
        # Verify mascota exists
        mascota = self.mascota_repo.get_by_id_or_fail(mascota_id)
        
        skip = page * page_size
        
        # Get ALL vacunas for this mascota
        vacunas = self.repository.find_by_mascota(
            id_mascota=mascota_id,
            skip=skip,
            limit=page_size,
            include_deleted=include_deleted
        )
        
        # Count total - get all and count
        all_vacunas = self.repository.find_by_mascota(
            id_mascota=mascota_id,
            skip=0,
            limit=100000,
            include_deleted=include_deleted
        )
        total_count = len(all_vacunas)
        
        # Enrich with data
        response_list = []
        for vacuna in vacunas:
            response_list.append(self._to_response_dict(vacuna, mascota))
        
        return response_list, total_count
    
    def update_vacuna(
        self,
        vacuna_id: str,
        vacuna_update: VacunaUpdate,
        current_user: UsuarioORM
    ) -> Vacuna:
        """
        Update a vacuna.
        
        Args:
            vacuna_id: Vacuna ID
            vacuna_update: Update data
            current_user: Current authenticated user
            
        Returns:
            Updated vacuna
            
        Raises:
            NotFoundException: If vacuna not found
            ForbiddenException: If user doesn't have permission
            ValidationException: If data is invalid
            BusinessException: If vacuna is deleted
        """
        validate_uuid(vacuna_id, "vacuna_id")
        vacuna = self.repository.get_by_id_or_fail(vacuna_id)
        
        # Validate not deleted
        self.validate_not_deleted(vacuna)
        
        # Only admin and the veterinarian who applied it can update
        if current_user.role not in ["admin", "veterinario"]:
            raise ForbiddenException("Solo administradores y veterinarios pueden actualizar vacunas")
        
        # Veterinarios can only update vacunas they applied
        if current_user.role == "veterinario" and vacuna.veterinario != current_user.username:
            raise ForbiddenException("Solo puedes actualizar vacunas que tú aplicaste")
        
        update_data = vacuna_update.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            if field == "tipo_vacuna" and value:
                setattr(vacuna, field, enum_to_value(value))
            elif value is not None:
                setattr(vacuna, field, value)
        
        # Validate proxima_dosis if updated
        if vacuna.proxima_dosis and vacuna.proxima_dosis <= vacuna.fecha_aplicacion:
            raise ValidationException(
                message="La próxima dosis debe ser posterior a la fecha de aplicación",
                field="proxima_dosis"
            )
        
        updated = self.repository.update(vacuna, user_id=current_user.id)
        self.repository.commit()
        
        logger.info(f"Vacuna {vacuna_id} updated")
        
        mascota = self.mascota_repo.get_by_id(updated.id_mascota)
        return self._to_response_model(updated, mascota)
    
    def delete_vacuna(
        self,
        vacuna_id: str,
        current_user: UsuarioORM
    ) -> None:
        """
        Delete a vacuna (soft delete).
        
        Args:
            vacuna_id: Vacuna ID
            current_user: Current authenticated user
            
        Raises:
            NotFoundException: If vacuna not found
            ForbiddenException: If user doesn't have permission
        """
        validate_uuid(vacuna_id, "vacuna_id")
        vacuna = self.repository.get_by_id_or_fail(vacuna_id)
        
        if vacuna.is_deleted:
            raise BusinessException("La vacuna ya está eliminada")
        
        # Admin or the veterinarian who applied it can delete
        if current_user.role == "admin":
            # Admin can delete any vacuna
            pass
        elif current_user.role == "veterinario":
            # Veterinario can only delete vacunas they applied
            if vacuna.veterinario != current_user.username:
                raise ForbiddenException("Solo puedes eliminar vacunas que tú aplicaste")
        else:
            raise ForbiddenException("Solo administradores y veterinarios pueden eliminar vacunas")
        
        self.repository.delete(vacuna, user_id=current_user.id, hard=False)
        self.repository.commit()
        
        logger.info(f"Vacuna {vacuna_id} deleted")
    
    def get_proximas_dosis(
        self,
        current_user: UsuarioORM,
        fecha_limite: Optional[date] = None
    ) -> List[Vacuna]:
        """
        Get vacunas with upcoming next doses.
        
        Args:
            current_user: Current authenticated user
            fecha_limite: Optional date limit
            
        Returns:
            List of vacunas with upcoming doses
        """
        vacunas = self.repository.find_proximas_dosis(
            fecha_limite=fecha_limite,
            skip=0,
            limit=100
        )
        
        # Filter by permissions
        result = []
        for vacuna in vacunas:
            mascota = self.mascota_repo.get_by_id(vacuna.id_mascota)
            if mascota:
                if (current_user.role == "admin" or 
                    current_user.role == "veterinario" or
                    mascota.propietario == current_user.username):
                    result.append(self._to_response_model(vacuna, mascota))
        
        return result
    
    def _get_owner_data(self, propietario_username: Optional[str]) -> Optional[UsuarioORM]:
        """Get owner usuario data."""
        if not propietario_username:
            return None
        return self.usuario_repo.find_by_username(propietario_username)
    
    def _to_response_model(self, vacuna: VacunaORM, mascota: Optional[MascotaORM] = None) -> Vacuna:
        """Convert ORM to Pydantic response model."""
        if not mascota:
            mascota = self.mascota_repo.get_by_id(vacuna.id_mascota)
        
        owner = self._get_owner_data(mascota.propietario if mascota else None)
        
        # Get veterinario name and phone from username
        vet = self.usuario_repo.find_by_username(vacuna.veterinario) if vacuna.veterinario else None
        veterinario_nombre = vet.nombre if vet else None
        veterinario_telefono = vet.telefono if vet else None
        
        return Vacuna(
            id_vacuna=vacuna.id,
            id_mascota=vacuna.id_mascota,
            mascota_nombre=mascota.nombre if mascota else "",
            propietario_username=owner.username if owner else (mascota.propietario if mascota else None),
            propietario_nombre=owner.nombre if owner else None,
            propietario_telefono=owner.telefono if owner else None,
            tipo_vacuna=normalize_stored_enum(vacuna.tipo_vacuna),
            fecha_aplicacion=vacuna.fecha_aplicacion,
            veterinario=vacuna.veterinario,  # username
            veterinario_nombre=veterinario_nombre,  # nombre completo
            veterinario_telefono=veterinario_telefono,  # teléfono
            lote_vacuna=vacuna.lote_vacuna,
            proxima_dosis=vacuna.proxima_dosis
        )
    
    def _to_response_dict(self, vacuna: VacunaORM, mascota: Optional[MascotaORM] = None) -> Dict[str, Any]:
        """Convert ORM to dictionary for response."""
        if not mascota:
            mascota = self.mascota_repo.get_by_id(vacuna.id_mascota)
        
        owner = self._get_owner_data(mascota.propietario if mascota else None)
        
        # Get veterinario name and phone from username
        vet = self.usuario_repo.find_by_username(vacuna.veterinario) if vacuna.veterinario else None
        veterinario_nombre = vet.nombre if vet else None
        veterinario_telefono = vet.telefono if vet else None
        
        return {
            "id_vacuna": vacuna.id,
            "id_mascota": vacuna.id_mascota,
            "mascota_nombre": mascota.nombre if mascota else "",
            "propietario_username": owner.username if owner else (mascota.propietario if mascota else None),
            "propietario_nombre": owner.nombre if owner else None,
            "propietario_telefono": owner.telefono if owner else None,
            "tipo_vacuna": normalize_stored_enum(vacuna.tipo_vacuna),
            "fecha_aplicacion": vacuna.fecha_aplicacion,
            "veterinario": vacuna.veterinario,  # username
            "veterinario_nombre": veterinario_nombre,  # nombre completo
            "veterinario_telefono": veterinario_telefono,  # teléfono
            "lote_vacuna": vacuna.lote_vacuna,
            "proxima_dosis": vacuna.proxima_dosis,
            "is_deleted": vacuna.is_deleted,
        }
