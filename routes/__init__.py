from .mascotas import router as mascotas_router
from .citas import router as citas_router
from .vacunas import router as vacunas_router
from .facturas import router as facturas_router
from .usuarios import router as usuarios_router
from .recetas import router as recetas_router

__all__ = [
    "mascotas_router",
    "citas_router",
    "vacunas_router",
    "facturas_router",
    "usuarios_router",
    "recetas_router",
]
