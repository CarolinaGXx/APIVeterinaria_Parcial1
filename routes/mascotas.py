from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from uuid import UUID as UUID_type, UUID
from datetime import datetime
from enum import Enum as _PyEnum

from models import Mascota, MascotaCreate, MascotaUpdate, TipoMascota
from database import (
    CitaORM,
    VacunaORM,
    MascotaORM,
    UsuarioORM,
    uuid_to_str,
    get_database_url,
    ensure_usuario_exists,
)
from database.db import get_db
from sqlalchemy.orm import Session
from auth import get_current_user_dep, require_roles

"""
Rutas relacionadas con mascotas.

Endpoints:
- crear_mascota: crear una mascota; el propietario se infiere del usuario autenticado.
- obtener_mascotas: listar mascotas, filtra por tipo y (para admin) por propietario.
- obtener_mascota: obtener una mascota por id (solo propietario o admin).
- actualizar_mascota: actualizar campos permitidos de la mascota (propietario no editable).
- eliminar_mascota: eliminar mascota si no tiene relaciones (citas/vacunas).

Nota: las operaciones registran campos de auditoría usando las utilidades en database.db.
Vacunas y citas se atienden desde sus routers específicos (no aquí).
"""

router = APIRouter(prefix="/mascotas", tags=["mascotas"])


def _enum_to_value(v):
    """Devuelve Enum.value si v es una enumeración; de lo contrario,
        devuelve v sin cambios.

    Este asistente se utiliza para almacenar valores
    de enumeración en campos de la base de datos cuando los
    modelos de Pydantic pueden proporcionar miembros de enumeración.
    """
    if isinstance(v, _PyEnum):
        return v.value
    return v


def _normalize_stored_tipo(s: str):
    """Normaliza las cadenas tipo almacenadas provenientes
        de la base de datos.

    La base de datos puede almacenar valores de enumeración
    como nombres completos (p. ej., "TipoMascota.perro").
    Este asistente devuelve el nombre corto después del punto
    («perro») o la entrada sin cambios/sin cambios cuando corresponda.
    """
    if s is None:
        return s
    if isinstance(s, str) and "." in s:
        return s.split(".", 1)[1]
    return s


def _validate_uuid(id_str: str, name: str) -> str:
    """Valida que id_str sea una cadena UUID y la devuelve.

    Acepta objetos UUID o representaciones de cadena.
    Genera HTTPException(400) si el valor no es un UUID válido.
    """
    try:
        UUID_type(str(id_str))
        return str(id_str)
    except Exception:
        raise HTTPException(
            status_code=400, detail=f"{name} inválido: debe ser un UUID"
        )


def _get_telefono_for_username(db_session, username: Optional[str]) -> Optional[str]:
    """Devuelve el teléfono de un nombre de usuario o
        "Ninguno" en caso de error o usuario faltante.

    Esta es una herramienta de máxima eficiencia que utilizan varios
    endpoints para incluir el teléfono del propietario en las
    respuestas sin generar errores cuando falta el registro del usuario.
    """
    if not username:
        return None
    try:
        u = (
            db_session.query(UsuarioORM)
            .filter(UsuarioORM.username == username)
            .one_or_none()
        )
        return u.telefono if u else None
    except Exception:
        return None


@router.post("/", response_model=Mascota, status_code=201)
async def crear_mascota(
    mascota: MascotaCreate,
    current_user=Depends(require_roles("veterinario", "cliente", "admin")),
    db: Session = Depends(get_db),
):
    """Crear una nueva mascota.

    El propietario se infiere del usuario autenticado. Los campos de auditoría
    se establecen usando el id del usuario autenticado. Devuelve la mascota
    creada junto con el teléfono del propietario cuando esté disponible.
    """
    data = mascota.model_dump()
    propietario_username = current_user.username
    telefono_prop = current_user.telefono if hasattr(current_user, "telefono") else None

    try:
        db_obj = MascotaORM(
            nombre=data["nombre"],
            tipo=_enum_to_value(data["tipo"]),
            raza=data.get("raza"),
            edad=data.get("edad"),
            peso=data.get("peso"),
            propietario=propietario_username,
        )
        from database.db import set_audit_fields

        set_audit_fields(db_obj, current_user.id, creating=True)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return {
            "id_mascota": db_obj.id,
            "nombre": db_obj.nombre,
            "tipo": _normalize_stored_tipo(db_obj.tipo),
            "raza": db_obj.raza,
            "edad": db_obj.edad,
            "peso": db_obj.peso,
            "propietario": db_obj.propietario,
            "telefono_propietario": telefono_prop,
        }
    except HTTPException:
        raise
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Error al crear mascota: {e}")


@router.get("/", response_model=List[Mascota])
async def obtener_mascotas(
    tipo: Optional[TipoMascota] = Query(
        None, description="Filtrar por tipo de mascota"
    ),
    propietario: Optional[str] = Query(
        None, description="Filtrar por propietario (admin only)"
    ),
    current_user=Depends(get_current_user_dep),
    db: Session = Depends(get_db),
):
    """Obtener lista de mascotas.

    Por defecto devuelve las mascotas pertenecientes al usuario autenticado.
    Los administradores pueden filtrar opcionalmente por propietario
    (coincidencia parcial).
    """
    q = db.query(MascotaORM)
    if tipo:
        q = q.filter(MascotaORM.tipo == _enum_to_value(tipo))

    if current_user.role == "admin":
        if propietario:
            q = q.filter(MascotaORM.propietario.ilike(f"%{propietario}%"))
    else:
        q = q.filter(MascotaORM.propietario == current_user.username)

    results = q.all()
    resp = []
    for r in results:
        telefono = _get_telefono_for_username(db, r.propietario)
        resp.append(
            {
                "id_mascota": r.id,
                "nombre": r.nombre,
                "tipo": _normalize_stored_tipo(r.tipo),
                "raza": r.raza,
                "edad": r.edad,
                "peso": r.peso,
                "propietario": r.propietario,
                "telefono_propietario": telefono,
            }
        )
    return resp


@router.get("/{mascota_id}", response_model=Mascota)
async def obtener_mascota(
    mascota_id: str,
    current_user=Depends(get_current_user_dep),
    db: Session = Depends(get_db),
):
    """Obtener una mascota por id.

    Solo el propietario o un administrador pueden ver la mascota. La respuesta
    incluye el telefono_propietario cuando esté disponible. La ausencia del
    registro de usuario se tolera (telefono será None).
    """
    try:
        mid = _validate_uuid(mascota_id, "mascota_id")
        r = db.get(MascotaORM, mid)
        if not r:
            raise HTTPException(status_code=404, detail="Mascota no encontrada")

        if current_user.role != "admin" and r.propietario != current_user.username:
            raise HTTPException(
                status_code=403, detail="No autorizado para ver esta mascota"
            )

        telefono = None
        try:
            usuario = (
                db.query(UsuarioORM)
                .filter(UsuarioORM.username == r.propietario)
                .one_or_none()
            )
            telefono = usuario.telefono if usuario else None
        except Exception:
            telefono = None
        return {
            "id_mascota": r.id,
            "nombre": r.nombre,
            "tipo": _normalize_stored_tipo(r.tipo),
            "raza": r.raza,
            "edad": r.edad,
            "peso": r.peso,
            "propietario": r.propietario,
            "telefono_propietario": telefono,
        }
    finally:
        pass


@router.put("/{mascota_id}", response_model=Mascota)
async def actualizar_mascota(
    mascota_id: str,
    mascota_update: MascotaUpdate,
    current_user=Depends(get_current_user_dep),
    db: Session = Depends(get_db),
):
    """Actualizar una mascota existente.

    Solo el propietario o un administrador pueden actualizar. El campo
    propietario no es editable mediante este endpoint y provocará un 400 si
    se proporciona. Los valores Enum se almacenan usando su .value. Los campos
    de auditoría se actualizan usando el id del usuario autenticado.
    """
    data = mascota_update.model_dump(exclude_unset=True)
    try:
        mid = _validate_uuid(mascota_id, "mascota_id")
        r = db.get(MascotaORM, mid)
        if not r:
            raise HTTPException(status_code=404, detail="Mascota no encontrada")

        if current_user.role != "admin" and r.propietario != current_user.username:
            raise HTTPException(
                status_code=403, detail="No autorizado para modificar esta mascota"
            )

        if "propietario" in data:
            raise HTTPException(
                status_code=400,
                detail="No está permitido actualizar el propietario mediante este endpoint; se infiere del usuario autenticado",
            )

        for field, value in data.items():
            if isinstance(value, _PyEnum):
                setattr(r, field, value.value)
            else:
                setattr(r, field, value)

        from database.db import set_audit_fields

        set_audit_fields(r, current_user.id, creating=False)
        db.add(r)
        db.commit()
        db.refresh(r)
        telefono = None
        try:
            usuario = (
                db.query(UsuarioORM)
                .filter(UsuarioORM.username == r.propietario)
                .one_or_none()
            )
            telefono = usuario.telefono if usuario else None
        except Exception:
            telefono = None
        return {
            "id_mascota": r.id,
            "nombre": r.nombre,
            "tipo": _normalize_stored_tipo(r.tipo),
            "raza": r.raza,
            "edad": r.edad,
            "peso": r.peso,
            "propietario": r.propietario,
            "telefono_propietario": telefono,
        }
    except HTTPException:
        raise
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Error al actualizar mascota: {e}")


@router.delete("/{mascota_id}")
async def eliminar_mascota(
    mascota_id: str,
    current_user=Depends(get_current_user_dep),
    db: Session = Depends(get_db),
):
    """Eliminar una mascota si no existen citas o vacunas relacionadas.

    Solo el propietario o un administrador pueden eliminar. El endpoint
    comprueba si existen registros relacionados en Cita y Vacuna y devuelve
    400 si existen para evitar la pérdida accidental de datos.
    """
    try:
        mid = _validate_uuid(mascota_id, "mascota_id")
        r = db.get(MascotaORM, mid)
        if not r:
            raise HTTPException(status_code=404, detail="Mascota no encontrada")

        if current_user.role != "admin" and r.propietario != current_user.username:
            raise HTTPException(
                status_code=403, detail="No autorizado para eliminar esta mascota"
            )

        citas_asociadas = db.query(CitaORM).filter(CitaORM.id_mascota == mid).first()
        vacunas_asociadas = (
            db.query(VacunaORM).filter(VacunaORM.id_mascota == mid).first()
        )
        if citas_asociadas or vacunas_asociadas:
            raise HTTPException(
                status_code=400,
                detail="No se puede eliminar la mascota porque tiene citas o vacunas asociadas",
            )
        db.delete(r)
        db.commit()
        return {"message": "Mascota eliminada exitosamente"}
    except HTTPException:
        raise
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Error al eliminar mascota: {e}")