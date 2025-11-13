"""
Funciones de utilidad generales.
"""

from typing import Optional, Any
from enum import Enum as PyEnum
from uuid import UUID


def enum_to_value(value: Any) -> Any:
    """
    Convierte un Enum a su valor, o devuelve el valor sin cambios.
    
    Args:
        value: Valor a convertir
        
    Returns:
        Enum.value si value es un Enum, de lo contrario el valor sin cambios
    """
    if isinstance(value, PyEnum):
        return value.value
    return value


def normalize_stored_enum(value: str) -> str:
    """
    Normaliza los valores de enum almacenados en la base de datos.
    
    La base de datos puede almacenar valores de enum como nombres completos (por ejemplo, "TipoMascota.perro").
    Este ayudante devuelve el nombre corto después del punto ("perro").
    
    Args:
        value: Valor de enum almacenado en la base de datos
        
    Returns:
        Valor normalizado (nombre corto)
    """
    if value is None:
        return value
    if isinstance(value, str) and "." in value:
        return value.split(".", 1)[1]
    return value


def uuid_to_str(value: Any) -> Optional[str]:
    """
    Convierte un UUID a una cadena, manejando None y valores de cadena existentes.
    
    Args:
        value: UUID, cadena o None
        
    Returns:
        Representación de cadena del UUID, o None
    """
    if value is None:
        return None
    if isinstance(value, UUID):
        return str(value)
    return str(value)
