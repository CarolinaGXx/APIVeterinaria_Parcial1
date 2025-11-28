"""
Tests for Receta Repository (CRUD operations).

Tests cover:
- Creating recetas with and without lineas
- Reading recetas by various filters
- Updating recetas and lineas
- Deleting recetas (soft delete)
- Relationship handling
"""

import pytest
from datetime import datetime
from uuid import uuid4

from repositories.receta_repository import RecetaRepository
from database.models import RecetaORM, RecetaLineaORM


class TestRecetaRepositoryCreate:
    """Tests for creating recetas."""
    
    def test_create_receta_exitoso(
        self,
        db_session,
        veterinario_usuario,
        cita_instance
    ):
        """Test successful receta creation."""
        receta_repo = RecetaRepository(db_session)
        
        receta_id = str(uuid4())
        receta = RecetaORM(
            id=receta_id,
            id_cita=str(cita_instance.id),
            fecha_emision=datetime.now(),
            indicaciones="Test receta",
            veterinario=veterinario_usuario.username
        )
        
        created = receta_repo.create(receta, user_id=veterinario_usuario.id)
        db_session.commit()
        
        assert created.id == receta_id
        assert created.id_cita == str(cita_instance.id)

    def test_create_receta_con_lineas(
        self,
        db_session,
        veterinario_usuario,
        cita_instance
    ):
        """Test creating receta with lineas."""
        receta_repo = RecetaRepository(db_session)
        
        receta_id = str(uuid4())
        receta = RecetaORM(
            id=receta_id,
            id_cita=str(cita_instance.id),
            fecha_emision=datetime.now(),
            indicaciones="Test",
            veterinario=veterinario_usuario.username
        )
        
        lineas = [
            RecetaLineaORM(medicamento="Amoxicilina", dosis="250mg", frecuencia="Cada 8 horas"),
            RecetaLineaORM(medicamento="Ibuprofeno", dosis="100mg", frecuencia="Cada 12 horas")
        ]
        
        created = receta_repo.create_with_lineas(receta, lineas, user_id=veterinario_usuario.id)
        db_session.commit()
        
        assert created.id == receta_id
        assert len(created.lineas) == 2

    def test_create_receta_sin_lineas(
        self,
        db_session,
        veterinario_usuario,
        cita_instance
    ):
        """Test creating receta without lineas."""
        receta_repo = RecetaRepository(db_session)
        
        receta_id = str(uuid4())
        receta = RecetaORM(
            id=receta_id,
            id_cita=str(cita_instance.id),
            fecha_emision=datetime.now(),
            indicaciones="Sin medicamentos",
            veterinario=veterinario_usuario.username
        )
        
        created = receta_repo.create(receta, user_id=veterinario_usuario.id)
        db_session.commit()
        
        assert created.id == receta_id
        assert len(created.lineas) == 0


class TestRecetaRepositoryRead:
    """Tests for reading recetas."""
    
    def test_get_by_id_exitoso(
        self,
        db_session,
        veterinario_usuario,
        cita_instance
    ):
        """Test get receta by ID."""
        receta_repo = RecetaRepository(db_session)
        
        receta_id = str(uuid4())
        receta = RecetaORM(
            id=receta_id,
            id_cita=str(cita_instance.id),
            fecha_emision=datetime.now(),
            indicaciones="Test",
            veterinario=veterinario_usuario.username
        )
        receta_repo.create(receta, user_id=veterinario_usuario.id)
        db_session.commit()
        
        retrieved = receta_repo.get_by_id(receta_id)
        
        assert retrieved is not None
        assert retrieved.id == receta_id

    def test_get_by_id_with_lineas(
        self,
        db_session,
        veterinario_usuario,
        cita_instance
    ):
        """Test get receta with lineas."""
        receta_repo = RecetaRepository(db_session)
        
        receta_id = str(uuid4())
        receta = RecetaORM(
            id=receta_id,
            id_cita=str(cita_instance.id),
            fecha_emision=datetime.now(),
            indicaciones="Test",
            veterinario=veterinario_usuario.username
        )
        
        lineas = [
            RecetaLineaORM(medicamento="Amoxicilina", dosis="250mg"),
            RecetaLineaORM(medicamento="Paracetamol", dosis="500mg")
        ]
        
        receta_repo.create_with_lineas(receta, lineas, user_id=veterinario_usuario.id)
        db_session.commit()
        
        retrieved = receta_repo.get_by_id_with_lineas(receta_id)
        
        assert retrieved is not None
        assert len(retrieved.lineas) == 2

    def test_find_by_cita(
        self,
        db_session,
        veterinario_usuario,
        cita_instance
    ):
        """Test find receta by cita."""
        receta_repo = RecetaRepository(db_session)
        
        receta_id = str(uuid4())
        receta = RecetaORM(
            id=receta_id,
            id_cita=str(cita_instance.id),
            fecha_emision=datetime.now(),
            indicaciones="Test",
            veterinario=veterinario_usuario.username
        )
        receta_repo.create(receta, user_id=veterinario_usuario.id)
        db_session.commit()
        
        retrieved = receta_repo.find_by_cita(str(cita_instance.id))
        
        assert retrieved is not None
        assert retrieved.id_cita == str(cita_instance.id)

    def test_find_by_cita_no_existe(
        self,
        db_session
    ):
        """Test find receta by non-existent cita."""
        receta_repo = RecetaRepository(db_session)
        
        cita_id = str(uuid4())
        retrieved = receta_repo.find_by_cita(cita_id)
        
        assert retrieved is None

    def test_find_by_veterinario(
        self,
        db_session,
        veterinario_usuario,
        cita_instance
    ):
        """Test find recetas by veterinario."""
        receta_repo = RecetaRepository(db_session)
        
        for i in range(3):
            receta_id = str(uuid4())
            receta = RecetaORM(
                id=receta_id,
                id_cita=str(cita_instance.id),
                fecha_emision=datetime.now(),
                indicaciones=f"Test {i}",
                veterinario=veterinario_usuario.username
            )
            receta_repo.create(receta, user_id=veterinario_usuario.id)
        db_session.commit()
        
        recetas = receta_repo.find_by_veterinario(veterinario_usuario.username)
        
        assert len(recetas) >= 3

    def test_find_by_mascota(
        self,
        db_session,
        veterinario_usuario,
        mascota_instance,
        cita_instance
    ):
        """Test find recetas by mascota."""
        receta_repo = RecetaRepository(db_session)
        
        receta_id = str(uuid4())
        receta = RecetaORM(
            id=receta_id,
            id_cita=str(cita_instance.id),
            fecha_emision=datetime.now(),
            indicaciones="Test",
            veterinario=veterinario_usuario.username
        )
        receta_repo.create(receta, user_id=veterinario_usuario.id)
        db_session.commit()
        
        recetas = receta_repo.find_by_mascota(mascota_instance.id)
        
        assert len(recetas) >= 1

    def test_find_by_propietario(
        self,
        db_session,
        veterinario_usuario,
        cliente_usuario,
        cita_instance
    ):
        """Test find recetas by propietario."""
        receta_repo = RecetaRepository(db_session)
        
        receta_id = str(uuid4())
        receta = RecetaORM(
            id=receta_id,
            id_cita=str(cita_instance.id),
            fecha_emision=datetime.now(),
            indicaciones="Test",
            veterinario=veterinario_usuario.username
        )
        receta_repo.create(receta, user_id=veterinario_usuario.id)
        db_session.commit()
        
        recetas = receta_repo.find_by_propietario(cliente_usuario.username)
        
        assert len(recetas) >= 1

    def test_get_all(
        self,
        db_session,
        veterinario_usuario,
        cita_instance
    ):
        """Test get all recetas."""
        receta_repo = RecetaRepository(db_session)
        
        for i in range(3):
            receta_id = str(uuid4())
            receta = RecetaORM(
                id=receta_id,
                id_cita=str(cita_instance.id),
                fecha_emision=datetime.now(),
                indicaciones=f"Test {i}",
                veterinario=veterinario_usuario.username
            )
            receta_repo.create(receta, user_id=veterinario_usuario.id)
        db_session.commit()
        
        recetas = receta_repo.get_all(limit=100)
        
        assert len(recetas) >= 3


class TestRecetaRepositoryUpdate:
    """Tests for updating recetas."""
    
    def test_update_indicaciones(
        self,
        db_session,
        veterinario_usuario,
        cita_instance
    ):
        """Test updating receta indicaciones."""
        receta_repo = RecetaRepository(db_session)
        
        receta_id = str(uuid4())
        receta = RecetaORM(
            id=receta_id,
            id_cita=str(cita_instance.id),
            fecha_emision=datetime.now(),
            indicaciones="Original",
            veterinario=veterinario_usuario.username
        )
        receta_repo.create(receta, user_id=veterinario_usuario.id)
        db_session.commit()
        
        receta.indicaciones = "Actualizado"
        receta_repo.update(receta)
        db_session.commit()
        
        retrieved = receta_repo.get_by_id(receta_id)
        assert retrieved.indicaciones == "Actualizado"

    def test_update_lineas(
        self,
        db_session,
        veterinario_usuario,
        cita_instance
    ):
        """Test updating receta lineas."""
        receta_repo = RecetaRepository(db_session)
        
        receta_id = str(uuid4())
        receta = RecetaORM(
            id=receta_id,
            id_cita=str(cita_instance.id),
            fecha_emision=datetime.now(),
            indicaciones="Test",
            veterinario=veterinario_usuario.username
        )
        
        old_lineas = [RecetaLineaORM(medicamento="Viejo", dosis="100mg")]
        receta_repo.create_with_lineas(receta, old_lineas, user_id=veterinario_usuario.id)
        db_session.commit()
        
        new_lineas = [
            RecetaLineaORM(medicamento="Nuevo1", dosis="200mg"),
            RecetaLineaORM(medicamento="Nuevo2", dosis="300mg")
        ]
        receta_repo.update_lineas(receta_id, new_lineas)
        db_session.commit()
        
        retrieved = receta_repo.get_by_id_with_lineas(receta_id)
        assert len(retrieved.lineas) == 2
        assert retrieved.lineas[0].medicamento == "Nuevo1"


class TestRecetaRepositoryDelete:
    """Tests for deleting recetas."""
    
    def test_soft_delete_receta(
        self,
        db_session,
        veterinario_usuario,
        cita_instance
    ):
        """Test soft delete receta."""
        receta_repo = RecetaRepository(db_session)
        
        receta_id = str(uuid4())
        receta = RecetaORM(
            id=receta_id,
            id_cita=str(cita_instance.id),
            fecha_emision=datetime.now(),
            indicaciones="Test",
            veterinario=veterinario_usuario.username
        )
        created = receta_repo.create(receta, user_id=veterinario_usuario.id)
        db_session.commit()
        
        receta_repo.delete(created, user_id=veterinario_usuario.id, hard=False)
        db_session.commit()
        
        assert created.is_deleted is True

    def test_restore_receta(
        self,
        db_session,
        veterinario_usuario,
        cita_instance
    ):
        """Test restore deleted receta."""
        receta_repo = RecetaRepository(db_session)
        
        receta_id = str(uuid4())
        receta = RecetaORM(
            id=receta_id,
            id_cita=str(cita_instance.id),
            fecha_emision=datetime.now(),
            indicaciones="Test",
            veterinario=veterinario_usuario.username
        )
        created = receta_repo.create(receta, user_id=veterinario_usuario.id)
        db_session.commit()
        
        receta_repo.delete(created, user_id=veterinario_usuario.id, hard=False)
        db_session.commit()
        
        receta_repo.restore(created)
        db_session.commit()
        
        retrieved = receta_repo.get_by_id(receta_id)
        assert retrieved.is_deleted is False

    def test_find_excludes_deleted_by_default(
        self,
        db_session,
        veterinario_usuario,
        cita_instance
    ):
        """Test that deleted recetas are excluded by default."""
        receta_repo = RecetaRepository(db_session)
        
        receta_id = str(uuid4())
        receta = RecetaORM(
            id=receta_id,
            id_cita=str(cita_instance.id),
            fecha_emision=datetime.now(),
            indicaciones="Test",
            veterinario=veterinario_usuario.username
        )
        created = receta_repo.create(receta, user_id=veterinario_usuario.id)
        db_session.commit()
        
        count_before = len(receta_repo.find_by_veterinario(veterinario_usuario.username))
        
        receta_repo.delete(created, user_id=veterinario_usuario.id, hard=False)
        db_session.commit()
        
        count_after = len(receta_repo.find_by_veterinario(veterinario_usuario.username))
        
        assert count_after == count_before - 1

    def test_find_includes_deleted_when_requested(
        self,
        db_session,
        veterinario_usuario,
        cita_instance
    ):
        """Test that deleted recetas can be included when requested."""
        receta_repo = RecetaRepository(db_session)
        
        receta_id = str(uuid4())
        receta = RecetaORM(
            id=receta_id,
            id_cita=str(cita_instance.id),
            fecha_emision=datetime.now(),
            indicaciones="Test",
            veterinario=veterinario_usuario.username
        )
        created = receta_repo.create(receta, user_id=veterinario_usuario.id)
        db_session.commit()
        
        receta_repo.delete(created, user_id=veterinario_usuario.id, hard=False)
        db_session.commit()
        
        recetas = receta_repo.find_by_veterinario(
            veterinario_usuario.username,
            include_deleted=True
        )
        
        assert len(recetas) >= 1


class TestRecetaRepositoryRelationships:
    """Tests for receta relationships."""
    
    def test_receta_cita_relationship(
        self,
        db_session,
        veterinario_usuario,
        cita_instance
    ):
        """Test receta-cita relationship."""
        receta_repo = RecetaRepository(db_session)
        
        receta_id = str(uuid4())
        receta = RecetaORM(
            id=receta_id,
            id_cita=str(cita_instance.id),
            fecha_emision=datetime.now(),
            indicaciones="Test",
            veterinario=veterinario_usuario.username
        )
        receta_repo.create(receta, user_id=veterinario_usuario.id)
        db_session.commit()
        
        retrieved = receta_repo.get_by_id(receta_id)
        
        assert retrieved is not None
        assert retrieved.id_cita == str(cita_instance.id)

    def test_receta_audit_fields(
        self,
        db_session,
        veterinario_usuario,
        cita_instance
    ):
        """Test receta audit fields."""
        receta_repo = RecetaRepository(db_session)
        
        receta_id = str(uuid4())
        receta = RecetaORM(
            id=receta_id,
            id_cita=str(cita_instance.id),
            fecha_emision=datetime.now(),
            indicaciones="Test",
            veterinario=veterinario_usuario.username
        )
        receta_repo.create(receta, user_id=veterinario_usuario.id)
        db_session.commit()
        
        retrieved = receta_repo.get_by_id(receta_id)
        
        assert retrieved.id_usuario_creacion is not None
        assert retrieved.fecha_creacion is not None
        assert retrieved.is_deleted is False
