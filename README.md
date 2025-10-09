# APIVeterinaria_Parcial1

**API Veterinaria – Parcial 1 Aplicaciones y Servicios Web**

Este README está actualizado con el estado actual del repositorio: FastAPI + SQLAlchemy + Alembic + Autenticación JWT.

**1. Descripción General**

Esta API RESTful permite gestionar digitalmente los procesos comunes en una veterinaria:

- Registro y gestión de mascotas
- Registro de vacunas aplicadas
- Agendamiento y gestión de citas
- Emisión de facturas y recetas
- Seguridad con autenticación JWT y control de roles

Diseñada para resolver la necesidad de digitalizar y centralizar la información clínica y administrativa en veterinarias pequeñas y medianas.

**2. Tecnologías Utilizadas**

- Alembic: control de versiones de la base de datos (migraciones)
- FastAPI: framework web moderno y veloz
- Pydantic: validación y serialización de datos
- PyODBC: conexión con SQL Server
- python-jose: manejo de JWT
- SQLAlchemy: ORM para manejo de base de datos
- Uvicorn: servidor ASGI para desarrollo

**3. Arquitectura o Diseño**
```
APIVeterinaria_Parcial1/
├─ alembic/             # Migraciones de base de datos
            
├─ database/                # "Base de datos" en memoria
│ ├─ __init__.py            
│ ├─ db.py                  # Diccionarios y generadores de IDs
│ ├─ models.py

├─ models/                  # Modelos Pydantic (request/response)
│ ├─ __init__.py               
│ ├─ citas.py               # CRUD y gestión de citas
│ ├─ facturas.py            # CRUD y facturación de consultas
│ └─ mascotas.py            # CRUD de mascotas + filtros por query
│ └─ recetas.py             # CRUD y recetas
│ └─ usuarios.py            # CRUD y usuarios
│ └─ vacunas.py             # CRUD y registro de vacunas

│─ routes/                  # Endpoints de la API (FastAPI Routers)
│ ├─ __init__.py
│ ├─ auth.py                   
│ ├─ citas.py               # Endpoints de citas
│ ├─ facturas.py            # Endpoints de facturas
│ └─ mascotas.py            # Endpoints de mascotas
│ └─ recetas.py             # Endpoints de recetas
│ └─ usuario.py             # Endpoints de usuarios
│ └─ vacunas.py             # Endpoints de vacunas

│─ .env                     # Archivo local con variables de entorno sensibles
│─ .gitignore               # Define los archivos/carpetas que Git debe ignorar
│─ alembic.ini              # Carpeta de migraciones generadas por Alembic para mantener el esquema de la base de datos versionado
│─ auth.py                  # Lógica relacionada a autenticación y autorización (manejo de JWT, roles, y seguridad)
│─ main.py                  # Punto de entrada principal de la aplicación

├─ requirements.txt         # Lista de dependencias necesarias para ejecutar el proyecto (FastAPI, SQLAlchemy, etc.)
└─ README.md                # Documento de documentación principal del proyecto

```

**4. Requisitos de Instalación**

Versión de Python: 3.10+ (se recomienda 3.11 o 3.12).

(Opcional para SQL Server) ODBC Driver 17+

```
# Clonar repositorio

git clone https://github.com/tuusuario/APIVeterinaria_Parcial1.git
cd APIVeterinaria_Parcial1

# Crear entorno virtual

python -m venv .venv
.\.venv\Scripts\Activate.ps1  # En Windows
# source .venv/bin/activate   # En Linux/Mac

# Instalar dependencias

pip install -r requirements.txt
```

**5. Variables de Entorno (.env)** > #No compartas ni subas el archivo `.env` a GitHub. Contiene información sensible.


Crea un archivo .env en la raíz con variables como:
```
DATABASE_URL=mssql+pyodbc:///?odbc_connect=DRIVER%3D%7BODBC+Driver+17+for+SQL+Server%7D%3BSERVER%3Dlocalhost%3BDATABASE%3Dveterinaria%3BTrusted_Connection%3Dyes%3B
JWT_SECRET_KEY=clave_super_secreta_generada
CORS_ALLOWED_ORIGINS=http://localhost:3000
```
**6. Ejecución del Proyecto**

uvicorn main:app --reload

Swagger UI: http://localhost:8000/docs

ReDoc: http://localhost:8000/redoc

**7. Seguridad y Autenticación**

- Autenticación: OAuth2PasswordBearer con JWT

- Roles soportados: cliente, veterinario, admin

- JWT con claims (sub, exp, iss, aud, etc.)

- Dependencias require_roles(...) para proteger endpoints

Endpoint:
```
POST /auth/token

Content-Type: application/x-www-form-urlencoded

username=usuario

password=contraseña
```

**8. Descripción de Endpoints**

#### 8.1. **Mascotas** `/mascotas`

> Gestión CRUD de las mascotas registradas en la veterinaria.

##### POST `/mascotas` → Crear mascota

```json
{
  "nombre": "Firulais",
  "especie": "perro",
  "edad": 3,
  "peso": 12.5,
  "raza": "Labrador"
}
```

##### GET `/mascotas` → Listar mascotas

* Soporta filtros opcionales por especie o edad:

  * `/mascotas?especie=perro`
  * `/mascotas?edad=3`

##### GET `/mascotas/{id}` → Obtener mascota por ID

```http
GET /mascotas/0b3a7f3e-8a2f-4d3c-9a1b-1234567890ab
```

##### PUT `/mascotas/{id}` → Actualizar datos

```json
{
  "nombre": "Max",
  "especie": "perro",
  "edad": 4,
  "peso": 13.2,
  "raza": "Golden Retriever"
}
```
##### DELETE `/mascotas/{id}` → Eliminar mascota

---

#### 8.2. **Vacunas** `/vacunas`

> Registro y consulta de vacunas aplicadas.

##### POST `/vacunas`

```json
{
  "mascota_id": "0b3a7f3e-8a2f-4d3c-9a1b-1234567890ab",
  "nombre_vacuna": "Rabia",
  "fecha": "2025-10-01"
}
```

##### GET `/vacunas` → Listar vacunas

##### GET `/vacunas/{id}` → Obtener vacuna por ID

---

#### 8.3. **Citas** `/citas`

> Gestión de agendamiento de citas médicas veterinarias.

##### POST `/citas`

```json
{
  "mascota_id": "0b3a7f3e-8a2f-4d3c-9a1b-1234567890ab",
  "fecha": "2025-10-10T14:30:00",
  "motivo": "Consulta general",
  "veterinario": "dr.vet"
}
```

##### GET `/citas` → Ver todas las citas

##### PUT `/citas/{id}` → Reprogramar o modificar cita

```json
{
  "fecha": "2025-10-12T10:00:00",
  "motivo": "Vacunación",
  "veterinario": "dr.luisa"
}
```

##### DELETE `/citas/{id}` → Cancelar cita

---

#### 8.4. **Facturas** `/facturas`

> Facturación de consultas o servicios veterinarios.

##### POST `/facturas`

```json
{
  "id_cita": "0b3a7f3e-8a2f-4d3c-9a1b-abc123456789",
  "tipo_servicio": "consulta_general",
  "descripcion": "Consulta por fiebre y vómito",
  "valor_servicio": 60.0,
  "iva": 11.4,
  "descuento": 0.0
}
```

##### GET `/facturas` → Listar todas las facturas

##### GET `/facturas/{id}` → Ver detalle de una factura

---

#### 8.5. **Recetas** `/recetas`

> Emisión de recetas médicas con indicaciones y medicamentos.

##### POST `/recetas`

```json
{
  "id_cita": "0b3a7f3e-8a2f-4d3c-9a1b-abc123456789",
  "fecha_emision": "2025-10-06T10:00:00",
  "indicaciones": "Administrar cada 8 horas",
  "lineas": [
    {
      "medicamento": "Amoxicilina",
      "dosis": "250mg",
      "frecuencia": "cada 8h",
      "duracion": "7 días"
    }
  ]
}
```

##### GET `/recetas` → Ver todas las recetas

##### GET `/recetas/{id}` → Obtener receta por ID

---

#### 8.6. **Autenticación** `/auth/token`

> Login para obtener un JWT (OAuth2 password grant).

##### POST `/auth/token`

Content-Type: `application/x-www-form-urlencoded`

```
username=admin
password=admin123
```

##### Respuesta

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

---

#### 8.7. **Health Check** `/health`

> Verifica que el servicio esté activo.

#GET `/health`

```json
{
  "status": "healthy",
  "service": "veterinaria-api",
  "version": "1.0.0"
}
```

**9.  Migraciones con Alembic**

```
# Generar migración
alembic revision --autogenerate -m "mensaje"

# Aplicar migraciones
alembic upgrade head

# (Opcional) Marcar estado actual como "head" sin aplicar cambios
alembic stamp head
```

**10. Próximas Mejoras**

- Implementar refresh tokens y revocación de sesiones
- Test suite con pytest y coverage
- Integración continua (CI) con GitHub Actions
- Rate limiting y paginación
- Dockerización y despliegue en la nube

**11. Autores / Integrantes del Grupo**

Dahyana Carolina Gonzalez

Santiago Gonzalez Gonzalez




