"""
Tests for Authentication endpoints.

Tests cover:
- Login (token generation)
- Token validation
- Token expiration
- Invalid credentials
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from typing import Dict, Any
from datetime import datetime, timedelta

from database.models import UsuarioORM
from auth import create_access_token, decode_token
from config import settings


class TestLogin:
    """Tests for login endpoint (POST /auth/token)."""
    
    def test_login_exitoso(
        self,
        client: TestClient,
        cliente_usuario: UsuarioORM,
        cliente_data: Dict[str, Any]
    ):
        """Test successful login returns valid token."""
        # Prepare form data (OAuth2PasswordRequestForm)
        login_data = {
            "username": cliente_data["username"],
            "password": cliente_data["password"]
        }
        
        response = client.post(
            "/auth/token",
            data=login_data  # Note: data, not json (form data)
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify token response structure
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        
        # Verify token is valid
        token = data["access_token"]
        payload = decode_token(token)
        assert payload["sub"] == cliente_usuario.id
    
    def test_login_credenciales_invalidas(
        self,
        client: TestClient,
        cliente_usuario: UsuarioORM
    ):
        """Test login with invalid password fails."""
        login_data = {
            "username": cliente_usuario.username,
            "password": "wrong_password"
        }
        
        response = client.post("/auth/token", data=login_data)
        
        assert response.status_code == 400
    
    def test_login_usuario_inexistente(
        self,
        client: TestClient
    ):
        """Test login with non-existent user fails."""
        login_data = {
            "username": "nonexistent_user",
            "password": "password123"
        }
        
        response = client.post("/auth/token", data=login_data)
        
        assert response.status_code == 400
    
    def test_login_sin_username(
        self,
        client: TestClient
    ):
        """Test login without username fails."""
        login_data = {
            "password": "password123"
        }
        
        response = client.post("/auth/token", data=login_data)
        
        assert response.status_code == 422
    
    def test_login_sin_password(
        self,
        client: TestClient,
        cliente_usuario: UsuarioORM
    ):
        """Test login without password fails."""
        login_data = {
            "username": cliente_usuario.username
        }
        
        response = client.post("/auth/token", data=login_data)
        
        assert response.status_code == 422


class TestTokenCreation:
    """Tests for token creation and validation."""
    
    def test_create_token_con_datos_validos(
        self,
        cliente_usuario: UsuarioORM
    ):
        """Test creating a token with valid data."""
        token_data = {
            "sub": cliente_usuario.id,
            "username": cliente_usuario.username,
            "role": cliente_usuario.role
        }
        
        token = create_access_token(data=token_data)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_decode_token_valido(
        self,
        cliente_usuario: UsuarioORM
    ):
        """Test decoding a valid token."""
        token_data = {
            "sub": cliente_usuario.id,
            "username": cliente_usuario.username,
            "role": cliente_usuario.role
        }
        
        token = create_access_token(data=token_data)
        payload = decode_token(token)
        
        # Verify payload contents
        assert payload["sub"] == cliente_usuario.id
        assert payload["username"] == cliente_usuario.username
        assert payload["role"] == cliente_usuario.role
        
        # Verify standard claims
        assert "exp" in payload
        assert "iat" in payload
        assert "iss" in payload
        assert "aud" in payload
        assert payload["iss"] == settings.jwt_issuer
        assert payload["aud"] == settings.jwt_audience
    
    def test_token_con_expiracion_custom(
        self,
        cliente_usuario: UsuarioORM
    ):
        """Test creating token with custom expiration."""
        from datetime import timezone
        
        token_data = {"sub": cliente_usuario.id}
        expires_delta = timedelta(minutes=5)
        
        token = create_access_token(data=token_data, expires_delta=expires_delta)
        payload = decode_token(token)
        
        # Verify expiration is approximately 5 minutes from now
        exp_timestamp = payload["exp"]
        now_timestamp = datetime.now(timezone.utc).timestamp()
        time_diff = exp_timestamp - now_timestamp
        
        # Allow 10 second margin for test execution time
        assert 4 * 60 <= time_diff <= 5 * 60 + 10
    
    def test_token_sin_sub_falla(self):
        """Test that creating token without 'sub' raises error."""
        token_data = {
            "username": "testuser"
        }
        
        with pytest.raises(ValueError):
            create_access_token(data=token_data)


class TestTokenValidation:
    """Tests for token validation and authentication."""
    
    def test_endpoint_protegido_sin_token_falla(
        self,
        client: TestClient
    ):
        """Test accessing protected endpoint without token fails."""
        response = client.get("/usuarios/me")
        
        assert response.status_code == 401
    
    def test_endpoint_protegido_con_token_valido(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str]
    ):
        """Test accessing protected endpoint with valid token."""
        response = client.get("/usuarios/me", headers=auth_headers_cliente)
        
        assert response.status_code == 200
    
    def test_token_invalido_falla(
        self,
        client: TestClient
    ):
        """Test invalid token is rejected."""
        invalid_token = "invalid.token.here"
        headers = {"Authorization": f"Bearer {invalid_token}"}
        
        response = client.get("/usuarios/me", headers=headers)
        
        assert response.status_code == 401
    
    def test_token_mal_formateado_falla(
        self,
        client: TestClient
    ):
        """Test malformed authorization header is rejected."""
        # Missing 'Bearer' prefix
        headers = {"Authorization": "some_token"}
        
        response = client.get("/usuarios/me", headers=headers)
        
        assert response.status_code == 401


class TestRoleBasedAccess:
    """Tests for role-based access control with tokens."""
    
    def test_admin_puede_acceder_endpoint_admin(
        self,
        client: TestClient,
        auth_headers_admin: Dict[str, str]
    ):
        """Test admin can access admin-only endpoints."""
        response = client.get("/usuarios/", headers=auth_headers_admin)
        
        assert response.status_code == 200
    
    def test_cliente_no_puede_acceder_endpoint_admin(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str]
    ):
        """Test cliente cannot access admin-only endpoints."""
        response = client.get("/usuarios/", headers=auth_headers_cliente)
        
        assert response.status_code == 403
    
    def test_veterinario_puede_crear_mascota(
        self,
        client: TestClient,
        auth_headers_veterinario: Dict[str, str],
        mascota_data: Dict[str, Any]
    ):
        """Test veterinario can create mascotas."""
        response = client.post(
            "/mascotas/",
            json=mascota_data,
            headers=auth_headers_veterinario
        )
        
        assert response.status_code == 201
    
    def test_cliente_puede_ver_sus_mascotas(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str],
        mascota_instance
    ):
        """Test cliente can view their own mascotas."""
        response = client.get("/mascotas/", headers=auth_headers_cliente)
        
        assert response.status_code == 200


class TestTokenSecurity:
    """Tests for token security features."""
    
    def test_token_contiene_claims_necesarios(
        self,
        cliente_token: str
    ):
        """Test token contains all required claims."""
        payload = decode_token(cliente_token)
        
        required_claims = ["sub", "exp", "iat", "iss", "aud"]
        for claim in required_claims:
            assert claim in payload, f"Missing required claim: {claim}"
    
    def test_token_issuer_correcto(
        self,
        cliente_token: str
    ):
        """Test token has correct issuer."""
        payload = decode_token(cliente_token)
        
        assert payload["iss"] == settings.jwt_issuer
    
    def test_token_audience_correcto(
        self,
        cliente_token: str
    ):
        """Test token has correct audience."""
        payload = decode_token(cliente_token)
        
        assert payload["aud"] == settings.jwt_audience
    
    def test_token_diferentes_usuarios_diferentes(
        self,
        cliente_token: str,
        veterinario_token: str
    ):
        """Test tokens for different users are different."""
        assert cliente_token != veterinario_token
        
        cliente_payload = decode_token(cliente_token)
        vet_payload = decode_token(veterinario_token)
        
        assert cliente_payload["sub"] != vet_payload["sub"]


class TestPasswordSecurity:
    """Tests for password hashing and verification."""
    
    def test_password_no_se_almacena_en_texto_plano(
        self,
        db_session: Session,
        cliente_usuario: UsuarioORM,
        cliente_data: Dict[str, Any]
    ):
        """Test password is not stored in plain text."""
        # Verify password hash is not the same as password
        assert cliente_usuario.password_hash != cliente_data["password"]
        
        # Verify salt exists
        assert cliente_usuario.password_salt is not None
        assert len(cliente_usuario.password_salt) > 0
    
    def test_mismo_password_diferentes_hashes(
        self,
        db_session: Session
    ):
        """Test same password generates different hashes (due to salt)."""
        from database.db import hash_password
        
        password = "test_password_123"
        
        salt1, hash1 = hash_password(password)
        salt2, hash2 = hash_password(password)
        
        # Different salts should produce different hashes
        assert salt1 != salt2
        assert hash1 != hash2
