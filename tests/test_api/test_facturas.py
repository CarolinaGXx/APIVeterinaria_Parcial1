"""
Tests for Factura API endpoints.

Tests cover:
- Creating facturas (with cita or vacuna)
- Listing facturas with filters and pagination
- Getting individual facturas
- Updating facturas
- Marking facturas as paid
- Canceling (anulando) facturas
- Deleting facturas (soft delete)
- Access control and role-based restrictions
"""

import pytest
from starlette.testclient import TestClient
from datetime import date, timedelta, datetime
from typing import Dict

from database.models import MascotaORM, UsuarioORM, CitaORM, VacunaORM


class TestFacturaCreation:
    """Tests for creating facturas."""
    
    def test_crear_factura_desde_cita_como_veterinario(
        self,
        client: TestClient,
        auth_headers_veterinario: Dict[str, str],
        cita_instance: CitaORM,
        veterinario_usuario: UsuarioORM
    ):
        """Test creating factura from cita as veterinario."""
        factura_data = {
            "id_cita": str(cita_instance.id),
            "tipo_servicio": "consulta_general",
            "descripcion": "Consulta de rutina",
            "valor_servicio": 100.0,
            "iva": 19.0,
            "descuento": 0.0
        }
        
        response = client.post(
            "/facturas/",
            json=factura_data,
            headers=auth_headers_veterinario
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["numero_factura"] is not None
        assert data["id_cita"] == str(cita_instance.id)
        assert data["tipo_servicio"] == "consulta_general"
        assert data["estado"] == "pendiente"
        assert data["total"] == 119.0  # 100 + 19
    
    def test_crear_factura_desde_vacuna_como_admin(
        self,
        client: TestClient,
        auth_headers_admin: Dict[str, str],
        vacuna_instance: VacunaORM
    ):
        """Test creating factura from vacuna as admin."""
        factura_data = {
            "id_vacuna": str(vacuna_instance.id),
            "tipo_servicio": "vacunacion",
            "descripcion": "Vacunación rabia",
            "valor_servicio": 50.0,
            "iva": 9.5,
            "descuento": 5.0
        }
        
        response = client.post(
            "/facturas/",
            json=factura_data,
            headers=auth_headers_admin
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["id_vacuna"] == str(vacuna_instance.id)
        assert data["tipo_servicio"] == "vacunacion"
        # Total: 50 + 9.5 - 5 = 54.5
        assert data["total"] == 54.5
    
    def test_crear_factura_cliente_rechazado(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str],
        cita_instance: CitaORM
    ):
        """Test that cliente cannot create facturas."""
        factura_data = {
            "id_cita": str(cita_instance.id),
            "tipo_servicio": "consulta_general",
            "descripcion": "Consulta",
            "valor_servicio": 100.0,
            "iva": 19.0,
            "descuento": 0.0
        }
        
        response = client.post(
            "/facturas/",
            json=factura_data,
            headers=auth_headers_cliente
        )
        
        assert response.status_code == 403
    
    def test_crear_factura_sin_cita_ni_vacuna_falla(
        self,
        client: TestClient,
        auth_headers_veterinario: Dict[str, str]
    ):
        """Test creating factura without cita or vacuna fails."""
        factura_data = {
            "tipo_servicio": "consulta_general",
            "descripcion": "Consulta",
            "valor_servicio": 100.0,
            "iva": 19.0,
            "descuento": 0.0
        }
        
        response = client.post(
            "/facturas/",
            json=factura_data,
            headers=auth_headers_veterinario
        )
        
        assert response.status_code == 422
    
    def test_crear_factura_con_cita_y_vacuna_falla(
        self,
        client: TestClient,
        auth_headers_veterinario: Dict[str, str],
        cita_instance: CitaORM,
        vacuna_instance: VacunaORM
    ):
        """Test creating factura with both cita and vacuna fails."""
        factura_data = {
            "id_cita": str(cita_instance.id),
            "id_vacuna": str(vacuna_instance.id),
            "tipo_servicio": "consulta_general",
            "descripcion": "Consulta",
            "valor_servicio": 100.0,
            "iva": 19.0,
            "descuento": 0.0
        }
        
        response = client.post(
            "/facturas/",
            json=factura_data,
            headers=auth_headers_veterinario
        )
        
        assert response.status_code == 422
    
    def test_crear_factura_valor_servicio_invalido(
        self,
        client: TestClient,
        auth_headers_veterinario: Dict[str, str],
        cita_instance: CitaORM
    ):
        """Test creating factura with invalid valor_servicio."""
        factura_data = {
            "id_cita": str(cita_instance.id),
            "tipo_servicio": "consulta_general",
            "descripcion": "Consulta",
            "valor_servicio": -50.0,  # Invalid: negative
            "iva": 19.0,
            "descuento": 0.0
        }
        
        response = client.post(
            "/facturas/",
            json=factura_data,
            headers=auth_headers_veterinario
        )
        
        assert response.status_code == 422
    
    def test_crear_factura_descuento_negativo_falla(
        self,
        client: TestClient,
        auth_headers_veterinario: Dict[str, str],
        cita_instance: CitaORM
    ):
        """Test creating factura with negative descuento fails."""
        factura_data = {
            "id_cita": str(cita_instance.id),
            "tipo_servicio": "consulta_general",
            "descripcion": "Consulta",
            "valor_servicio": 100.0,
            "iva": 19.0,
            "descuento": -10.0  # Invalid: negative
        }
        
        response = client.post(
            "/facturas/",
            json=factura_data,
            headers=auth_headers_veterinario
        )
        
        assert response.status_code == 422
    
    def test_crear_factura_sin_autenticacion_falla(
        self,
        client: TestClient,
        cita_instance: CitaORM
    ):
        """Test creating factura without authentication fails."""
        factura_data = {
            "id_cita": str(cita_instance.id),
            "tipo_servicio": "consulta_general",
            "descripcion": "Consulta",
            "valor_servicio": 100.0,
            "iva": 19.0,
            "descuento": 0.0
        }
        
        response = client.post("/facturas/", json=factura_data)
        
        assert response.status_code == 401


class TestFacturaList:
    """Tests for listing facturas."""
    
    def test_listar_facturas_cliente_solo_propias(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str],
        db_session,
        cliente_usuario: UsuarioORM,
        veterinario_usuario: UsuarioORM,
        mascota_cliente: MascotaORM,
        mascota_otro_cliente: MascotaORM
    ):
        """Test that cliente only sees facturas for their own pets."""
        # Create citas for both mascotas
        cita1 = CitaORM(
            id_mascota=mascota_cliente.id,
            fecha=datetime.fromisoformat((date.today() + timedelta(days=1)).isoformat() + "T10:00:00"),
            motivo="Control",
            veterinario=veterinario_usuario.username
        )
        cita2 = CitaORM(
            id_mascota=mascota_otro_cliente.id,
            fecha=datetime.fromisoformat((date.today() + timedelta(days=2)).isoformat() + "T11:00:00"),
            motivo="Control",
            veterinario=veterinario_usuario.username
        )
        db_session.add(cita1)
        db_session.add(cita2)
        db_session.commit()
        
        # Create facturas via API
        from repositories.factura_repository import FacturaRepository
        factura_repo = FacturaRepository(db_session)
        from database.models import FacturaORM
        from database.db import generar_numero_factura_uuid
        from uuid import uuid4
        
        factura_id1 = str(uuid4())
        factura1 = FacturaORM(
            id=factura_id1,
            numero_factura=generar_numero_factura_uuid(factura_id1),
            id_cita=str(cita1.id),
            id_mascota=mascota_cliente.id,
            fecha_factura=date.today(),
            tipo_servicio="consulta_general",
            descripcion="Consulta",
            veterinario=veterinario_usuario.username,
            valor_servicio=100.0,
            iva=19.0,
            descuento=0.0,
            total=119.0
        )
        
        factura_id2 = str(uuid4())
        factura2 = FacturaORM(
            id=factura_id2,
            numero_factura=generar_numero_factura_uuid(factura_id2),
            id_cita=str(cita2.id),
            id_mascota=mascota_otro_cliente.id,
            fecha_factura=date.today(),
            tipo_servicio="consulta_general",
            descripcion="Consulta",
            veterinario=veterinario_usuario.username,
            valor_servicio=100.0,
            iva=19.0,
            descuento=0.0,
            total=119.0
        )
        
        factura_repo.create(factura1, user_id=veterinario_usuario.id)
        factura_repo.create(factura2, user_id=veterinario_usuario.id)
        db_session.commit()
        
        response = client.get("/facturas/", headers=auth_headers_cliente)
        
        assert response.status_code == 200
        response_data = response.json()
        facturas = response_data["data"]
        
        # Cliente should only see factura1
        assert len(facturas) == 1
        assert facturas[0]["id_mascota"] == str(mascota_cliente.id)
    
    def test_listar_facturas_veterinario_ve_todas(
        self,
        client: TestClient,
        auth_headers_veterinario: Dict[str, str],
        db_session,
        veterinario_usuario: UsuarioORM,
        mascota_cliente: MascotaORM
    ):
        """Test that veterinario sees all facturas."""
        # Create multiple facturas
        from repositories.factura_repository import FacturaRepository
        from database.models import FacturaORM
        from database.db import generar_numero_factura_uuid
        from uuid import uuid4
        
        factura_repo = FacturaRepository(db_session)
        
        for i in range(3):
            factura_id = str(uuid4())
            factura = FacturaORM(
                id=factura_id,
                numero_factura=generar_numero_factura_uuid(factura_id),
                id_mascota=mascota_cliente.id,
                fecha_factura=date.today(),
                tipo_servicio="consulta_general",
                descripcion=f"Consulta {i}",
                veterinario=veterinario_usuario.username,
                valor_servicio=100.0,
                iva=19.0,
                descuento=0.0,
                total=119.0
            )
            factura_repo.create(factura, user_id=veterinario_usuario.id)
        db_session.commit()
        
        response = client.get("/facturas/", headers=auth_headers_veterinario)
        
        assert response.status_code == 200
        data = response.json()
        facturas = data["data"]
        
        assert len(facturas) >= 3
    
    def test_listar_facturas_admin_ve_todas(
        self,
        client: TestClient,
        auth_headers_admin: Dict[str, str],
        db_session,
        veterinario_usuario: UsuarioORM,
        mascota_cliente: MascotaORM
    ):
        """Test that admin sees all facturas."""
        response = client.get("/facturas/", headers=auth_headers_admin)
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
    
    def test_listar_facturas_filtro_por_estado(
        self,
        client: TestClient,
        auth_headers_admin: Dict[str, str],
        db_session,
        veterinario_usuario: UsuarioORM,
        mascota_cliente: MascotaORM
    ):
        """Test filtering facturas by estado (admin can filter)."""
        from repositories.factura_repository import FacturaRepository
        from database.models import FacturaORM
        from database.db import generar_numero_factura_uuid
        from uuid import uuid4
        
        factura_repo = FacturaRepository(db_session)
        
        # Create facturas with different states
        factura_id1 = str(uuid4())
        factura1 = FacturaORM(
            id=factura_id1,
            numero_factura=generar_numero_factura_uuid(factura_id1),
            id_mascota=mascota_cliente.id,
            fecha_factura=date.today(),
            tipo_servicio="consulta_general",
            descripcion="Consulta",
            veterinario=veterinario_usuario.username,
            valor_servicio=100.0,
            iva=19.0,
            descuento=0.0,
            total=119.0,
            estado="pendiente"
        )
        
        factura_id2 = str(uuid4())
        factura2 = FacturaORM(
            id=factura_id2,
            numero_factura=generar_numero_factura_uuid(factura_id2),
            id_mascota=mascota_cliente.id,
            fecha_factura=date.today(),
            tipo_servicio="consulta_general",
            descripcion="Consulta",
            veterinario=veterinario_usuario.username,
            valor_servicio=100.0,
            iva=19.0,
            descuento=0.0,
            total=119.0,
            estado="pagada"
        )
        
        factura_repo.create(factura1, user_id=veterinario_usuario.id)
        factura_repo.create(factura2, user_id=veterinario_usuario.id)
        db_session.commit()
        
        response = client.get(
            "/facturas/?estado=pagada",
            headers=auth_headers_admin
        )

        assert response.status_code == 200
        response_data = response.json()
        facturas = response_data["data"]

        # Should only return pagada facturas
        assert len(facturas) >= 1, f"Expected at least 1 factura, got {len(facturas)}"
        assert all(f["estado"] == "pagada" for f in facturas)
    
    def test_listar_facturas_paginacion(
        self,
        client: TestClient,
        auth_headers_veterinario: Dict[str, str],
        db_session,
        veterinario_usuario: UsuarioORM,
        mascota_cliente: MascotaORM
    ):
        """Test pagination of facturas."""
        from repositories.factura_repository import FacturaRepository
        from database.models import FacturaORM
        from database.db import generar_numero_factura_uuid
        from uuid import uuid4
        
        factura_repo = FacturaRepository(db_session)
        
        # Create 10 facturas
        for i in range(10):
            factura_id = str(uuid4())
            factura = FacturaORM(
                id=factura_id,
                numero_factura=generar_numero_factura_uuid(factura_id),
                id_mascota=mascota_cliente.id,
                fecha_factura=date.today(),
                tipo_servicio="consulta_general",
                descripcion=f"Consulta {i}",
                veterinario=veterinario_usuario.username,
                valor_servicio=100.0,
                iva=19.0,
                descuento=0.0,
                total=119.0
            )
            factura_repo.create(factura, user_id=veterinario_usuario.id)
        db_session.commit()
        
        response = client.get(
            "/facturas/?page=0&page_size=5",
            headers=auth_headers_veterinario
        )
        
        assert response.status_code == 200
        data = response.json()
        facturas = data["data"]
        pagination = data["pagination"]
        
        assert len(facturas) == 5
        assert pagination["page"] == 0
        assert pagination["page_size"] == 5


class TestFacturaGet:
    """Tests for getting individual facturas."""
    
    def test_obtener_factura_propia(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str],
        db_session,
        cliente_usuario: UsuarioORM,
        veterinario_usuario: UsuarioORM,
        mascota_cliente: MascotaORM
    ):
        """Test cliente getting factura for own pet."""
        from repositories.factura_repository import FacturaRepository
        from database.models import FacturaORM
        from database.db import generar_numero_factura_uuid
        from uuid import uuid4
        
        factura_repo = FacturaRepository(db_session)
        
        factura_id = str(uuid4())
        factura = FacturaORM(
            id=factura_id,
            numero_factura=generar_numero_factura_uuid(factura_id),
            id_mascota=mascota_cliente.id,
            fecha_factura=date.today(),
            tipo_servicio="consulta_general",
            descripcion="Consulta",
            veterinario=veterinario_usuario.username,
            valor_servicio=100.0,
            iva=19.0,
            descuento=0.0,
            total=119.0
        )
        factura_repo.create(factura, user_id=veterinario_usuario.id)
        db_session.commit()
        
        response = client.get(f"/facturas/{factura_id}", headers=auth_headers_cliente)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id_factura"] == factura_id
    
    def test_obtener_factura_como_veterinario(
        self,
        client: TestClient,
        auth_headers_veterinario: Dict[str, str],
        db_session,
        veterinario_usuario: UsuarioORM,
        mascota_cliente: MascotaORM
    ):
        """Test veterinario can get any factura."""
        from repositories.factura_repository import FacturaRepository
        from database.models import FacturaORM
        from database.db import generar_numero_factura_uuid
        from uuid import uuid4
        
        factura_repo = FacturaRepository(db_session)
        
        factura_id = str(uuid4())
        factura = FacturaORM(
            id=factura_id,
            numero_factura=generar_numero_factura_uuid(factura_id),
            id_mascota=mascota_cliente.id,
            fecha_factura=date.today(),
            tipo_servicio="consulta_general",
            descripcion="Consulta",
            veterinario=veterinario_usuario.username,
            valor_servicio=100.0,
            iva=19.0,
            descuento=0.0,
            total=119.0
        )
        factura_repo.create(factura, user_id=veterinario_usuario.id)
        db_session.commit()
        
        response = client.get(f"/facturas/{factura_id}", headers=auth_headers_veterinario)
        
        assert response.status_code == 200
    
    def test_obtener_factura_inexistente(
        self,
        client: TestClient,
        auth_headers_veterinario: Dict[str, str]
    ):
        """Test getting non-existent factura returns 404."""
        response = client.get(
            "/facturas/00000000-0000-0000-0000-000000000000",
            headers=auth_headers_veterinario
        )
        
        assert response.status_code == 404
    
    def test_cliente_no_puede_ver_factura_otra_mascota(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str],
        db_session,
        veterinario_usuario: UsuarioORM,
        mascota_otro_cliente: MascotaORM
    ):
        """Test cliente cannot see factura for another's pet."""
        from repositories.factura_repository import FacturaRepository
        from database.models import FacturaORM
        from database.db import generar_numero_factura_uuid
        from uuid import uuid4
        
        factura_repo = FacturaRepository(db_session)
        
        factura_id = str(uuid4())
        factura = FacturaORM(
            id=factura_id,
            numero_factura=generar_numero_factura_uuid(factura_id),
            id_mascota=mascota_otro_cliente.id,
            fecha_factura=date.today(),
            tipo_servicio="consulta_general",
            descripcion="Consulta",
            veterinario=veterinario_usuario.username,
            valor_servicio=100.0,
            iva=19.0,
            descuento=0.0,
            total=119.0
        )
        factura_repo.create(factura, user_id=veterinario_usuario.id)
        db_session.commit()
        
        response = client.get(f"/facturas/{factura_id}", headers=auth_headers_cliente)
        
        assert response.status_code == 403


class TestFacturaUpdate:
    """Tests for updating facturas."""
    
    def test_actualizar_factura_descripcion(
        self,
        client: TestClient,
        auth_headers_veterinario: Dict[str, str],
        db_session,
        veterinario_usuario: UsuarioORM,
        mascota_cliente: MascotaORM
    ):
        """Test updating factura description."""
        from repositories.factura_repository import FacturaRepository
        from database.models import FacturaORM
        from database.db import generar_numero_factura_uuid
        from uuid import uuid4
        
        factura_repo = FacturaRepository(db_session)
        
        factura_id = str(uuid4())
        factura = FacturaORM(
            id=factura_id,
            numero_factura=generar_numero_factura_uuid(factura_id),
            id_mascota=mascota_cliente.id,
            fecha_factura=date.today(),
            tipo_servicio="consulta_general",
            descripcion="Consulta",
            veterinario=veterinario_usuario.username,
            valor_servicio=100.0,
            iva=19.0,
            descuento=0.0,
            total=119.0
        )
        factura_repo.create(factura, user_id=veterinario_usuario.id)
        db_session.commit()
        
        update_data = {"descripcion": "Consulta actualizada"}
        
        response = client.put(
            f"/facturas/{factura_id}",
            json=update_data,
            headers=auth_headers_veterinario
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["descripcion"] == "Consulta actualizada"
    
    def test_actualizar_factura_estado(
        self,
        client: TestClient,
        auth_headers_veterinario: Dict[str, str],
        db_session,
        veterinario_usuario: UsuarioORM,
        mascota_cliente: MascotaORM
    ):
        """Test updating factura estado."""
        from repositories.factura_repository import FacturaRepository
        from database.models import FacturaORM
        from database.db import generar_numero_factura_uuid
        from uuid import uuid4
        
        factura_repo = FacturaRepository(db_session)
        
        factura_id = str(uuid4())
        factura = FacturaORM(
            id=factura_id,
            numero_factura=generar_numero_factura_uuid(factura_id),
            id_mascota=mascota_cliente.id,
            fecha_factura=date.today(),
            tipo_servicio="consulta_general",
            descripcion="Consulta",
            veterinario=veterinario_usuario.username,
            valor_servicio=100.0,
            iva=19.0,
            descuento=0.0,
            total=119.0,
            estado="pendiente"
        )
        factura_repo.create(factura, user_id=veterinario_usuario.id)
        db_session.commit()
        
        update_data = {"estado": "pagada"}
        
        response = client.put(
            f"/facturas/{factura_id}",
            json=update_data,
            headers=auth_headers_veterinario
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["estado"] == "pagada"
    
    def test_actualizar_factura_cliente_falla(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str],
        db_session,
        veterinario_usuario: UsuarioORM,
        mascota_cliente: MascotaORM
    ):
        """Test cliente cannot update facturas."""
        from repositories.factura_repository import FacturaRepository
        from database.models import FacturaORM
        from database.db import generar_numero_factura_uuid
        from uuid import uuid4
        
        factura_repo = FacturaRepository(db_session)
        
        factura_id = str(uuid4())
        factura = FacturaORM(
            id=factura_id,
            numero_factura=generar_numero_factura_uuid(factura_id),
            id_mascota=mascota_cliente.id,
            fecha_factura=date.today(),
            tipo_servicio="consulta_general",
            descripcion="Consulta",
            veterinario=veterinario_usuario.username,
            valor_servicio=100.0,
            iva=19.0,
            descuento=0.0,
            total=119.0
        )
        factura_repo.create(factura, user_id=veterinario_usuario.id)
        db_session.commit()
        
        update_data = {"descripcion": "Updated"}
        
        response = client.put(
            f"/facturas/{factura_id}",
            json=update_data,
            headers=auth_headers_cliente
        )
        
        assert response.status_code == 403


class TestFacturaMarkAsPaid:
    """Tests for marking facturas as paid."""
    
    def test_marcar_como_pagada_cliente(
        self,
        client: TestClient,
        auth_headers_cliente: Dict[str, str],
        db_session,
        cliente_usuario: UsuarioORM,
        veterinario_usuario: UsuarioORM,
        mascota_cliente: MascotaORM
    ):
        """Test cliente can mark own factura as paid."""
        from repositories.factura_repository import FacturaRepository
        from database.models import FacturaORM
        from database.db import generar_numero_factura_uuid
        from uuid import uuid4
        
        factura_repo = FacturaRepository(db_session)
        
        factura_id = str(uuid4())
        factura = FacturaORM(
            id=factura_id,
            numero_factura=generar_numero_factura_uuid(factura_id),
            id_mascota=mascota_cliente.id,
            fecha_factura=date.today(),
            tipo_servicio="consulta_general",
            descripcion="Consulta",
            veterinario=veterinario_usuario.username,
            valor_servicio=100.0,
            iva=19.0,
            descuento=0.0,
            total=119.0,
            estado="pendiente"
        )
        factura_repo.create(factura, user_id=veterinario_usuario.id)
        db_session.commit()
        
        response = client.post(
            f"/facturas/{factura_id}/pagar",
            headers=auth_headers_cliente
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["estado"] == "pagada"
    
    def test_marcar_como_pagada_veterinario(
        self,
        client: TestClient,
        auth_headers_veterinario: Dict[str, str],
        db_session,
        veterinario_usuario: UsuarioORM,
        mascota_cliente: MascotaORM
    ):
        """Test veterinario can mark factura as paid."""
        from repositories.factura_repository import FacturaRepository
        from database.models import FacturaORM
        from database.db import generar_numero_factura_uuid
        from uuid import uuid4
        
        factura_repo = FacturaRepository(db_session)
        
        factura_id = str(uuid4())
        factura = FacturaORM(
            id=factura_id,
            numero_factura=generar_numero_factura_uuid(factura_id),
            id_mascota=mascota_cliente.id,
            fecha_factura=date.today(),
            tipo_servicio="consulta_general",
            descripcion="Consulta",
            veterinario=veterinario_usuario.username,
            valor_servicio=100.0,
            iva=19.0,
            descuento=0.0,
            total=119.0,
            estado="pendiente"
        )
        factura_repo.create(factura, user_id=veterinario_usuario.id)
        db_session.commit()
        
        response = client.post(
            f"/facturas/{factura_id}/pagar",
            headers=auth_headers_veterinario
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["estado"] == "pagada"


class TestFacturaAnular:
    """Tests for canceling (anulando) facturas."""
    
    def test_anular_factura_como_admin(
        self,
        client: TestClient,
        auth_headers_admin: Dict[str, str],
        db_session,
        admin_usuario: UsuarioORM,
        veterinario_usuario: UsuarioORM,
        mascota_cliente: MascotaORM
    ):
        """Test admin can anular facturas."""
        from repositories.factura_repository import FacturaRepository
        from database.models import FacturaORM
        from database.db import generar_numero_factura_uuid
        from uuid import uuid4
        
        factura_repo = FacturaRepository(db_session)
        
        factura_id = str(uuid4())
        factura = FacturaORM(
            id=factura_id,
            numero_factura=generar_numero_factura_uuid(factura_id),
            id_mascota=mascota_cliente.id,
            fecha_factura=date.today(),
            tipo_servicio="consulta_general",
            descripcion="Consulta",
            veterinario=veterinario_usuario.username,
            valor_servicio=100.0,
            iva=19.0,
            descuento=0.0,
            total=119.0,
            estado="pendiente"
        )
        factura_repo.create(factura, user_id=veterinario_usuario.id)
        db_session.commit()
        
        response = client.post(
            f"/facturas/{factura_id}/anular",
            headers=auth_headers_admin
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_anular_factura_veterinario_falla(
        self,
        client: TestClient,
        auth_headers_veterinario: Dict[str, str],
        db_session,
        veterinario_usuario: UsuarioORM,
        mascota_cliente: MascotaORM
    ):
        """Test veterinario cannot anular facturas."""
        from repositories.factura_repository import FacturaRepository
        from database.models import FacturaORM
        from database.db import generar_numero_factura_uuid
        from uuid import uuid4
        
        factura_repo = FacturaRepository(db_session)
        
        factura_id = str(uuid4())
        factura = FacturaORM(
            id=factura_id,
            numero_factura=generar_numero_factura_uuid(factura_id),
            id_mascota=mascota_cliente.id,
            fecha_factura=date.today(),
            tipo_servicio="consulta_general",
            descripcion="Consulta",
            veterinario=veterinario_usuario.username,
            valor_servicio=100.0,
            iva=19.0,
            descuento=0.0,
            total=119.0
        )
        factura_repo.create(factura, user_id=veterinario_usuario.id)
        db_session.commit()
        
        response = client.post(
            f"/facturas/{factura_id}/anular",
            headers=auth_headers_veterinario
        )
        
        assert response.status_code == 403


class TestFacturaDelete:
    """Tests for deleting facturas (soft delete)."""
    
    def test_eliminar_factura_como_admin(
        self,
        client: TestClient,
        auth_headers_admin: Dict[str, str],
        db_session,
        admin_usuario: UsuarioORM,
        veterinario_usuario: UsuarioORM,
        mascota_cliente: MascotaORM
    ):
        """Test admin can delete facturas."""
        from repositories.factura_repository import FacturaRepository
        from database.models import FacturaORM
        from database.db import generar_numero_factura_uuid
        from uuid import uuid4
        
        factura_repo = FacturaRepository(db_session)
        
        factura_id = str(uuid4())
        factura = FacturaORM(
            id=factura_id,
            numero_factura=generar_numero_factura_uuid(factura_id),
            id_mascota=mascota_cliente.id,
            fecha_factura=date.today(),
            tipo_servicio="consulta_general",
            descripcion="Consulta",
            veterinario=veterinario_usuario.username,
            valor_servicio=100.0,
            iva=19.0,
            descuento=0.0,
            total=119.0
        )
        factura_repo.create(factura, user_id=veterinario_usuario.id)
        db_session.commit()
        
        response = client.delete(
            f"/facturas/{factura_id}",
            headers=auth_headers_admin
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_eliminar_factura_veterinario_falla(
        self,
        client: TestClient,
        auth_headers_veterinario: Dict[str, str],
        db_session,
        veterinario_usuario: UsuarioORM,
        mascota_cliente: MascotaORM
    ):
        """Test veterinario cannot delete facturas."""
        from repositories.factura_repository import FacturaRepository
        from database.models import FacturaORM
        from database.db import generar_numero_factura_uuid
        from uuid import uuid4
        
        factura_repo = FacturaRepository(db_session)
        
        factura_id = str(uuid4())
        factura = FacturaORM(
            id=factura_id,
            numero_factura=generar_numero_factura_uuid(factura_id),
            id_mascota=mascota_cliente.id,
            fecha_factura=date.today(),
            tipo_servicio="consulta_general",
            descripcion="Consulta",
            veterinario=veterinario_usuario.username,
            valor_servicio=100.0,
            iva=19.0,
            descuento=0.0,
            total=119.0
        )
        factura_repo.create(factura, user_id=veterinario_usuario.id)
        db_session.commit()
        
        response = client.delete(
            f"/facturas/{factura_id}",
            headers=auth_headers_veterinario
        )
        
        assert response.status_code == 403


class TestFacturaAccessControl:
    """Tests for access control."""
    
    def test_sin_autenticacion_falla(
        self,
        client: TestClient
    ):
        """Test endpoints without authentication fail."""
        response = client.get("/facturas/")
        
        assert response.status_code == 401
