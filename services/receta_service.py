"""
Service for Receta business logic.

Handles all business operations related to recetas (prescriptions) with lineas (medication lines).
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from services.base_service import BaseService
from repositories.receta_repository import RecetaRepository
from repositories.cita_repository import CitaRepository
from repositories.mascota_repository import MascotaRepository
from repositories.usuario_repository import UsuarioRepository
from database.models import RecetaORM, RecetaLineaORM, CitaORM, MascotaORM, UsuarioORM
from models.recetas import RecetaCreate, RecetaUpdate, Receta, RecetaSummary, RecetaLinea
from core.exceptions import (
    BusinessException,
    ValidationException,
    NotFoundException,
    ForbiddenException,
)
from core.security import validate_uuid
from core.pagination import calculate_skip

logger = logging.getLogger(__name__)


class RecetaService(BaseService[RecetaORM, RecetaRepository]):
    """Service for managing receta business logic."""
    
    def __init__(
        self,
        receta_repository: RecetaRepository,
        cita_repository: CitaRepository,
        mascota_repository: MascotaRepository,
        usuario_repository: UsuarioRepository
    ):
        """
        Initialize receta service.
        
        Args:
            receta_repository: RecetaRepository instance
            cita_repository: CitaRepository instance
            mascota_repository: MascotaRepository instance
            usuario_repository: UsuarioRepository instance
        """
        super().__init__(receta_repository)
        self.cita_repo = cita_repository
        self.mascota_repo = mascota_repository
        self.usuario_repo = usuario_repository
    
    def create_receta(
        self,
        receta_data: RecetaCreate,
        current_user: UsuarioORM
    ) -> Receta:
        """
        Create a new receta with lineas.
        
        Args:
            receta_data: Receta creation data
            current_user: Current authenticated user (veterinario or admin)
            
        Returns:
            Created receta with lineas
            
        Raises:
            ValidationException: If data is invalid
            NotFoundException: If cita not found
            BusinessException: If cita already has receta
            ForbiddenException: If user doesn't have permission
        """
        # Get and validate cita
        cita = self.cita_repo.get_by_id_or_fail(str(receta_data.id_cita))
        
        if cita.is_deleted:
            raise BusinessException("No se puede crear una receta para una cita cancelada")
        
        # Check if cita already has receta
        existing_receta = self.repository.find_by_cita(cita.id)
        if existing_receta and not existing_receta.is_deleted:
            raise BusinessException("La cita ya tiene una receta asociada")
        
        # Validate veterinario permission
        if current_user.role == "veterinario" and cita.veterinario != current_user.username:
            raise ForbiddenException(
                "No autorizado: la cita está asignada a otro veterinario"
            )
        
        # Get mascota
        mascota = self.mascota_repo.get_by_id_or_fail(cita.id_mascota)
        
        if mascota.is_deleted:
            raise BusinessException("No se puede crear una receta para una mascota inactiva")
        
        # Create receta
        from utils.datetime_utils import get_local_now
        receta_orm = RecetaORM(
            id_cita=str(receta_data.id_cita),
            fecha_emision=get_local_now(),
            veterinario=current_user.username,  # Guardar username
            indicaciones=receta_data.indicaciones,
        )
        
        # Create lineas
        lineas_orm = []
        if receta_data.lineas:
            for linea_data in receta_data.lineas:
                linea_orm = RecetaLineaORM(
                    medicamento=linea_data.medicamento,
                    dosis=linea_data.dosis,
                    frecuencia=linea_data.frecuencia,
                    duracion=linea_data.duracion,
                )
                lineas_orm.append(linea_orm)
        
        created = self.repository.create_with_lineas(
            receta_orm,
            lineas_orm,
            user_id=current_user.id
        )
        self.repository.commit()
        
        logger.info(f"Receta {created.id} created for cita {cita.id} with {len(lineas_orm)} lineas")
        
        return self._to_response_model(created, cita, mascota)
    
    def get_receta(
        self,
        receta_id: str,
        current_user: UsuarioORM
    ) -> Receta:
        """
        Get a receta by ID with lineas.
        
        Args:
            receta_id: Receta ID
            current_user: Current authenticated user
            
        Returns:
            Receta data with lineas
            
        Raises:
            NotFoundException: If receta not found
            ForbiddenException: If user doesn't have access
        """
        validate_uuid(receta_id, "receta_id")
        receta = self.repository.get_by_id_with_lineas(receta_id)
        
        if not receta:
            raise NotFoundException("Receta", receta_id)
        
        # Check permissions
        cita = self.cita_repo.get_by_id_or_fail(receta.id_cita)
        mascota = self.mascota_repo.get_by_id_or_fail(cita.id_mascota)
        
        if current_user.role == "cliente":
            # Clientes can only view recetas for their own pets
            if mascota.propietario != current_user.username:
                raise ForbiddenException("No autorizado para ver esta receta")
        # Admin and veterinarios can view any receta (needed for clinical history)
        
        return self._to_response_model(receta, cita, mascota)
    
    def get_recetas(
        self,
        current_user: UsuarioORM,
        page: int = 0,
        page_size: int = 50,
        veterinario: Optional[str] = None,
        include_deleted: bool = False
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        Get list of recetas (summary without lineas).
        
        Args:
            current_user: Current authenticated user
            page: Page number (0-indexed)
            page_size: Items per page
            veterinario: Optional veterinario filter
            include_deleted: Include soft-deleted recetas
            
        Returns:
            Tuple of (list of receta summaries, total count)
        """
        skip = calculate_skip(page, page_size)
        
        # Apply role-based filtering
        if current_user.role == "admin":
            # Admin sees all recetas
            if veterinario:
                recetas = self.repository.find_by_veterinario(
                    veterinario=veterinario,
                    skip=skip,
                    limit=page_size,
                    include_deleted=include_deleted
                )
                total_count = self.repository.count_by_filters(
                    veterinario=veterinario,
                    include_deleted=include_deleted
                )
            else:
                recetas = self.repository.get_all(
                    skip=skip,
                    limit=page_size,
                    include_deleted=include_deleted,
                    order_by="fecha_emision",
                    order_desc=True
                )
                total_count = self.repository.count(include_deleted=include_deleted)
        elif current_user.role == "veterinario":
            # Veterinario sees only their own recetas in lists
            recetas = self.repository.find_by_veterinario_or_propietario(
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
            # Cliente sees only recetas for their own pets
            recetas = self.repository.find_by_propietario(
                propietario_username=current_user.username,
                skip=skip,
                limit=page_size,
                include_deleted=include_deleted
            )
            total_count = self.repository.count_by_filters(
                propietario_username=current_user.username,
                include_deleted=include_deleted
            )
        
        # Convert to summary (without lineas)
        response_list = []
        for receta in recetas:
            cita = self.cita_repo.get_by_id(receta.id_cita)
            mascota = self.mascota_repo.get_by_id(cita.id_mascota) if cita else None
            response_list.append(self._to_summary_dict(receta, cita, mascota))
        
        return response_list, total_count
    
    def get_recetas_by_mascota(
        self,
        mascota_id: str,
        page: int = 0,
        page_size: int = 50,
        include_deleted: bool = False
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        Get ALL recetas for a specific mascota (complete clinical history).
        
        This method returns ALL prescriptions for a pet, regardless of which
        veterinarian issued them. Used for viewing complete clinical history.
        
        Args:
            mascota_id: Mascota ID
            page: Page number (0-indexed)
            page_size: Items per page
            include_deleted: Include deleted recetas
            
        Returns:
            Tuple of (list of recetas, total count)
        """
        validate_uuid(mascota_id, "mascota_id")
        
        # Verify mascota exists
        mascota = self.mascota_repo.get_by_id_or_fail(mascota_id)
        
        skip = page * page_size
        
        # Get ALL recetas for this mascota (via citas)
        recetas = self.repository.find_by_mascota(
            mascota_id=mascota_id,
            skip=skip,
            limit=page_size,
            include_deleted=include_deleted
        )
        
        # Count total - get all and count
        all_recetas = self.repository.find_by_mascota(
            mascota_id=mascota_id,
            skip=0,
            limit=100000,
            include_deleted=include_deleted
        )
        total_count = len(all_recetas)
        
        # Convert to summary (without lineas)
        response_list = []
        for receta in recetas:
            cita = self.cita_repo.get_by_id(receta.id_cita)
            response_list.append(self._to_summary_dict(receta, cita, mascota))
        
        return response_list, total_count
    
    def get_receta_by_cita(
        self,
        cita_id: str,
        current_user: UsuarioORM
    ) -> Optional[Receta]:
        """
        Get receta for a specific cita.
        
        Args:
            cita_id: Cita ID
            current_user: Current authenticated user
            
        Returns:
            Receta or None if not found
        """
        validate_uuid(cita_id, "cita_id")
        
        receta = self.repository.find_by_cita(cita_id)
        if not receta:
            return None
        
        # Check permissions
        cita = self.cita_repo.get_by_id_or_fail(cita_id)
        mascota = self.mascota_repo.get_by_id_or_fail(cita.id_mascota)
        
        if current_user.role == "cliente":
            # Clientes can only view recetas for their own pets
            if mascota.propietario != current_user.username:
                raise ForbiddenException("No autorizado para ver esta receta")
        # Admin and veterinarios can view any receta (needed for clinical history)
        
        return self._to_response_model(receta, cita, mascota)
    
    def update_receta(
        self,
        receta_id: str,
        receta_update: RecetaUpdate,
        current_user: UsuarioORM
    ) -> Receta:
        """
        Update a receta (including lineas).
        
        Args:
            receta_id: Receta ID
            receta_update: Update data
            current_user: Current authenticated user
            
        Returns:
            Updated receta
            
        Raises:
            NotFoundException: If receta not found
            ForbiddenException: If user doesn't have permission
            BusinessException: If receta is deleted
        """
        validate_uuid(receta_id, "receta_id")
        receta = self.repository.get_by_id_with_lineas(receta_id)
        
        if not receta:
            raise NotFoundException("Receta", receta_id)
        
        # Validate not deleted
        self.validate_not_deleted(receta)
        
        # Only admin and the veterinarian who issued it can update
        if current_user.role not in ["admin", "veterinario"]:
            raise ForbiddenException("No autorizado para actualizar recetas")
        
        # Veterinarios can only update recetas they issued
        if current_user.role == "veterinario" and receta.veterinario != current_user.username:
            raise ForbiddenException("Solo puedes actualizar recetas que tú emitiste")
        
        # Apply updates (fecha_emision no se puede modificar)
        update_data = receta_update.model_dump(exclude_unset=True)
        
        if "indicaciones" in update_data:
            receta.indicaciones = update_data["indicaciones"]
        
        # Update lineas if provided
        if "lineas" in update_data and update_data["lineas"] is not None:
            new_lineas = []
            for linea_data in update_data["lineas"]:
                linea_orm = RecetaLineaORM(
                    medicamento=linea_data["medicamento"],
                    dosis=linea_data.get("dosis"),
                    frecuencia=linea_data.get("frecuencia"),
                    duracion=linea_data.get("duracion"),
                )
                new_lineas.append(linea_orm)
            
            self.repository.update_lineas(receta_id, new_lineas)
        
        updated = self.repository.update(receta, user_id=current_user.id)
        self.repository.commit()
        
        logger.info(f"Receta {receta_id} updated")
        
        # Reload with lineas
        updated_with_lineas = self.repository.get_by_id_with_lineas(receta_id)
        cita = self.cita_repo.get_by_id(updated_with_lineas.id_cita)
        mascota = self.mascota_repo.get_by_id(cita.id_mascota) if cita else None
        
        return self._to_response_model(updated_with_lineas, cita, mascota)
    
    def _get_owner_data(self, propietario_username: Optional[str]) -> Optional[UsuarioORM]:
        """Get owner usuario data."""
        if not propietario_username:
            return None
        return self.usuario_repo.find_by_username(propietario_username)
    
    def _to_response_model(
        self,
        receta: RecetaORM,
        cita: Optional[CitaORM] = None,
        mascota: Optional[MascotaORM] = None
    ) -> Receta:
        """Convert ORM to Pydantic response model with lineas."""
        if not cita:
            cita = self.cita_repo.get_by_id(receta.id_cita)
        if not mascota and cita:
            mascota = self.mascota_repo.get_by_id(cita.id_mascota)
        
        owner = self._get_owner_data(mascota.propietario if mascota else None)
        
        # Get veterinario name and phone from username
        vet = self.usuario_repo.find_by_username(receta.veterinario) if receta.veterinario else None
        veterinario_nombre = vet.nombre if vet else None
        veterinario_telefono = vet.telefono if vet else None
        
        # Convert lineas
        lineas_pydantic = []
        if hasattr(receta, 'lineas') and receta.lineas:
            for linea in receta.lineas:
                lineas_pydantic.append(RecetaLinea(
                    medicamento=linea.medicamento,
                    dosis=linea.dosis,
                    frecuencia=linea.frecuencia,
                    duracion=linea.duracion
                ))
        
        return Receta(
            id_receta=receta.id,
            id_cita=receta.id_cita,
            id_mascota=cita.id_mascota if cita else None,
            mascota_nombre=mascota.nombre if mascota else "",
            mascota_tipo=mascota.tipo if mascota else None,
            veterinario=receta.veterinario,  # username
            veterinario_nombre=veterinario_nombre,  # nombre completo
            veterinario_telefono=veterinario_telefono,  # teléfono
            propietario_username=owner.username if owner else (mascota.propietario if mascota else None),
            propietario_nombre=owner.nombre if owner else None,
            propietario_telefono=owner.telefono if owner else None,
            fecha_emision=receta.fecha_emision,
            indicaciones=receta.indicaciones,
            lineas=lineas_pydantic if lineas_pydantic else None
        )
    
    def _to_summary_dict(
        self,
        receta: RecetaORM,
        cita: Optional[CitaORM] = None,
        mascota: Optional[MascotaORM] = None
    ) -> Dict[str, Any]:
        """Convert ORM to dictionary summary (without lineas)."""
        if not cita:
            cita = self.cita_repo.get_by_id(receta.id_cita)
        if not mascota and cita:
            mascota = self.mascota_repo.get_by_id(cita.id_mascota)
        
        owner = self._get_owner_data(mascota.propietario if mascota else None)
        
        # Get veterinario name and phone from username
        vet = self.usuario_repo.find_by_username(receta.veterinario) if receta.veterinario else None
        veterinario_nombre = vet.nombre if vet else None
        veterinario_telefono = vet.telefono if vet else None
        
        return {
            "id_receta": receta.id,
            "id_cita": receta.id_cita,
            "id_mascota": cita.id_mascota if cita else None,
            "mascota_nombre": mascota.nombre if mascota else "",
            "veterinario": receta.veterinario,  # username
            "veterinario_nombre": veterinario_nombre,  # nombre completo
            "veterinario_telefono": veterinario_telefono,  # teléfono
            "propietario_username": owner.username if owner else (mascota.propietario if mascota else None),
            "propietario_nombre": owner.nombre if owner else None,
            "propietario_telefono": owner.telefono if owner else None,
            "fecha_emision": receta.fecha_emision,
            "is_deleted": receta.is_deleted,
        }
