"""
Tests for UsuarioRepository CRUD operations.

Tests cover:
- Creating usuarios
- Finding by ID, username
- Finding by role
- Updating usuarios
- Soft delete/restore
- Username uniqueness checks
"""

import pytest
from sqlalchemy.orm import Session
from typing import Dict, Any

from database.models import UsuarioORM
from repositories.usuario_repository import UsuarioRepository
from database.db import hash_password
from core.exceptions import NotFoundException, DatabaseException


@pytest.fixture
def usuario_repository(db_session: Session) -> UsuarioRepository:
    """Create a UsuarioRepository instance."""
    return UsuarioRepository(db_session)


class TestUsuarioRepositoryCreate:
    """Tests for creating usuarios in repository."""
    
    def test_create_usuario(
        self,
        usuario_repository: UsuarioRepository,
        cliente_data: Dict[str, Any]
    ):
        """Test creating a usuario."""
        salt_hex, hash_hex = hash_password(cliente_data["password"])
        
        usuario = UsuarioORM(
            username=cliente_data["username"],
            nombre=cliente_data["nombre"],
            edad=cliente_data["edad"],
            telefono=cliente_data["telefono"],
            role="cliente",
            password_salt=salt_hex,
            password_hash=hash_hex,
        )
        
        created = usuario_repository.create(usuario)
        usuario_repository.commit()
        
        assert created.id is not None
        assert created.username == cliente_data["username"]
        assert created.nombre == cliente_data["nombre"]
        assert created.role == "cliente"
        assert created.is_deleted is False
    
    def test_create_usuario_veterinario(
        self,
        usuario_repository: UsuarioRepository,
        veterinario_data: Dict[str, Any]
    ):
        """Test creating a veterinario."""
        salt_hex, hash_hex = hash_password(veterinario_data["password"])
        
        usuario = UsuarioORM(
            username=veterinario_data["username"],
            nombre=veterinario_data["nombre"],
            edad=veterinario_data["edad"],
            telefono=veterinario_data["telefono"],
            role="veterinario",
            password_salt=salt_hex,
            password_hash=hash_hex,
        )
        
        created = usuario_repository.create(usuario)
        usuario_repository.commit()
        
        assert created.role == "veterinario"


class TestUsuarioRepositoryRead:
    """Tests for reading usuarios from repository."""
    
    def test_get_by_id(
        self,
        usuario_repository: UsuarioRepository,
        cliente_usuario: UsuarioORM
    ):
        """Test getting usuario by ID."""
        usuario = usuario_repository.get_by_id(cliente_usuario.id)
        
        assert usuario is not None
        assert usuario.id == cliente_usuario.id
        assert usuario.username == cliente_usuario.username
    
    def test_get_by_id_nonexistent(
        self,
        usuario_repository: UsuarioRepository
    ):
        """Test getting non-existent usuario returns None."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        usuario = usuario_repository.get_by_id(fake_id)
        
        assert usuario is None
    
    def test_get_by_id_or_fail(
        self,
        usuario_repository: UsuarioRepository,
        cliente_usuario: UsuarioORM
    ):
        """Test get_by_id_or_fail returns usuario."""
        usuario = usuario_repository.get_by_id_or_fail(cliente_usuario.id)
        
        assert usuario is not None
        assert usuario.id == cliente_usuario.id
    
    def test_get_by_id_or_fail_raises_exception(
        self,
        usuario_repository: UsuarioRepository
    ):
        """Test get_by_id_or_fail raises exception for non-existent."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        
        with pytest.raises(NotFoundException):
            usuario_repository.get_by_id_or_fail(fake_id)
    
    def test_find_by_username(
        self,
        usuario_repository: UsuarioRepository,
        cliente_usuario: UsuarioORM
    ):
        """Test finding usuario by username."""
        usuario = usuario_repository.find_by_username(cliente_usuario.username)
        
        assert usuario is not None
        assert usuario.username == cliente_usuario.username
        assert usuario.id == cliente_usuario.id
    
    def test_find_by_username_nonexistent(
        self,
        usuario_repository: UsuarioRepository
    ):
        """Test finding non-existent username returns None."""
        usuario = usuario_repository.find_by_username("nonexistent_user")
        
        assert usuario is None
    
    def test_find_by_role(
        self,
        usuario_repository: UsuarioRepository,
        cliente_usuario: UsuarioORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test finding usuarios by role."""
        clientes = usuario_repository.find_by_role("cliente")
        
        assert len(clientes) >= 1
        assert all(u.role == "cliente" for u in clientes)
        
        # Verify cliente_usuario is in the list
        cliente_ids = [u.id for u in clientes]
        assert cliente_usuario.id in cliente_ids
    
    def test_find_by_role_with_pagination(
        self,
        usuario_repository: UsuarioRepository,
        db_session: Session
    ):
        """Test finding usuarios by role with pagination."""
        # Create multiple clientes
        for i in range(10):
            salt_hex, hash_hex = hash_password("password123")
            usuario = UsuarioORM(
                username=f"cliente{i}",
                nombre=f"Cliente {i}",
                edad=25,
                telefono=f"300{i:07d}",
                role="cliente",
                password_salt=salt_hex,
                password_hash=hash_hex,
            )
            db_session.add(usuario)
        db_session.commit()
        
        # Get first page
        page1 = usuario_repository.find_by_role("cliente", skip=0, limit=5)
        assert len(page1) == 5
        
        # Get second page
        page2 = usuario_repository.find_by_role("cliente", skip=5, limit=5)
        assert len(page2) == 5
        
        # Verify different results
        page1_ids = {u.id for u in page1}
        page2_ids = {u.id for u in page2}
        assert page1_ids.isdisjoint(page2_ids)
    
    def test_count_by_role(
        self,
        usuario_repository: UsuarioRepository,
        cliente_usuario: UsuarioORM,
        veterinario_usuario: UsuarioORM,
        admin_usuario: UsuarioORM
    ):
        """Test counting usuarios by role."""
        cliente_count = usuario_repository.count_by_role("cliente")
        vet_count = usuario_repository.count_by_role("veterinario")
        admin_count = usuario_repository.count_by_role("admin")
        
        assert cliente_count >= 1
        assert vet_count >= 1
        assert admin_count >= 1
    
    def test_get_all(
        self,
        usuario_repository: UsuarioRepository,
        cliente_usuario: UsuarioORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test getting all usuarios."""
        usuarios = usuario_repository.get_all(limit=100)
        
        assert len(usuarios) >= 2
        
        # Verify both test usuarios are in the list
        usuario_ids = [u.id for u in usuarios]
        assert cliente_usuario.id in usuario_ids
        assert veterinario_usuario.id in usuario_ids
    
    def test_count(
        self,
        usuario_repository: UsuarioRepository,
        cliente_usuario: UsuarioORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test counting all usuarios."""
        count = usuario_repository.count()
        
        assert count >= 2


class TestUsuarioRepositoryUpdate:
    """Tests for updating usuarios in repository."""
    
    def test_update_usuario(
        self,
        usuario_repository: UsuarioRepository,
        cliente_usuario: UsuarioORM
    ):
        """Test updating a usuario."""
        cliente_usuario.nombre = "Nombre Actualizado"
        cliente_usuario.edad = 31
        
        updated = usuario_repository.update(cliente_usuario)
        usuario_repository.commit()
        
        # Verify changes persisted
        usuario = usuario_repository.get_by_id(cliente_usuario.id)
        assert usuario.nombre == "Nombre Actualizado"
        assert usuario.edad == 31
    
    def test_update_username(
        self,
        usuario_repository: UsuarioRepository,
        cliente_usuario: UsuarioORM
    ):
        """Test updating username."""
        old_username = cliente_usuario.username
        new_username = "new_username"
        
        cliente_usuario.username = new_username
        usuario_repository.update(cliente_usuario)
        usuario_repository.commit()
        
        # Verify username changed
        usuario = usuario_repository.get_by_id(cliente_usuario.id)
        assert usuario.username == new_username
        
        # Verify old username not found
        old_user = usuario_repository.find_by_username(old_username)
        assert old_user is None


class TestUsuarioRepositoryDelete:
    """Tests for deleting usuarios (soft delete)."""
    
    def test_soft_delete_usuario(
        self,
        usuario_repository: UsuarioRepository,
        db_session: Session
    ):
        """Test soft deleting a usuario."""
        # Create a usuario to delete
        salt_hex, hash_hex = hash_password("password123")
        usuario = UsuarioORM(
            username="to_delete",
            nombre="To Delete",
            edad=25,
            telefono="3005555555",
            role="cliente",
            password_salt=salt_hex,
            password_hash=hash_hex,
        )
        db_session.add(usuario)
        db_session.commit()
        db_session.refresh(usuario)
        
        # Soft delete
        usuario_repository.delete(usuario, hard=False)
        usuario_repository.commit()
        
        # Verify soft deleted
        deleted_user = usuario_repository.get_by_id(usuario.id)
        assert deleted_user.is_deleted is True
        assert deleted_user.deleted_at is not None
    
    def test_restore_usuario(
        self,
        usuario_repository: UsuarioRepository,
        db_session: Session
    ):
        """Test restoring a soft-deleted usuario."""
        # Create and soft delete a usuario
        salt_hex, hash_hex = hash_password("password123")
        usuario = UsuarioORM(
            username="to_restore",
            nombre="To Restore",
            edad=25,
            telefono="3006666666",
            role="cliente",
            password_salt=salt_hex,
            password_hash=hash_hex,
            is_deleted=True
        )
        db_session.add(usuario)
        db_session.commit()
        db_session.refresh(usuario)
        
        # Restore
        restored = usuario_repository.restore(usuario)
        usuario_repository.commit()
        
        # Verify restored
        usuario_check = usuario_repository.get_by_id(usuario.id)
        assert usuario_check.is_deleted is False
        assert usuario_check.deleted_at is None
    
    def test_find_excludes_deleted_by_default(
        self,
        usuario_repository: UsuarioRepository,
        db_session: Session
    ):
        """Test that find operations exclude deleted usuarios by default."""
        # Create and delete a usuario
        salt_hex, hash_hex = hash_password("password123")
        usuario = UsuarioORM(
            username="deleted_user",
            nombre="Deleted User",
            edad=25,
            telefono="3007777777",
            role="cliente",
            password_salt=salt_hex,
            password_hash=hash_hex,
            is_deleted=True
        )
        db_session.add(usuario)
        db_session.commit()
        
        # Get all should exclude deleted
        all_usuarios = usuario_repository.get_all(include_deleted=False)
        deleted_ids = [u.id for u in all_usuarios if u.id == usuario.id]
        assert len(deleted_ids) == 0
        
        # Find by role should exclude deleted
        clientes = usuario_repository.find_by_role("cliente", include_deleted=False)
        deleted_ids = [u.id for u in clientes if u.id == usuario.id]
        assert len(deleted_ids) == 0
    
    def test_find_includes_deleted_when_requested(
        self,
        usuario_repository: UsuarioRepository,
        db_session: Session
    ):
        """Test that find operations can include deleted usuarios."""
        # Create and delete a usuario
        salt_hex, hash_hex = hash_password("password123")
        usuario = UsuarioORM(
            username="deleted_user2",
            nombre="Deleted User 2",
            edad=25,
            telefono="3008888888",
            role="cliente",
            password_salt=salt_hex,
            password_hash=hash_hex,
            is_deleted=True
        )
        db_session.add(usuario)
        db_session.commit()
        
        # Get all with deleted
        all_usuarios = usuario_repository.get_all(include_deleted=True)
        deleted_ids = [u.id for u in all_usuarios if u.id == usuario.id]
        assert len(deleted_ids) == 1


class TestUsuarioRepositoryValidation:
    """Tests for repository validation methods."""
    
    def test_exists_username_true(
        self,
        usuario_repository: UsuarioRepository,
        cliente_usuario: UsuarioORM
    ):
        """Test exists_username returns True for existing username."""
        exists = usuario_repository.exists_username(cliente_usuario.username)
        
        assert exists is True
    
    def test_exists_username_false(
        self,
        usuario_repository: UsuarioRepository
    ):
        """Test exists_username returns False for non-existent username."""
        exists = usuario_repository.exists_username("nonexistent_username")
        
        assert exists is False
    
    def test_exists_username_with_exclusion(
        self,
        usuario_repository: UsuarioRepository,
        cliente_usuario: UsuarioORM
    ):
        """Test exists_username can exclude specific ID."""
        # Should return False when excluding the same user
        exists = usuario_repository.exists_username(
            cliente_usuario.username,
            exclude_id=cliente_usuario.id
        )
        
        assert exists is False
    
    def test_search_by_name(
        self,
        usuario_repository: UsuarioRepository,
        cliente_usuario: UsuarioORM
    ):
        """Test searching usuarios by name."""
        # Search by full name
        usuarios = usuario_repository.search_by_name(cliente_usuario.nombre)
        
        assert len(usuarios) >= 1
        usuario_ids = [u.id for u in usuarios]
        assert cliente_usuario.id in usuario_ids
    
    def test_search_by_name_partial(
        self,
        usuario_repository: UsuarioRepository,
        cliente_usuario: UsuarioORM
    ):
        """Test partial name search works."""
        # Search by first word of name
        first_word = cliente_usuario.nombre.split()[0]
        usuarios = usuario_repository.search_by_name(first_word)
        
        assert len(usuarios) >= 1
    
    def test_search_by_name_case_insensitive(
        self,
        usuario_repository: UsuarioRepository,
        cliente_usuario: UsuarioORM
    ):
        """Test name search is case insensitive."""
        # Search with different case
        usuarios = usuario_repository.search_by_name(
            cliente_usuario.nombre.upper()
        )
        
        assert len(usuarios) >= 1
        usuario_ids = [u.id for u in usuarios]
        assert cliente_usuario.id in usuario_ids
