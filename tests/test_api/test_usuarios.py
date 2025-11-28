"""
Tests for Usuario API endpoints.

Tests cover:
- User registration (public)
- User authentication
- User CRUD operations
- Role-based access control
- Soft delete/restore
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from typing import Dict, Any

from database.models import UsuarioORM
from tests.conftest import assert_valid_uuid, assert_datetime_format


class TestUsuarioRegistration:
    """Tests for user registration endpoint (POST /usuarios/)."""
    
    def test_crear_usuario_cliente_exitoso(
        self,
        client: TestClient,
        cliente_data: Dict[str, Any]
    ):
        """Test successful cliente registration."""
        response = client.post("/usuarios/", json=cliente_data)
        
        assert response.status_code == 201
        data = response.json()
        
        # Verify response structure
        assert "id_usuario" in data
        assert "username" in data
        assert "role" in data
        assert "fecha_creacion" in data
        
        # Verify data correctness
        assert data["username"] == cliente_data["username"]
        assert data["nombre"] == cliente_data["nombre"]
        assert data["edad"] == cliente_data["edad"]
        assert data["telefono"] == cliente_data["telefono"]
        assert data["role"] == "cliente"  # Always cliente for public registration
        assert data["is_deleted"] is False
        
        # Verify UUID format
        assert assert_valid_uuid(data["id_usuario"])
        assert assert_datetime_format(data["fecha_creacion"])
        
        # Verify password is not returned
        assert "password" not in data
        assert "password_hash" not in data
        assert "password_salt" not in data
    
    def test_crear_usuario_username_duplicado(
        self,
        client: TestClient,
        cliente_usuario: UsuarioORM
    ):
        """Test registration with duplicate username fails."""
        duplicate_data = {
            "username": cliente_usuario.username,
            "nombre": "Otro Usuario",
            "edad": 25,
            "telefono": "3001111111",
            "password": "password123"
        }
        
        response = client.post("/usuarios/", json=duplicate_data)
        
        assert response.status_code == 400
        assert "username" in response.json()["detail"].lower()
    
    def test_crear_usuario_datos_invalidos(self, client: TestClient):
        """Test registration with invalid data fails."""
        # Missing required fields
        response = client.post("/usuarios/", json={"username": "test"})
        assert response.status_code == 422
        
        # Invalid edad (negative)
        invalid_data = {
            "username": "testuser",
            "nombre": "Test User",
            "edad": -5,
            "telefono": "3001234567",
            "password": "password123"
        }
        response = client.post("/usuarios/", json=invalid_data)
        assert response.status_code == 422
        
        # Password too short
        short_password_data = {
            "username": "testuser",
            "nombre": "Test User",
            "edad": 25,
            "telefono": "3001234567",
            "password": "123"
        }
        response = client.post("/usuarios/", json=short_password_data)
        assert response.status_code == 422
    
    def test_crear_usuario_sin_rol_asigna_cliente(
        self,
        client: TestClient
    ):
        """Test that public registration always assigns 'cliente' role."""
        data = {
            "username": "newuser",
            "nombre": "New User",
            "edad": 30,
            "telefono": "3009999999",
            "password": "password123"
        }
        
        response = client.post("/usuarios/", json=data)
        
        assert response.status_code == 201
        assert response.json()["role"] == "cliente"


class TestUsuarioPrivilegedCreation:
    """Tests for privileged user creation endpoint (POST /usuarios/admin/create)."""
    
    def test_crear_veterinario_como_admin(
        self,
        client: TestClient,
        auth_headers_admin: Dict[str, str]
    ):
        """Test admin can create veterinario."""
        vet_data = {
            "username": "newvet",
            "nombre": "Dr. New Veterinario",
            "edad": 35,
            "telefono": "3002222222",
            "password": "password123",
            "role": "veterinario"
        }
        
        response = client.post(
            "/usuarios/admin/create",
            json=vet_data,
            headers=auth_headers_admin
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["role"] == "veterinario"
        assert data["username"] == vet_data["username"]
    
    def test_crear_admin_como_admin(
        self,
        client: TestClient,
        auth_headers_admin: Dict[str, str]
    ):
        """Test admin can create another admin."""
        admin_data = {
            "username": "newadmin",
            "nombre": "New Admin",
            "edad": 40,
            "telefono": "3003333333",
            "password": "password123",
            "role": "admin"
        }
        
        response = client.post(
            "/usuarios/admin/create",
            json=admin_data,
            headers=auth_headers_admin
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["role"] == "admin"
    
    def test_crear_privilegiado_sin_autenticacion_falla(
        self,
        client: TestClient
    ):
        """Test privileged creation fails without auth."""
        vet_data = {
            "username": "newvet",
            "nombre": "Dr. New",
            "edad": 35,
            "telefono": "3002222222",
            "password": "password123",
            "role": "veterinario"
        }
        
        response = client.post("/usuarios/admin/create", json=vet_data)
        
        assert response.status_code == 401
    
    def test_crear_privilegiado_como_cliente_falla(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str]
    ):
        """Test cliente cannot create privileged users."""
        vet_data = {
            "username": "newvet",
            "nombre": "Dr. New",
            "edad": 35,
            "telefono": "3002222222",
            "password": "password123",
            "role": "veterinario"
        }
        
        response = client.post(
            "/usuarios/admin/create",
            json=vet_data,
            headers=auth_headers_cliente
        )
        
        assert response.status_code == 403


class TestUsuarioList:
    """Tests for listing usuarios (GET /usuarios/)."""
    
    def test_listar_usuarios_como_admin(
        self,
        client: TestClient,
        auth_headers_admin: Dict[str, str],
        cliente_usuario: UsuarioORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test admin can list all users."""
        response = client.get("/usuarios/", headers=auth_headers_admin)
        
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
        assert "total_pages" in pagination
        
        # Verify we have users
        assert len(data["data"]) >= 3  # admin, cliente, veterinario
        assert pagination["total_items"] >= 3
    
    def test_listar_usuarios_filtro_por_rol(
        self,
        client: TestClient,
        auth_headers_admin: Dict[str, str],
        cliente_usuario: UsuarioORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test filtering users by role."""
        response = client.get(
            "/usuarios/?role=cliente",
            headers=auth_headers_admin
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all returned users are clientes
        for usuario in data["data"]:
            assert usuario["role"] == "cliente"
    
    def test_listar_usuarios_paginacion(
        self,
        client: TestClient,
        auth_headers_admin: Dict[str, str],
        db_session: Session
    ):
        """Test pagination works correctly."""
        # Create multiple users
        from database.db import hash_password
        for i in range(10):
            salt_hex, hash_hex = hash_password("password123")
            usuario = UsuarioORM(
                username=f"user{i}",
                nombre=f"User {i}",
                edad=25,
                telefono=f"300{i:07d}",
                role="cliente",
                password_salt=salt_hex,
                password_hash=hash_hex,
            )
            db_session.add(usuario)
        db_session.commit()
        
        # Test first page
        response = client.get(
            "/usuarios/?page=0&page_size=5",
            headers=auth_headers_admin
        )
        
        assert response.status_code == 200
        data = response.json()
        pagination = data["pagination"]
        assert len(data["data"]) == 5
        assert pagination["page"] == 0
        assert pagination["page_size"] == 5
    
    def test_listar_usuarios_sin_autenticacion_falla(
        self,
        client: TestClient
    ):
        """Test listing users requires authentication."""
        response = client.get("/usuarios/")
        assert response.status_code == 401
    
    def test_listar_usuarios_como_cliente_falla(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str]
    ):
        """Test cliente cannot list all users."""
        response = client.get("/usuarios/", headers=auth_headers_cliente)
        assert response.status_code == 403


class TestUsuarioGet:
    """Tests for getting individual usuario (GET /usuarios/{id} and /usuarios/me)."""
    
    def test_obtener_mi_usuario(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str],
        cliente_usuario: UsuarioORM
    ):
        """Test getting own user data."""
        response = client.get("/usuarios/me", headers=auth_headers_cliente)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id_usuario"] == cliente_usuario.id
        assert data["username"] == cliente_usuario.username
        assert data["nombre"] == cliente_usuario.nombre
        assert "password" not in data
    
    def test_obtener_usuario_por_id_como_admin(
        self,
        client: TestClient,
        auth_headers_admin: Dict[str, str],
        cliente_usuario: UsuarioORM
    ):
        """Test admin can get any user by ID."""
        response = client.get(
            f"/usuarios/{cliente_usuario.id}",
            headers=auth_headers_admin
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id_usuario"] == cliente_usuario.id
    
    def test_obtener_usuario_inexistente(
        self,
        client: TestClient,
        auth_headers_admin: Dict[str, str]
    ):
        """Test getting non-existent user returns 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(
            f"/usuarios/{fake_id}",
            headers=auth_headers_admin
        )
        
        assert response.status_code == 404
    
    def test_obtener_mi_usuario_sin_autenticacion_falla(
        self,
        client: TestClient
    ):
        """Test getting own user without auth fails."""
        response = client.get("/usuarios/me")
        assert response.status_code == 401


class TestUsuarioUpdate:
    """Tests for updating usuario (PUT /usuarios/me)."""
    
    def test_actualizar_mi_usuario(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str],
        cliente_usuario: UsuarioORM
    ):
        """Test updating own user data."""
        update_data = {
            "nombre": "Nombre Actualizado",
            "edad": 31,
            "telefono": "3009999999"
        }
        
        response = client.put(
            "/usuarios/me",
            json=update_data,
            headers=auth_headers_cliente
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["nombre"] == update_data["nombre"]
        assert data["edad"] == update_data["edad"]
        assert data["telefono"] == update_data["telefono"]
    
    def test_actualizar_username(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str]
    ):
        """Test updating username."""
        update_data = {
            "username": "newusername"
        }
        
        response = client.put(
            "/usuarios/me",
            json=update_data,
            headers=auth_headers_cliente
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "newusername"
    
    def test_actualizar_usuario_parcial(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str],
        cliente_usuario: UsuarioORM
    ):
        """Test partial update (only some fields)."""
        update_data = {
            "telefono": "3001111111"
        }
        
        response = client.put(
            "/usuarios/me",
            json=update_data,
            headers=auth_headers_cliente
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["telefono"] == "3001111111"
        # Other fields should remain unchanged
        assert data["nombre"] == cliente_usuario.nombre
    
    def test_actualizar_usuario_username_duplicado(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str],
        veterinario_usuario: UsuarioORM
    ):
        """Test updating to duplicate username fails."""
        update_data = {
            "username": veterinario_usuario.username
        }
        
        response = client.put(
            "/usuarios/me",
            json=update_data,
            headers=auth_headers_cliente
        )
        
        assert response.status_code == 400


class TestUsuarioDelete:
    """Tests for deleting usuario (DELETE /usuarios/me and /usuarios/{id})."""
    
    def test_eliminar_mi_usuario(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str]
    ):
        """Test soft deleting own user."""
        response = client.delete("/usuarios/me", headers=auth_headers_cliente)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "eliminado" in data["message"].lower()
        assert data["soft_delete"] is True
    
    def test_eliminar_usuario_como_admin(
        self,
        client: TestClient,
        auth_headers_admin: Dict[str, str],
        cliente_usuario: UsuarioORM
    ):
        """Test admin can delete any user."""
        response = client.delete(
            f"/usuarios/{cliente_usuario.id}",
            headers=auth_headers_admin
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_admin_no_puede_eliminarse_a_si_mismo_via_id(
        self,
        client: TestClient,
        auth_headers_admin: Dict[str, str],
        admin_usuario: UsuarioORM
    ):
        """Test admin cannot delete themselves via admin endpoint."""
        response = client.delete(
            f"/usuarios/{admin_usuario.id}",
            headers=auth_headers_admin
        )
        
        assert response.status_code == 400
    
    def test_restaurar_usuario(
        self,
        client: TestClient,
        auth_headers_admin: Dict[str, str],
        db_session: Session
    ):
        """Test restoring a deleted user."""
        # Create and delete a user
        from database.db import hash_password
        salt_hex, hash_hex = hash_password("password123")
        usuario = UsuarioORM(
            username="todelete",
            nombre="To Delete",
            edad=25,
            telefono="3005555555",
            role="cliente",
            password_salt=salt_hex,
            password_hash=hash_hex,
            is_deleted=True
        )
        db_session.add(usuario)
        db_session.commit()
        db_session.refresh(usuario)
        
        # Restore the user
        response = client.post(
            f"/usuarios/{usuario.id}/restore",
            headers=auth_headers_admin
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "restaurado" in data["message"].lower()


class TestUsuarioRoleChange:
    """Tests for changing user roles (PATCH /usuarios/{id}/role)."""
    
    def test_cambiar_rol_como_admin(
        self,
        client: TestClient,
        auth_headers_admin: Dict[str, str],
        cliente_usuario: UsuarioORM
    ):
        """Test admin can change user roles."""
        role_data = {
            "role": "veterinario"
        }
        
        response = client.patch(
            f"/usuarios/{cliente_usuario.id}/role",
            json=role_data,
            headers=auth_headers_admin
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "veterinario"
    
    def test_admin_no_puede_cambiar_su_propio_rol(
        self,
        client: TestClient,
        auth_headers_admin: Dict[str, str],
        admin_usuario: UsuarioORM
    ):
        """Test admin cannot change their own role."""
        role_data = {
            "role": "cliente"
        }
        
        response = client.patch(
            f"/usuarios/{admin_usuario.id}/role",
            json=role_data,
            headers=auth_headers_admin
        )
        
        assert response.status_code == 400
    
    def test_cambiar_rol_sin_permisos_falla(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str],
        veterinario_usuario: UsuarioORM
    ):
        """Test non-admin cannot change roles."""
        role_data = {
            "role": "admin"
        }
        
        response = client.patch(
            f"/usuarios/{veterinario_usuario.id}/role",
            json=role_data,
            headers=auth_headers_cliente
        )
        
        assert response.status_code == 403


class TestVeterinariosList:
    """Tests for listing veterinarios (GET /usuarios/veterinarios)."""
    
    def test_listar_veterinarios(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str],
        veterinario_usuario: UsuarioORM
    ):
        """Test any authenticated user can list veterinarios."""
        response = client.get(
            "/usuarios/veterinarios",
            headers=auth_headers_cliente
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify it's a list
        assert isinstance(data, list)
        
        # Verify structure (simplified for dropdowns)
        if len(data) > 0:
            assert "username" in data[0]
            assert "nombre" in data[0]
    
    def test_listar_veterinarios_solo_retorna_veterinarios(
        self,
        client: TestClient,
        auth_headers_admin: Dict[str, str],
        cliente_usuario: UsuarioORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test veterinarios list only returns veterinarios."""
        response = client.get(
            "/usuarios/veterinarios",
            headers=auth_headers_admin
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned users should be veterinarios (check by username)
        vet_usernames = [v["username"] for v in data]
        assert veterinario_usuario.username in vet_usernames
        assert cliente_usuario.username not in vet_usernames
