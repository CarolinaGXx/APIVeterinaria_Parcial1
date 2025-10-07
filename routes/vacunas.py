from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from uuid import UUID
from enum import Enum as _PyEnum

from models import Vacuna, VacunaCreate, VacunaUpdate, TipoVacuna
from database import VacunaORM, MascotaORM, UsuarioORM, uuid_to_str
from database.db import get_db
from sqlalchemy.orm import Session
from auth import get_current_user_dep, require_roles

"""
Rutas para gestión de vacunas.

Incluye registro, listado, obtención por id, actualización y eliminación de
registros de vacunación. Permisos basados en roles y en la relación
propietario-mascota.
"""

router = APIRouter(prefix="/vacunas", tags=["vacunas"])


def _enum_to_value(v):
    if isinstance(v, _PyEnum):
        return v.value
    return v


def _normalize_stored_tipo_vacuna(s: str):
    """Normaliza valores de tipo_vacuna almacenados en la BD.

    Convierte por ejemplo 'TipoVacuna.raza' -> 'raza' si procede.
    """
    if s is None:
        return s
    if isinstance(s, str) and "." in s:
        return s.split(".", 1)[1]
    return s


def _validate_uuid(id_str: str, name: str) -> str:
    """Validar que id_str sea un UUID válido y devolverlo como string.

    Lanza HTTPException(400) si no es un UUID válido.
    """
    try:
        UUID(str(id_str))
        return str(id_str)
    except Exception:
        raise HTTPException(
            status_code=400, detail=f"{name} inválido: debe ser un UUID"
        )


@router.post("/", response_model=Vacuna, status_code=201)
async def registrar_vacuna(
    vacuna: VacunaCreate, current_user=Depends(require_roles("veterinario", "admin")), db: Session = Depends(get_db)
):
    """Registrar una nueva vacuna.

    Solo veterinarios o administradores pueden crear registros de vacunación.
    El veterinario se toma del usuario autenticado.
    """
    data = vacuna.model_dump()
    try:
        mascota = db.get(MascotaORM, uuid_to_str(data["id_mascota"]))
        if not mascota:
            raise HTTPException(
                status_code=400, detail="La mascota especificada no existe"
            )

        vet_username = current_user.username

        db_obj = VacunaORM(
            id_mascota=uuid_to_str(data["id_mascota"]),
            tipo_vacuna=_enum_to_value(data["tipo_vacuna"]),
            fecha_aplicacion=data["fecha_aplicacion"],
            veterinario=vet_username,
            lote_vacuna=data["lote_vacuna"],
            proxima_dosis=data.get("proxima_dosis"),
        )
        from database.db import set_audit_fields

        set_audit_fields(db_obj, current_user.id, creating=True)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        owner = None
        if mascota and mascota.propietario:
            owner = (
                db.query(UsuarioORM)
                .filter(UsuarioORM.username == mascota.propietario)
                .one_or_none()
            )
        return {
            "id_vacuna": db_obj.id,
            "id_mascota": db_obj.id_mascota,
            "mascota_nombre": mascota.nombre,
            "propietario_username": (
                owner.username if owner else (mascota.propietario if mascota else None)
            ),
            "propietario_nombre": owner.nombre if owner else None,
            "propietario_telefono": owner.telefono if owner else None,
            "tipo_vacuna": _normalize_stored_tipo_vacuna(db_obj.tipo_vacuna),
            "fecha_aplicacion": db_obj.fecha_aplicacion,
            "veterinario": db_obj.veterinario,
            "lote_vacuna": db_obj.lote_vacuna,
            "proxima_dosis": db_obj.proxima_dosis,
        }
    except HTTPException:
        raise
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[Vacuna])
async def obtener_vacunas(
    tipo_vacuna: Optional[TipoVacuna] = Query(
        None, description="Filtrar por tipo de vacuna"
    ),
    veterinario: Optional[str] = Query(None, description="Filtrar por veterinario"),
    current_user=Depends(get_current_user_dep),
    db: Session = Depends(get_db),
):
    """Listar vacunas según filtros y permisos del usuario.

    Reglas de visibilidad similares a citas: admin ve todo; veterinario ve
    vacunas asignadas a él o de mascotas que posee; cliente ve solo vacunas
    de sus mascotas.
    """
    q = db.query(VacunaORM)
    if tipo_vacuna:
        q = q.filter(VacunaORM.tipo_vacuna == _enum_to_value(tipo_vacuna))
    if veterinario:
        q = q.filter(VacunaORM.veterinario.ilike(f"%{veterinario}%"))

    if current_user.role == "admin":
        pass
    elif current_user.role == "veterinario":
        from sqlalchemy import or_

        q = q.join(MascotaORM, VacunaORM.id_mascota == MascotaORM.id).filter(
            or_(
                VacunaORM.veterinario == current_user.username,
                MascotaORM.propietario == current_user.username,
            )
        )
    else:
        q = q.join(MascotaORM, VacunaORM.id_mascota == MascotaORM.id).filter(
            MascotaORM.propietario == current_user.username
        )

    resultados = q.all()
    mascota_ids = list({r.id_mascota for r in resultados})
    mascotas_map = {}
    owners_map = {}
    if mascota_ids:
        mascotas = db.query(MascotaORM).filter(MascotaORM.id.in_(mascota_ids)).all()
        mascotas_map = {m.id: m for m in mascotas}
        owner_usernames = list({m.propietario for m in mascotas if m.propietario})
        if owner_usernames:
            users = (
                db.query(UsuarioORM)
                .filter(UsuarioORM.username.in_(owner_usernames))
                .all()
            )
            owners_map = {u.username: u for u in users}
    resp = []
    for r in resultados:
        m = mascotas_map.get(r.id_mascota)
        owner = None
        if m and m.propietario:
            owner = owners_map.get(m.propietario)
        resp.append(
            {
                "id_vacuna": r.id,
                "id_mascota": r.id_mascota,
                "mascota_nombre": m.nombre if m else None,
                "propietario_username": (
                    owner.username if owner else (m.propietario if m else None)
                ),
                "propietario_nombre": owner.nombre if owner else None,
                "propietario_telefono": owner.telefono if owner else None,
                "tipo_vacuna": _normalize_stored_tipo_vacuna(r.tipo_vacuna),
                "fecha_aplicacion": r.fecha_aplicacion,
                "veterinario": r.veterinario,
                "lote_vacuna": r.lote_vacuna,
                "proxima_dosis": r.proxima_dosis,
            }
        )
    return resp
    
    
@router.get("/{vacuna_id}", response_model=Vacuna)
async def obtener_vacuna(vacuna_id: str, current_user=Depends(get_current_user_dep), db: Session = Depends(get_db)):
    """Obtener una vacuna por id.

    Acceso permitido para admin, propietario de la mascota o veterinario asignado.
    """
    try:
        vid = _validate_uuid(vacuna_id, "vacuna_id")
        r = db.get(VacunaORM, vid)
        if not r:
            raise HTTPException(status_code=404, detail="Vacuna no encontrada")
        m = db.get(MascotaORM, r.id_mascota)
        if current_user.role == "admin":
            pass
        elif current_user.role == "veterinario":
            if r.veterinario != current_user.username and (
                not m or m.propietario != current_user.username
            ):
                raise HTTPException(
                    status_code=403, detail="No autorizado para ver esta vacuna"
                )
        else:
            if not m or m.propietario != current_user.username:
                raise HTTPException(
                    status_code=403, detail="No autorizado para ver esta vacuna"
                )
        owner = None
        if m and m.propietario:
            owner = (
                db.query(UsuarioORM)
                .filter(UsuarioORM.username == m.propietario)
                .one_or_none()
            )
        return {
            "id_vacuna": r.id,
            "id_mascota": r.id_mascota,
            "mascota_nombre": m.nombre if m else None,
            "propietario_username": (
                owner.username if owner else (m.propietario if m else None)
            ),
            "propietario_nombre": owner.nombre if owner else None,
            "propietario_telefono": owner.telefono if owner else None,
            "tipo_vacuna": _normalize_stored_tipo_vacuna(r.tipo_vacuna),
            "fecha_aplicacion": r.fecha_aplicacion,
            "veterinario": r.veterinario,
            "lote_vacuna": r.lote_vacuna,
            "proxima_dosis": r.proxima_dosis,
        }
    finally:
        pass


@router.put("/{vacuna_id}", response_model=Vacuna)
async def actualizar_vacuna(
    vacuna_id: str,
    vacuna_update: VacunaUpdate,
    current_user=Depends(require_roles("veterinario", "admin")),
    db: Session = Depends(get_db),
):
    """Actualizar un registro de vacuna.

    No se permite cambiar la mascota asociada. Solo el veterinario asignado
    (o admin) puede editar; si el editor es un veterinario, se firma con su
    username.
    """
    update_data = vacuna_update.model_dump(exclude_unset=True)
    try:
        vid = _validate_uuid(vacuna_id, "vacuna_id")
        r = db.get(VacunaORM, vid)
        if not r:
            raise HTTPException(status_code=404, detail="Vacuna no encontrada")

        if "id_mascota" in update_data:
            raise HTTPException(
                status_code=400,
                detail="No está permitido actualizar id_mascota mediante este endpoint",
            )

        if current_user.role == "veterinario":
            if r.veterinario != current_user.username:
                raise HTTPException(
                    status_code=403, detail="No autorizado para modificar esta vacuna"
                )

        for field, value in update_data.items():
            if isinstance(value, _PyEnum):
                setattr(r, field, value.value)
            else:
                setattr(r, field, value)

        if current_user.role == "veterinario":
            r.veterinario = current_user.username

        from database.db import set_audit_fields

        set_audit_fields(r, current_user.id, creating=False)
        db.add(r)
        db.commit()
        db.refresh(r)
        m = db.get(MascotaORM, r.id_mascota)
        owner = None
        if m and m.propietario:
            owner = (
                db.query(UsuarioORM)
                .filter(UsuarioORM.username == m.propietario)
                .one_or_none()
            )
        return {
            "id_vacuna": r.id,
            "id_mascota": r.id_mascota,
            "mascota_nombre": m.nombre if m else None,
            "propietario_username": (
                owner.username if owner else (m.propietario if m else None)
            ),
            "propietario_nombre": owner.nombre if owner else None,
            "propietario_telefono": owner.telefono if owner else None,
            "tipo_vacuna": _normalize_stored_tipo_vacuna(r.tipo_vacuna),
            "fecha_aplicacion": r.fecha_aplicacion,
            "veterinario": r.veterinario,
            "lote_vacuna": r.lote_vacuna,
            "proxima_dosis": r.proxima_dosis,
        }
    except HTTPException:
        raise
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))
    


@router.delete("/{vacuna_id}")
async def eliminar_vacuna(
    vacuna_id: str, current_user=Depends(require_roles("veterinario", "admin")), db: Session = Depends(get_db)
):
    """Eliminar un registro de vacuna.

    Solo el veterinario asignado a la vacuna o un administrador pueden eliminar.
    """
    try:
        vid = _validate_uuid(vacuna_id, "vacuna_id")
        r = db.get(VacunaORM, vid)
        if not r:
            raise HTTPException(status_code=404, detail="Vacuna no encontrada")
        if (
            current_user.role == "veterinario"
            and r.veterinario != current_user.username
        ):
            raise HTTPException(
                status_code=403, detail="No autorizado para eliminar esta vacuna"
            )
        db.delete(r)
        db.commit()
        return {"message": "Registro de vacuna eliminado exitosamente"}
    except HTTPException:
        raise
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))
