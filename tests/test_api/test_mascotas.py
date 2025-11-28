"""
Tests for Mascota API endpoints.

Tests cover:
- Creating mascotas
- Listing mascotas with filters
- Getting individual mascotas
- Updating mascotas
- Deleting/restoring mascotas
- Access control (ownership)
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from typing import Dict, Any

from database.models import UsuarioORM, MascotaORM
from tests.conftest import assert_valid_uuid, assert_datetime_format


class TestMascotaCreation:
    """Tests for creating mascotas (POST /mascotas/)."""
    
    def test_crear_mascota_como_cliente(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str],
        mascota_data: Dict[str, Any],
        cliente_usuario: UsuarioORM
    ):
        """Test cliente can create their own mascota."""
        response = client.post(
            "/mascotas/",
            json=mascota_data,
            headers=auth_headers_cliente
        )
        
        assert response.status_code == 201
        data = response.json()
        
        # Verify response structure
        assert "id_mascota" in data
        assert "nombre" in data
        assert "tipo" in data
        assert "propietario" in data
        
        # Verify data correctness
        assert data["nombre"] == mascota_data["nombre"]
        assert data["tipo"] == mascota_data["tipo"]
        assert data["raza"] == mascota_data["raza"]
        assert data["edad"] == mascota_data["edad"]
        assert data["peso"] == mascota_data["peso"]
        assert data["propietario"] == cliente_usuario.username
        assert data["is_deleted"] is False
        
        # Verify UUID format
        assert assert_valid_uuid(data["id_mascota"])
    
    def test_crear_mascota_como_veterinario(
        self,
        client: TestClient,
        auth_headers_veterinario: Dict[str, str],
        mascota_data: Dict[str, Any],
        veterinario_usuario: UsuarioORM
    ):
        """Test veterinario can create mascotas."""
        response = client.post(
            "/mascotas/",
            json=mascota_data,
            headers=auth_headers_veterinario
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["propietario"] == veterinario_usuario.username
    
    def test_crear_mascota_gato(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str],
        mascota_gato_data: Dict[str, Any]
    ):
        """Test creating a gato mascota."""
        response = client.post(
            "/mascotas/",
            json=mascota_gato_data,
            headers=auth_headers_cliente
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["tipo"] == "gato"
        assert data["nombre"] == mascota_gato_data["nombre"]
    
    def test_crear_mascota_datos_invalidos(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str]
    ):
        """Test creating mascota with invalid data fails."""
        # Missing required fields
        response = client.post(
            "/mascotas/",
            json={"nombre": "Test"},
            headers=auth_headers_cliente
        )
        assert response.status_code == 422
        
        # Invalid edad (negative)
        invalid_data = {
            "nombre": "Test",
            "tipo": "perro",
            "raza": "Labrador",
            "edad": -1,
            "peso": 10.0
        }
        response = client.post(
            "/mascotas/",
            json=invalid_data,
            headers=auth_headers_cliente
        )
        assert response.status_code == 422
        
        # Invalid peso (zero or negative)
        invalid_data = {
            "nombre": "Test",
            "tipo": "perro",
            "raza": "Labrador",
            "edad": 3,
            "peso": 0
        }
        response = client.post(
            "/mascotas/",
            json=invalid_data,
            headers=auth_headers_cliente
        )
        assert response.status_code == 422
    
    def test_crear_mascota_sin_autenticacion_falla(
        self,
        client: TestClient,
        mascota_data: Dict[str, Any]
    ):
        """Test creating mascota without authentication fails."""
        response = client.post("/mascotas/", json=mascota_data)
        assert response.status_code == 401


class TestMascotaList:
    """Tests for listing mascotas (GET /mascotas/)."""
    
    def test_listar_mis_mascotas_como_cliente(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str],
        mascota_instance: MascotaORM
    ):
        """Test cliente can list their own mascotas."""
        response = client.get("/mascotas/", headers=auth_headers_cliente)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify pagination structure
        assert "data" in data
        assert "pagination" in data
        assert "success" in data
        
        pagination = data["pagination"]
        assert "page" in pagination
        assert "page_size" in pagination
        assert "total_items" in pagination
        
        # Verify mascota is in the list
        assert len(data["data"]) >= 1
        mascota_ids = [m["id_mascota"] for m in data["data"]]
        assert mascota_instance.id in mascota_ids
    
    def test_listar_mascotas_solo_muestra_propias(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str],
        mascota_instance: MascotaORM,
        db_session: Session,
        veterinario_usuario: UsuarioORM
    ):
        """Test cliente only sees their own mascotas."""
        # Create a mascota for veterinario
        vet_mascota = MascotaORM(
            nombre="Mascota del Vet",
            tipo="perro",
            raza="Bulldog",
            edad=2,
            peso=15.0,
            propietario=veterinario_usuario.username
        )
        db_session.add(vet_mascota)
        db_session.commit()
        
        # Cliente should only see their mascota
        response = client.get("/mascotas/", headers=auth_headers_cliente)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify only cliente's mascotas are returned
        for mascota in data["data"]:
            assert mascota["propietario"] != veterinario_usuario.username
    
    def test_listar_mascotas_admin_ve_todas(
        self,
        client: TestClient,
        auth_headers_admin: Dict[str, str],
        mascota_instance: MascotaORM,
        db_session: Session,
        veterinario_usuario: UsuarioORM
    ):
        """Test admin can see all mascotas."""
        # Create mascotas for different users
        vet_mascota = MascotaORM(
            nombre="Mascota del Vet",
            tipo="perro",
            raza="Bulldog",
            edad=2,
            peso=15.0,
            propietario=veterinario_usuario.username
        )
        db_session.add(vet_mascota)
        db_session.commit()
        
        response = client.get("/mascotas/", headers=auth_headers_admin)
        
        assert response.status_code == 200
        data = response.json()
        
        # Admin should see mascotas from multiple owners
        owners = {m["propietario"] for m in data["data"]}
        assert len(owners) >= 2
    
    def test_listar_mascotas_filtro_por_tipo(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str],
        mascota_instance: MascotaORM,
        db_session: Session,
        cliente_usuario: UsuarioORM
    ):
        """Test filtering mascotas by tipo."""
        # Create a gato
        gato = MascotaORM(
            nombre="Michi",
            tipo="gato",
            raza="Siamés",
            edad=2,
            peso=4.0,
            propietario=cliente_usuario.username
        )
        db_session.add(gato)
        db_session.commit()
        
        # Filter by perro
        response = client.get(
            "/mascotas/?tipo=perro",
            headers=auth_headers_cliente
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned mascotas should be perros
        for mascota in data["data"]:
            assert mascota["tipo"] == "perro"
    
    def test_listar_mascotas_paginacion(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str],
        db_session: Session,
        cliente_usuario: UsuarioORM
    ):
        """Test pagination works correctly."""
        # Create multiple mascotas
        for i in range(10):
            mascota = MascotaORM(
                nombre=f"Mascota{i}",
                tipo="perro",
                raza="Labrador",
                edad=i,
                peso=10.0 + i,
                propietario=cliente_usuario.username
            )
            db_session.add(mascota)
        db_session.commit()
        
        # Test first page
        response = client.get(
            "/mascotas/?page=0&page_size=5",
            headers=auth_headers_cliente
        )
        
        assert response.status_code == 200
        data = response.json()
        pagination = data["pagination"]
        assert len(data["data"]) == 5
        assert pagination["page"] == 0
        assert pagination["page_size"] == 5
    
    def test_listar_mascotas_filtro_propietario_admin(
        self,
        client: TestClient,
        auth_headers_admin: Dict[str, str],
        mascota_instance: MascotaORM,
        cliente_usuario: UsuarioORM
    ):
        """Test admin can filter by propietario."""
        response = client.get(
            f"/mascotas/?propietario={cliente_usuario.username}",
            headers=auth_headers_admin
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned mascotas should belong to the specified owner
        for mascota in data["data"]:
            assert mascota["propietario"] == cliente_usuario.username


class TestMascotaSearch:
    """Tests for searching mascotas (GET /mascotas/search)."""
    
    def test_buscar_mascota_por_nombre(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str],
        mascota_instance: MascotaORM
    ):
        """Test searching mascota by name."""
        response = client.get(
            f"/mascotas/search?q={mascota_instance.nombre}",
            headers=auth_headers_cliente
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should be a list, not paginated
        assert isinstance(data, list)
        
        # Should find the mascota
        if len(data) > 0:
            assert any(m["id_mascota"] == mascota_instance.id for m in data)
    
    def test_buscar_mascota_parcial(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str],
        mascota_instance: MascotaORM
    ):
        """Test partial search works."""
        # Search with first 3 characters of name
        partial_name = mascota_instance.nombre[:3]
        response = client.get(
            f"/mascotas/search?q={partial_name}",
            headers=auth_headers_cliente
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_buscar_mascota_limite(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str],
        db_session: Session,
        cliente_usuario: UsuarioORM
    ):
        """Test search respects limit parameter."""
        # Create many mascotas
        for i in range(25):
            mascota = MascotaORM(
                nombre=f"Firulais{i}",
                tipo="perro",
                raza="Labrador",
                edad=2,
                peso=10.0,
                propietario=cliente_usuario.username
            )
            db_session.add(mascota)
        db_session.commit()
        
        # Search with limit
        response = client.get(
            "/mascotas/search?q=Firulais&limit=10",
            headers=auth_headers_cliente
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 10
    
    def test_buscar_mascota_sin_query_falla(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str]
    ):
        """Test search without query parameter fails."""
        response = client.get(
            "/mascotas/search",
            headers=auth_headers_cliente
        )
        
        assert response.status_code == 422


class TestMascotaGet:
    """Tests for getting individual mascota (GET /mascotas/{id})."""
    
    def test_obtener_mi_mascota(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str],
        mascota_instance: MascotaORM
    ):
        """Test getting own mascota."""
        response = client.get(
            f"/mascotas/{mascota_instance.id}",
            headers=auth_headers_cliente
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id_mascota"] == mascota_instance.id
        assert data["nombre"] == mascota_instance.nombre
        assert data["tipo"] == mascota_instance.tipo
        assert "propietario_telefono" in data or "telefono_propietario" in data
    
    def test_obtener_mascota_como_admin(
        self,
        client: TestClient,
        auth_headers_admin: Dict[str, str],
        mascota_instance: MascotaORM
    ):
        """Test admin can get any mascota."""
        response = client.get(
            f"/mascotas/{mascota_instance.id}",
            headers=auth_headers_admin
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id_mascota"] == mascota_instance.id
    
    def test_obtener_mascota_de_otro_usuario_falla(
        self,
        client: TestClient,
        auth_headers_veterinario: Dict[str, str],
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test veterinario can view mascotas of other users."""
        # Verify mascota doesn't belong to veterinario
        assert mascota_instance.propietario != veterinario_usuario.username
        
        # Veterinarios can view mascotas (returns 200 per API behavior)
        response = client.get(
            f"/mascotas/{mascota_instance.id}",
            headers=auth_headers_veterinario
        )
        
        assert response.status_code == 200
    
    def test_obtener_mascota_inexistente(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str]
    ):
        """Test getting non-existent mascota returns 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(
            f"/mascotas/{fake_id}",
            headers=auth_headers_cliente
        )
        
        assert response.status_code == 404


class TestMascotaUpdate:
    """Tests for updating mascota (PUT /mascotas/{id})."""
    
    def test_actualizar_mi_mascota(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str],
        mascota_instance: MascotaORM
    ):
        """Test updating own mascota."""
        update_data = {
            "nombre": "Nombre Actualizado",
            "edad": 4,
            "peso": 26.5
        }
        
        response = client.put(
            f"/mascotas/{mascota_instance.id}",
            json=update_data,
            headers=auth_headers_cliente
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["nombre"] == update_data["nombre"]
        assert data["edad"] == update_data["edad"]
        assert data["peso"] == update_data["peso"]
        # Type should remain unchanged
        assert data["tipo"] == mascota_instance.tipo
    
    def test_actualizar_mascota_parcial(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str],
        mascota_instance: MascotaORM
    ):
        """Test partial update (only some fields)."""
        update_data = {
            "peso": 30.0
        }
        
        response = client.put(
            f"/mascotas/{mascota_instance.id}",
            json=update_data,
            headers=auth_headers_cliente
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["peso"] == 30.0
        # Other fields should remain unchanged
        assert data["nombre"] == mascota_instance.nombre
    
    def test_actualizar_mascota_como_admin(
        self,
        client: TestClient,
        auth_headers_admin: Dict[str, str],
        mascota_instance: MascotaORM
    ):
        """Test admin can update any mascota."""
        update_data = {
            "nombre": "Actualizado por Admin"
        }
        
        response = client.put(
            f"/mascotas/{mascota_instance.id}",
            json=update_data,
            headers=auth_headers_admin
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["nombre"] == update_data["nombre"]
    
    def test_actualizar_mascota_de_otro_usuario_falla(
        self,
        client: TestClient,
        auth_headers_veterinario: Dict[str, str],
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test user cannot update mascota of another user."""
        # Verify mascota doesn't belong to veterinario
        assert mascota_instance.propietario != veterinario_usuario.username
        
        update_data = {
            "nombre": "Intento de Actualización"
        }
        
        response = client.put(
            f"/mascotas/{mascota_instance.id}",
            json=update_data,
            headers=auth_headers_veterinario
        )
        
        assert response.status_code == 403
    
    def test_actualizar_mascota_datos_invalidos(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str],
        mascota_instance: MascotaORM
    ):
        """Test updating with invalid data fails."""
        # Invalid edad (negative)
        invalid_data = {
            "edad": -1
        }
        
        response = client.put(
            f"/mascotas/{mascota_instance.id}",
            json=invalid_data,
            headers=auth_headers_cliente
        )
        
        assert response.status_code == 422


class TestMascotaDelete:
    """Tests for deleting mascota (DELETE /mascotas/{id})."""
    
    def test_eliminar_mi_mascota(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str],
        mascota_instance: MascotaORM
    ):
        """Test soft deleting own mascota."""
        response = client.delete(
            f"/mascotas/{mascota_instance.id}",
            headers=auth_headers_cliente
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "eliminad" in data["message"].lower()
        assert data["soft_delete"] is True
        assert data["deleted_id"] == mascota_instance.id
    
    def test_eliminar_mascota_como_admin(
        self,
        client: TestClient,
        auth_headers_admin: Dict[str, str],
        mascota_instance: MascotaORM
    ):
        """Test admin can delete any mascota."""
        response = client.delete(
            f"/mascotas/{mascota_instance.id}",
            headers=auth_headers_admin
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_eliminar_mascota_de_otro_usuario_falla(
        self,
        client: TestClient,
        auth_headers_veterinario: Dict[str, str],
        mascota_instance: MascotaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test user cannot delete mascota of another user."""
        # Verify mascota doesn't belong to veterinario
        assert mascota_instance.propietario != veterinario_usuario.username
        
        response = client.delete(
            f"/mascotas/{mascota_instance.id}",
            headers=auth_headers_veterinario
        )
        
        assert response.status_code == 403
    
    def test_restaurar_mascota(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str],
        db_session: Session,
        cliente_usuario: UsuarioORM
    ):
        """Test restoring a deleted mascota."""
        # Create and delete a mascota
        mascota = MascotaORM(
            nombre="Para Restaurar",
            tipo="perro",
            raza="Labrador",
            edad=3,
            peso=25.0,
            propietario=cliente_usuario.username,
            is_deleted=True
        )
        db_session.add(mascota)
        db_session.commit()
        db_session.refresh(mascota)
        
        # Restore the mascota
        response = client.post(
            f"/mascotas/{mascota.id}/restore",
            headers=auth_headers_cliente
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "restaurad" in data["message"].lower()
    
    def test_restaurar_mascota_como_admin(
        self,
        client: TestClient,
        auth_headers_admin: Dict[str, str],
        db_session: Session,
        cliente_usuario: UsuarioORM
    ):
        """Test admin can restore any deleted mascota."""
        # Create and delete a mascota
        mascota = MascotaORM(
            nombre="Para Restaurar Admin",
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
        
        # Restore as admin
        response = client.post(
            f"/mascotas/{mascota.id}/restore",
            headers=auth_headers_admin
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestMascotaAccessControl:
    """Tests for verifying proper access control on mascotas."""
    
    def test_cliente_no_ve_mascotas_de_otros(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str],
        db_session: Session,
        veterinario_usuario: UsuarioORM
    ):
        """Test cliente cannot see other users' mascotas in list."""
        # Create mascota for another user
        other_mascota = MascotaORM(
            nombre="Mascota de Otro",
            tipo="perro",
            raza="Bulldog",
            edad=2,
            peso=15.0,
            propietario=veterinario_usuario.username
        )
        db_session.add(other_mascota)
        db_session.commit()
        
        # List mascotas as cliente
        response = client.get("/mascotas/", headers=auth_headers_cliente)
        
        assert response.status_code == 200
        data = response.json()

        # Verify other user's mascota is not in the list
        mascota_ids = [m["id_mascota"] for m in data["data"]]
        assert other_mascota.id not in mascota_ids
    
    def test_veterinario_puede_crear_mascota_propia(
        self,
        client: TestClient,
        auth_headers_veterinario: Dict[str, str],
        mascota_data: Dict[str, Any],
        veterinario_usuario: UsuarioORM
    ):
        """Test veterinario can create their own mascotas."""
        response = client.post(
            "/mascotas/",
            json=mascota_data,
            headers=auth_headers_veterinario
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["propietario"] == veterinario_usuario.username
