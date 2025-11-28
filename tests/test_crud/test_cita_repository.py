"""
Tests for Cita Repository CRUD operations.

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
from datetime import datetime, timedelta, timezone
from typing import List

from database.models import CitaORM, MascotaORM, UsuarioORM
from repositories.cita_repository import CitaRepository
from core.exceptions import NotFoundException


class TestCitaRepositoryCreate:
    """Tests for creating citas."""
    
    def test_create_cita_exitoso(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test creating a cita successfully."""
        repo = CitaRepository(db_session)
        
        cita_data = CitaORM(
            id_mascota=mascota_instance.id,
            fecha=datetime.now(timezone.utc) + timedelta(days=5),
            motivo="Revisión general",
            veterinario=veterinario_usuario.username,
            estado="pendiente"
        )
        
        created = repo.create(cita_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        assert created.id is not None
        assert created.id_mascota == mascota_instance.id
        assert created.motivo == "Revisión general"
        assert created.estado == "pendiente"
        assert created.id_usuario_creacion == veterinario_usuario.id
    
    def test_create_cita_con_diagnostico(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test creating a cita with diagnostico."""
        repo = CitaRepository(db_session)
        
        cita_data = CitaORM(
            id_mascota=mascota_instance.id,
            fecha=datetime.now(timezone.utc) - timedelta(days=1),
            motivo="Revisión",
            veterinario=veterinario_usuario.username,
            estado="completada",
            diagnostico="Animal en buen estado",
            tratamiento="Reposo"
        )
        
        created = repo.create(cita_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        assert created.diagnostico == "Animal en buen estado"
        assert created.tratamiento == "Reposo"
        assert created.estado == "completada"
    
    def test_create_multiple_citas(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test creating multiple citas."""
        repo = CitaRepository(db_session)
        
        created_ids = []
        for i in range(5):
            cita_data = CitaORM(
                id_mascota=mascota_instance.id,
                fecha=datetime.now(timezone.utc) + timedelta(days=i+1),
                motivo=f"Revisión {i+1}",
                veterinario=veterinario_usuario.username,
                estado="pendiente"
            )
            created = repo.create(cita_data, user_id=veterinario_usuario.id)
            created_ids.append(created.id)
        
        db_session.commit()
        
        assert len(created_ids) == 5
        # All IDs should be unique
        assert len(set(created_ids)) == 5


class TestCitaRepositoryRead:
    """Tests for reading citas."""
    
    def test_get_by_id_exitoso(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test getting cita by ID."""
        repo = CitaRepository(db_session)
        
        cita_data = CitaORM(
            id_mascota=mascota_instance.id,
            fecha=datetime.now(timezone.utc) + timedelta(days=5),
            motivo="Revisión",
            veterinario=veterinario_usuario.username,
            estado="pendiente"
        )
        created = repo.create(cita_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        retrieved = repo.get_by_id(created.id)
        
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.motivo == "Revisión"
    
    def test_get_by_id_nonexistent(
        self,
        db_session: Session
    ):
        """Test getting non-existent cita returns None."""
        repo = CitaRepository(db_session)
        
        result = repo.get_by_id("00000000-0000-0000-0000-000000000000")
        
        assert result is None
    
    def test_get_by_id_or_fail(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test get_by_id_or_fail with valid ID."""
        repo = CitaRepository(db_session)
        
        cita_data = CitaORM(
            id_mascota=mascota_instance.id,
            fecha=datetime.now(timezone.utc) + timedelta(days=5),
            motivo="Revisión",
            veterinario=veterinario_usuario.username,
            estado="pendiente"
        )
        created = repo.create(cita_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        retrieved = repo.get_by_id_or_fail(created.id)
        
        assert retrieved.id == created.id
    
    def test_get_by_id_or_fail_raises_exception(
        self,
        db_session: Session
    ):
        """Test get_by_id_or_fail raises exception for non-existent cita."""
        repo = CitaRepository(db_session)
        
        with pytest.raises(NotFoundException):
            repo.get_by_id_or_fail("00000000-0000-0000-0000-000000000000")
    
    def test_find_by_mascota(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test finding citas by mascota ID."""
        repo = CitaRepository(db_session)
        
        # Create multiple citas for same mascota
        for i in range(3):
            cita_data = CitaORM(
                id_mascota=mascota_instance.id,
                fecha=datetime.now(timezone.utc) + timedelta(days=i+1),
                motivo=f"Revisión {i+1}",
                veterinario=veterinario_usuario.username,
                estado="pendiente"
            )
            repo.create(cita_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        citas = repo.find_by_mascota(mascota_instance.id, skip=0, limit=50)
        
        assert len(citas) == 3
        assert all(c.id_mascota == mascota_instance.id for c in citas)
    
    def test_find_by_mascota_pagination(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test finding citas by mascota with pagination."""
        repo = CitaRepository(db_session)
        
        # Create 10 citas
        for i in range(10):
            cita_data = CitaORM(
                id_mascota=mascota_instance.id,
                fecha=datetime.now(timezone.utc) + timedelta(days=i+1),
                motivo=f"Revisión {i+1}",
                veterinario=veterinario_usuario.username,
                estado="pendiente"
            )
            repo.create(cita_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        # First page
        page1 = repo.find_by_mascota(mascota_instance.id, skip=0, limit=5)
        assert len(page1) == 5
        
        # Second page
        page2 = repo.find_by_mascota(mascota_instance.id, skip=5, limit=5)
        assert len(page2) == 5
        
        # Third page (partial)
        page3 = repo.find_by_mascota(mascota_instance.id, skip=10, limit=5)
        assert len(page3) == 0
    
    def test_find_by_estado(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test finding citas by estado."""
        repo = CitaRepository(db_session)
        
        # Create citas with different estados
        for estado in ["pendiente", "completada", "cancelada", "pendiente"]:
            cita_data = CitaORM(
                id_mascota=mascota_instance.id,
                fecha=datetime.now(timezone.utc) + timedelta(days=1),
                motivo="Revisión",
                veterinario=veterinario_usuario.username,
                estado=estado
            )
            repo.create(cita_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        pendientes = repo.find_by_estado("pendiente", skip=0, limit=50)
        completadas = repo.find_by_estado("completada", skip=0, limit=50)
        
        assert len(pendientes) == 2
        assert len(completadas) == 1
    
    def test_find_by_veterinario(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM,
        cliente_usuario: UsuarioORM
    ):
        """Test finding citas by veterinario."""
        repo = CitaRepository(db_session)
        
        # Create citas for same veterinario
        for i in range(3):
            cita_data = CitaORM(
                id_mascota=mascota_instance.id,
                fecha=datetime.now(timezone.utc) + timedelta(days=i+1),
                motivo="Revisión",
                veterinario=veterinario_usuario.username,
                estado="pendiente"
            )
            repo.create(cita_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        citas = repo.find_by_veterinario(
            veterinario_usuario.username,
            skip=0,
            limit=50
        )
        
        assert len(citas) == 3
        assert all(c.veterinario == veterinario_usuario.username for c in citas)
    
    def test_find_by_propietario(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM,
        cliente_usuario: UsuarioORM
    ):
        """Test finding citas by propietario (owner)."""
        repo = CitaRepository(db_session)
        
        # Create citas for mascota (which has propietario=cliente)
        for i in range(3):
            cita_data = CitaORM(
                id_mascota=mascota_instance.id,
                fecha=datetime.now(timezone.utc) + timedelta(days=i+1),
                motivo="Revisión",
                veterinario=veterinario_usuario.username,
                estado="pendiente"
            )
            repo.create(cita_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        citas = repo.find_by_propietario(
            cliente_usuario.username,
            skip=0,
            limit=50
        )
        
        assert len(citas) == 3
    
    def test_get_all(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test getting all citas."""
        repo = CitaRepository(db_session)
        
        # Create citas
        for i in range(3):
            cita_data = CitaORM(
                id_mascota=mascota_instance.id,
                fecha=datetime.now(timezone.utc) + timedelta(days=i+1),
                motivo=f"Revisión {i+1}",
                veterinario=veterinario_usuario.username,
                estado="pendiente"
            )
            repo.create(cita_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        all_citas = repo.get_all(skip=0, limit=50)
        
        assert len(all_citas) >= 3
    
    def test_count(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test counting citas."""
        repo = CitaRepository(db_session)
        
        initial_count = repo.count()
        
        # Create citas
        for i in range(3):
            cita_data = CitaORM(
                id_mascota=mascota_instance.id,
                fecha=datetime.now(timezone.utc) + timedelta(days=i+1),
                motivo="Revisión",
                veterinario=veterinario_usuario.username,
                estado="pendiente"
            )
            repo.create(cita_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        final_count = repo.count()
        
        assert final_count == initial_count + 3


class TestCitaRepositoryUpdate:
    """Tests for updating citas."""
    
    def test_update_cita_estado(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test updating cita estado."""
        repo = CitaRepository(db_session)
        
        cita_data = CitaORM(
            id_mascota=mascota_instance.id,
            fecha=datetime.now(timezone.utc) + timedelta(days=5),
            motivo="Revisión",
            veterinario=veterinario_usuario.username,
            estado="pendiente"
        )
        created = repo.create(cita_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        created.estado = "completada"
        updated = repo.update(created, user_id=veterinario_usuario.id)
        db_session.commit()
        
        assert updated.estado == "completada"
        assert updated.id_usuario_actualizacion == veterinario_usuario.id
    
    def test_update_cita_diagnostico_y_tratamiento(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test updating cita diagnostico and tratamiento."""
        repo = CitaRepository(db_session)
        
        cita_data = CitaORM(
            id_mascota=mascota_instance.id,
            fecha=datetime.now(timezone.utc) - timedelta(days=1),
            motivo="Revisión",
            veterinario=veterinario_usuario.username,
            estado="pendiente"
        )
        created = repo.create(cita_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        created.diagnostico = "Animal en buen estado"
        created.tratamiento = "Reposo completo"
        created.estado = "completada"
        
        updated = repo.update(created, user_id=veterinario_usuario.id)
        db_session.commit()
        
        assert updated.diagnostico == "Animal en buen estado"
        assert updated.tratamiento == "Reposo completo"
        assert updated.estado == "completada"
    
    def test_update_cita_fecha_y_motivo(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test updating cita fecha and motivo."""
        repo = CitaRepository(db_session)
        
        cita_data = CitaORM(
            id_mascota=mascota_instance.id,
            fecha=datetime.now(timezone.utc) + timedelta(days=5),
            motivo="Revisión general",
            veterinario=veterinario_usuario.username,
            estado="pendiente"
        )
        created = repo.create(cita_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        nueva_fecha = datetime.now(timezone.utc) + timedelta(days=10)
        created.fecha = nueva_fecha
        created.motivo = "Revisión dental"
        
        updated = repo.update(created, user_id=veterinario_usuario.id)
        db_session.commit()
        
        assert updated.motivo == "Revisión dental"
        # Comparar sin timezone (SQLite almacena naive datetime)
        assert updated.fecha.replace(tzinfo=None) == nueva_fecha.replace(tzinfo=None)


class TestCitaRepositoryDelete:
    """Tests for deleting citas (soft delete)."""
    
    def test_soft_delete_cita(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test soft deleting a cita."""
        repo = CitaRepository(db_session)
        
        cita_data = CitaORM(
            id_mascota=mascota_instance.id,
            fecha=datetime.now(timezone.utc) + timedelta(days=5),
            motivo="Revisión",
            veterinario=veterinario_usuario.username,
            estado="pendiente"
        )
        created = repo.create(cita_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        repo.delete(created, user_id=veterinario_usuario.id, hard=False)
        db_session.commit()
        
        # Should be marked as deleted
        assert created.is_deleted is True
        assert created.deleted_at is not None
        assert created.deleted_by == veterinario_usuario.id
    
    def test_restore_cita(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test restoring a soft-deleted cita."""
        repo = CitaRepository(db_session)
        
        cita_data = CitaORM(
            id_mascota=mascota_instance.id,
            fecha=datetime.now(timezone.utc) + timedelta(days=5),
            motivo="Revisión",
            veterinario=veterinario_usuario.username,
            estado="pendiente",
            is_deleted=True
        )
        created = repo.create(cita_data, user_id=veterinario_usuario.id)
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
        """Test that find operations exclude deleted citas by default."""
        repo = CitaRepository(db_session)
        
        # Create one active and one deleted cita
        active_cita = CitaORM(
            id_mascota=mascota_instance.id,
            fecha=datetime.now(timezone.utc) + timedelta(days=5),
            motivo="Revisión",
            veterinario=veterinario_usuario.username,
            estado="pendiente"
        )
        deleted_cita = CitaORM(
            id_mascota=mascota_instance.id,
            fecha=datetime.now(timezone.utc) + timedelta(days=6),
            motivo="Vacunación",
            veterinario=veterinario_usuario.username,
            estado="pendiente",
            is_deleted=True
        )
        
        repo.create(active_cita, user_id=veterinario_usuario.id)
        repo.create(deleted_cita, user_id=veterinario_usuario.id)
        db_session.commit()
        
        citas = repo.find_by_mascota(mascota_instance.id, skip=0, limit=50)
        
        # Should only return active cita
        assert len(citas) == 1
        assert citas[0].motivo == "Revisión"
    
    def test_find_includes_deleted_when_requested(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test that find operations include deleted citas when requested."""
        repo = CitaRepository(db_session)
        
        # Create one active and one deleted cita
        active_cita = CitaORM(
            id_mascota=mascota_instance.id,
            fecha=datetime.now(timezone.utc) + timedelta(days=5),
            motivo="Revisión",
            veterinario=veterinario_usuario.username,
            estado="pendiente"
        )
        deleted_cita = CitaORM(
            id_mascota=mascota_instance.id,
            fecha=datetime.now(timezone.utc) + timedelta(days=6),
            motivo="Vacunación",
            veterinario=veterinario_usuario.username,
            estado="pendiente",
            is_deleted=True
        )
        
        repo.create(active_cita, user_id=veterinario_usuario.id)
        repo.create(deleted_cita, user_id=veterinario_usuario.id)
        db_session.commit()
        
        citas = repo.find_by_mascota(
            mascota_instance.id,
            skip=0,
            limit=50,
            include_deleted=True
        )
        
        # Should return both
        assert len(citas) == 2


class TestCitaRepositoryFiltering:
    """Tests for filtering citas."""
    
    def test_filter_by_estado_and_veterinario(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test filtering by both estado and veterinario."""
        repo = CitaRepository(db_session)
        
        # Create citas with different combinations
        cita1 = CitaORM(
            id_mascota=mascota_instance.id,
            fecha=datetime.now(timezone.utc) + timedelta(days=1),
            motivo="Revisión",
            veterinario=veterinario_usuario.username,
            estado="pendiente"
        )
        cita2 = CitaORM(
            id_mascota=mascota_instance.id,
            fecha=datetime.now(timezone.utc) + timedelta(days=2),
            motivo="Revisión",
            veterinario=veterinario_usuario.username,
            estado="completada"
        )
        
        repo.create(cita1, user_id=veterinario_usuario.id)
        repo.create(cita2, user_id=veterinario_usuario.id)
        db_session.commit()
        
        # Filter by estado
        pendientes = repo.find_by_estado("pendiente", skip=0, limit=50)
        assert len(pendientes) >= 1
        
        # Filter by veterinario
        vet_citas = repo.find_by_veterinario(
            veterinario_usuario.username,
            skip=0,
            limit=50
        )
        assert len(vet_citas) >= 2
    
    def test_count_by_filters(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test counting citas with filters."""
        repo = CitaRepository(db_session)
        
        # Create citas
        for estado in ["pendiente", "pendiente", "completada"]:
            cita_data = CitaORM(
                id_mascota=mascota_instance.id,
                fecha=datetime.now(timezone.utc) + timedelta(days=1),
                motivo="Revisión",
                veterinario=veterinario_usuario.username,
                estado=estado
            )
            repo.create(cita_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        pendientes_count = repo.count_by_filters(estado="pendiente")
        completadas_count = repo.count_by_filters(estado="completada")
        
        assert pendientes_count >= 2
        assert completadas_count >= 1


class TestCitaRepositoryRelationships:
    """Tests for relationships with other entities."""
    
    def test_cita_mascota_relationship(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test that cita properly references mascota."""
        repo = CitaRepository(db_session)
        
        cita_data = CitaORM(
            id_mascota=mascota_instance.id,
            fecha=datetime.now(timezone.utc) + timedelta(days=5),
            motivo="Revisión",
            veterinario=veterinario_usuario.username,
            estado="pendiente"
        )
        created = repo.create(cita_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        # Refresh to load relationship
        db_session.refresh(created)
        
        assert created.id_mascota == mascota_instance.id
    
    def test_cita_audit_fields(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test that audit fields are properly populated."""
        repo = CitaRepository(db_session)
        
        cita_data = CitaORM(
            id_mascota=mascota_instance.id,
            fecha=datetime.now(timezone.utc) + timedelta(days=5),
            motivo="Revisión",
            veterinario=veterinario_usuario.username,
            estado="pendiente"
        )
        created = repo.create(cita_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        # Check audit fields
        assert created.id_usuario_creacion == veterinario_usuario.id
        assert created.fecha_creacion is not None
        assert created.fecha_actualizacion is not None
        
        # Update and check audit fields
        created.estado = "completada"
        updated = repo.update(created, user_id=veterinario_usuario.id)
        db_session.commit()
        
        assert updated.id_usuario_actualizacion == veterinario_usuario.id
        assert updated.fecha_actualizacion >= created.fecha_actualizacion
