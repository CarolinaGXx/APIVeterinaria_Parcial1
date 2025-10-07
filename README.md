# APIVeterinaria_Parcial1

**1. Título del Proyecto**

API Veterinaria – Parcial 1 Aplicaciones y Servicios Web

Este README está actualizado para el estado actual del repositorio (FastAPI + SQLAlchemy + Alembic).

**2. Descripción General**

Esta API RESTful permite gestionar de forma digital los procesos más comunes en una veterinaria: registrar mascotas (perros, gatos y aves), aplicar y consultar vacunas, agendar o cancelar citas y generar facturas de las consultas realizadas. Integra validación de datos con Pydantic, manejo adecuado de códigos HTTP y documentación automática con FastAPI (Swagger UI y ReDoc).

Es útil porque centraliza toda la información en un solo sistema, lo que mejora la organización y reduce la pérdida de datos. Responde al problema frecuente de muchas veterinarias pequeñas y medianas que todavía llevan sus registros de forma manual o dispersa, dificultando el seguimiento clínico y administrativo de cada mascota. Con esta API se estandarizan los procesos y se facilita la consulta de información de manera rápida y confiable.

**3. Arquitectura o Diseño**
```
APIVeterinaria_Parcial1/
├─ database/                # "Base de datos" en memoria

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
```

**4. Requisitos de Instalación**

Versión de Python: 3.10+ (se recomienda 3.11 o 3.12).

Librerías:

FastAPI → Framework web para construir la API

Uvicorn → Servidor ASGI para ejecutar FastAPI

Pydantic → Validación y modelado de datos (ya incluido en FastAPI)

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
```
1. Mascotas (/mascotas)
Gestión de las mascotas registradas en la veterinaria.

GET /mascotas → Lista todas las mascotas.
GET http://localhost:8000/mascotas

GET /mascotas/{id} → Obtiene una mascota por su ID.
GET http://localhost:8000/mascotas/1

POST /mascotas → Crea una nueva mascota.
Body (JSON):

{
  "nombre": "Firulais",
  "especie": "perro",
  "edad": 3
}

PUT /mascotas/{id} → Actualiza datos de una mascota.
PUT http://localhost:8000/mascotas/1

DELETE /mascotas/{id} → Elimina una mascota.
DELETE http://localhost:8000/docs/mascotas/1

Query Params disponibles:
/mascotas?especie=perro → Filtra mascotas por especie.

2. Vacunas (/vacunas)
Registro y consulta de vacunas aplicadas a las mascotas.

GET /vacunas → Lista todas las vacunas registradas.
POST /vacunas → Registra una nueva vacuna.
Body (JSON):

{
  "mascota_id": 1,
  "nombre_vacuna": "Rabia",
  "fecha": "2025-09-01"
}

3. Citas (/citas)
Gestión de citas veterinarias.

GET /citas → Lista todas las citas.
POST /citas → Agenda una nueva cita.
Body (JSON):

{
  "mascota_id": 1,
  "fecha": "2025-09-10",
  "motivo": "Consulta general"
}

4. Facturas (/facturas)
Facturación de consultas veterinarias.

GET /facturas → Lista todas las facturas emitidas.
POST /facturas → Genera una factura por una consulta.
Body (JSON):

{
  "mascota_id": 1,
  "monto": 50.00,
  "descripcion": "Consulta veterinaria general"
}

5. Health Check (/health)

Verifica que el servicio esté activo.
GET http://localhost:8000/health

Respuesta
{
  "status": "healthy",
  "service": "veterinaria-api",
  "version": "1.0.0"
}

```
**7. Autores / Integrantes del Grupo**

Dahyana Carolina Gonzalez

Santiago Gonzalez Gonzalez




