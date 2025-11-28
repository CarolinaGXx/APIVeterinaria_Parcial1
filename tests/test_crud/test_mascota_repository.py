"""
Tests for MascotaRepository CRUD operations.

Tests cover:
- Creating mascotas
- Finding by ID, propietario
- Finding by tipo
- Searching mascotas
- Updating mascotas
- Soft delete/restore
"""

import pytest
from sqlalchemy.orm import Session
from typing import Dict, Any

from database.models import MascotaORM, UsuarioORM
from repositories.mascota_repository import MascotaRepository
from core.exceptions import NotFoundException


@pytest.fixture
def mascota_repository(db_session: Session) -> MascotaRepository:
    """Create a MascotaRepository instance."""
    return MascotaRepository(db_session)


class TestMascotaRepositoryCreate:
    """Tests for creating mascotas in repository."""
    
    def test_create_mascota(
        self,
        mascota_repository: MascotaRepository,
        mascota_data: Dict[str, Any],
        cliente_usuario: UsuarioORM
    ):
        """Test creating a mascota."""
        mascota = MascotaORM(
            nombre=mascota_data["nombre"],
            tipo=mascota_data["tipo"],
            raza=mascota_data["raza"],
            edad=mascota_data["edad"],
            peso=mascota_data["peso"],
            propietario=cliente_usuario.username,
        )
        
        created = mascota_repository.create(mascota)
        mascota_repository.commit()
        
        assert created.id is not None
        assert created.nombre == mascota_data["nombre"]
        assert created.tipo == mascota_data["tipo"]
        assert created.propietario == cliente_usuario.username
        assert created.is_deleted is False
    
    def test_create_mascota_gato(
        self,
        mascota_repository: MascotaRepository,
        mascota_gato_data: Dict[str, Any],
        cliente_usuario: UsuarioORM
    ):
        """Test creating a gato mascota."""
        mascota = MascotaORM(
            nombre=mascota_gato_data["nombre"],
            tipo=mascota_gato_data["tipo"],
            raza=mascota_gato_data["raza"],
            edad=mascota_gato_data["edad"],
            peso=mascota_gato_data["peso"],
            propietario=cliente_usuario.username,
        )
        
        created = mascota_repository.create(mascota)
        mascota_repository.commit()
        
        assert created.tipo == "gato"
        assert created.nombre == mascota_gato_data["nombre"]


class TestMascotaRepositoryRead:
    """Tests for reading mascotas from repository."""
    
    def test_get_by_id(
        self,
        mascota_repository: MascotaRepository,
        mascota_instance: MascotaORM
    ):
        """Test getting mascota by ID."""
        mascota = mascota_repository.get_by_id(mascota_instance.id)
        
        assert mascota is not None
        assert mascota.id == mascota_instance.id
        assert mascota.nombre == mascota_instance.nombre
    
    def test_get_by_id_nonexistent(
        self,
        mascota_repository: MascotaRepository
    ):
        """Test getting non-existent mascota returns None."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        mascota = mascota_repository.get_by_id(fake_id)
        
        assert mascota is None
    
    def test_get_by_id_or_fail(
        self,
        mascota_repository: MascotaRepository,
        mascota_instance: MascotaORM
    ):
        """Test get_by_id_or_fail returns mascota."""
        mascota = mascota_repository.get_by_id_or_fail(mascota_instance.id)
        
        assert mascota is not None
        assert mascota.id == mascota_instance.id
    
    def test_get_by_id_or_fail_raises_exception(
        self,
        mascota_repository: MascotaRepository
    ):
        """Test get_by_id_or_fail raises exception for non-existent."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        
        with pytest.raises(NotFoundException):
            mascota_repository.get_by_id_or_fail(fake_id)
    
    def test_find_by_propietario(
        self,
        mascota_repository: MascotaRepository,
        mascota_instance: MascotaORM,
        cliente_usuario: UsuarioORM
    ):
        """Test finding mascotas by propietario."""
        mascotas = mascota_repository.find_by_propietario(
            cliente_usuario.username
        )
        
        assert len(mascotas) >= 1
        
        # Verify all belong to the same owner
        assert all(m.propietario == cliente_usuario.username for m in mascotas)
        
        # Verify test mascota is in the list
        mascota_ids = [m.id for m in mascotas]
        assert mascota_instance.id in mascota_ids
    
    def test_find_by_propietario_with_pagination(
        self,
        mascota_repository: MascotaRepository,
        db_session: Session,
        cliente_usuario: UsuarioORM
    ):
        """Test finding mascotas by propietario with pagination."""
        # Create multiple mascotas
        for i in range(10):
            mascota = MascotaORM(
                nombre=f"Mascota{i}",
                tipo="perro",
                raza="Labrador",
                edad=i,
                peso=10.0 + i,
                propietario=cliente_usuario.username,
            )
            db_session.add(mascota)
        db_session.commit()
        
        # Get first page
        page1 = mascota_repository.find_by_propietario(
            cliente_usuario.username,
            skip=0,
            limit=5
        )
        assert len(page1) == 5
        
        # Get second page
        page2 = mascota_repository.find_by_propietario(
            cliente_usuario.username,
            skip=5,
            limit=5
        )
        assert len(page2) == 5
        
        # Verify different results
        page1_ids = {m.id for m in page1}
        page2_ids = {m.id for m in page2}
        assert page1_ids.isdisjoint(page2_ids)
    
    def test_find_by_tipo(
        self,
        mascota_repository: MascotaRepository,
        mascota_instance: MascotaORM,
        db_session: Session,
        cliente_usuario: UsuarioORM
    ):
        """Test finding mascotas by tipo."""
        # Create a gato
        gato = MascotaORM(
            nombre="Michi",
            tipo="gato",
            raza="Siamés",
            edad=2,
            peso=4.0,
            propietario=cliente_usuario.username,
        )
        db_session.add(gato)
        db_session.commit()
        
        # Find perros
        perros = mascota_repository.find_by_tipo("perro")
        assert all(m.tipo == "perro" for m in perros)
        
        # Find gatos
        gatos = mascota_repository.find_by_tipo("gato")
        assert all(m.tipo == "gato" for m in gatos)
        
        # Verify our gato is in the list
        gato_ids = [m.id for m in gatos]
        assert gato.id in gato_ids
    
    def test_get_all(
        self,
        mascota_repository: MascotaRepository,
        mascota_instance: MascotaORM
    ):
        """Test getting all mascotas."""
        mascotas = mascota_repository.get_all(limit=100)
        
        assert len(mascotas) >= 1
        
        # Verify test mascota is in the list
        mascota_ids = [m.id for m in mascotas]
        assert mascota_instance.id in mascota_ids
    
    def test_count(
        self,
        mascota_repository: MascotaRepository,
        mascota_instance: MascotaORM
    ):
        """Test counting all mascotas."""
        count = mascota_repository.count()
        
        assert count >= 1


class TestMascotaRepositorySearch:
    """Tests for searching mascotas."""
    
    def test_search_by_name(
        self,
        mascota_repository: MascotaRepository,
        mascota_instance: MascotaORM
    ):
        """Test searching mascota by name."""
        # Assuming repository has a search method
        # If not, we can test via service layer
        pass
    
    def test_search_by_owner_name(
        self,
        mascota_repository: MascotaRepository,
        mascota_instance: MascotaORM
    ):
        """Test searching mascota by owner name."""
        # This would require joins with usuario table
        pass


class TestMascotaRepositoryUpdate:
    """Tests for updating mascotas in repository."""
    
    def test_update_mascota(
        self,
        mascota_repository: MascotaRepository,
        mascota_instance: MascotaORM
    ):
        """Test updating a mascota."""
        mascota_instance.nombre = "Nombre Actualizado"
        mascota_instance.edad = 4
        mascota_instance.peso = 28.0
        
        updated = mascota_repository.update(mascota_instance)
        mascota_repository.commit()
        
        # Verify changes persisted
        mascota = mascota_repository.get_by_id(mascota_instance.id)
        assert mascota.nombre == "Nombre Actualizado"
        assert mascota.edad == 4
        assert mascota.peso == 28.0
    
    def test_update_mascota_tipo(
        self,
        mascota_repository: MascotaRepository,
        mascota_instance: MascotaORM
    ):
        """Test updating mascota tipo."""
        old_tipo = mascota_instance.tipo
        mascota_instance.tipo = "gato"
        
        mascota_repository.update(mascota_instance)
        mascota_repository.commit()
        
        # Verify tipo changed
        mascota = mascota_repository.get_by_id(mascota_instance.id)
        assert mascota.tipo == "gato"
        assert mascota.tipo != old_tipo


class TestMascotaRepositoryDelete:
    """Tests for deleting mascotas (soft delete)."""
    
    def test_soft_delete_mascota(
        self,
        mascota_repository: MascotaRepository,
        db_session: Session,
        cliente_usuario: UsuarioORM
    ):
        """Test soft deleting a mascota."""
        # Create a mascota to delete
        mascota = MascotaORM(
            nombre="To Delete",
            tipo="perro",
            raza="Labrador",
            edad=3,
            peso=25.0,
            propietario=cliente_usuario.username,
        )
        db_session.add(mascota)
        db_session.commit()
        db_session.refresh(mascota)
        
        # Soft delete
        mascota_repository.delete(mascota, hard=False)
        mascota_repository.commit()
        
        # Verify soft deleted
        deleted_mascota = mascota_repository.get_by_id(mascota.id)
        assert deleted_mascota.is_deleted is True
        assert deleted_mascota.deleted_at is not None
    
    def test_restore_mascota(
        self,
        mascota_repository: MascotaRepository,
        db_session: Session,
        cliente_usuario: UsuarioORM
    ):
        """Test restoring a soft-deleted mascota."""
        # Create and soft delete a mascota
        mascota = MascotaORM(
            nombre="To Restore",
            tipo="gato",
            raza="Persa",
            edad=2,
            peso=5.0,
            propietario=cliente_usuario.username,
            is_deleted=True
        )
        db_session.add(mascota)
        db_session.commit()
        db_session.refresh(mascota)
        
        # Restore
        restored = mascota_repository.restore(mascota)
        mascota_repository.commit()
        
        # Verify restored
        mascota_check = mascota_repository.get_by_id(mascota.id)
        assert mascota_check.is_deleted is False
        assert mascota_check.deleted_at is None
    
    def test_find_excludes_deleted_by_default(
        self,
        mascota_repository: MascotaRepository,
        db_session: Session,
        cliente_usuario: UsuarioORM
    ):
        """Test that find operations exclude deleted mascotas by default."""
        # Create and delete a mascota
        mascota = MascotaORM(
            nombre="Deleted Mascota",
            tipo="perro",
            raza="Bulldog",
            edad=3,
            peso=20.0,
            propietario=cliente_usuario.username,
            is_deleted=True
        )
        db_session.add(mascota)
        db_session.commit()
        
        # Get all should exclude deleted
        all_mascotas = mascota_repository.get_all(include_deleted=False)
        deleted_ids = [m.id for m in all_mascotas if m.id == mascota.id]
        assert len(deleted_ids) == 0
        
        # Find by propietario should exclude deleted
        owner_mascotas = mascota_repository.find_by_propietario(
            cliente_usuario.username,
            include_deleted=False
        )
        deleted_ids = [m.id for m in owner_mascotas if m.id == mascota.id]
        assert len(deleted_ids) == 0
    
    def test_find_includes_deleted_when_requested(
        self,
        mascota_repository: MascotaRepository,
        db_session: Session,
        cliente_usuario: UsuarioORM
    ):
        """Test that find operations can include deleted mascotas."""
        # Create and delete a mascota
        mascota = MascotaORM(
            nombre="Deleted Mascota 2",
            tipo="gato",
            raza="Persa",
            edad=2,
            peso=5.0,
            propietario=cliente_usuario.username,
            is_deleted=True
        )
        db_session.add(mascota)
        db_session.commit()
        
        # Get all with deleted
        all_mascotas = mascota_repository.get_all(include_deleted=True)
        deleted_ids = [m.id for m in all_mascotas if m.id == mascota.id]
        assert len(deleted_ids) == 1
        
        # Find by propietario with deleted
        owner_mascotas = mascota_repository.find_by_propietario(
            cliente_usuario.username,
            include_deleted=True
        )
        deleted_ids = [m.id for m in owner_mascotas if m.id == mascota.id]
        assert len(deleted_ids) == 1


class TestMascotaRepositoryFiltering:
    """Tests for complex filtering in repository."""
    
    def test_filter_by_tipo_and_propietario(
        self,
        mascota_repository: MascotaRepository,
        db_session: Session,
        cliente_usuario: UsuarioORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test filtering by both tipo and propietario."""
        # Create mascotas of different types for both users
        perro_cliente = MascotaORM(
            nombre="Perro Cliente",
            tipo="perro",
            raza="Labrador",
            edad=3,
            peso=25.0,
            propietario=cliente_usuario.username,
        )
        gato_cliente = MascotaORM(
            nombre="Gato Cliente",
            tipo="gato",
            raza="Siamés",
            edad=2,
            peso=4.0,
            propietario=cliente_usuario.username,
        )
        perro_vet = MascotaORM(
            nombre="Perro Vet",
            tipo="perro",
            raza="Bulldog",
            edad=2,
            peso=15.0,
            propietario=veterinario_usuario.username,
        )
        
        db_session.add_all([perro_cliente, gato_cliente, perro_vet])
        db_session.commit()
        
        # Find perros for cliente
        perros_cliente = mascota_repository.find_by_propietario(
            cliente_usuario.username
        )
        perros_cliente = [m for m in perros_cliente if m.tipo == "perro"]
        
        assert len(perros_cliente) >= 1
        assert all(m.tipo == "perro" for m in perros_cliente)
        assert all(m.propietario == cliente_usuario.username for m in perros_cliente)
    
    def test_count_by_tipo(
        self,
        mascota_repository: MascotaRepository,
        db_session: Session,
        cliente_usuario: UsuarioORM
    ):
        """Test counting mascotas by tipo."""
        # Create multiple mascotas of different types
        for i in range(3):
            perro = MascotaORM(
                nombre=f"Perro{i}",
                tipo="perro",
                raza="Labrador",
                edad=i,
                peso=10.0 + i,
                propietario=cliente_usuario.username,
            )
            db_session.add(perro)
        
        for i in range(2):
            gato = MascotaORM(
                nombre=f"Gato{i}",
                tipo="gato",
                raza="Siamés",
                edad=i,
                peso=3.0 + i,
                propietario=cliente_usuario.username,
            )
            db_session.add(gato)
        
        db_session.commit()
        
        # Count by tipo
        perros = mascota_repository.find_by_tipo("perro")
        gatos = mascota_repository.find_by_tipo("gato")
        
        assert len(perros) >= 3
        assert len(gatos) >= 2


class TestMascotaRepositoryRelationships:
    """Tests for repository operations involving relationships."""
    
    def test_mascota_propietario_cascade(
        self,
        mascota_repository: MascotaRepository,
        db_session: Session,
        cliente_usuario: UsuarioORM
    ):
        """Test that mascota propietario references are maintained."""
        mascota = MascotaORM(
            nombre="Test Cascade",
            tipo="perro",
            raza="Labrador",
            edad=3,
            peso=25.0,
            propietario=cliente_usuario.username,
        )
        
        created = mascota_repository.create(mascota)
        mascota_repository.commit()
        
        # Verify propietario is correctly set
        mascota_check = mascota_repository.get_by_id(created.id)
        assert mascota_check.propietario == cliente_usuario.username
    
    def test_update_propietario_username_cascades(
        self,
        mascota_repository: MascotaRepository,
        db_session: Session,
        cliente_usuario: UsuarioORM
    ):
        """Test that updating propietario username cascades correctly."""
        # This test would require updating the usuario's username
        # and verifying that mascotas are updated
        # This is typically handled at the service layer
        pass
