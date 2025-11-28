"""
Tests for Vacuna API endpoints.

Tests cover:
- Vacuna registration (vaccine recording)
- Listing vacunas with filters and pagination
- Getting vacuna by ID
- Updating vacuna details
- Deleting vacunas
- Access control (role-based)
- Proximas dosis (upcoming doses)
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from typing import Dict, Any
from datetime import date, timedelta

from database.models import VacunaORM, UsuarioORM, MascotaORM
from tests.conftest import assert_valid_uuid


class TestVacunaCreation:
    """Tests for vacuna registration endpoint (POST /vacunas/)."""
    
    def test_registrar_vacuna_como_veterinario(
        self,
        client: TestClient,
        auth_headers_veterinario: Dict[str, str],
        veterinario_usuario: UsuarioORM,
        mascota_instance: MascotaORM
    ):
        """Test veterinario can register a vaccine."""
        vacuna_data = {
            "id_mascota": str(mascota_instance.id),
            "tipo_vacuna": "rabia",
            "lote_vacuna": "LOTE123456",
            "proxima_dosis": (date.today() + timedelta(days=365)).isoformat()
        }
        
        response = client.post(
            "/vacunas/",
            json=vacuna_data,
            headers=auth_headers_veterinario
        )
        
        assert response.status_code == 201
        data = response.json()
        
        # Verify response structure
        assert "id_vacuna" in data
        assert "id_mascota" in data
        assert "tipo_vacuna" in data
        assert "fecha_aplicacion" in data
        assert "lote_vacuna" in data
        assert "veterinario" in data
        assert "mascota_nombre" in data
        
        # Verify data correctness
        assert data["tipo_vacuna"] == "rabia"
        assert data["lote_vacuna"] == "LOTE123456"
        assert data["veterinario"] == veterinario_usuario.username
        assert data["mascota_nombre"] == mascota_instance.nombre
        assert assert_valid_uuid(data["id_vacuna"])
    
    def test_registrar_vacuna_como_admin(
        self,
        client: TestClient,
        auth_headers_admin: Dict[str, str],
        mascota_instance: MascotaORM
    ):
        """Test admin can register a vaccine."""
        vacuna_data = {
            "id_mascota": str(mascota_instance.id),
            "tipo_vacuna": "parvovirus",
            "lote_vacuna": "LOTE789012",
            "proxima_dosis": (date.today() + timedelta(days=30)).isoformat()
        }
        
        response = client.post(
            "/vacunas/",
            json=vacuna_data,
            headers=auth_headers_admin
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["tipo_vacuna"] == "parvovirus"
    
    def test_registrar_vacuna_cliente_falla(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str],
        mascota_instance: MascotaORM
    ):
        """Test cliente cannot register vaccines."""
        vacuna_data = {
            "id_mascota": str(mascota_instance.id),
            "tipo_vacuna": "rabia",
            "lote_vacuna": "LOTE123456"
        }
        
        response = client.post(
            "/vacunas/",
            json=vacuna_data,
            headers=auth_headers_cliente
        )
        
        assert response.status_code == 403
    
    def test_registrar_vacuna_mascota_inexistente(
        self,
        client: TestClient,
        auth_headers_veterinario: Dict[str, str]
    ):
        """Test registering vaccine for non-existent pet fails."""
        vacuna_data = {
            "id_mascota": "00000000-0000-0000-0000-000000000000",
            "tipo_vacuna": "rabia",
            "lote_vacuna": "LOTE123456"
        }
        
        response = client.post(
            "/vacunas/",
            json=vacuna_data,
            headers=auth_headers_veterinario
        )
        
        assert response.status_code == 404
    
    def test_registrar_vacuna_lote_invalido(
        self,
        client: TestClient,
        auth_headers_veterinario: Dict[str, str],
        mascota_instance: MascotaORM
    ):
        """Test registering vaccine with invalid lot number fails."""
        vacuna_data = {
            "id_mascota": str(mascota_instance.id),
            "tipo_vacuna": "rabia",
            "lote_vacuna": ""  # Empty lot number
        }
        
        response = client.post(
            "/vacunas/",
            json=vacuna_data,
            headers=auth_headers_veterinario
        )
        
        assert response.status_code == 422
    
    def test_registrar_vacuna_proxima_dosis_invalida(
        self,
        client: TestClient,
        auth_headers_veterinario: Dict[str, str],
        mascota_instance: MascotaORM
    ):
        """Test registering vaccine with invalid proxima_dosis fails."""
        vacuna_data = {
            "id_mascota": str(mascota_instance.id),
            "tipo_vacuna": "rabia",
            "lote_vacuna": "LOTE123456",
            "proxima_dosis": (date.today() - timedelta(days=1)).isoformat()  # Past date
        }

        response = client.post(
            "/vacunas/",
            json=vacuna_data,
            headers=auth_headers_veterinario
        )

        assert response.status_code == 422
    
    def test_registrar_vacuna_sin_autenticacion_falla(
        self,
        client: TestClient,
        mascota_instance: MascotaORM
    ):
        """Test registering vaccine without authentication fails."""
        vacuna_data = {
            "id_mascota": str(mascota_instance.id),
            "tipo_vacuna": "rabia",
            "lote_vacuna": "LOTE123456"
        }
        
        response = client.post("/vacunas/", json=vacuna_data)
        
        assert response.status_code == 401


class TestVacunaList:
    """Tests for listing vacunas with pagination and filters."""
    
    def test_listar_vacunas_cliente_solo_propias(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str],
        cliente_usuario: UsuarioORM,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM,
        db_session: Session
    ):
        """Test cliente only sees vaccines for their own pets."""
        # Create a vaccine
        vacuna = VacunaORM(
            id_mascota=mascota_instance.id,
            tipo_vacuna="rabia",
            fecha_aplicacion=date.today(),
            lote_vacuna="LOTE123456",
            veterinario=veterinario_usuario.username,
            proxima_dosis=date.today() + timedelta(days=365)
        )
        db_session.add(vacuna)
        db_session.commit()
        
        response = client.get("/vacunas/", headers=auth_headers_cliente)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify pagination structure
        assert "data" in data
        assert "pagination" in data
        
        # All returned vacunas should be for their pets
        for vac in data["data"]:
            assert vac["propietario_username"] == cliente_usuario.username
    
    def test_listar_vacunas_veterinario_ve_todas(
        self,
        client: TestClient,
        auth_headers_veterinario: Dict[str, str],
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM,
        db_session: Session
    ):
        """Test veterinario can see all vaccines."""
        vacuna = VacunaORM(
            id_mascota=mascota_instance.id,
            tipo_vacuna="parvovirus",
            fecha_aplicacion=date.today(),
            lote_vacuna="LOTE789012",
            veterinario=veterinario_usuario.username
        )
        db_session.add(vacuna)
        db_session.commit()
        
        response = client.get("/vacunas/", headers=auth_headers_veterinario)
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
    
    def test_listar_vacunas_admin_ve_todas(
        self,
        client: TestClient,
        auth_headers_admin: Dict[str, str],
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM,
        db_session: Session
    ):
        """Test admin can see all vaccines."""
        vacuna = VacunaORM(
            id_mascota=mascota_instance.id,
            tipo_vacuna="moquillo",
            fecha_aplicacion=date.today(),
            lote_vacuna="LOTE345678",
            veterinario=veterinario_usuario.username
        )
        db_session.add(vacuna)
        db_session.commit()
        
        response = client.get("/vacunas/", headers=auth_headers_admin)
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
    
    def test_listar_vacunas_filtro_por_tipo(
        self,
        client: TestClient,
        auth_headers_admin: Dict[str, str],
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM,
        db_session: Session
    ):
        """Test filtering vaccines by type."""
        # Create vaccines with different types
        vac1 = VacunaORM(
            id_mascota=mascota_instance.id,
            tipo_vacuna="rabia",
            fecha_aplicacion=date.today(),
            lote_vacuna="LOTE123456",
            veterinario=veterinario_usuario.username
        )
        vac2 = VacunaORM(
            id_mascota=mascota_instance.id,
            tipo_vacuna="parvovirus",
            fecha_aplicacion=date.today(),
            lote_vacuna="LOTE789012",
            veterinario=veterinario_usuario.username
        )
        db_session.add_all([vac1, vac2])
        db_session.commit()
        
        response = client.get(
            "/vacunas/?tipo_vacuna=rabia",
            headers=auth_headers_admin
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned vaccines should be rabia type
        for vac in data["data"]:
            assert vac["tipo_vacuna"] == "rabia"
    
    def test_listar_vacunas_paginacion(
        self,
        client: TestClient,
        auth_headers_admin: Dict[str, str],
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM,
        db_session: Session
    ):
        """Test pagination works correctly."""
        # Create multiple vaccines
        for i in range(10):
            vacuna = VacunaORM(
                id_mascota=mascota_instance.id,
                tipo_vacuna="rabia",
                fecha_aplicacion=date.today() - timedelta(days=i),
                lote_vacuna=f"LOTE{i:06d}",
                veterinario=veterinario_usuario.username
            )
            db_session.add(vacuna)
        db_session.commit()
        
        response = client.get(
            "/vacunas/?page=0&page_size=5",
            headers=auth_headers_admin
        )
        
        assert response.status_code == 200
        data = response.json()
        pagination = data["pagination"]
        
        assert len(data["data"]) <= 5
        assert pagination["page"] == 0
        assert pagination["page_size"] == 5


class TestVacunaGet:
    """Tests for getting vaccine by ID."""
    
    def test_obtener_vacuna_propia(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str],
        cliente_usuario: UsuarioORM,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM,
        db_session: Session
    ):
        """Test cliente can get vaccine for their pet."""
        vacuna = VacunaORM(
            id_mascota=mascota_instance.id,
            tipo_vacuna="rabia",
            fecha_aplicacion=date.today(),
            lote_vacuna="LOTE123456",
            veterinario=veterinario_usuario.username
        )
        db_session.add(vacuna)
        db_session.commit()
        
        response = client.get(
            f"/vacunas/{vacuna.id}",
            headers=auth_headers_cliente
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id_vacuna"] == vacuna.id
        assert data["tipo_vacuna"] == "rabia"
    
    def test_obtener_vacuna_como_veterinario(
        self,
        client: TestClient,
        auth_headers_veterinario: Dict[str, str],
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM,
        db_session: Session
    ):
        """Test veterinario can get any vaccine."""
        vacuna = VacunaORM(
            id_mascota=mascota_instance.id,
            tipo_vacuna="parvovirus",
            fecha_aplicacion=date.today(),
            lote_vacuna="LOTE789012",
            veterinario=veterinario_usuario.username
        )
        db_session.add(vacuna)
        db_session.commit()
        
        response = client.get(
            f"/vacunas/{vacuna.id}",
            headers=auth_headers_veterinario
        )
        
        assert response.status_code == 200
    
    def test_obtener_vacuna_inexistente(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str]
    ):
        """Test getting non-existent vaccine returns 404."""
        response = client.get(
            "/vacunas/00000000-0000-0000-0000-000000000000",
            headers=auth_headers_cliente
        )
        
        assert response.status_code == 404
    
    def test_cliente_no_puede_ver_vacuna_otra_mascota(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str],
        auth_headers_admin: Dict[str, str],
        veterinario_usuario: UsuarioORM,
        db_session: Session
    ):
        """Test cliente cannot see vaccine for other user's pet."""
        # Create another mascota for admin
        otra_mascota = MascotaORM(
            id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            nombre="Otro",
            tipo="gato",
            raza="Siamés",
            edad=1,
            peso=4.0,
            propietario=veterinario_usuario.username
        )
        db_session.add(otra_mascota)
        db_session.commit()
        
        vacuna = VacunaORM(
            id_mascota=otra_mascota.id,
            tipo_vacuna="rabia",
            fecha_aplicacion=date.today(),
            lote_vacuna="LOTE123456",
            veterinario=veterinario_usuario.username
        )
        db_session.add(vacuna)
        db_session.commit()
        
        response = client.get(
            f"/vacunas/{vacuna.id}",
            headers=auth_headers_cliente
        )
        
        assert response.status_code == 403


class TestVacunaUpdate:
    """Tests for updating vaccines."""
    
    def test_actualizar_vacuna_proxima_dosis(
        self,
        client: TestClient,
        auth_headers_veterinario: Dict[str, str],
        veterinario_usuario: UsuarioORM,
        mascota_instance: MascotaORM,
        db_session: Session
    ):
        """Test updating vaccine proxima_dosis."""
        vacuna = VacunaORM(
            id_mascota=mascota_instance.id,
            tipo_vacuna="rabia",
            fecha_aplicacion=date.today(),
            lote_vacuna="LOTE123456",
            veterinario=veterinario_usuario.username,
            proxima_dosis=None
        )
        db_session.add(vacuna)
        db_session.commit()
        
        update_data = {
            "proxima_dosis": (date.today() + timedelta(days=365)).isoformat()
        }
        
        response = client.put(
            f"/vacunas/{vacuna.id}",
            json=update_data,
            headers=auth_headers_veterinario
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["proxima_dosis"] is not None
    
    def test_actualizar_vacuna_lote(
        self,
        client: TestClient,
        auth_headers_veterinario: Dict[str, str],
        veterinario_usuario: UsuarioORM,
        mascota_instance: MascotaORM,
        db_session: Session
    ):
        """Test updating vaccine lote."""
        vacuna = VacunaORM(
            id_mascota=mascota_instance.id,
            tipo_vacuna="parvovirus",
            fecha_aplicacion=date.today(),
            lote_vacuna="LOTE123456",
            veterinario=veterinario_usuario.username
        )
        db_session.add(vacuna)
        db_session.commit()
        
        update_data = {
            "lote_vacuna": "LOTE999999"
        }
        
        response = client.put(
            f"/vacunas/{vacuna.id}",
            json=update_data,
            headers=auth_headers_veterinario
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["lote_vacuna"] == "LOTE999999"
    
    def test_actualizar_vacuna_cliente_falla(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str],
        cliente_usuario: UsuarioORM,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM,
        db_session: Session
    ):
        """Test cliente cannot update vaccines."""
        vacuna = VacunaORM(
            id_mascota=mascota_instance.id,
            tipo_vacuna="rabia",
            fecha_aplicacion=date.today(),
            lote_vacuna="LOTE123456",
            veterinario=veterinario_usuario.username
        )
        db_session.add(vacuna)
        db_session.commit()
        
        update_data = {
            "lote_vacuna": "LOTE999999"
        }
        
        response = client.put(
            f"/vacunas/{vacuna.id}",
            json=update_data,
            headers=auth_headers_cliente
        )
        
        assert response.status_code == 403


class TestVacunaDelete:
    """Tests for deleting vaccines (soft delete)."""
    
    def test_eliminar_vacuna_como_admin(
        self,
        client: TestClient,
        auth_headers_admin: Dict[str, str],
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM,
        db_session: Session
    ):
        """Test admin can delete vaccines."""
        vacuna = VacunaORM(
            id_mascota=mascota_instance.id,
            tipo_vacuna="rabia",
            fecha_aplicacion=date.today(),
            lote_vacuna="LOTE123456",
            veterinario=veterinario_usuario.username
        )
        db_session.add(vacuna)
        db_session.commit()
        
        response = client.delete(
            f"/vacunas/{vacuna.id}",
            headers=auth_headers_admin
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_eliminar_vacuna_veterinario_falla(
        self,
        client: TestClient,
        auth_headers_veterinario: Dict[str, str],
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM,
        db_session: Session
    ):
        """Test veterinario cannot delete vaccines."""
        vacuna = VacunaORM(
            id_mascota=mascota_instance.id,
            tipo_vacuna="rabia",
            fecha_aplicacion=date.today(),
            lote_vacuna="LOTE123456",
            veterinario=veterinario_usuario.username
        )
        db_session.add(vacuna)
        db_session.commit()
        
        response = client.delete(
            f"/vacunas/{vacuna.id}",
            headers=auth_headers_veterinario
        )
        
        assert response.status_code == 403
    
    def test_eliminar_vacuna_cliente_falla(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str],
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM,
        db_session: Session
    ):
        """Test cliente cannot delete vaccines."""
        vacuna = VacunaORM(
            id_mascota=mascota_instance.id,
            tipo_vacuna="rabia",
            fecha_aplicacion=date.today(),
            lote_vacuna="LOTE123456",
            veterinario=veterinario_usuario.username
        )
        db_session.add(vacuna)
        db_session.commit()
        
        response = client.delete(
            f"/vacunas/{vacuna.id}",
            headers=auth_headers_cliente
        )
        
        assert response.status_code == 403


class TestVacunaProximasDosis:
    """Tests for getting upcoming vaccine doses."""
    
    def test_obtener_proximas_dosis_cliente(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str],
        cliente_usuario: UsuarioORM,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM,
        db_session: Session
    ):
        """Test cliente can get upcoming doses for their pets."""
        # Create vaccines with upcoming doses
        vacuna = VacunaORM(
            id_mascota=mascota_instance.id,
            tipo_vacuna="rabia",
            fecha_aplicacion=date.today() - timedelta(days=365),
            lote_vacuna="LOTE123456",
            veterinario=veterinario_usuario.username,
            proxima_dosis=date.today() + timedelta(days=30)
        )
        db_session.add(vacuna)
        db_session.commit()
        
        response = client.get(
            "/vacunas/proximas-dosis",
            headers=auth_headers_cliente
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, (dict, list))
    
    def test_obtener_proximas_dosis_con_fecha_limite(
        self,
        client: TestClient,
        auth_headers_admin: Dict[str, str],
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM,
        db_session: Session
    ):
        """Test getting upcoming doses with date limit."""
        vacuna = VacunaORM(
            id_mascota=mascota_instance.id,
            tipo_vacuna="rabia",
            fecha_aplicacion=date.today() - timedelta(days=365),
            lote_vacuna="LOTE123456",
            veterinario=veterinario_usuario.username,
            proxima_dosis=date.today() + timedelta(days=60)
        )
        db_session.add(vacuna)
        db_session.commit()
        
        fecha_limite = (date.today() + timedelta(days=30)).isoformat()
        response = client.get(
            f"/vacunas/proximas-dosis?fecha_limite={fecha_limite}",
            headers=auth_headers_admin
        )
        
        assert response.status_code == 200


class TestVacunaAccessControl:
    """Tests for access control and permissions."""
    
    def test_sin_autenticacion_falla(
        self,
        client: TestClient,
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM,
        db_session: Session
    ):
        """Test requests without authentication fail."""
        vacuna = VacunaORM(
            id_mascota=mascota_instance.id,
            tipo_vacuna="rabia",
            fecha_aplicacion=date.today(),
            lote_vacuna="LOTE123456",
            veterinario=veterinario_usuario.username
        )
        db_session.add(vacuna)
        db_session.commit()
        
        # Try to get without auth
        response = client.get(f"/vacunas/{vacuna.id}")
        assert response.status_code == 401
        
        # Try to list without auth
        response = client.get("/vacunas/")
        assert response.status_code == 401
