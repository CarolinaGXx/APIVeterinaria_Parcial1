"""módulo de base de datos con manejo mejorado de errores y configuración centralizada."""
from typing import Optional, Generator
from datetime import datetime
from uuid import uuid4, UUID
import hashlib
import logging
import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

# import ORM classes and Base from models.py
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

#import configuration
from config import settings

logger = logging.getLogger(__name__)

#engine / session con configuración centralizada
engine = create_engine(
    settings.database_url,
    echo=settings.debug_mode,
    future=True,
    pool_pre_ping=True,  #verifica conexiones antes de usarlas
    pool_recycle=3600,   #recicla conexiones cada hora
    connect_args={
        "timeout": 30,   #timeout de conexión en segundos
        "connect_timeout": 30  #timeout adicional para pyodbc
    }
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    """dependencia de FastAPI que provee una sesión con manejo robusto de errores.
    
    Yields:
        Session: Sesión de SQLAlchemy
        
    Nota:
        - Hace rollback automático si hay excepciones SQLAlchemy
        - Cierra la sesión de forma segura
        - No captura HTTPException (son errores esperados de negocio)
    """
    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError as e:
        logger.error(f"Error de base de datos en sesión: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def create_tables() -> None:
    """Crear tablas ORM en la base de datos.
    
    Raises:
        SQLAlchemyError: Si hay error al crear las tablas
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Tablas de base de datos creadas/verificadas exitosamente")
    except SQLAlchemyError as e:
        logger.error(f"Error al crear tablas: {e}", exc_info=True)
        raise


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
    """Obtiene la URL de la base de datos (sin credenciales sensibles)."""
    try:
        url = str(engine.url)
        #ocultar credenciales si existen
        if '@' in url:
            parts = url.split('@')
            return f"***@{parts[1]}"
        return url
    except Exception as e:
        logger.warning(f"Error al obtener URL de BD: {e}")
        return "***"


def ensure_usuario_exists(user_id: Optional[str]) -> bool:
    """Verifica si un usuario existe en la tabla usuarios
    
    Args:
        user_id: ID del usuario a verificar
        
    Returns:
        bool: True si el usuario existe, False en caso contrario
        
    Raises:
        SQLAlchemyError: Si hay error de base de datos
    """
    if not user_id:
        return False
    user_id_str = str(user_id)
    db = None
    try:
        db = SessionLocal()
        u = db.get(UsuarioORM, user_id_str)
        return u is not None
    except SQLAlchemyError as e:
        logger.error(f"Error al verificar usuario {user_id_str}: {e}")
        if db:
            try:
                db.rollback()
            except Exception:
                pass
        raise
    finally:
        if db:
            try:
                db.close()
            except Exception:
                pass


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


def set_audit_fields(obj, user_id: Optional[str], creating: bool = True) -> None:
    """helper para setear campos de auditoría en una instancia ORM

    Args:
        obj: instancia ORM a modificar
        user_id: ID del usuario responsable (puede ser None)
        creating: Si True setea campos de creación, si False solo actualización
    """
    from utils.datetime_utils import get_local_now
    now = get_local_now().replace(tzinfo=None)
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
    except Exception as e:
        # no fallar por auditoría, solo registrar
        logger.warning(f"Error al setear campos de auditoría: {e}")


def soft_delete(obj, user_id: Optional[str]) -> None:
    """
    marca un objeto como eliminado (soft delete)
    
    Args:
        obj: instancia ORM a marcar como eliminada
        user_id: ID del usuario que realiza la eliminación
    """
    from utils.datetime_utils import get_local_now
    now = get_local_now().replace(tzinfo=None)
    try:
        if hasattr(obj, "is_deleted"):
            obj.is_deleted = True
        if hasattr(obj, "deleted_at"):
            obj.deleted_at = now
        if hasattr(obj, "deleted_by"):
            obj.deleted_by = user_id
        # También actualizar campos de auditoría
        set_audit_fields(obj, user_id, creating=False)
    except Exception as e:
        logger.warning(f"Error al aplicar soft delete: {e}")


def restore_deleted(obj, user_id: Optional[str]) -> None:
    """restaura un objeto previamente eliminado con soft delete
    
    Args:
        obj: instancia ORM a restaurar
        user_id: ID del usuario que realiza la restauración
    """
    try:
        if hasattr(obj, "is_deleted"):
            obj.is_deleted = False
        if hasattr(obj, "deleted_at"):
            obj.deleted_at = None
        if hasattr(obj, "deleted_by"):
            obj.deleted_by = None
        # Actualizar campos de auditoría
        set_audit_fields(obj, user_id, creating=False)
    except Exception as e:
        logger.warning(f"Error al restaurar objeto: {e}")
