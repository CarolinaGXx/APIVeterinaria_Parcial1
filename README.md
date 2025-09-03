# APIVeterinaria_Parcial1

**1. Título del Proyecto**

API Veterinaria – Parcial 1 Aplicaciones y Servicios Web

**2. Descripción General**

API RESTful básica para gestionar una veterinaria con tres entidades principales y operaciones clave:

-Mascotas (perros, gatos, aves): registro y gestión.
-Vacunas: registrar y consultar vacunas aplicadas.
-Citas: agendar, reprogramar y cancelar.
-Facturas: facturar consultas/citas realizadas.

La API expone endpoints CRUD, valida datos con Pydantic, maneja códigos HTTP adecuados y se autodocumenta con Swagger UI y ReDoc de FastAPI. Incluye ejemplos para Postman y un esquema de colaboración en GitHub.

**3. Arquitectura o Diseño**

APIVeterinaria_Parcial1/
├─ database/                  # "Base de datos" en memoria
│ ├─ __init__.py            
│ ├─ db.py                  # Diccionarios y generadores de IDs

├─ models/                  # Modelos Pydantic (request/response)
│ ├─ __init__.py               
│ ├─ citas.py               # CRUD y gestión de citas
│ ├─ facturas.py            # CRUD y facturación de consultas
│ └─ mascotas.py            # CRUD de mascotas + filtros por query
│ └─ vacunas.py             # CRUD y registro de vacunas

│─ routes/                  # Endpoints de la API (FastAPI Routers)
│ ├─ __init__.py             
│ ├─ citas.py               # Endpoints de citas
│ ├─ facturas.py            # Endpoints de facturas
│ └─ mascotas.py            # Endpoints de mascotas
│ └─ vacunas.py             # Endpoints de vacunas

│─ main                     # Punto de entrada principal

├─ requirements.txt         # Dependencias
└─ README.md                # Este documento

**4. Requisitos de Instalación**

Versión de Python:
Python 3.10+ (recomendado 3.13)

Librerías:

FastAPI → Framework web para construir la API.

Uvicorn → Servidor ASGI para ejecutar FastAPI.

Pydantic → Validación y modelado de datos (ya incluido en FastAPI).

Dependencias:

fastapi==0.104.1

uvicorn[standard]==0.24.0

pydantic==2.5.0

python-multipart==0.0.6

**5. Instrucciones de Ejecución**

Ejecución:
python main.py

Probar los endpoints:
Documentación interactiva (Swagger UI)
Abrir en el navegador: http://localhost:8000/docs

**6. Descripción de Endpoints**

Ejemplos de Uso
Crear una mascota
bashPOST /mascotas
{
    "nombre": "Rex",
    "tipo": "perro",
    "raza": "Golden Retriever",
    "edad": 3,
    "peso": 25.5,
    "propietario": "Juan Pérez",
    "telefono_propietario": "3001234567"
}
Agendar una cita
bashPOST /citas
{
    "mascota_id": 1,
    "fecha": "2024-12-01T10:00:00",
    "motivo": "Consulta de rutina",
    "veterinario": "Dr. María García"
}
Registrar vacuna
bashPOST /vacunas
{
    "mascota_id": 1,
    "tipo_vacuna": "rabia",
    "fecha_aplicacion": "2024-11-20",
    "veterinario": "Dr. María García",
    "lote_vacuna": "VAC2024001",
    "proxima_dosis": "2025-11-20"
}

**7. Autores / Integrantes del Grupo**

Dahyana Carolina Gonzalez

Santiago Gonzalez Gonzalez




