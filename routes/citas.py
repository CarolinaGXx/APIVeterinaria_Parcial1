from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from datetime import datetime
from uuid import UUID
from enum import Enum as _PyEnum

from models import Cita, CitaCreate, CitaUpdate, EstadoCita
from database import CitaORM, MascotaORM, UsuarioORM, uuid_to_str
from database.db import get_db
from sqlalchemy.orm import Session
from auth import get_current_user_dep, require_roles

"""
Rutas para gestión de citas.

Proporciona endpoints para agendar, listar, obtener, actualizar y cancelar citas.
Los permisos están basados en roles y en la relación propietario-mascota.
"""

router = APIRouter(prefix="/citas", tags=["citas"])


def _enum_to_value(v):
    if isinstance(v, _PyEnum):
        return v.value
    return v


def _normalize_stored_estado(s: str):
    """Normaliza el campo estado retornado desde BD.

    Convierte por ejemplo 'EstadoCita.pendiente' -> 'pendiente' si procede.
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


@router.post("/", response_model=Cita, status_code=201)
async def agendar_cita(
    cita: CitaCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("veterinario", "cliente", "admin")),
):
    """Agendar una nueva cita.

    El propietario se infiere del usuario autenticado. Solo el propietario de
    la mascota o un administrador pueden crear citas para esa mascota. Si se
    especifica un veterinario, debe existir y tener role 'veterinario'.
    """
    data = cita.model_dump()
    try:
        mascota = db.get(MascotaORM, uuid_to_str(data["id_mascota"]))
        if not mascota:
            raise HTTPException(
                status_code=400, detail="La mascota especificada no existe"
            )

        if (
            current_user.role != "admin"
            and mascota.propietario != current_user.username
        ):
            raise HTTPException(
                status_code=403,
                detail="No autorizado para crear una cita para esta mascota",
            )

        vet = (
            db.query(UsuarioORM)
            .filter(
                UsuarioORM.username == data["veterinario"],
                UsuarioORM.role == "veterinario",
            )
            .one_or_none()
        )
        if not vet:
            raise HTTPException(
                status_code=400,
                detail=f"Veterinario '{data['veterinario']}' no encontrado o no es veterinario",
            )

        db_obj = CitaORM(
            id_mascota=uuid_to_str(data["id_mascota"]),
            fecha=data["fecha"],
            motivo=data["motivo"],
            veterinario=data["veterinario"],
            estado=_enum_to_value(EstadoCita.pendiente),
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
            "id_cita": db_obj.id,
            "id_mascota": db_obj.id_mascota,
            "mascota_nombre": mascota.nombre,
            "propietario_username": (
                owner.username if owner else (mascota.propietario if mascota else None)
            ),
            "propietario_nombre": owner.nombre if owner else None,
            "propietario_telefono": owner.telefono if owner else None,
            "fecha": db_obj.fecha,
            "motivo": db_obj.motivo,
            "veterinario": db_obj.veterinario,
            "estado": _normalize_stored_estado(db_obj.estado),
        }
    except HTTPException:
        raise
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Error al crear cita: {e}")


@router.get("/", response_model=List[Cita])
async def obtener_citas(
    estado: Optional[EstadoCita] = Query(
        None, description="Filtrar por estado de cita"
    ),
    veterinario: Optional[str] = Query(None, description="Filtrar por veterinario"),
    current_user=Depends(get_current_user_dep),
    db: Session = Depends(get_db),
):
    """Listar citas según filtros y permisos del usuario.

    Reglas de visibilidad:
    - admin: ve todas las citas
    - veterinario: ve citas asignadas a él o citas de mascotas que posee
    - cliente: ve solo citas de sus mascotas
    """
    q = db.query(CitaORM)
    if estado:
        q = q.filter(CitaORM.estado == _enum_to_value(estado))
    if veterinario:
        q = q.filter(CitaORM.veterinario.ilike(f"%{veterinario}%"))

    if current_user.role == "admin":
        pass
    elif current_user.role == "veterinario":
        from sqlalchemy import or_

        q = q.join(MascotaORM, CitaORM.id_mascota == MascotaORM.id).filter(
            or_(
                CitaORM.veterinario == current_user.username,
                MascotaORM.propietario == current_user.username,
            )
        )
    else:
        q = q.join(MascotaORM, CitaORM.id_mascota == MascotaORM.id).filter(
            MascotaORM.propietario == current_user.username
        )

    results = q.all()
    mascota_ids = list({r.id_mascota for r in results})
    nombres = {}
    mascotas_map = {}
    owners_map = {}
    if mascota_ids:
        mascotas = db.query(MascotaORM).filter(MascotaORM.id.in_(mascota_ids)).all()
        mascotas_map = {m.id: m for m in mascotas}
        nombres = {m.id: m.nombre for m in mascotas}
        owner_usernames = list({m.propietario for m in mascotas if m.propietario})
        if owner_usernames:
            users = (
                db.query(UsuarioORM)
                .filter(UsuarioORM.username.in_(owner_usernames))
                .all()
            )
            owners_map = {u.username: u for u in users}

    return [
        {
            "id_cita": r.id,
            "id_mascota": r.id_mascota,
            "mascota_nombre": (
                mascotas_map.get(r.id_mascota).nombre
                if mascotas_map.get(r.id_mascota)
                else nombres.get(r.id_mascota)
            ),
            "propietario_username": (
                owners_map.get(mascotas_map.get(r.id_mascota).propietario).username
                if mascotas_map.get(r.id_mascota)
                and owners_map.get(mascotas_map.get(r.id_mascota).propietario)
                else (
                    mascotas_map.get(r.id_mascota).propietario
                    if mascotas_map.get(r.id_mascota)
                    else None
                )
            ),
            "propietario_nombre": (
                owners_map.get(mascotas_map.get(r.id_mascota).propietario).nombre
                if mascotas_map.get(r.id_mascota)
                and owners_map.get(mascotas_map.get(r.id_mascota).propietario)
                else None
            ),
            "propietario_telefono": (
                owners_map.get(mascotas_map.get(r.id_mascota).propietario).telefono
                if mascotas_map.get(r.id_mascota)
                and owners_map.get(mascotas_map.get(r.id_mascota).propietario)
                else None
            ),
            "fecha": r.fecha,
            "motivo": r.motivo,
            "veterinario": r.veterinario,
            "estado": _normalize_stored_estado(r.estado),
        }
        for r in results
    ]
    


@router.get("/{cita_id}", response_model=Cita)
async def obtener_cita(cita_id: str, current_user=Depends(get_current_user_dep), db: Session = Depends(get_db)):
    """Obtener una cita por id.

    Acceso permitido para admin, propietario de la mascota o veterinario asignado.
    """
    try:
        cid = _validate_uuid(cita_id, "cita_id")
        r = db.get(CitaORM, cid)
        if not r:
            raise HTTPException(status_code=404, detail="Cita no encontrada")
        m = db.get(MascotaORM, r.id_mascota)
        if current_user.role == "admin":
            pass
        elif current_user.role == "veterinario":
            if r.veterinario != current_user.username and (
                not m or m.propietario != current_user.username
            ):
                raise HTTPException(
                    status_code=403, detail="No autorizado para ver esta cita"
                )
        else:
            if not m or m.propietario != current_user.username:
                raise HTTPException(
                    status_code=403, detail="No autorizado para ver esta cita"
                )
        owner = None
        if m and m.propietario:
            owner = (
                db.query(UsuarioORM)
                .filter(UsuarioORM.username == m.propietario)
                .one_or_none()
            )
        return {
            "id_cita": r.id,
            "id_mascota": r.id_mascota,
            "mascota_nombre": m.nombre if m else None,
            "propietario_username": (
                owner.username if owner else (m.propietario if m else None)
            ),
            "propietario_nombre": owner.nombre if owner else None,
            "propietario_telefono": owner.telefono if owner else None,
            "fecha": r.fecha,
            "motivo": r.motivo,
            "veterinario": r.veterinario,
            "estado": _normalize_stored_estado(r.estado),
        }
    finally:
        pass


@router.put("/{cita_id}", response_model=Cita)
async def actualizar_cita(
    cita_id: str, cita_update: CitaUpdate, current_user=Depends(get_current_user_dep), db: Session = Depends(get_db)
):
    """Actualizar una cita.

    No se permite cambiar la mascota asociada ni que un cliente modifique el
    estado directamente. Si se cambia el veterinario, se valida que exista
    y sea veterinario. Solo el propietario de la mascota o admin pueden
    realizar la actualización.
    """
    update_data = cita_update.model_dump(exclude_unset=True)
    try:
        cid = _validate_uuid(cita_id, "cita_id")
        r = db.get(CitaORM, cid)
        if not r:
            raise HTTPException(status_code=404, detail="Cita no encontrada")
        if "id_mascota" in update_data:
            raise HTTPException(
                status_code=400,
                detail="No está permitido actualizar id_mascota mediante este endpoint",
            )
        if "estado" in update_data:
            raise HTTPException(
                status_code=400,
                detail="No está permitido actualizar el estado de la cita mediante este endpoint",
            )
        if "veterinario" in update_data and update_data["veterinario"] is not None:
            vet_upd = (
                db.query(UsuarioORM)
                .filter(
                    UsuarioORM.username == update_data["veterinario"],
                    UsuarioORM.role == "veterinario",
                )
                .one_or_none()
            )
            if not vet_upd:
                raise HTTPException(
                    status_code=400,
                    detail=f"Veterinario '{update_data['veterinario']}' no encontrado o no es veterinario",
                )
        mascota = db.get(MascotaORM, r.id_mascota)
        if current_user.role != "admin" and (
            not mascota or mascota.propietario != current_user.username
        ):
            raise HTTPException(
                status_code=403, detail="No autorizado para modificar esta cita"
            )

        for field, value in update_data.items():
            if isinstance(value, _PyEnum):
                setattr(r, field, value.value)
            else:
                setattr(r, field, value)
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
            "id_cita": r.id,
            "id_mascota": r.id_mascota,
            "mascota_nombre": m.nombre if m else None,
            "propietario_username": (
                owner.username if owner else (m.propietario if m else None)
            ),
            "propietario_nombre": owner.nombre if owner else None,
            "propietario_telefono": owner.telefono if owner else None,
            "fecha": r.fecha,
            "motivo": r.motivo,
            "veterinario": r.veterinario,
            "estado": _normalize_stored_estado(r.estado),
        }
    except HTTPException:
        raise
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Error al actualizar cita: {e}")


@router.delete("/{cita_id}")
async def cancelar_cita(cita_id: str, current_user=Depends(get_current_user_dep), db: Session = Depends(get_db)):
    """Cancelar (eliminar) una cita.

    Solo el propietario de la mascota o un administrador pueden cancelar la cita.
    """
    try:
        cid = _validate_uuid(cita_id, "cita_id")
        r = db.get(CitaORM, cid)
        if not r:
            raise HTTPException(status_code=404, detail="Cita no encontrada")
        mascota = db.get(MascotaORM, r.id_mascota)
        if current_user.role != "admin" and (
            not mascota or mascota.propietario != current_user.username
        ):
            raise HTTPException(
                status_code=403, detail="No autorizado para cancelar esta cita"
            )
        db.delete(r)
        db.commit()
        return {"message": "Cita cancelada exitosamente"}
    except HTTPException:
        raise
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Error al cancelar cita: {e}")
