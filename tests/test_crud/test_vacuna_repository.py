"""
Tests for Vacuna Repository CRUD operations.

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
from datetime import date, timedelta
from typing import List

from database.models import VacunaORM, MascotaORM, UsuarioORM
from repositories.vacuna_repository import VacunaRepository
from core.exceptions import NotFoundException


class TestVacunaRepositoryCreate:
    """Tests for creating vaccines."""
    
    def test_create_vacuna_exitoso(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test creating a vaccine successfully."""
        repo = VacunaRepository(db_session)
        
        vacuna_data = VacunaORM(
            id_mascota=mascota_instance.id,
            tipo_vacuna="rabia",
            fecha_aplicacion=date.today(),
            lote_vacuna="LOTE123456",
            veterinario=veterinario_usuario.username,
            proxima_dosis=date.today() + timedelta(days=365)
        )
        
        created = repo.create(vacuna_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        assert created.id is not None
        assert created.id_mascota == mascota_instance.id
        assert created.tipo_vacuna == "rabia"
        assert created.lote_vacuna == "LOTE123456"
        assert created.id_usuario_creacion == veterinario_usuario.id
    
    def test_create_vacuna_sin_proxima_dosis(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test creating a vaccine without proxima_dosis."""
        repo = VacunaRepository(db_session)
        
        vacuna_data = VacunaORM(
            id_mascota=mascota_instance.id,
            tipo_vacuna="parvovirus",
            fecha_aplicacion=date.today(),
            lote_vacuna="LOTE789012",
            veterinario=veterinario_usuario.username,
            proxima_dosis=None
        )
        
        created = repo.create(vacuna_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        assert created.proxima_dosis is None
        assert created.tipo_vacuna == "parvovirus"
    
    def test_create_multiple_vacunas(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test creating multiple vaccines."""
        repo = VacunaRepository(db_session)
        
        tipos = ["rabia", "parvovirus", "moquillo"]
        created_ids = []
        
        for tipo in tipos:
            vacuna_data = VacunaORM(
                id_mascota=mascota_instance.id,
                tipo_vacuna=tipo,
                fecha_aplicacion=date.today(),
                lote_vacuna=f"LOTE{tipo}",
                veterinario=veterinario_usuario.username
            )
            created = repo.create(vacuna_data, user_id=veterinario_usuario.id)
            created_ids.append(created.id)
        
        db_session.commit()
        
        assert len(created_ids) == 3
        assert len(set(created_ids)) == 3


class TestVacunaRepositoryRead:
    """Tests for reading vaccines."""
    
    def test_get_by_id_exitoso(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test getting vaccine by ID."""
        repo = VacunaRepository(db_session)
        
        vacuna_data = VacunaORM(
            id_mascota=mascota_instance.id,
            tipo_vacuna="rabia",
            fecha_aplicacion=date.today(),
            lote_vacuna="LOTE123456",
            veterinario=veterinario_usuario.username
        )
        created = repo.create(vacuna_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        retrieved = repo.get_by_id(created.id)
        
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.tipo_vacuna == "rabia"
    
    def test_get_by_id_nonexistent(
        self,
        db_session: Session
    ):
        """Test getting non-existent vaccine returns None."""
        repo = VacunaRepository(db_session)
        
        result = repo.get_by_id("00000000-0000-0000-0000-000000000000")
        
        assert result is None
    
    def test_get_by_id_or_fail(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test get_by_id_or_fail with valid ID."""
        repo = VacunaRepository(db_session)
        
        vacuna_data = VacunaORM(
            id_mascota=mascota_instance.id,
            tipo_vacuna="parvovirus",
            fecha_aplicacion=date.today(),
            lote_vacuna="LOTE789012",
            veterinario=veterinario_usuario.username
        )
        created = repo.create(vacuna_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        retrieved = repo.get_by_id_or_fail(created.id)
        
        assert retrieved.id == created.id
    
    def test_get_by_id_or_fail_raises_exception(
        self,
        db_session: Session
    ):
        """Test get_by_id_or_fail raises exception for non-existent vaccine."""
        repo = VacunaRepository(db_session)
        
        with pytest.raises(NotFoundException):
            repo.get_by_id_or_fail("00000000-0000-0000-0000-000000000000")
    
    def test_find_by_mascota(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test finding vaccines by mascota ID."""
        repo = VacunaRepository(db_session)
        
        # Create multiple vaccines for same mascota
        for i in range(3):
            vacuna_data = VacunaORM(
                id_mascota=mascota_instance.id,
                tipo_vacuna="rabia",
                fecha_aplicacion=date.today() - timedelta(days=i),
                lote_vacuna=f"LOTE{i:06d}",
                veterinario=veterinario_usuario.username
            )
            repo.create(vacuna_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        vacunas = repo.find_by_mascota(mascota_instance.id, skip=0, limit=50)
        
        assert len(vacunas) == 3
        assert all(v.id_mascota == mascota_instance.id for v in vacunas)
    
    def test_find_by_mascota_pagination(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test finding vaccines by mascota with pagination."""
        repo = VacunaRepository(db_session)
        
        # Create 10 vaccines
        for i in range(10):
            vacuna_data = VacunaORM(
                id_mascota=mascota_instance.id,
                tipo_vacuna="rabia",
                fecha_aplicacion=date.today() - timedelta(days=i),
                lote_vacuna=f"LOTE{i:06d}",
                veterinario=veterinario_usuario.username
            )
            repo.create(vacuna_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        # First page
        page1 = repo.find_by_mascota(mascota_instance.id, skip=0, limit=5)
        assert len(page1) == 5
        
        # Second page
        page2 = repo.find_by_mascota(mascota_instance.id, skip=5, limit=5)
        assert len(page2) == 5
    
    def test_find_by_tipo_vacuna(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test finding vaccines by type."""
        repo = VacunaRepository(db_session)
        
        # Create vaccines of different types
        tipos = ["rabia", "parvovirus", "moquillo", "rabia"]
        for tipo in tipos:
            vacuna_data = VacunaORM(
                id_mascota=mascota_instance.id,
                tipo_vacuna=tipo,
                fecha_aplicacion=date.today(),
                lote_vacuna=f"LOTE{tipo}",
                veterinario=veterinario_usuario.username
            )
            repo.create(vacuna_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        rabia_vacunas = repo.find_by_tipo("rabia", skip=0, limit=50)
        parvovirus_vacunas = repo.find_by_tipo("parvovirus", skip=0, limit=50)
        
        assert len(rabia_vacunas) == 2
        assert len(parvovirus_vacunas) == 1
    
    def test_find_by_veterinario(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test finding vaccines by veterinario."""
        repo = VacunaRepository(db_session)
        
        # Create vaccines for same veterinario
        for i in range(3):
            vacuna_data = VacunaORM(
                id_mascota=mascota_instance.id,
                tipo_vacuna="rabia",
                fecha_aplicacion=date.today() - timedelta(days=i),
                lote_vacuna=f"LOTE{i:06d}",
                veterinario=veterinario_usuario.username
            )
            repo.create(vacuna_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        vacunas = repo.find_by_veterinario(
            veterinario_usuario.username,
            skip=0,
            limit=50
        )
        
        assert len(vacunas) >= 3
    
    def test_find_by_proxima_dosis_before_date(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test finding vaccines with proxima_dosis before date."""
        repo = VacunaRepository(db_session)
        
        # Create vaccines with different proxima_dosis
        vac1 = VacunaORM(
            id_mascota=mascota_instance.id,
            tipo_vacuna="rabia",
            fecha_aplicacion=date.today(),
            lote_vacuna="LOTE001",
            veterinario=veterinario_usuario.username,
            proxima_dosis=date.today() + timedelta(days=30)
        )
        vac2 = VacunaORM(
            id_mascota=mascota_instance.id,
            tipo_vacuna="parvovirus",
            fecha_aplicacion=date.today(),
            lote_vacuna="LOTE002",
            veterinario=veterinario_usuario.username,
            proxima_dosis=date.today() + timedelta(days=90)
        )
        vac3 = VacunaORM(
            id_mascota=mascota_instance.id,
            tipo_vacuna="moquillo",
            fecha_aplicacion=date.today(),
            lote_vacuna="LOTE003",
            veterinario=veterinario_usuario.username,
            proxima_dosis=None
        )
        
        repo.create(vac1, user_id=veterinario_usuario.id)
        repo.create(vac2, user_id=veterinario_usuario.id)
        repo.create(vac3, user_id=veterinario_usuario.id)
        db_session.commit()
        
        fecha_limite = date.today() + timedelta(days=60)
        vacunas = repo.find_proximas_dosis(fecha_limite, skip=0, limit=50)
        
        # Should find vac1 (30 days)
        assert len(vacunas) >= 1
    
    def test_get_all(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test getting all vaccines."""
        repo = VacunaRepository(db_session)
        
        # Create vaccines
        for i in range(3):
            vacuna_data = VacunaORM(
                id_mascota=mascota_instance.id,
                tipo_vacuna="rabia",
                fecha_aplicacion=date.today() - timedelta(days=i),
                lote_vacuna=f"LOTE{i:06d}",
                veterinario=veterinario_usuario.username
            )
            repo.create(vacuna_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        all_vacunas = repo.get_all(skip=0, limit=50)
        
        assert len(all_vacunas) >= 3
    
    def test_count(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test counting vaccines."""
        repo = VacunaRepository(db_session)
        
        initial_count = repo.count()
        
        # Create vaccines
        for i in range(3):
            vacuna_data = VacunaORM(
                id_mascota=mascota_instance.id,
                tipo_vacuna="rabia",
                fecha_aplicacion=date.today() - timedelta(days=i),
                lote_vacuna=f"LOTE{i:06d}",
                veterinario=veterinario_usuario.username
            )
            repo.create(vacuna_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        final_count = repo.count()
        
        assert final_count == initial_count + 3


class TestVacunaRepositoryUpdate:
    """Tests for updating vaccines."""
    
    def test_update_vacuna_lote(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test updating vaccine lote."""
        repo = VacunaRepository(db_session)
        
        vacuna_data = VacunaORM(
            id_mascota=mascota_instance.id,
            tipo_vacuna="rabia",
            fecha_aplicacion=date.today(),
            lote_vacuna="LOTE123456",
            veterinario=veterinario_usuario.username
        )
        created = repo.create(vacuna_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        created.lote_vacuna = "LOTE999999"
        updated = repo.update(created, user_id=veterinario_usuario.id)
        db_session.commit()
        
        assert updated.lote_vacuna == "LOTE999999"
    
    def test_update_vacuna_proxima_dosis(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test updating vaccine proxima_dosis."""
        repo = VacunaRepository(db_session)
        
        vacuna_data = VacunaORM(
            id_mascota=mascota_instance.id,
            tipo_vacuna="parvovirus",
            fecha_aplicacion=date.today(),
            lote_vacuna="LOTE789012",
            veterinario=veterinario_usuario.username,
            proxima_dosis=None
        )
        created = repo.create(vacuna_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        nueva_fecha = date.today() + timedelta(days=365)
        created.proxima_dosis = nueva_fecha
        
        updated = repo.update(created, user_id=veterinario_usuario.id)
        db_session.commit()
        
        assert updated.proxima_dosis == nueva_fecha
        assert updated.id_usuario_actualizacion == veterinario_usuario.id
    
    def test_update_vacuna_tipo(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test updating vaccine type."""
        repo = VacunaRepository(db_session)
        
        vacuna_data = VacunaORM(
            id_mascota=mascota_instance.id,
            tipo_vacuna="rabia",
            fecha_aplicacion=date.today(),
            lote_vacuna="LOTE123456",
            veterinario=veterinario_usuario.username
        )
        created = repo.create(vacuna_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        created.tipo_vacuna = "parvovirus"
        updated = repo.update(created, user_id=veterinario_usuario.id)
        db_session.commit()
        
        assert updated.tipo_vacuna == "parvovirus"


class TestVacunaRepositoryDelete:
    """Tests for deleting vaccines (soft delete)."""
    
    def test_soft_delete_vacuna(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test soft deleting a vaccine."""
        repo = VacunaRepository(db_session)
        
        vacuna_data = VacunaORM(
            id_mascota=mascota_instance.id,
            tipo_vacuna="rabia",
            fecha_aplicacion=date.today(),
            lote_vacuna="LOTE123456",
            veterinario=veterinario_usuario.username
        )
        created = repo.create(vacuna_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        repo.delete(created, user_id=veterinario_usuario.id, hard=False)
        db_session.commit()
        
        # Should be marked as deleted
        assert created.is_deleted is True
        assert created.deleted_at is not None
        assert created.deleted_by == veterinario_usuario.id
    
    def test_restore_vacuna(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test restoring a soft-deleted vaccine."""
        repo = VacunaRepository(db_session)
        
        vacuna_data = VacunaORM(
            id_mascota=mascota_instance.id,
            tipo_vacuna="rabia",
            fecha_aplicacion=date.today(),
            lote_vacuna="LOTE123456",
            veterinario=veterinario_usuario.username,
            is_deleted=True
        )
        created = repo.create(vacuna_data, user_id=veterinario_usuario.id)
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
        """Test that find operations exclude deleted vaccines by default."""
        repo = VacunaRepository(db_session)
        
        # Create one active and one deleted vaccine
        active_vac = VacunaORM(
            id_mascota=mascota_instance.id,
            tipo_vacuna="rabia",
            fecha_aplicacion=date.today(),
            lote_vacuna="LOTE001",
            veterinario=veterinario_usuario.username
        )
        deleted_vac = VacunaORM(
            id_mascota=mascota_instance.id,
            tipo_vacuna="parvovirus",
            fecha_aplicacion=date.today(),
            lote_vacuna="LOTE002",
            veterinario=veterinario_usuario.username,
            is_deleted=True
        )
        
        repo.create(active_vac, user_id=veterinario_usuario.id)
        repo.create(deleted_vac, user_id=veterinario_usuario.id)
        db_session.commit()
        
        vacunas = repo.find_by_mascota(mascota_instance.id, skip=0, limit=50)
        
        # Should only return active vaccine
        assert len(vacunas) == 1
        assert vacunas[0].lote_vacuna == "LOTE001"
    
    def test_find_includes_deleted_when_requested(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test that find operations include deleted vaccines when requested."""
        repo = VacunaRepository(db_session)
        
        # Create one active and one deleted vaccine
        active_vac = VacunaORM(
            id_mascota=mascota_instance.id,
            tipo_vacuna="rabia",
            fecha_aplicacion=date.today(),
            lote_vacuna="LOTE001",
            veterinario=veterinario_usuario.username
        )
        deleted_vac = VacunaORM(
            id_mascota=mascota_instance.id,
            tipo_vacuna="parvovirus",
            fecha_aplicacion=date.today(),
            lote_vacuna="LOTE002",
            veterinario=veterinario_usuario.username,
            is_deleted=True
        )
        
        repo.create(active_vac, user_id=veterinario_usuario.id)
        repo.create(deleted_vac, user_id=veterinario_usuario.id)
        db_session.commit()
        
        vacunas = repo.find_by_mascota(
            mascota_instance.id,
            skip=0,
            limit=50,
            include_deleted=True
        )
        
        # Should return both
        assert len(vacunas) == 2


class TestVacunaRepositoryRelationships:
    """Tests for relationships with other entities."""
    
    def test_vacuna_mascota_relationship(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test that vaccine properly references mascota."""
        repo = VacunaRepository(db_session)
        
        vacuna_data = VacunaORM(
            id_mascota=mascota_instance.id,
            tipo_vacuna="rabia",
            fecha_aplicacion=date.today(),
            lote_vacuna="LOTE123456",
            veterinario=veterinario_usuario.username
        )
        created = repo.create(vacuna_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        assert created.id_mascota == mascota_instance.id
    
    def test_vacuna_audit_fields(
        self,
        db_session: Session,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test that audit fields are properly populated."""
        repo = VacunaRepository(db_session)
        
        vacuna_data = VacunaORM(
            id_mascota=mascota_instance.id,
            tipo_vacuna="rabia",
            fecha_aplicacion=date.today(),
            lote_vacuna="LOTE123456",
            veterinario=veterinario_usuario.username
        )
        created = repo.create(vacuna_data, user_id=veterinario_usuario.id)
        db_session.commit()
        
        # Check audit fields
        assert created.id_usuario_creacion == veterinario_usuario.id
        assert created.fecha_creacion is not None
        assert created.fecha_actualizacion is not None
        
        # Update and check audit fields
        created.lote_vacuna = "LOTE999999"
        updated = repo.update(created, user_id=veterinario_usuario.id)
        db_session.commit()
        
        assert updated.id_usuario_actualizacion == veterinario_usuario.id
        assert updated.fecha_actualizacion >= created.fecha_actualizacion
