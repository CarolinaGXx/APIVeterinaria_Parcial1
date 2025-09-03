# APIVeterinaria_Parcial1

**Tema:** Veterinaria (perros, gatos, aves) – Registrar vacuna, agendar cita, facturar consulta.

**1. Título del Proyecto**
API Veterinaria – Parcial 1 Aplicaciones y Servicios Web

**2. Descripción General**

API RESTful básica para gestionar una veterinaria con tres entidades principales y operaciones clave:

-Mascotas (perros, gatos, aves): registro y gestión.
-Vacunas: registrar y consultar vacunas aplicadas.
-Citas: agendar, reprogramar y cancelar.
-Facturas: facturar consultas/citas realizadas.

La API expone endpoints CRUD, valida datos con Pydantic, maneja códigos HTTP adecuados y se autodocumenta con Swagger UI y ReDoc de FastAPI. Incluye ejemplos para Postman y un esquema de colaboración en GitHub.

vetcare-api/
├─ app/
│ ├─ __init__.py
│ ├─ main.py                 # Punto de entrada FastAPI + inclusión de routers
│ ├─ models.py/              # Modelos Pydantic (request/response)
│ ├─ pets.py                 # CRUD de mascotas + filtros por query
│ ├─ vaccines.py             # CRUD y registro de vacunas
│ ├─ appointments.py         # CRUD y gestión de citas
│ └─ invoices.py 

│ ├─ database.py             # "DB" en memoria (dicts) + generadores de ID
│ └─ routers/
│ ├─ pets.py                 # CRUD de mascotas + filtros por query
│ ├─ vaccines.py             # CRUD y registro de vacunas
│ ├─ appointments.py         # CRUD y gestión de citas
│ └─ invoices.py             # CRUD y facturación de consultas
├─ requirements.txt
└─ README.md                 # Este documento

**4. Requisitos de Instalación**

Python 3.10+ (recomendado 3.11)
pip o uv/pipx

Dependencias (requirements.txt)
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
python-multipart==0.0.6

