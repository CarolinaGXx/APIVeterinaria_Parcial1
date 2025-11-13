"""
Service for Factura business logic.

Handles all business operations related to facturas (invoices).
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import uuid4
import logging
from utils.datetime_utils import get_local_now

from services.base_service import BaseService
from repositories.factura_repository import FacturaRepository
from repositories.cita_repository import CitaRepository
from repositories.vacuna_repository import VacunaRepository
from repositories.mascota_repository import MascotaRepository
from repositories.usuario_repository import UsuarioRepository
from database.models import FacturaORM, CitaORM, VacunaORM, MascotaORM, UsuarioORM
from database.db import generar_numero_factura_uuid
from models.facturas import FacturaCreate, FacturaUpdate, Factura
from core.exceptions import (
    BusinessException,
    ValidationException,
    NotFoundException,
    ForbiddenException,
)
from core.security import validate_uuid
from core.utils import enum_to_value, normalize_stored_enum
from core.pagination import calculate_skip

logger = logging.getLogger(__name__)


class FacturaService(BaseService[FacturaORM, FacturaRepository]):
    """Service for managing factura business logic."""
    
    def __init__(
        self,
        factura_repository: FacturaRepository,
        cita_repository: CitaRepository,
        vacuna_repository: VacunaRepository,
        mascota_repository: MascotaRepository,
        usuario_repository: UsuarioRepository
    ):
        """
        Initialize factura service.
        
        Args:
            factura_repository: FacturaRepository instance
            cita_repository: CitaRepository instance
            vacuna_repository: VacunaRepository instance
            mascota_repository: MascotaRepository instance
            usuario_repository: UsuarioRepository instance
        """
        super().__init__(factura_repository)
        self.cita_repo = cita_repository
        self.vacuna_repo = vacuna_repository
        self.mascota_repo = mascota_repository
        self.usuario_repo = usuario_repository
    
    def create_factura(
        self,
        factura_data: FacturaCreate,
        current_user: UsuarioORM
    ) -> Factura:
        """
        Create a new factura.
        
        Args:
            factura_data: Factura creation data (with id_cita or id_vacuna)
            current_user: Current authenticated user (veterinario or admin)
            
        Returns:
            Created factura
            
        Raises:
            ValidationException: If data is invalid
            NotFoundException: If cita or vacuna not found
            BusinessException: If cita/vacuna already has factura
            ForbiddenException: If user doesn't have permission
        """
        id_mascota = None
        veterinario_origen = None
        
        # Determine if it's a cita or vacuna
        if factura_data.id_cita:
            # Get and validate cita
            cita = self.cita_repo.get_by_id_or_fail(str(factura_data.id_cita))
            
            if cita.is_deleted:
                raise BusinessException("No se puede crear una factura para una cita cancelada")
            
            # Check if cita already has factura
            existing_factura = self.repository.find_by_cita(cita.id)
            if existing_factura and not existing_factura.is_deleted:
                raise BusinessException("La cita ya tiene una factura asociada")
            
            id_mascota = cita.id_mascota
            veterinario_origen = cita.veterinario
            
        elif factura_data.id_vacuna:
            # Get and validate vacuna
            vacuna = self.vacuna_repo.get_by_id_or_fail(str(factura_data.id_vacuna))
            
            if vacuna.is_deleted:
                raise BusinessException("No se puede crear una factura para una vacuna eliminada")
            
            # Check if vacuna already has factura
            existing_factura = self.repository.find_by_vacuna(vacuna.id)
            if existing_factura and not existing_factura.is_deleted:
                raise BusinessException("La vacuna ya tiene una factura asociada")
            
            id_mascota = vacuna.id_mascota
            veterinario_origen = vacuna.veterinario
        
        # Validate veterinario permission
        if current_user.role == "veterinario" and veterinario_origen != current_user.username:
            raise ForbiddenException(
                "No autorizado: la cita/vacuna está asignada a otro veterinario"
            )
        
        # Get mascota
        mascota = self.mascota_repo.get_by_id_or_fail(id_mascota)
        
        if mascota.is_deleted:
            raise BusinessException("No se puede crear una factura para una mascota inactiva")
        
        # Calculate total
        total = self._calculate_total(
            factura_data.valor_servicio,
            factura_data.iva,
            factura_data.descuento
        )
        
        # Generate factura ID and numero
        factura_id = str(uuid4())
        numero_factura = generar_numero_factura_uuid(factura_id)
        
        # Create factura
        factura_orm = FacturaORM(
            id=factura_id,
            numero_factura=numero_factura,
            id_cita=str(factura_data.id_cita) if factura_data.id_cita else None,
            id_vacuna=str(factura_data.id_vacuna) if factura_data.id_vacuna else None,
            id_mascota=id_mascota,
            fecha_factura=get_local_now(),
            tipo_servicio=enum_to_value(factura_data.tipo_servicio),
            descripcion=factura_data.descripcion,
            veterinario=current_user.username,  # Guardar username
            valor_servicio=factura_data.valor_servicio,
            iva=factura_data.iva,
            descuento=factura_data.descuento,
            total=total,
            estado="pendiente",
        )
        
        created = self.repository.create(factura_orm, user_id=current_user.id)
        
        # Mark cita as completada (only if it's a cita, not a vacuna)
        if factura_data.id_cita:
            cita.estado = "completada"
            self.cita_repo.update(cita, user_id=current_user.id)
        
        self.repository.commit()
        
        if factura_data.id_cita:
            logger.info(f"Factura {created.id} created for cita {factura_data.id_cita}")
        else:
            logger.info(f"Factura {created.id} created for vacuna {factura_data.id_vacuna}")
        
        return self._to_response_model(created, mascota)
    
    def get_factura(
        self,
        factura_id: str,
        current_user: UsuarioORM
    ) -> Factura:
        """
        Get a factura by ID.
        
        Args:
            factura_id: Factura ID
            current_user: Current authenticated user
            
        Returns:
            Factura data
            
        Raises:
            NotFoundException: If factura not found
            ForbiddenException: If user doesn't have access
        """
        validate_uuid(factura_id, "factura_id")
        factura = self.repository.get_by_id_or_fail(factura_id)
        
        # Check permissions
        mascota = self.mascota_repo.get_by_id_or_fail(factura.id_mascota)
        
        if current_user.role != "admin":
            # User must be the pet owner or the veterinario who issued the invoice
            if (mascota.propietario != current_user.username and 
                factura.veterinario != current_user.username):
                raise ForbiddenException("No autorizado para ver esta factura")
        
        return self._to_response_model(factura, mascota)
    
    def get_facturas(
        self,
        current_user: UsuarioORM,
        page: int = 0,
        page_size: int = 50,
        estado: Optional[str] = None,
        veterinario: Optional[str] = None,
        include_deleted: bool = False
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        Get list of facturas with filters based on user permissions.
        
        Args:
            current_user: Current authenticated user
            page: Page number (0-indexed)
            page_size: Items per page
            estado: Optional estado filter
            veterinario: Optional veterinario filter
            include_deleted: Include soft-deleted facturas
            
        Returns:
            Tuple of (list of facturas, total count)
        """
        skip = calculate_skip(page, page_size)
        
        # Apply role-based filtering
        if current_user.role == "admin":
            # Admin sees all facturas
            if estado:
                facturas = self.repository.find_by_estado(
                    estado=estado,
                    skip=skip,
                    limit=page_size,
                    include_deleted=include_deleted
                )
            elif veterinario:
                facturas = self.repository.find_by_veterinario(
                    veterinario=veterinario,
                    skip=skip,
                    limit=page_size,
                    include_deleted=include_deleted
                )
            else:
                facturas = self.repository.get_all(
                    skip=skip,
                    limit=page_size,
                    include_deleted=include_deleted,
                    order_by="fecha_factura",
                    order_desc=True
                )
            
            total_count = self.repository.count_by_filters(
                estado=estado,
                veterinario=veterinario,
                include_deleted=include_deleted
            )
        elif current_user.role == "veterinario":
            # Veterinario sees only their own facturas in lists
            facturas = self.repository.find_by_veterinario_or_propietario(
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
            # Cliente sees only facturas for their own pets
            facturas = self.repository.find_by_propietario(
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
        for factura in facturas:
            mascota = self.mascota_repo.get_by_id(factura.id_mascota)
            response_list.append(self._to_response_dict(factura, mascota))
        
        return response_list, total_count
    
    def get_facturas_by_mascota(
        self,
        mascota_id: str,
        current_user: UsuarioORM,
        page: int = 0,
        page_size: int = 50,
        include_deleted: bool = False
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        Get facturas for a specific mascota with privacy restrictions.
        
        Privacy rules:
        - Pet owner (cliente): sees ALL invoices for their pet
        - Veterinarian: sees only invoices THEY issued for this pet
        - Admin: sees ALL invoices for this pet
        
        Args:
            mascota_id: Mascota ID
            current_user: Current authenticated user
            page: Page number (0-indexed)
            page_size: Items per page
            include_deleted: Include deleted facturas
            
        Returns:
            Tuple of (list of facturas, total count)
        """
        validate_uuid(mascota_id, "mascota_id")
        
        # Verify mascota exists
        mascota = self.mascota_repo.get_by_id_or_fail(mascota_id)
        
        skip = page * page_size
        
        # Apply privacy filters based on role
        if current_user.role == "admin":
            # Admin sees ALL facturas for this mascota
            facturas = self.repository.find_by_mascota(
                id_mascota=mascota_id,
                skip=skip,
                limit=page_size,
                include_deleted=include_deleted
            )
            # Get total count
            all_facturas = self.repository.find_by_mascota(
                id_mascota=mascota_id,
                skip=0,
                limit=100000,
                include_deleted=include_deleted
            )
            total_count = len(all_facturas)
        elif current_user.role == "cliente":
            # Cliente sees ALL facturas for their own pet
            if mascota.propietario != current_user.username:
                raise ForbiddenException("No autorizado para ver facturas de esta mascota")
            
            facturas = self.repository.find_by_mascota(
                id_mascota=mascota_id,
                skip=skip,
                limit=page_size,
                include_deleted=include_deleted
            )
            # Get total count
            all_facturas = self.repository.find_by_mascota(
                id_mascota=mascota_id,
                skip=0,
                limit=100000,
                include_deleted=include_deleted
            )
            total_count = len(all_facturas)
        else:  # veterinario
            # Veterinarian sees only facturas THEY issued for this mascota
            facturas = self.repository.find_by_veterinario_and_mascota(
                veterinario=current_user.username,
                mascota_id=mascota_id,
                skip=skip,
                limit=page_size,
                include_deleted=include_deleted
            )
            # Get total count
            all_facturas = self.repository.find_by_veterinario_and_mascota(
                veterinario=current_user.username,
                mascota_id=mascota_id,
                skip=0,
                limit=100000,
                include_deleted=include_deleted
            )
            total_count = len(all_facturas)
        
        # Enrich with data
        response_list = []
        for factura in facturas:
            response_list.append(self._to_response_dict(factura, mascota))
        
        return response_list, total_count
    
    def update_factura(
        self,
        factura_id: str,
        factura_update: FacturaUpdate,
        current_user: UsuarioORM
    ) -> Factura:
        """
        Update a factura.
        
        Args:
            factura_id: Factura ID
            factura_update: Update data
            current_user: Current authenticated user
            
        Returns:
            Updated factura
            
        Raises:
            NotFoundException: If factura not found
            ForbiddenException: If user doesn't have permission
            BusinessException: If factura is deleted
        """
        validate_uuid(factura_id, "factura_id")
        factura = self.repository.get_by_id_or_fail(factura_id)
        
        # Validate not deleted
        self.validate_not_deleted(factura)
        
        # Only admin and the veterinarian who issued it can update
        if current_user.role not in ["admin", "veterinario"]:
            raise ForbiddenException("No autorizado para actualizar facturas")
        
        # Veterinarios can only update facturas they issued
        if current_user.role == "veterinario" and factura.veterinario != current_user.username:
            raise ForbiddenException("Solo puedes actualizar facturas que tú emitiste")
        
        # Apply updates
        update_data = factura_update.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            if field in ["tipo_servicio", "estado"] and value:
                setattr(factura, field, enum_to_value(value))
            elif value is not None:
                setattr(factura, field, value)
        
        # Recalculate total if financial fields changed
        if any(k in update_data for k in ["valor_servicio", "iva", "descuento"]):
            factura.total = self._calculate_total(
                factura.valor_servicio,
                factura.iva,
                factura.descuento
            )
        
        updated = self.repository.update(factura, user_id=current_user.id)
        self.repository.commit()
        
        logger.info(f"Factura {factura_id} updated")
        
        mascota = self.mascota_repo.get_by_id(updated.id_mascota)
        return self._to_response_model(updated, mascota)
    
    def mark_as_paid(
        self,
        factura_id: str,
        current_user: UsuarioORM
    ) -> Factura:
        """
        Mark a factura as paid.
        
        Args:
            factura_id: Factura ID
            current_user: Current authenticated user
            
        Returns:
            Updated factura
        """
        validate_uuid(factura_id, "factura_id")
        factura = self.repository.get_by_id_or_fail(factura_id)
        
        if factura.estado == "pagada":
            raise BusinessException("La factura ya está marcada como pagada")
        
        if factura.estado == "anulada":
            raise BusinessException("No se puede marcar como pagada una factura anulada")
        
        # Veterinarios can only mark as paid facturas they issued
        if current_user.role == "veterinario" and factura.veterinario != current_user.username:
            raise ForbiddenException("Solo puedes marcar como pagada facturas que tú emitiste")
        
        factura.estado = "pagada"
        updated = self.repository.update(factura, user_id=current_user.id)
        self.repository.commit()
        
        logger.info(f"Factura {factura_id} marked as paid")
        
        mascota = self.mascota_repo.get_by_id(updated.id_mascota)
        return self._to_response_model(updated, mascota)
    
    def anular_factura(
        self,
        factura_id: str,
        current_user: UsuarioORM
    ) -> None:
        """
        Anular a factura (change estado to anulada and soft delete).
        
        Args:
            factura_id: Factura ID
            current_user: Current authenticated user
        """
        validate_uuid(factura_id, "factura_id")
        factura = self.repository.get_by_id_or_fail(factura_id)
        
        if factura.is_deleted or factura.estado == "anulada":
            raise BusinessException("La factura ya está anulada")
        
        # Admin or the veterinarian who issued it can anular
        if current_user.role == "admin":
            # Admin can anular any factura
            pass
        elif current_user.role == "veterinario":
            # Veterinario can only anular facturas they issued
            if factura.veterinario != current_user.username:
                raise ForbiddenException("Solo puedes anular facturas que tú emitiste")
        else:
            raise ForbiddenException("Solo administradores y veterinarios pueden anular facturas")
        
        # Change estado to anulada
        factura.estado = "anulada"
        self.repository.update(factura, user_id=current_user.id)
        
        # Soft delete (marca is_deleted, deleted_at, deleted_by)
        self.repository.delete(factura, user_id=current_user.id, hard=False)
        self.repository.commit()
        
        logger.info(f"Factura {factura_id} anulada and soft deleted by user {current_user.id}")
    
    def _calculate_total(
        self,
        valor_servicio: float,
        iva: float,
        descuento: float
    ) -> float:
        """Calculate factura total."""
        return (valor_servicio + iva) - descuento
    
    def _get_owner_data(self, propietario_username: Optional[str]) -> Optional[UsuarioORM]:
        """Get owner usuario data."""
        if not propietario_username:
            return None
        return self.usuario_repo.find_by_username(propietario_username)
    
    def _to_response_model(self, factura: FacturaORM, mascota: Optional[MascotaORM] = None) -> Factura:
        """Convert ORM to Pydantic response model."""
        if not mascota:
            mascota = self.mascota_repo.get_by_id(factura.id_mascota)
        
        owner = self._get_owner_data(mascota.propietario if mascota else None)
        
        # Get veterinario name and phone from username
        vet = self.usuario_repo.find_by_username(factura.veterinario) if factura.veterinario else None
        veterinario_nombre = vet.nombre if vet else None
        veterinario_telefono = vet.telefono if vet else None
        
        return Factura(
            id_factura=factura.id,
            numero_factura=factura.numero_factura,
            id_mascota=factura.id_mascota,
            id_cita=factura.id_cita,
            id_vacuna=factura.id_vacuna,
            mascota_nombre=mascota.nombre if mascota else "",
            mascota_tipo=mascota.tipo if mascota else None,
            propietario_username=owner.username if owner else (mascota.propietario if mascota else None),
            propietario_nombre=owner.nombre if owner else None,
            propietario_telefono=owner.telefono if owner else None,
            fecha_factura=factura.fecha_factura,
            tipo_servicio=normalize_stored_enum(factura.tipo_servicio),
            descripcion=factura.descripcion,
            veterinario=factura.veterinario,  # username
            veterinario_nombre=veterinario_nombre,  # nombre completo
            veterinario_telefono=veterinario_telefono,  # teléfono
            valor_servicio=factura.valor_servicio,
            iva=factura.iva,
            descuento=factura.descuento,
            total=factura.total,
            estado=normalize_stored_enum(factura.estado)
        )
    
    def _to_response_dict(self, factura: FacturaORM, mascota: Optional[MascotaORM] = None) -> Dict[str, Any]:
        """Convert ORM to dictionary for response."""
        if not mascota:
            mascota = self.mascota_repo.get_by_id(factura.id_mascota)
        
        owner = self._get_owner_data(mascota.propietario if mascota else None)
        
        # Get veterinario name and phone from username
        vet = self.usuario_repo.find_by_username(factura.veterinario) if factura.veterinario else None
        veterinario_nombre = vet.nombre if vet else None
        veterinario_telefono = vet.telefono if vet else None
        
        return {
            "id_factura": factura.id,
            "numero_factura": factura.numero_factura,
            "id_mascota": factura.id_mascota,
            "id_cita": factura.id_cita,
            "id_vacuna": factura.id_vacuna,
            "mascota_nombre": mascota.nombre if mascota else "",
            "mascota_tipo": mascota.tipo if mascota else None,
            "propietario_username": owner.username if owner else (mascota.propietario if mascota else None),
            "propietario_nombre": owner.nombre if owner else None,
            "propietario_telefono": owner.telefono if owner else None,
            "fecha_factura": factura.fecha_factura,
            "tipo_servicio": normalize_stored_enum(factura.tipo_servicio),
            "descripcion": factura.descripcion,
            "veterinario": factura.veterinario,  # username
            "veterinario_nombre": veterinario_nombre,  # nombre completo
            "veterinario_telefono": veterinario_telefono,  # teléfono
            "valor_servicio": factura.valor_servicio,
            "iva": factura.iva,
            "descuento": factura.descuento,
            "total": factura.total,
            "estado": normalize_stored_enum(factura.estado),
            "is_deleted": factura.is_deleted,
        }
