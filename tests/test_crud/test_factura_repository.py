"""
Tests for Factura Repository CRUD operations.

Tests cover:
- Create operations
- Read operations (by ID, by filters)
- Update operations
- Delete operations (soft delete and restore)
- Filtering and pagination
- Relationships with other entities
"""

import pytest
from sqlalchemy.orm import Session
from datetime import date
from typing import List
from uuid import uuid4

from database.models import FacturaORM, MascotaORM, UsuarioORM, CitaORM, VacunaORM
from repositories.factura_repository import FacturaRepository
from database.db import generar_numero_factura_uuid
from core.exceptions import NotFoundException


class TestFacturaRepositoryCreate:
    """Tests for creating facturas."""
    
    def test_create_factura_exitoso(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test creating a factura successfully."""
        repo = FacturaRepository(db_session)
        
        factura_id = str(uuid4())
        factura_data = FacturaORM(
            id=factura_id,
            numero_factura=generar_numero_factura_uuid(factura_id),
            id_mascota=mascota_instance.id,
            fecha_factura=date.today(),
            tipo_servicio="consulta_general",
            descripcion="Consulta de rutina",
            veterinario=veterinario_usuario.username,
            valor_servicio=100.0,
            iva=19.0,
            descuento=0.0,
            total=119.0
        )
        
        created = repo.create(factura_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        assert created.id is not None
        assert created.numero_factura is not None
        assert created.id_mascota == mascota_instance.id
        assert created.estado == "pendiente"
        assert created.total == 119.0
        assert created.id_usuario_creacion == veterinario_usuario.id
    
    def test_create_factura_con_descuento(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test creating a factura with discount."""
        repo = FacturaRepository(db_session)
        
        factura_id = str(uuid4())
        factura_data = FacturaORM(
            id=factura_id,
            numero_factura=generar_numero_factura_uuid(factura_id),
            id_mascota=mascota_instance.id,
            fecha_factura=date.today(),
            tipo_servicio="cirugia",
            descripcion="Cirugía menor",
            veterinario=veterinario_usuario.username,
            valor_servicio=500.0,
            iva=95.0,
            descuento=50.0,
            total=545.0  # 500 + 95 - 50
        )
        
        created = repo.create(factura_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        assert created.total == 545.0
        assert created.descuento == 50.0
    
    def test_create_factura_con_cita(
        self,
        db_session: Session,
        cita_instance: CitaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test creating a factura with cita reference."""
        repo = FacturaRepository(db_session)
        
        factura_id = str(uuid4())
        factura_data = FacturaORM(
            id=factura_id,
            numero_factura=generar_numero_factura_uuid(factura_id),
            id_cita=cita_instance.id,
            id_mascota=cita_instance.id_mascota,
            fecha_factura=date.today(),
            tipo_servicio="consulta_general",
            descripcion="Consulta",
            veterinario=veterinario_usuario.username,
            valor_servicio=100.0,
            iva=19.0,
            descuento=0.0,
            total=119.0
        )
        
        created = repo.create(factura_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        assert created.id_cita == str(cita_instance.id)


class TestFacturaRepositoryRead:
    """Tests for reading facturas."""
    
    def test_get_by_id_exitoso(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test getting factura by ID."""
        repo = FacturaRepository(db_session)
        
        factura_id = str(uuid4())
        factura_data = FacturaORM(
            id=factura_id,
            numero_factura=generar_numero_factura_uuid(factura_id),
            id_mascota=mascota_instance.id,
            fecha_factura=date.today(),
            tipo_servicio="consulta_general",
            descripcion="Consulta",
            veterinario=veterinario_usuario.username,
            valor_servicio=100.0,
            iva=19.0,
            descuento=0.0,
            total=119.0
        )
        created = repo.create(factura_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        retrieved = repo.get_by_id(created.id)
        
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.numero_factura == created.numero_factura
    
    def test_get_by_id_nonexistent(
        self,
        db_session: Session
    ):
        """Test getting non-existent factura returns None."""
        repo = FacturaRepository(db_session)
        
        result = repo.get_by_id("00000000-0000-0000-0000-000000000000")
        
        assert result is None
    
    def test_get_by_id_or_fail(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test get_by_id_or_fail with valid ID."""
        repo = FacturaRepository(db_session)
        
        factura_id = str(uuid4())
        factura_data = FacturaORM(
            id=factura_id,
            numero_factura=generar_numero_factura_uuid(factura_id),
            id_mascota=mascota_instance.id,
            fecha_factura=date.today(),
            tipo_servicio="consulta_general",
            descripcion="Consulta",
            veterinario=veterinario_usuario.username,
            valor_servicio=100.0,
            iva=19.0,
            descuento=0.0,
            total=119.0
        )
        created = repo.create(factura_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        retrieved = repo.get_by_id_or_fail(created.id)
        
        assert retrieved.id == created.id
    
    def test_get_by_id_or_fail_raises_exception(
        self,
        db_session: Session
    ):
        """Test get_by_id_or_fail raises exception for non-existent factura."""
        repo = FacturaRepository(db_session)
        
        with pytest.raises(NotFoundException):
            repo.get_by_id_or_fail("00000000-0000-0000-0000-000000000000")
    
    def test_find_by_mascota(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test finding facturas by mascota ID."""
        repo = FacturaRepository(db_session)
        
        # Create multiple facturas for same mascota
        for i in range(3):
            factura_id = str(uuid4())
            factura_data = FacturaORM(
                id=factura_id,
                numero_factura=generar_numero_factura_uuid(factura_id),
                id_mascota=mascota_instance.id,
                fecha_factura=date.today(),
                tipo_servicio="consulta_general",
                descripcion=f"Consulta {i}",
                veterinario=veterinario_usuario.username,
                valor_servicio=100.0,
                iva=19.0,
                descuento=0.0,
                total=119.0
            )
            repo.create(factura_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        facturas = repo.find_by_mascota(mascota_instance.id, skip=0, limit=50)
        
        assert len(facturas) == 3
        assert all(f.id_mascota == mascota_instance.id for f in facturas)
    
    def test_find_by_mascota_pagination(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test finding facturas by mascota with pagination."""
        repo = FacturaRepository(db_session)
        
        # Create 10 facturas
        for i in range(10):
            factura_id = str(uuid4())
            factura_data = FacturaORM(
                id=factura_id,
                numero_factura=generar_numero_factura_uuid(factura_id),
                id_mascota=mascota_instance.id,
                fecha_factura=date.today(),
                tipo_servicio="consulta_general",
                descripcion=f"Consulta {i}",
                veterinario=veterinario_usuario.username,
                valor_servicio=100.0,
                iva=19.0,
                descuento=0.0,
                total=119.0
            )
            repo.create(factura_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        # First page
        page1 = repo.find_by_mascota(mascota_instance.id, skip=0, limit=5)
        assert len(page1) == 5
        
        # Second page
        page2 = repo.find_by_mascota(mascota_instance.id, skip=5, limit=5)
        assert len(page2) == 5
    
    def test_find_by_estado(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test finding facturas by estado."""
        repo = FacturaRepository(db_session)
        
        # Create facturas with different states
        for estado in ["pendiente", "pagada", "pendiente"]:
            factura_id = str(uuid4())
            factura_data = FacturaORM(
                id=factura_id,
                numero_factura=generar_numero_factura_uuid(factura_id),
                id_mascota=mascota_instance.id,
                fecha_factura=date.today(),
                tipo_servicio="consulta_general",
                descripcion="Consulta",
                veterinario=veterinario_usuario.username,
                valor_servicio=100.0,
                iva=19.0,
                descuento=0.0,
                total=119.0,
                estado=estado
            )
            repo.create(factura_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        pendientes = repo.find_by_estado("pendiente", skip=0, limit=50)
        pagadas = repo.find_by_estado("pagada", skip=0, limit=50)
        
        assert len(pendientes) == 2
        assert len(pagadas) == 1
    
    def test_find_by_veterinario(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test finding facturas by veterinario."""
        repo = FacturaRepository(db_session)
        
        # Create facturas for same veterinario
        for i in range(3):
            factura_id = str(uuid4())
            factura_data = FacturaORM(
                id=factura_id,
                numero_factura=generar_numero_factura_uuid(factura_id),
                id_mascota=mascota_instance.id,
                fecha_factura=date.today(),
                tipo_servicio="consulta_general",
                descripcion=f"Consulta {i}",
                veterinario=veterinario_usuario.username,
                valor_servicio=100.0,
                iva=19.0,
                descuento=0.0,
                total=119.0
            )
            repo.create(factura_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        facturas = repo.find_by_veterinario(
            veterinario_usuario.username,
            skip=0,
            limit=50
        )
        
        assert len(facturas) >= 3
    
    def test_find_by_cita(
        self,
        db_session: Session,
        cita_instance: CitaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test finding factura by cita."""
        repo = FacturaRepository(db_session)
        
        factura_id = str(uuid4())
        factura_data = FacturaORM(
            id=factura_id,
            numero_factura=generar_numero_factura_uuid(factura_id),
            id_cita=cita_instance.id,
            id_mascota=cita_instance.id_mascota,
            fecha_factura=date.today(),
            tipo_servicio="consulta_general",
            descripcion="Consulta",
            veterinario=veterinario_usuario.username,
            valor_servicio=100.0,
            iva=19.0,
            descuento=0.0,
            total=119.0
        )
        repo.create(factura_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        found = repo.find_by_cita(cita_instance.id)
        
        assert found is not None
        assert found.id_cita == str(cita_instance.id)
    
    def test_find_by_vacuna(
        self,
        db_session: Session,
        vacuna_instance: VacunaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test finding factura by vacuna."""
        repo = FacturaRepository(db_session)
        
        factura_id = str(uuid4())
        factura_data = FacturaORM(
            id=factura_id,
            numero_factura=generar_numero_factura_uuid(factura_id),
            id_vacuna=vacuna_instance.id,
            id_mascota=vacuna_instance.id_mascota,
            fecha_factura=date.today(),
            tipo_servicio="vacunacion",
            descripcion="Vacunación",
            veterinario=veterinario_usuario.username,
            valor_servicio=50.0,
            iva=9.5,
            descuento=0.0,
            total=59.5
        )
        repo.create(factura_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        found = repo.find_by_vacuna(vacuna_instance.id)
        
        assert found is not None
        assert found.id_vacuna == str(vacuna_instance.id)
    
    def test_get_all(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test getting all facturas."""
        repo = FacturaRepository(db_session)
        
        # Create facturas
        for i in range(3):
            factura_id = str(uuid4())
            factura_data = FacturaORM(
                id=factura_id,
                numero_factura=generar_numero_factura_uuid(factura_id),
                id_mascota=mascota_instance.id,
                fecha_factura=date.today(),
                tipo_servicio="consulta_general",
                descripcion=f"Consulta {i}",
                veterinario=veterinario_usuario.username,
                valor_servicio=100.0,
                iva=19.0,
                descuento=0.0,
                total=119.0
            )
            repo.create(factura_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        all_facturas = repo.get_all(skip=0, limit=50)
        
        assert len(all_facturas) >= 3
    
    def test_count(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test counting facturas."""
        repo = FacturaRepository(db_session)
        
        initial_count = repo.count()
        
        # Create facturas
        for i in range(3):
            factura_id = str(uuid4())
            factura_data = FacturaORM(
                id=factura_id,
                numero_factura=generar_numero_factura_uuid(factura_id),
                id_mascota=mascota_instance.id,
                fecha_factura=date.today(),
                tipo_servicio="consulta_general",
                descripcion=f"Consulta {i}",
                veterinario=veterinario_usuario.username,
                valor_servicio=100.0,
                iva=19.0,
                descuento=0.0,
                total=119.0
            )
            repo.create(factura_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        final_count = repo.count()
        
        assert final_count == initial_count + 3


class TestFacturaRepositoryUpdate:
    """Tests for updating facturas."""
    
    def test_update_factura_descripcion(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test updating factura description."""
        repo = FacturaRepository(db_session)
        
        factura_id = str(uuid4())
        factura_data = FacturaORM(
            id=factura_id,
            numero_factura=generar_numero_factura_uuid(factura_id),
            id_mascota=mascota_instance.id,
            fecha_factura=date.today(),
            tipo_servicio="consulta_general",
            descripcion="Consulta",
            veterinario=veterinario_usuario.username,
            valor_servicio=100.0,
            iva=19.0,
            descuento=0.0,
            total=119.0
        )
        created = repo.create(factura_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        created.descripcion = "Consulta de seguimiento"
        updated = repo.update(created, user_id=veterinario_usuario.id)
        db_session.commit()
        
        assert updated.descripcion == "Consulta de seguimiento"
    
    def test_update_factura_estado(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test updating factura estado."""
        repo = FacturaRepository(db_session)
        
        factura_id = str(uuid4())
        factura_data = FacturaORM(
            id=factura_id,
            numero_factura=generar_numero_factura_uuid(factura_id),
            id_mascota=mascota_instance.id,
            fecha_factura=date.today(),
            tipo_servicio="consulta_general",
            descripcion="Consulta",
            veterinario=veterinario_usuario.username,
            valor_servicio=100.0,
            iva=19.0,
            descuento=0.0,
            total=119.0,
            estado="pendiente"
        )
        created = repo.create(factura_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        created.estado = "pagada"
        updated = repo.update(created, user_id=veterinario_usuario.id)
        db_session.commit()
        
        assert updated.estado == "pagada"
        assert updated.id_usuario_actualizacion == veterinario_usuario.id
    
    def test_update_factura_valor_servicio(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test updating factura valor_servicio."""
        repo = FacturaRepository(db_session)
        
        factura_id = str(uuid4())
        factura_data = FacturaORM(
            id=factura_id,
            numero_factura=generar_numero_factura_uuid(factura_id),
            id_mascota=mascota_instance.id,
            fecha_factura=date.today(),
            tipo_servicio="consulta_general",
            descripcion="Consulta",
            veterinario=veterinario_usuario.username,
            valor_servicio=100.0,
            iva=19.0,
            descuento=0.0,
            total=119.0
        )
        created = repo.create(factura_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        created.valor_servicio = 150.0
        created.total = 178.5  # 150 + 28.5 (19% de 150)
        updated = repo.update(created, user_id=veterinario_usuario.id)
        db_session.commit()
        
        assert updated.valor_servicio == 150.0
        assert updated.total == 178.5


class TestFacturaRepositoryDelete:
    """Tests for deleting facturas (soft delete)."""
    
    def test_soft_delete_factura(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test soft deleting a factura."""
        repo = FacturaRepository(db_session)
        
        factura_id = str(uuid4())
        factura_data = FacturaORM(
            id=factura_id,
            numero_factura=generar_numero_factura_uuid(factura_id),
            id_mascota=mascota_instance.id,
            fecha_factura=date.today(),
            tipo_servicio="consulta_general",
            descripcion="Consulta",
            veterinario=veterinario_usuario.username,
            valor_servicio=100.0,
            iva=19.0,
            descuento=0.0,
            total=119.0
        )
        created = repo.create(factura_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        repo.delete(created, user_id=veterinario_usuario.id, hard=False)
        db_session.commit()
        
        # Should be marked as deleted
        assert created.is_deleted is True
        assert created.deleted_at is not None
        assert created.deleted_by == veterinario_usuario.id
    
    def test_restore_factura(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test restoring a soft-deleted factura."""
        repo = FacturaRepository(db_session)
        
        factura_id = str(uuid4())
        factura_data = FacturaORM(
            id=factura_id,
            numero_factura=generar_numero_factura_uuid(factura_id),
            id_mascota=mascota_instance.id,
            fecha_factura=date.today(),
            tipo_servicio="consulta_general",
            descripcion="Consulta",
            veterinario=veterinario_usuario.username,
            valor_servicio=100.0,
            iva=19.0,
            descuento=0.0,
            total=119.0,
            is_deleted=True
        )
        created = repo.create(factura_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        repo.restore(created, user_id=veterinario_usuario.id)
        db_session.commit()
        
        assert created.is_deleted is False
        assert created.deleted_at is None
        assert created.deleted_by is None
    
    def test_find_excludes_deleted_by_default(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test that find operations exclude deleted facturas by default."""
        repo = FacturaRepository(db_session)
        
        # Create one active and one deleted factura
        active_id = str(uuid4())
        active = FacturaORM(
            id=active_id,
            numero_factura=generar_numero_factura_uuid(active_id),
            id_mascota=mascota_instance.id,
            fecha_factura=date.today(),
            tipo_servicio="consulta_general",
            descripcion="Consulta",
            veterinario=veterinario_usuario.username,
            valor_servicio=100.0,
            iva=19.0,
            descuento=0.0,
            total=119.0
        )
        
        deleted_id = str(uuid4())
        deleted = FacturaORM(
            id=deleted_id,
            numero_factura=generar_numero_factura_uuid(deleted_id),
            id_mascota=mascota_instance.id,
            fecha_factura=date.today(),
            tipo_servicio="consulta_general",
            descripcion="Consulta",
            veterinario=veterinario_usuario.username,
            valor_servicio=100.0,
            iva=19.0,
            descuento=0.0,
            total=119.0,
            is_deleted=True
        )
        
        repo.create(active, user_id=veterinario_usuario.id)
        repo.create(deleted, user_id=veterinario_usuario.id)
        db_session.commit()
        
        facturas = repo.find_by_mascota(mascota_instance.id, skip=0, limit=50)
        
        # Should only return active factura
        assert len(facturas) == 1
        assert facturas[0].id == active_id
    
    def test_find_includes_deleted_when_requested(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test that find operations include deleted facturas when requested."""
        repo = FacturaRepository(db_session)
        
        # Create one active and one deleted factura
        active_id = str(uuid4())
        active = FacturaORM(
            id=active_id,
            numero_factura=generar_numero_factura_uuid(active_id),
            id_mascota=mascota_instance.id,
            fecha_factura=date.today(),
            tipo_servicio="consulta_general",
            descripcion="Consulta",
            veterinario=veterinario_usuario.username,
            valor_servicio=100.0,
            iva=19.0,
            descuento=0.0,
            total=119.0
        )
        
        deleted_id = str(uuid4())
        deleted = FacturaORM(
            id=deleted_id,
            numero_factura=generar_numero_factura_uuid(deleted_id),
            id_mascota=mascota_instance.id,
            fecha_factura=date.today(),
            tipo_servicio="consulta_general",
            descripcion="Consulta",
            veterinario=veterinario_usuario.username,
            valor_servicio=100.0,
            iva=19.0,
            descuento=0.0,
            total=119.0,
            is_deleted=True
        )
        
        repo.create(active, user_id=veterinario_usuario.id)
        repo.create(deleted, user_id=veterinario_usuario.id)
        db_session.commit()
        
        facturas = repo.find_by_mascota(
            mascota_instance.id,
            skip=0,
            limit=50,
            include_deleted=True
        )
        
        # Should return both
        assert len(facturas) == 2


class TestFacturaRepositoryRelationships:
    """Tests for relationships with other entities."""
    
    def test_factura_mascota_relationship(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test that factura properly references mascota."""
        repo = FacturaRepository(db_session)
        
        factura_id = str(uuid4())
        factura_data = FacturaORM(
            id=factura_id,
            numero_factura=generar_numero_factura_uuid(factura_id),
            id_mascota=mascota_instance.id,
            fecha_factura=date.today(),
            tipo_servicio="consulta_general",
            descripcion="Consulta",
            veterinario=veterinario_usuario.username,
            valor_servicio=100.0,
            iva=19.0,
            descuento=0.0,
            total=119.0
        )
        created = repo.create(factura_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        assert created.id_mascota == mascota_instance.id
    
    def test_factura_audit_fields(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test that audit fields are properly populated."""
        repo = FacturaRepository(db_session)
        
        factura_id = str(uuid4())
        factura_data = FacturaORM(
            id=factura_id,
            numero_factura=generar_numero_factura_uuid(factura_id),
            id_mascota=mascota_instance.id,
            fecha_factura=date.today(),
            tipo_servicio="consulta_general",
            descripcion="Consulta",
            veterinario=veterinario_usuario.username,
            valor_servicio=100.0,
            iva=19.0,
            descuento=0.0,
            total=119.0
        )
        created = repo.create(factura_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        # Check audit fields
        assert created.id_usuario_creacion == veterinario_usuario.id
        assert created.fecha_creacion is not None
        assert created.fecha_actualizacion is not None
        
        # Update and check audit fields
        created.descripcion = "Updated"
        updated = repo.update(created, user_id=veterinario_usuario.id)
        db_session.commit()
        
        assert updated.id_usuario_actualizacion == veterinario_usuario.id
        assert updated.fecha_actualizacion >= created.fecha_actualizacion
