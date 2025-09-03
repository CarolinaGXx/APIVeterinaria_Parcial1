from fastapi import FastAPI
import uvicorn

# Importar routers
from routes import (
    mascotas_router,
    citas_router,
    vacunas_router,
    facturas_router
)

# Importar routers adicionales para endpoints cruzados
from routes.mascotas import mascotas_vacunas_router
from routes.facturas import mascotas_facturas_router

# Inicializar FastAPI
app = FastAPI(
    title="API Veterinaria",
    description="Sistema de gestión veterinaria para mascotas",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Endpoint raíz
@app.get("/")
async def root():
    return {
        "message": "API Veterinaria - Sistema de Gestión de Mascotas",
        "version": "1.0.0",
        "status": "active",
        "docs": "/docs",
        "redoc": "/redoc"
    }

# Incluir routers principales
app.include_router(mascotas_router)
app.include_router(citas_router)
app.include_router(vacunas_router)
app.include_router(facturas_router)

# Incluir routers para endpoints cruzados
app.include_router(mascotas_vacunas_router)
app.include_router(mascotas_facturas_router)

# Endpoint de health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "APIVeterinaria_Parcial1",
        "version": "1.0.0"
    }

# Ejecutar la aplicación
if __name__ == "__main__":
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info"
    )