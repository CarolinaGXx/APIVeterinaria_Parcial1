from typing import Optional
from datetime import datetime
from uuid import uuid4, UUID

from sqlalchemy import Column, String, Integer, DateTime, Float, Text, ForeignKey, Date
from sqlalchemy.orm import declarative_base

Base = declarative_base()


def gen_uuid_str():
    return str(uuid4())


# ORM: Usuarios
class UsuarioORM(Base):
    __tablename__ = "usuarios"
    # columna en DB: id_usuario, atributo python: id
    id = Column("id_usuario", String(36), primary_key=True, default=gen_uuid_str)
    username = Column(String(100), nullable=False, unique=True)
    nombre = Column(String(200), nullable=False)
    edad = Column(Integer, nullable=False)
    telefono = Column(String(20), nullable=False)
    role = Column(String(20), nullable=False, default="cliente")
    password_salt = Column(String(64), nullable=False)
    password_hash = Column(String(128), nullable=False)
    # Auditoría
    id_usuario_creacion = Column(String(36), nullable=True)
    id_usuario_actualizacion = Column(String(36), nullable=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ORM: Mascotas
class MascotaORM(Base):
    __tablename__ = "mascotas"
    id = Column("id_mascota", String(36), primary_key=True, default=gen_uuid_str)
    nombre = Column(String(50), nullable=False)
    tipo = Column(String(20), nullable=False)
    raza = Column(String(50))
    edad = Column(Integer)
    peso = Column(Float)
    propietario = Column(String(100))  # username, validated at insert time
    # Auditoría
    id_usuario_creacion = Column(String(36), nullable=True)
    id_usuario_actualizacion = Column(String(36), nullable=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ORM: Citas
class CitaORM(Base):
    __tablename__ = "citas"
    id = Column("id_cita", String(36), primary_key=True, default=gen_uuid_str)
    id_mascota = Column(String(36), ForeignKey("mascotas.id_mascota"), nullable=False)
    fecha = Column(DateTime, nullable=False)
    motivo = Column(String(200))
    veterinario = Column(String(100))
    estado = Column(String(20), default="pendiente")
    # Auditoría
    id_usuario_creacion = Column(String(36), nullable=True)
    id_usuario_actualizacion = Column(String(36), nullable=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ORM: Vacunas
class VacunaORM(Base):
    __tablename__ = "vacunas"
    id = Column("id_vacuna", String(36), primary_key=True, default=gen_uuid_str)
    id_mascota = Column(String(36), ForeignKey("mascotas.id_mascota"), nullable=False)
    tipo_vacuna = Column(String(50))
    fecha_aplicacion = Column(Date)
    veterinario = Column(String(100))
    lote_vacuna = Column(String(20))
    proxima_dosis = Column(Date, nullable=True)
    # Auditoría
    id_usuario_creacion = Column(String(36), nullable=True)
    id_usuario_actualizacion = Column(String(36), nullable=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ORM: Facturas
class FacturaORM(Base):
    __tablename__ = "facturas"
    id = Column("id_factura", String(36), primary_key=True, default=gen_uuid_str)
    numero_factura = Column(String(50), nullable=False, unique=True)
    id_mascota = Column(String(36), ForeignKey("mascotas.id_mascota"), nullable=False)
    id_cita = Column(String(36), ForeignKey("citas.id_cita"), nullable=True)
    fecha_factura = Column(DateTime, nullable=False)
    tipo_servicio = Column(String(50))
    descripcion = Column(Text)
    veterinario = Column(String(100))
    valor_servicio = Column(Float)
    iva = Column(Float)
    descuento = Column(Float)
    estado = Column(String(20), default="pendiente")
    total = Column(Float)
    # Auditoría
    id_usuario_creacion = Column(String(36), nullable=True)
    id_usuario_actualizacion = Column(String(36), nullable=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ORM: Recetas
class RecetaORM(Base):
    __tablename__ = "recetas"
    id = Column("id_receta", String(36), primary_key=True, default=gen_uuid_str)
    id_cita = Column(String(36), ForeignKey("citas.id_cita"), nullable=False)
    fecha_emision = Column(DateTime, nullable=False)
    veterinario = Column(String(100))
    indicaciones = Column(Text)
    # Auditoría
    id_usuario_creacion = Column(String(36), nullable=True)
    id_usuario_actualizacion = Column(String(36), nullable=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Opcional: líneas de receta (medicamentos) como tabla separada
class RecetaLineaORM(Base):
    __tablename__ = "receta_lineas"
    id = Column("id_receta_linea", String(36), primary_key=True, default=gen_uuid_str)
    id_receta = Column(String(36), ForeignKey("recetas.id_receta"), nullable=False)
    medicamento = Column(String(200), nullable=False)
    dosis = Column(String(100))
    frecuencia = Column(String(100))
    duracion = Column(String(100))

__all__ = [
    "Base",
    "UsuarioORM",
    "MascotaORM",
    "CitaORM",
    "VacunaORM",
    "FacturaORM",
    "RecetaORM",
    "RecetaLineaORM",
]
