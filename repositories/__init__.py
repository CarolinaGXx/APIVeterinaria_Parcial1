"""
Capa de repositorio para el acceso a datos.
Este paquete contiene clases de repositorio que gestionan todas las operaciones de la base de datos.
Los repositorios proporcionan una abstracción sobre el ORM y no deben contener
lógica de negocio.

"""

from .base_repository import BaseRepository

__all__ = [
    "BaseRepository",
]
