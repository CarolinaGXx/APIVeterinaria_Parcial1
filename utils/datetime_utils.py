"""
Utilidades para manejo de fechas y zonas horarias.

Este módulo proporciona funciones para trabajar con fechas
en la zona horaria configurada de la aplicación.
"""
from datetime import datetime
from zoneinfo import ZoneInfo
from config import settings


def get_local_now() -> datetime:
    """
    Obtiene la fecha y hora actual en la zona horaria local configurada.
    
    Returns:
        datetime: Fecha y hora actual con zona horaria.
    """
    tz = ZoneInfo(settings.timezone)
    return datetime.now(tz)


def get_local_timezone() -> ZoneInfo:
    """
    Obtiene la zona horaria configurada.
    
    Returns:
        ZoneInfo: Zona horaria de la aplicación.
    """
    return ZoneInfo(settings.timezone)


def to_local_time(dt: datetime) -> datetime:
    """
    Convierte una fecha UTC a la zona horaria local.
    
    Args:
        dt: Datetime en UTC o naive.
    
    Returns:
        datetime: Fecha en zona horaria local.
    """
    if dt is None:
        return None
    
    tz = get_local_timezone()
    
    # Si el datetime es naive (sin zona horaria), asumimos que es UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    
    # Convertir a zona horaria local
    return dt.astimezone(tz)


def from_local_to_utc(dt: datetime) -> datetime:
    """
    Convierte una fecha de zona horaria local a UTC.
    
    Args:
        dt: Datetime en zona horaria local.
    
    Returns:
        datetime: Fecha en UTC.
    """
    if dt is None:
        return None
    
    # Si es naive, asumimos que está en hora local
    if dt.tzinfo is None:
        tz = get_local_timezone()
        dt = dt.replace(tzinfo=tz)
    
    # Convertir a UTC
    return dt.astimezone(ZoneInfo("UTC"))
