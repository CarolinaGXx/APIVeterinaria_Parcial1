from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import uvicorn
import logging

from routes import (
    mascotas_router,
    citas_router,
    vacunas_router,
    facturas_router,
    usuarios_router,
    recetas_router,
)

from routes.facturas import mascotas_facturas_router

from database.db import create_tables

app = FastAPI(
    title="API Veterinaria",
    description="Sistema de gestión veterinaria para mascotas",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

_allowed = os.getenv("CORS_ALLOWED_ORIGINS")
if _allowed:
    ALLOWED_ORIGINS = [o.strip() for o in _allowed.split(",") if o.strip()]
else:
    ALLOWED_ORIGINS = [
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:8000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    try:
        create_tables()
    except Exception as e:
        logger = logging.getLogger("apiveterinaria.startup")
        logging.basicConfig(level=logging.INFO)
        logger.warning("No se pudieron crear tablas en la base de datos: %s", e)

@app.get("/")
async def root():
    return {
        "message": "API Veterinaria - Sistema de Gestión de Mascotas",
        "version": "1.0.0",
        "status": "active",
        "docs": "/docs",
        "redoc": "/redoc"
    }

app.include_router(mascotas_router)
app.include_router(citas_router)
app.include_router(vacunas_router)
app.include_router(facturas_router)
app.include_router(usuarios_router)
app.include_router(recetas_router)

from routes.auth import router as auth_router
app.include_router(auth_router)

app.include_router(mascotas_facturas_router)

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "APIVeterinaria_Parcial1",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info"
    )