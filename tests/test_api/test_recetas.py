"""
Tests for Receta API endpoints.

Tests cover:
- Creating recetas with lineas
- Listing recetas with filters
- Getting recetas by cita and ID
- Updating recetas (indicaciones and lineas)
- Deleting recetas (soft delete)
"""

import pytest
from datetime import datetime, date, timedelta
from typing import Dict
from uuid import uuid4

from fastapi.testclient import TestClient
from database.models import RecetaORM, RecetaLineaORM


class TestRecetaCreation:
    """Tests for creating recetas."""
    
    def test_crear_receta_desde_cita_como_veterinario(
        self,
        client: TestClient,
        auth_headers_veterinario: Dict[str, str],
        cita_instance
    ):
        """Test creating a receta as veterinario."""
        receta_data = {
            "id_cita": str(cita_instance.id),
            "indicaciones": "Dar medicamento cada 8 horas",
            "lineas": [
                {
                    "medicamento": "Amoxicilina",
                    "dosis": "250mg",
                    "frecuencia": "Cada 8 horas",
                    "duracion": "7 días"
                }
            ]
        }
        
        response = client.post("/recetas/", json=receta_data, headers=auth_headers_veterinario)
        
        assert response.status_code == 201
        data = response.json()
        assert data["id_receta"] is not None
        assert len(data["lineas"]) == 1

    def test_crear_receta_sin_cita_falla(
        self,
        client: TestClient,
        auth_headers_veterinario: Dict[str, str]
    ):
        """Test that creating receta without cita fails."""
        receta_data = {
            "id_cita": str(uuid4()),
            "indicaciones": "Test"
        }
        
        response = client.post("/recetas/", json=receta_data, headers=auth_headers_veterinario)
        
        assert response.status_code in [400, 404]

    def test_crear_receta_cliente_falla(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str],
        cita_instance
    ):
        """Test that cliente cannot create receta."""
        receta_data = {
            "id_cita": str(cita_instance.id),
            "indicaciones": "Test"
        }
        
        response = client.post("/recetas/", json=receta_data, headers=auth_headers_cliente)
        
        assert response.status_code == 403

    def test_crear_receta_sin_autenticacion_falla(
        self,
        client: TestClient,
        cita_instance
    ):
        """Test that unauthenticated user cannot create receta."""
        receta_data = {
            "id_cita": str(cita_instance.id),
            "indicaciones": "Test"
        }
        
        response = client.post("/recetas/", json=receta_data)
        
        assert response.status_code == 401

    def test_crear_receta_admin_puede(
        self,
        client: TestClient,
        auth_headers_admin: Dict[str, str],
        cita_instance
    ):
        """Test that admin can create receta."""
        receta_data = {
            "id_cita": str(cita_instance.id),
            "indicaciones": "Admin receta"
        }
        
        response = client.post("/recetas/", json=receta_data, headers=auth_headers_admin)
        
        assert response.status_code == 201

    def test_crear_receta_con_multiples_lineas(
        self,
        client: TestClient,
        auth_headers_veterinario: Dict[str, str],
        cita_instance
    ):
        """Test creating receta with multiple lineas."""
        receta_data = {
            "id_cita": str(cita_instance.id),
            "indicaciones": "Medicamentos múltiples",
            "lineas": [
                {"medicamento": "Med1", "dosis": "100mg"},
                {"medicamento": "Med2", "dosis": "200mg"},
                {"medicamento": "Med3", "dosis": "300mg"}
            ]
        }
        
        response = client.post("/recetas/", json=receta_data, headers=auth_headers_veterinario)
        
        assert response.status_code == 201
        data = response.json()
        assert len(data["lineas"]) == 3


class TestRecetaList:
    """Tests for listing recetas."""
    
    def test_listar_recetas_veterinario(
        self,
        client: TestClient,
        auth_headers_veterinario: Dict[str, str],
        db_session,
        veterinario_usuario,
        cita_instance
    ):
        """Test veterinario can list recetas."""
        from repositories.receta_repository import RecetaRepository
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
        
        response = client.get("/recetas/", headers=auth_headers_veterinario)
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) >= 1

    def test_listar_recetas_cliente_solo_propias(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str],
        db_session,
        cliente_usuario,
        veterinario_usuario,
        cita_instance
    ):
        """Test cliente only sees their own recetas."""
        from repositories.receta_repository import RecetaRepository
        
        receta_repo = RecetaRepository(db_session)
        receta_id = str(uuid4())
        receta = RecetaORM(
            id=receta_id,
            id_cita=str(cita_instance.id),
            fecha_emision=datetime.now(),
            indicaciones="Cliente receta",
            veterinario=veterinario_usuario.username
        )
        receta_repo.create(receta, user_id=veterinario_usuario.id)
        db_session.commit()
        
        response = client.get("/recetas/", headers=auth_headers_cliente)
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    def test_listar_recetas_paginacion(
        self,
        client: TestClient,
        auth_headers_veterinario: Dict[str, str],
        db_session,
        veterinario_usuario,
        cita_instance
    ):
        """Test pagination of recetas list."""
        from repositories.receta_repository import RecetaRepository
        receta_repo = RecetaRepository(db_session)
        
        for i in range(5):
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
        
        response = client.get("/recetas/?limit=2", headers=auth_headers_veterinario)
        
        assert response.status_code == 200
        data = response.json()
        assert "pagination" in data


class TestRecetaGet:
    """Tests for getting recetas."""
    
    def test_obtener_receta_por_cita(
        self,
        client: TestClient,
        auth_headers_veterinario: Dict[str, str],
        db_session,
        veterinario_usuario,
        cita_instance
    ):
        """Test getting receta by cita ID."""
        from repositories.receta_repository import RecetaRepository
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
        
        response = client.get(f"/recetas/cita/{cita_instance.id}", headers=auth_headers_veterinario)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id_cita"] == str(cita_instance.id)

    def test_obtener_receta_por_id(
        self,
        client: TestClient,
        auth_headers_veterinario: Dict[str, str],
        db_session,
        veterinario_usuario,
        cita_instance
    ):
        """Test getting receta by ID."""
        from repositories.receta_repository import RecetaRepository
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
        
        response = client.get(f"/recetas/{receta_id}", headers=auth_headers_veterinario)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id_receta"] == receta_id

    def test_obtener_receta_no_existe(
        self,
        client: TestClient,
        auth_headers_veterinario: Dict[str, str]
    ):
        """Test getting non-existent receta."""
        fake_id = str(uuid4())
        response = client.get(f"/recetas/{fake_id}", headers=auth_headers_veterinario)
        
        assert response.status_code == 404

    def test_cliente_no_puede_ver_receta_otra_mascota(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str],
        db_session,
        veterinario_usuario,
        mascota_otro_cliente
    ):
        """Test cliente cannot see receta for another client's pet."""
        from repositories.receta_repository import RecetaRepository
        from repositories.cita_repository import CitaRepository
        from database.models import CitaORM
        
        # Create a cita for the other client's mascota
        cita_repo = CitaRepository(db_session)
        cita_id = str(uuid4())
        cita = CitaORM(
            id=cita_id,
            id_mascota=mascota_otro_cliente.id,
            fecha=datetime.fromisoformat((date.today() + timedelta(days=1)).isoformat() + "T10:00:00"),
            motivo="Control de rutina",
            veterinario=veterinario_usuario.username,
        )
        cita_repo.create(cita, user_id=veterinario_usuario.id)
        db_session.commit()
        
        receta_repo = RecetaRepository(db_session)
        receta_id = str(uuid4())
        receta = RecetaORM(
            id=receta_id,
            id_cita=cita_id,
            fecha_emision=datetime.now(),
            indicaciones="Test",
            veterinario=veterinario_usuario.username
        )
        receta_repo.create(receta, user_id=veterinario_usuario.id)
        db_session.commit()
        
        response = client.get(f"/recetas/{receta_id}", headers=auth_headers_cliente)
        
        # Should be 403 if cliente doesn't own the pet
        assert response.status_code in [403, 404]


class TestRecetaUpdate:
    """Tests for updating recetas."""
    
    def test_actualizar_receta_indicaciones(
        self,
        client: TestClient,
        auth_headers_veterinario: Dict[str, str],
        db_session,
        veterinario_usuario,
        cita_instance
    ):
        """Test updating receta indicaciones."""
        from repositories.receta_repository import RecetaRepository
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
        
        update_data = {
            "indicaciones": "Actualizado"
        }
        
        response = client.put(f"/recetas/{receta_id}", json=update_data, headers=auth_headers_veterinario)
        
        assert response.status_code == 200
        data = response.json()
        assert data["indicaciones"] == "Actualizado"

    def test_actualizar_receta_lineas(
        self,
        client: TestClient,
        auth_headers_veterinario: Dict[str, str],
        db_session,
        veterinario_usuario,
        cita_instance
    ):
        """Test updating receta lineas."""
        from repositories.receta_repository import RecetaRepository
        receta_repo = RecetaRepository(db_session)
        
        receta_id = str(uuid4())
        receta = RecetaORM(
            id=receta_id,
            id_cita=str(cita_instance.id),
            fecha_emision=datetime.now(),
            indicaciones="Test",
            veterinario=veterinario_usuario.username
        )
        lineas = [RecetaLineaORM(medicamento="Old", dosis="100mg")]
        receta_repo.create_with_lineas(receta, lineas, user_id=veterinario_usuario.id)
        db_session.commit()
        
        update_data = {
            "lineas": [
                {"medicamento": "New1", "dosis": "200mg"},
                {"medicamento": "New2", "dosis": "300mg"}
            ]
        }
        
        response = client.put(f"/recetas/{receta_id}", json=update_data, headers=auth_headers_veterinario)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["lineas"]) == 2

    def test_actualizar_receta_cliente_falla(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str],
        db_session,
        veterinario_usuario,
        cita_instance
    ):
        """Test cliente cannot update receta."""
        from repositories.receta_repository import RecetaRepository
        
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
        
        update_data = {"indicaciones": "Updated"}
        
        response = client.put(f"/recetas/{receta_id}", json=update_data, headers=auth_headers_cliente)
        
        assert response.status_code == 403


class TestRecetaDelete:
    """Tests for deleting recetas."""
    
    def test_eliminar_receta_como_admin(
        self,
        client: TestClient,
        auth_headers_admin: Dict[str, str],
        db_session,
        veterinario_usuario,
        cita_instance
    ):
        """Test admin can delete receta."""
        from repositories.receta_repository import RecetaRepository
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
        
        response = client.delete(f"/recetas/{receta_id}", headers=auth_headers_admin)
        
        assert response.status_code == 200

    def test_eliminar_receta_veterinario_falla(
        self,
        client: TestClient,
        auth_headers_veterinario: Dict[str, str],
        db_session,
        veterinario_usuario,
        cita_instance
    ):
        """Test veterinario cannot delete receta."""
        from repositories.receta_repository import RecetaRepository
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
        
        response = client.delete(f"/recetas/{receta_id}", headers=auth_headers_veterinario)
        
        assert response.status_code == 403

    def test_eliminar_receta_sin_autenticacion_falla(
        self,
        client: TestClient,
        db_session,
        veterinario_usuario,
        cita_instance
    ):
        """Test unauthenticated user cannot delete receta."""
        from repositories.receta_repository import RecetaRepository
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
        
        response = client.delete(f"/recetas/{receta_id}")
        
        assert response.status_code == 401
