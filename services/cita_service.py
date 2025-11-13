"""
Servicio para la lógica de negocio de Citas.
Gestiona todas las operaciones comerciales relacionadas con las citas.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
from utils.datetime_utils import get_local_now

from services.base_service import BaseService
from repositories.cita_repository import CitaRepository
from repositories.mascota_repository import MascotaRepository
from repositories.usuario_repository import UsuarioRepository
from database.models import CitaORM, MascotaORM, UsuarioORM
from models.citas import CitaCreate, CitaUpdate, Cita
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


class CitaService(BaseService[CitaORM, CitaRepository]):
    """Servicio para la lógica de negocio de Citas."""
    
    def __init__(
        self,
        cita_repository: CitaRepository,
        mascota_repository: MascotaRepository,
        usuario_repository: UsuarioRepository
    ):
        """
        Inicializa el servicio de citas.
        
        Args:
            cita_repository: CitaRepository instance
            mascota_repository: MascotaRepository instance
            usuario_repository: UsuarioRepository instance
        """
        super().__init__(cita_repository)
        self.mascota_repo = mascota_repository
        self.usuario_repo = usuario_repository
    
    def create_cita(
        self,
        cita_data: CitaCreate,
        current_user: UsuarioORM
    ) -> Cita:
        """
        Crea una nueva cita.
        
        Args:
            cita_data: Cita create data
            current_user: Current authenticated user
            
        Returns:
            Cita creada
            
        Raises:
            ValidationException: Si los datos son inválidos
            NotFoundException: Si mascota o veterinario no se encuentra
            ForbiddenException: Si el usuario no tiene permiso
        """
        # Validate fecha is not in the past
        fecha_cita = cita_data.fecha
        if fecha_cita.tzinfo is not None:
            fecha_cita = fecha_cita.replace(tzinfo=None)
        
        now_local = get_local_now().replace(tzinfo=None)
        if fecha_cita < now_local:
            raise ValidationException(
                message="No se puede agendar una cita con fecha anterior a la actual",
                field="fecha"
            )
        
        # Get and validate mascota
        mascota = self.mascota_repo.get_by_id_or_fail(str(cita_data.id_mascota))
        
        if mascota.is_deleted:
            raise BusinessException(
                "No se puede crear una cita para una mascota inactiva (eliminada)"
            )
        
        # Check ownership
        if current_user.role != "admin":
            check_ownership_by_username(
                current_username=current_user.username,
                owner_username=mascota.propietario,
                user_role=current_user.role,
                resource_name="mascota"
            )
        
        # Validate veterinario exists and has correct role (by username)
        veterinario = self.usuario_repo.find_by_username(cita_data.veterinario)
        if not veterinario or veterinario.role != "veterinario":
            raise ValidationException(
                message=f"Veterinario '{cita_data.veterinario}' no encontrado o no es veterinario",
                field="veterinario"
            )
        
        # Create cita - guardar username del veterinario
        cita_orm = CitaORM(
            id_mascota=str(cita_data.id_mascota),
            fecha=cita_data.fecha,
            motivo=cita_data.motivo,
            veterinario=cita_data.veterinario,  # Guardar username
            estado="pendiente",
        )
        
        created = self.repository.create(cita_orm, user_id=current_user.id)
        self.repository.commit()
        
        logger.info(f"Cita {created.id} created for mascota {mascota.id}")
        
        return self._to_response_model(created, mascota)
    
    def get_cita(
        self,
        cita_id: str,
        current_user: UsuarioORM
    ) -> Cita:
        """
        Obtiene una cita por ID.
        
        Args:
            cita_id: Cita ID
            current_user: Current authenticated user
            
        Returns:
            Cita data
            
        Raises:
            NotFoundException: If cita not found
            ForbiddenException: If user doesn't have access
        """
        validate_uuid(cita_id, "cita_id")
        cita = self.repository.get_by_id_or_fail(cita_id)
        
        # Check permissions
        mascota = self.mascota_repo.get_by_id_or_fail(cita.id_mascota)
        
        if current_user.role == "cliente":
            # Clientes can only view citas for their own pets
            if mascota.propietario != current_user.username:
                raise ForbiddenException("No autorizado para ver esta cita")
        # Admin and veterinarios can view any cita (needed for clinical history)
        
        return self._to_response_model(cita, mascota)
    
    def get_citas(
        self,
        current_user: UsuarioORM,
        page: int = 0,
        page_size: int = 50,
        estado: Optional[str] = None,
        veterinario: Optional[str] = None,
        include_deleted: bool = False
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        Obtiene una lista de citas con filtros basados en los permisos del usuario.
        
        Args:
            current_user: Current authenticated user
            page: Page number (0-indexed)
            page_size: Items per page
            estado: Optional estado filter
            veterinario: Optional veterinario filter
            include_deleted: Include soft-deleted citas
            
        Returns:
            Tuple of (list of citas, total count)
        """
        skip = calculate_skip(page, page_size)
        
        # Apply role-based filtering
        if current_user.role == "admin":
            # Admin sees all citas
            if estado:
                citas = self.repository.find_by_estado(
                    estado=estado,
                    skip=skip,
                    limit=page_size,
                    include_deleted=include_deleted
                )
            elif veterinario:
                citas = self.repository.find_by_veterinario(
                    veterinario=veterinario,
                    skip=skip,
                    limit=page_size,
                    include_deleted=include_deleted
                )
            else:
                citas = self.repository.get_all(
                    skip=skip,
                    limit=page_size,
                    include_deleted=include_deleted,
                    order_by="fecha",
                    order_desc=True
                )
            
            total_count = self.repository.count_by_filters(
                estado=estado,
                veterinario=veterinario,
                include_deleted=include_deleted
            )
        elif current_user.role == "veterinario":
            # Veterinario sees only their own citas in lists
            citas = self.repository.find_by_veterinario_or_propietario(
                username=current_user.username,
                skip=skip,
                limit=page_size,
                include_deleted=include_deleted
            )
            total_count = len(self.repository.find_by_veterinario_or_propietario(
                username=current_user.username,
                skip=0,
                limit=100000,
                include_deleted=include_deleted
            ))
        else:
            # Cliente sees only citas for their own pets
            citas = self.repository.find_by_propietario(
                propietario_username=current_user.username,
                skip=skip,
                limit=page_size,
                include_deleted=include_deleted
            )
            total_count = self.repository.count_by_filters(
                propietario_username=current_user.username,
                include_deleted=include_deleted
            )
        
        # Enrich with mascota and owner data
        response_list = []
        for cita in citas:
            mascota = self.mascota_repo.get_by_id(cita.id_mascota)
            response_list.append(self._to_response_dict(cita, mascota))
        
        return response_list, total_count
    
    def get_citas_by_mascota(
        self,
        mascota_id: str,
        page: int = 0,
        page_size: int = 50,
        include_deleted: bool = False
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        Get ALL citas for a specific mascota (complete clinical history).
        
        This method returns ALL appointments for a pet, regardless of which
        veterinarian attended them. Used for viewing complete clinical history.
        
        Args:
            mascota_id: Mascota ID
            page: Page number (0-indexed)
            page_size: Items per page
            include_deleted: Include deleted citas
            
        Returns:
            Tuple of (list of citas, total count)
        """
        validate_uuid(mascota_id, "mascota_id")
        
        # Verify mascota exists
        mascota = self.mascota_repo.get_by_id_or_fail(mascota_id)
        
        skip = page * page_size
        
        # Get ALL citas for this mascota
        citas = self.repository.find_by_mascota(
            id_mascota=mascota_id,
            skip=skip,
            limit=page_size,
            include_deleted=include_deleted
        )
        
        # Count total - get all and count
        all_citas = self.repository.find_by_mascota(
            id_mascota=mascota_id,
            skip=0,
            limit=100000,
            include_deleted=include_deleted
        )
        total_count = len(all_citas)
        
        # Enrich with data
        response_list = []
        for cita in citas:
            response_list.append(self._to_response_dict(cita, mascota))
        
        return response_list, total_count
    
    def update_cita(
        self,
        cita_id: str,
        cita_update: CitaUpdate,
        current_user: UsuarioORM
    ) -> Cita:
        """
        Update a cita.
        
        Args:
            cita_id: Cita ID
            cita_update: Update data
            current_user: Current authenticated user
            
        Returns:
            Updated cita
            
        Raises:
            NotFoundException: If cita not found
            ForbiddenException: If user doesn't have permission
            ValidationException: If update data is invalid
            BusinessException: If cita is deleted
        """
        validate_uuid(cita_id, "cita_id")
        cita = self.repository.get_by_id_or_fail(cita_id)
        
        # Validate not deleted
        self.validate_not_deleted(cita)
        
        # Get mascota for permission checks
        mascota = self.mascota_repo.get_by_id_or_fail(cita.id_mascota)
        
        # Apply updates with granular permission checks
        update_data = cita_update.model_dump(exclude_unset=True)
        
        # Campos que solo el propietario o admin pueden actualizar
        # Si es veterinario, simplemente IGNORAMOS estos campos (no lanzamos error)
        if current_user.role == "veterinario":
            # Veterinarios NO pueden cambiar fecha, motivo, veterinario - los removemos
            update_data.pop("fecha", None)
            update_data.pop("motivo", None)
            update_data.pop("veterinario", None)
        elif current_user.role != "admin":
            # Clientes solo pueden actualizar sus propias mascotas
            if any(field in update_data for field in ["fecha", "motivo", "veterinario"]):
                check_ownership_by_username(
                    current_username=current_user.username,
                    owner_username=mascota.propietario,
                    user_role=current_user.role,
                    resource_name="cita"
                )
        
        # Ahora aplicamos los campos permitidos
        if "fecha" in update_data:
            fecha_nueva = update_data["fecha"]
            if fecha_nueva.tzinfo is not None:
                fecha_nueva = fecha_nueva.replace(tzinfo=None)
            now_local = get_local_now().replace(tzinfo=None)
            if fecha_nueva < now_local:
                raise ValidationException(
                    message="No se puede actualizar con una fecha anterior a la actual",
                    field="fecha"
                )
            cita.fecha = fecha_nueva
        
        if "motivo" in update_data:
            cita.motivo = update_data["motivo"]
        
        if "veterinario" in update_data:
            # Validate new veterinario by username
            vet = self.usuario_repo.find_by_username(update_data["veterinario"])
            if not vet or vet.role != "veterinario":
                raise ValidationException(
                    message=f"Veterinario '{update_data['veterinario']}' no encontrado o no es veterinario",
                    field="veterinario"
                )
            cita.veterinario = update_data["veterinario"]  # Store username
        
        # Campos que el veterinario asignado puede actualizar (diagnóstico, tratamiento, estado)
        if any(field in update_data for field in ["diagnostico", "tratamiento", "estado"]):
            # Admin puede actualizar cualquier cosa
            if current_user.role == "admin":
                pass
            # Veterinario asignado puede actualizar sus propias citas
            elif current_user.role == "veterinario":
                if cita.veterinario != current_user.username:
                    raise ForbiddenException(
                        "Solo el veterinario asignado a esta cita puede actualizar el diagnóstico y tratamiento"
                    )
            # Propietario/cliente también puede actualizar si es su mascota
            else:
                check_ownership_by_username(
                    current_username=current_user.username,
                    owner_username=mascota.propietario,
                    user_role=current_user.role,
                    resource_name="cita"
                )
            
            if "estado" in update_data:
                cita.estado = update_data["estado"]
            
            if "diagnostico" in update_data:
                cita.diagnostico = update_data["diagnostico"]
            
            if "tratamiento" in update_data:
                cita.tratamiento = update_data["tratamiento"]
        
        updated = self.repository.update(cita, user_id=current_user.id)
        self.repository.commit()
        
        logger.info(f"Cita {cita_id} updated")
        
        return self._to_response_model(updated, mascota)
    
    def cancel_cita(
        self,
        cita_id: str,
        current_user: UsuarioORM
    ) -> None:
        """
        Cancel a cita (change estado to cancelada and soft delete).
        
        Args:
            cita_id: Cita ID
            current_user: Current authenticated user
            
        Raises:
            NotFoundException: If cita not found
            ForbiddenException: If user doesn't have permission
            BusinessException: If cita is already cancelled
        """
        validate_uuid(cita_id, "cita_id")
        cita = self.repository.get_by_id_or_fail(cita_id)
        
        if cita.is_deleted or cita.estado == "cancelada":
            raise BusinessException("La cita ya está cancelada")
        
        # Check permissions - solo admin o el propietario de la mascota pueden cancelar
        mascota = self.mascota_repo.get_by_id_or_fail(cita.id_mascota)
        
        if current_user.role == "veterinario":
            raise ForbiddenException(
                "Los veterinarios no pueden cancelar citas. Solo el propietario de la mascota o un administrador."
            )
        
        if current_user.role != "admin":
            check_ownership_by_username(
                current_username=current_user.username,
                owner_username=mascota.propietario,
                user_role=current_user.role,
                resource_name="cita"
            )
        
        # Change estado to cancelada
        cita.estado = "cancelada"
        self.repository.update(cita, user_id=current_user.id)
        
        # Soft delete (marca is_deleted, deleted_at, deleted_by)
        self.repository.delete(cita, user_id=current_user.id, hard=False)
        self.repository.commit()
        
        logger.info(f"Cita {cita_id} cancelled and soft deleted by user {current_user.id}")
    
    def _get_owner_data(self, propietario_username: Optional[str]) -> Optional[UsuarioORM]:
        """Get owner usuario data."""
        if not propietario_username:
            return None
        return self.usuario_repo.find_by_username(propietario_username)
    
    def _to_response_model(self, cita: CitaORM, mascota: Optional[MascotaORM] = None) -> Cita:
        """Convert ORM to Pydantic response model."""
        if not mascota:
            mascota = self.mascota_repo.get_by_id(cita.id_mascota)
        
        owner = self._get_owner_data(mascota.propietario if mascota else None)
        
        # Get veterinario name and phone from username
        vet = self.usuario_repo.find_by_username(cita.veterinario) if cita.veterinario else None
        veterinario_nombre = vet.nombre if vet else None
        veterinario_telefono = vet.telefono if vet else None
        
        return Cita(
            id_cita=cita.id,
            id_mascota=cita.id_mascota,
            mascota_nombre=mascota.nombre if mascota else "",
            propietario_username=owner.username if owner else (mascota.propietario if mascota else None),
            propietario_nombre=owner.nombre if owner else None,
            propietario_telefono=owner.telefono if owner else None,
            fecha=cita.fecha,
            motivo=cita.motivo,
            veterinario=cita.veterinario,  # username
            veterinario_nombre=veterinario_nombre,  # nombre completo
            veterinario_telefono=veterinario_telefono,  # teléfono
            diagnostico=cita.diagnostico if hasattr(cita, 'diagnostico') else None,
            tratamiento=cita.tratamiento if hasattr(cita, 'tratamiento') else None,
            estado=normalize_stored_enum(cita.estado),
            is_deleted=cita.is_deleted
        )
    
    def _to_response_dict(self, cita: CitaORM, mascota: Optional[MascotaORM] = None) -> Dict[str, Any]:
        """Convert ORM to dictionary for response."""
        # Cambiar a usar _to_response_model para mantener consistencia
        return self._to_response_model(cita, mascota).model_dump()
