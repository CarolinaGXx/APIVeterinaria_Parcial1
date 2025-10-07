from typing import Optional
from datetime import datetime
from uuid import uuid4, UUID
import os
import urllib.parse
import hashlib

try:
    # use dynamic import so static analyzers don't require the package to be installed
    import importlib

    _dotenv = importlib.import_module("dotenv")
    _DOTENV_AVAILABLE = True
except Exception:
    _DOTENV_AVAILABLE = False

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import ORM classes and Base from models.py
from .models import (
    Base,
    UsuarioORM,
    MascotaORM,
    CitaORM,
    VacunaORM,
    FacturaORM,
    RecetaORM,
    RecetaLineaORM,
)

# Load .env for local development if python-dotenv is installed
if _DOTENV_AVAILABLE:
    try:
        _dotenv.load_dotenv()
    except Exception:
        pass

# Engine / session
# If DATABASE_URL env var is set, use it; otherwise fall back to previous SQL Server default
params = urllib.parse.quote_plus(
    "DRIVER={ODBC Driver 17 for SQL Server};SERVER=SANTIAGO\\SQLEXPRESS;DATABASE=APIVeterinaria;Trusted_Connection=yes;"
)
DATABASE_URL = os.getenv("DATABASE_URL") or ("mssql+pyodbc:///?odbc_connect=" + params)

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    """Dependencia de FastAPI que provee una sesión y la cierra al terminar."""
    db = SessionLocal()
    try:
        yield db
    finally:
        try:
            db.close()
        except Exception:
            pass


def create_tables():
    """Crear tablas ORM en la base de datos SQL Server (o la DB configurada)."""
    Base.metadata.create_all(bind=engine)


def generar_numero_factura_uuid(factura_uuid: str) -> str:
    año_actual = datetime.now().year
    short = factura_uuid.replace("-", "")[:8].upper()
    return f"FAC-{año_actual}-{short}"


def uuid_to_str(value) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, UUID):
        return str(value)
    return str(value)


def get_database_url() -> str:
    try:
        return str(engine.url)
    except Exception:
        return DATABASE_URL


def ensure_usuario_exists(user_id: Optional[str]) -> bool:
    """Verifica si un usuario existe en la tabla usuarios (no crea usuarios)."""
    if not user_id:
        return False
    user_id_str = str(user_id)
    db = None
    try:
        db = SessionLocal()
        u = db.get(UsuarioORM, user_id_str)
        return u is not None
    except Exception:
        if db:
            try:
                db.rollback()
            except Exception:
                pass
        raise
    finally:
        if db:
            db.close()


def hash_password(password: str) -> tuple[str, str]:
    """Genera salt y hash (ambos hex) usando PBKDF2-HMAC-SHA256."""
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return salt.hex(), dk.hex()


def verify_password(salt_hex: str, hash_hex: str, password: str) -> bool:
    """Verifica que password coincida con salt+hash almacenados."""
    salt = bytes.fromhex(salt_hex)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return dk.hex() == hash_hex


def set_audit_fields(obj, user_id: Optional[str], creating: bool = True):
    """Helper para setear campos de auditoría en una instancia ORM.

    - obj: instancia ORM
    - user_id: id del usuario responsable (puede ser None)
    - creating: si True setea id_usuario_creacion y fecha_creacion
                si False setea id_usuario_actualizacion y fecha_actualizacion
    """
    now = datetime.utcnow()
    try:
        if creating:
            if hasattr(obj, "id_usuario_creacion"):
                obj.id_usuario_creacion = user_id
            if hasattr(obj, "fecha_creacion") and (
                getattr(obj, "fecha_creacion", None) is None
            ):
                obj.fecha_creacion = now
        # siempre setear actualización
        if hasattr(obj, "id_usuario_actualizacion"):
            obj.id_usuario_actualizacion = user_id
        if hasattr(obj, "fecha_actualizacion"):
            obj.fecha_actualizacion = now
    except Exception:
        # no fallar por auditoría
        pass
