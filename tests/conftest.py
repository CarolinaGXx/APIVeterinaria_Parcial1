"""
Configuración de fixtures para pytest.

Este módulo contiene fixtures reutilizables para todos los tests.
"""

import pytest
import os
from typing import Generator, Dict, Any
from datetime import datetime, date, timedelta
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# Configurar para usar base de datos en memoria para tests
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from main import app
from database.db import get_db, Base, hash_password
from database.models import UsuarioORM, MascotaORM
from auth import create_access_token
from config import settings


# ==================== Database Fixtures ====================

@pytest.fixture(scope="function")
def db_engine():
    """Create an in-memory SQLite database engine for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Enable foreign keys for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine) -> Generator[Session, None, None]:
    """Create a new database session for a test."""
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=db_engine
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Create a test client with database session override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


# ==================== User Fixtures ====================

@pytest.fixture
def cliente_data() -> Dict[str, Any]:
    """Sample cliente data for testing."""
    return {
        "username": "testcliente",
        "nombre": "Cliente Test",
        "edad": 30,
        "telefono": "3001234567",
        "password": "password123"
    }


@pytest.fixture
def veterinario_data() -> Dict[str, Any]:
    """Sample veterinario data for testing."""
    return {
        "username": "testvet",
        "nombre": "Dr. Veterinario Test",
        "edad": 35,
        "telefono": "3007654321",
        "password": "password123"
    }


@pytest.fixture
def admin_data() -> Dict[str, Any]:
    """Sample admin data for testing."""
    return {
        "username": "testadmin",
        "nombre": "Admin Test",
        "edad": 40,
        "telefono": "3009876543",
        "password": "password123"
    }


@pytest.fixture
def cliente_usuario(db_session: Session, cliente_data: Dict[str, Any]) -> UsuarioORM:
    """Create a cliente user in the database."""
    salt_hex, hash_hex = hash_password(cliente_data["password"])
    usuario = UsuarioORM(
        id="12345678-1234-5678-1234-567812345678",
        username=cliente_data["username"],
        nombre=cliente_data["nombre"],
        edad=cliente_data["edad"],
        telefono=cliente_data["telefono"],
        role="cliente",
        password_salt=salt_hex,
        password_hash=hash_hex,
    )
    db_session.add(usuario)
    db_session.commit()
    db_session.refresh(usuario)
    return usuario


@pytest.fixture
def veterinario_usuario(db_session: Session, veterinario_data: Dict[str, Any]) -> UsuarioORM:
    """Create a veterinario user in the database."""
    salt_hex, hash_hex = hash_password(veterinario_data["password"])
    usuario = UsuarioORM(
        id="87654321-4321-8765-4321-876543218765",
        username=veterinario_data["username"],
        nombre=veterinario_data["nombre"],
        edad=veterinario_data["edad"],
        telefono=veterinario_data["telefono"],
        role="veterinario",
        password_salt=salt_hex,
        password_hash=hash_hex,
    )
    db_session.add(usuario)
    db_session.commit()
    db_session.refresh(usuario)
    return usuario


@pytest.fixture
def admin_usuario(db_session: Session, admin_data: Dict[str, Any]) -> UsuarioORM:
    """Create an admin user in the database."""
    salt_hex, hash_hex = hash_password(admin_data["password"])
    usuario = UsuarioORM(
        id="ffffffff-ffff-ffff-ffff-ffffffffffff",
        username=admin_data["username"],
        nombre=admin_data["nombre"],
        edad=admin_data["edad"],
        telefono=admin_data["telefono"],
        role="admin",
        password_salt=salt_hex,
        password_hash=hash_hex,
    )
    db_session.add(usuario)
    db_session.commit()
    db_session.refresh(usuario)
    return usuario


# ==================== Auth Token Fixtures ====================

@pytest.fixture
def cliente_token(cliente_usuario: UsuarioORM) -> str:
    """Generate a valid JWT token for cliente user."""
    return create_access_token(data={"sub": cliente_usuario.id})


@pytest.fixture
def veterinario_token(veterinario_usuario: UsuarioORM) -> str:
    """Generate a valid JWT token for veterinario user."""
    return create_access_token(data={"sub": veterinario_usuario.id})


@pytest.fixture
def admin_token(admin_usuario: UsuarioORM) -> str:
    """Generate a valid JWT token for admin user."""
    return create_access_token(data={"sub": admin_usuario.id})


@pytest.fixture
def auth_headers_cliente(cliente_token: str) -> Dict[str, str]:
    """Generate authentication headers for cliente."""
    return {"Authorization": f"Bearer {cliente_token}"}


@pytest.fixture
def auth_headers_veterinario(veterinario_token: str) -> Dict[str, str]:
    """Generate authentication headers for veterinario."""
    return {"Authorization": f"Bearer {veterinario_token}"}


@pytest.fixture
def auth_headers_admin(admin_token: str) -> Dict[str, str]:
    """Generate authentication headers for admin."""
    return {"Authorization": f"Bearer {admin_token}"}


# ==================== Mascota Fixtures ====================

@pytest.fixture
def mascota_data() -> Dict[str, Any]:
    """Sample mascota data for testing."""
    return {
        "nombre": "Firulais",
        "tipo": "perro",
        "raza": "Labrador",
        "edad": 3,
        "peso": 25.5
    }


@pytest.fixture
def mascota_gato_data() -> Dict[str, Any]:
    """Sample gato mascota data for testing."""
    return {
        "nombre": "Michi",
        "tipo": "gato",
        "raza": "Siamés",
        "edad": 2,
        "peso": 4.5
    }


@pytest.fixture
def mascota_instance(
    db_session: Session,
    cliente_usuario: UsuarioORM,
    mascota_data: Dict[str, Any]
) -> MascotaORM:
    """Create a mascota in the database."""
    mascota = MascotaORM(
        id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        nombre=mascota_data["nombre"],
        tipo=mascota_data["tipo"],
        raza=mascota_data["raza"],
        edad=mascota_data["edad"],
        peso=mascota_data["peso"],
        propietario=cliente_usuario.username,
    )
    db_session.add(mascota)
    db_session.commit()
    db_session.refresh(mascota)
    return mascota


@pytest.fixture
def mascota_cliente(
    db_session: Session,
    cliente_usuario: UsuarioORM,
    mascota_data: Dict[str, Any]
) -> MascotaORM:
    """Create a mascota for the cliente user (same as mascota_instance)."""
    mascota = MascotaORM(
        id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        nombre=mascota_data["nombre"],
        tipo=mascota_data["tipo"],
        raza=mascota_data["raza"],
        edad=mascota_data["edad"],
        peso=mascota_data["peso"],
        propietario=cliente_usuario.username,
    )
    db_session.add(mascota)
    db_session.commit()
    db_session.refresh(mascota)
    return mascota


@pytest.fixture
def mascota_otro_cliente(
    db_session: Session,
    cliente_usuario: UsuarioORM,
    veterinario_usuario: UsuarioORM
) -> MascotaORM:
    """Create a mascota for another cliente (used to test access control)."""
    # Create another cliente user first
    from uuid import uuid4
    otro_cliente_id = str(uuid4())
    salt_hex, hash_hex = hash_password("password456")
    otro_cliente = UsuarioORM(
        id=otro_cliente_id,
        username="otroclient",
        nombre="Otro Cliente",
        edad=35,
        telefono="3009876543",
        role="cliente",
        password_salt=salt_hex,
        password_hash=hash_hex,
    )
    db_session.add(otro_cliente)
    db_session.commit()
    
    mascota = MascotaORM(
        id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        nombre="Otro Perro",
        tipo="perro",
        raza="Pastor Alemán",
        edad=4,
        peso=30.0,
        propietario=otro_cliente.username,
    )
    db_session.add(mascota)
    db_session.commit()
    db_session.refresh(mascota)
    return mascota


# ==================== Cita Fixtures ====================

@pytest.fixture
def cita_instance(
    db_session: Session,
    mascota_instance: MascotaORM,
    veterinario_usuario: UsuarioORM
):
    """Create a cita in the database."""
    from database.models import CitaORM
    
    cita = CitaORM(
        id="cccccccc-cccc-cccc-cccc-cccccccccccc",
        id_mascota=mascota_instance.id,
        fecha=datetime.fromisoformat((date.today() + timedelta(days=1)).isoformat() + "T10:00:00"),
        motivo="Control de rutina",
        veterinario=veterinario_usuario.username,
    )
    db_session.add(cita)
    db_session.commit()
    db_session.refresh(cita)
    return cita


# ==================== Vacuna Fixtures ====================

@pytest.fixture
def vacuna_instance(
    db_session: Session,
    mascota_instance: MascotaORM,
    veterinario_usuario: UsuarioORM
):
    """Create a vacuna in the database."""
    from database.models import VacunaORM
    
    vacuna = VacunaORM(
        id="dddddddd-dddd-dddd-dddd-dddddddddddd",
        id_mascota=mascota_instance.id,
        tipo_vacuna="rabia",
        fecha_aplicacion=date.today(),
        lote_vacuna="LOTE123456",
        veterinario=veterinario_usuario.username,
    )
    db_session.add(vacuna)
    db_session.commit()
    db_session.refresh(vacuna)
    return vacuna


# ==================== Utility Functions ====================

def assert_valid_uuid(uuid_string: str) -> bool:
    """Assert that a string is a valid UUID."""
    from uuid import UUID
    try:
        UUID(str(uuid_string))
        return True
    except (ValueError, AttributeError):
        return False


def assert_datetime_format(dt_string: str) -> bool:
    """Assert that a string is a valid datetime in ISO format."""
    try:
        datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
        return True
    except (ValueError, AttributeError):
        return False
