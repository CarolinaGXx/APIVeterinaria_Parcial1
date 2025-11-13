from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import logging

from config import settings, configure_logging

from routes import (
    mascotas_router,
    citas_router,
    vacunas_router,
    facturas_router,
    usuarios_router,
    recetas_router,
)
from routes.estadisticas import router as estadisticas_router
from routes.mascota_historial import router as mascota_historial_router
from database.db import create_tables

logger = logging.getLogger(__name__)

# Configurar logging una sola vez al inicio
configure_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Maneja el ciclo de vida de la aplicación."""
    # Startup
    try:
        create_tables()
    except Exception as e:
        logger.warning(f"No se pudieron crear tablas en la base de datos: {e}")
    yield
    # Shutdown

app = FastAPI(
    title=settings.app_name,
    description="Sistema de gestión veterinaria para mascotas. API optimizada para frontend Blazor.",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    debug=settings.debug_mode
)

# Configurar CORS para permitir frontend Blazor
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

@app.get("/")
async def root():
    """Endpoint raíz con información de la API."""
    return {
        "message": f"{settings.app_name} - Sistema de Gestión de Mascotas",
        "version": settings.app_version,
        "status": "active",
        "environment": "production" if settings.is_production else "development",
        "docs": "/docs",
        "redoc": "/redoc"
    }

app.include_router(mascotas_router)
app.include_router(mascota_historial_router)  # Historial clínico completo
app.include_router(citas_router)
app.include_router(vacunas_router)
app.include_router(facturas_router)
app.include_router(usuarios_router)
app.include_router(recetas_router)
app.include_router(estadisticas_router)

from routes.auth import router as auth_router
app.include_router(auth_router)

@app.get("/health")
async def health_check():
    """Health check endpoint con verificación de base de datos."""
    from database.db import engine
    from sqlalchemy import text
    
    db_status = "unknown"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        logger.error(f"Health check: Error de conexión a BD: {e}")
        db_status = "disconnected"
    
    return {
        "status": "healthy" if db_status == "connected" else "unhealthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "database": db_status,
        "environment": "production" if settings.is_production else "development"
    }

if __name__ == "__main__":
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info"
    )