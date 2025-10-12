from fastapi import APIRouter, HTTPException, Depends
from typing import List
from uuid import UUID
from datetime import datetime

from models import Receta, RecetaCreate, RecetaSummary
from models import RecetaUpdate
from database import (
    RecetaORM,
    RecetaLineaORM,
    CitaORM,
    MascotaORM,
    UsuarioORM,
    uuid_to_str,
)
from database.db import get_db
from sqlalchemy.orm import Session
from auth import get_current_user_dep, require_roles

"""
Rutas para gestión de recetas médicas.

Incluye creación, listado, consulta por cita/id, actualización completa y
parcial (PATCH). Control de acceso por roles y relación propietario-mascota.
"""

router = APIRouter(prefix="/recetas", tags=["recetas"])


@router.post("/", response_model=Receta, status_code=201)
async def crear_receta(
    receta: RecetaCreate,
    current_user=Depends(require_roles("veterinario", "admin")),
    db: Session = Depends(get_db),
):
    """Crear una nueva receta.

    Valida que la cita exista y que el veterinario autenticado pueda crear la
    receta para dicha cita. Si se incluyen líneas (medicamentos) se insertan
    como RecetaLineaORM.
    """
    data = receta.model_dump()
    try:
        cita = db.get(CitaORM, uuid_to_str(data["id_cita"]))
        if not cita:
            raise HTTPException(
                status_code=400, detail="La cita especificada no existe"
            )

        if (
            current_user.role == "veterinario"
            and cita.veterinario
            and cita.veterinario != current_user.username
        ):
            raise HTTPException(
                status_code=403,
                detail="No autorizado: la cita está asignada a otro veterinario",
            )

        mascota = db.get(MascotaORM, cita.id_mascota)
        if not mascota:
            raise HTTPException(
                status_code=400, detail="La mascota asociada a la cita no existe"
            )

        db_obj = RecetaORM(
            id_cita=uuid_to_str(data["id_cita"]),
            fecha_emision=data["fecha_emision"],
            veterinario=current_user.username,
            indicaciones=data.get("indicaciones"),
        )
        from database.db import set_audit_fields

        set_audit_fields(db_obj, current_user.id, creating=True)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        if data.get("lineas"):
            for l in data["lineas"]:
                rl = RecetaLineaORM(
                    id_receta=db_obj.id,
                    medicamento=l.get("medicamento"),
                    dosis=l.get("dosis"),
                    frecuencia=l.get("frecuencia"),
                    duracion=l.get("duracion"),
                )
                db.add(rl)
            db.commit()

        owner = None
        if mascota and mascota.propietario:
            owner = (
                db.query(UsuarioORM)
                .filter(UsuarioORM.username == mascota.propietario)
                .one_or_none()
            )

        return {
            "id_receta": db_obj.id,
            "id_cita": db_obj.id_cita,
            "id_mascota": cita.id_mascota,
            "mascota_nombre": mascota.nombre if mascota else None,
            "fecha_emision": db_obj.fecha_emision,
            "veterinario": db_obj.veterinario,
            "indicaciones": db_obj.indicaciones,
            "lineas": data.get("lineas"),
            "propietario_username": (
                owner.username if owner else (mascota.propietario if mascota else None)
            ),
            "propietario_nombre": owner.nombre if owner else None,
            "propietario_telefono": owner.telefono if owner else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[RecetaSummary])
async def listar_recetas(current_user=Depends(get_current_user_dep), db: Session = Depends(get_db)):
    """Listar recetas con control de acceso según rol.

    - cliente: solo recetas de sus mascotas
    - veterinario: solo recetas emitidas por él
    - admin: todas las recetas
    """
    try:
        rows = db.query(RecetaORM).all()
        resp = []
        for r in rows:
            cita = db.get(CitaORM, r.id_cita) if r.id_cita else None
            mascota = db.get(MascotaORM, cita.id_mascota) if cita else None
            if current_user.role == "cliente":
                if not mascota or mascota.propietario != current_user.username:
                    continue
            if current_user.role == "veterinario":
                if r.veterinario != current_user.username:
                    continue

            owner = None
            if mascota and mascota.propietario:
                owner = (
                    db.query(UsuarioORM)
                    .filter(UsuarioORM.username == mascota.propietario)
                    .one_or_none()
                )

            resp.append(
                {
                    "id_receta": r.id,
                    "id_cita": r.id_cita,
                    "id_mascota": mascota.id if mascota else None,
                    "mascota_nombre": mascota.nombre if mascota else None,
                    "fecha_emision": r.fecha_emision,
                    "veterinario": r.veterinario,
                    "propietario_username": (
                        owner.username
                        if owner
                        else (mascota.propietario if mascota else None)
                    ),
                    "propietario_nombre": owner.nombre if owner else None,
                    "propietario_telefono": owner.telefono if owner else None,
                }
            )
        return resp
    finally:
        pass


@router.get("/cita/{cita_id}", response_model=List[RecetaSummary])
async def obtener_recetas_por_cita(
    cita_id: str, current_user=Depends(get_current_user_dep), db: Session = Depends(get_db)
):
    """Obtener las recetas asociadas a una cita.

    Valida la existencia de la cita y comprueba permisos: cliente debe ser
    propietario de la mascota; veterinario debe estar asignado a la cita o
    ser admin.
    """
    try:
        cita_obj = db.get(CitaORM, str(cita_id))
        if not cita_obj:
            raise HTTPException(status_code=404, detail="Cita no encontrada")

        mascota = db.get(MascotaORM, cita_obj.id_mascota) if cita_obj else None
        if current_user.role == "cliente":
            if not mascota or mascota.propietario != current_user.username:
                raise HTTPException(
                    status_code=403,
                    detail="No autorizado para ver las recetas de esta cita",
                )
        if current_user.role == "veterinario":
            if cita_obj.veterinario and cita_obj.veterinario != current_user.username:
                raise HTTPException(
                    status_code=403,
                    detail="No autorizado para ver las recetas de esta cita",
                )

        rows = db.query(RecetaORM).filter(RecetaORM.id_cita == str(cita_id)).all()
        resp = []
        for r in rows:
            if (
                current_user.role == "veterinario"
                and r.veterinario != current_user.username
            ):
                continue

            owner = None
            if mascota and mascota.propietario:
                owner = (
                    db.query(UsuarioORM)
                    .filter(UsuarioORM.username == mascota.propietario)
                    .one_or_none()
                )
            resp.append(
                {
                    "id_receta": r.id,
                    "id_cita": r.id_cita,
                    "id_mascota": mascota.id if mascota else None,
                    "mascota_nombre": mascota.nombre if mascota else None,
                    "fecha_emision": r.fecha_emision,
                    "veterinario": r.veterinario,
                    "propietario_username": (
                        owner.username
                        if owner
                        else (mascota.propietario if mascota else None)
                    ),
                    "propietario_nombre": owner.nombre if owner else None,
                    "propietario_telefono": owner.telefono if owner else None,
                }
            )
        return resp
    finally:
        pass


@router.get("/{receta_id}", response_model=Receta)
async def obtener_receta(receta_id: str, current_user=Depends(get_current_user_dep), db: Session = Depends(get_db)):
    """Obtener una receta por id, incluyendo líneas.

    Se aplican reglas RBAC: cliente solo puede ver recetas de sus mascotas;
    veterinario solo puede ver sus propias recetas.
    """
    try:
        r = db.get(RecetaORM, str(receta_id))
        if not r:
            raise HTTPException(status_code=404, detail="Receta no encontrada")
        lineas = db.query(RecetaLineaORM).filter(RecetaLineaORM.id_receta == r.id).all()
        lineas_out = [
            {
                "medicamento": l.medicamento,
                "dosis": l.dosis,
                "frecuencia": l.frecuencia,
                "duracion": l.duracion,
            }
            for l in lineas
        ]
        cita = db.get(CitaORM, r.id_cita)
        mascota = db.get(MascotaORM, cita.id_mascota) if cita else None
        if current_user.role == "cliente":
            if not mascota or mascota.propietario != current_user.username:
                raise HTTPException(
                    status_code=403, detail="No autorizado para ver esta receta"
                )
        if (
            current_user.role == "veterinario"
            and r.veterinario != current_user.username
        ):
            raise HTTPException(
                status_code=403, detail="No autorizado para ver esta receta"
            )

        owner = None
        if mascota and mascota.propietario:
            owner = (
                db.query(UsuarioORM)
                .filter(UsuarioORM.username == mascota.propietario)
                .one_or_none()
            )

        return {
            "id_receta": r.id,
            "id_cita": r.id_cita,
            "id_mascota": cita.id_mascota if cita else None,
            "mascota_nombre": mascota.nombre if mascota else None,
            "fecha_emision": r.fecha_emision,
            "veterinario": r.veterinario,
            "indicaciones": r.indicaciones,
            "lineas": lineas_out,
            "propietario_username": (
                owner.username if owner else (mascota.propietario if mascota else None)
            ),
            "propietario_nombre": owner.nombre if owner else None,
            "propietario_telefono": owner.telefono if owner else None,
        }
    finally:
        pass


@router.put("/{receta_id}", response_model=Receta)
async def actualizar_receta(
    receta_id: str,
    receta_update: RecetaUpdate,
    current_user=Depends(require_roles("veterinario", "admin")),
    db: Session = Depends(get_db),
):
    """Actualizar una receta (PUT).

    No se permite cambiar id_cita. Si se actualizan líneas, se eliminan las
    existentes y se reinserta la nueva lista.
    """
    update_data = receta_update.model_dump(exclude_unset=True)
    try:
        r = db.get(RecetaORM, str(receta_id))
        if not r:
            raise HTTPException(status_code=404, detail="Receta no encontrada")
        if "id_cita" in update_data:
            raise HTTPException(
                status_code=400,
                detail="No está permitido actualizar id_cita mediante este endpoint",
            )

        if (
            current_user.role == "veterinario"
            and r.veterinario != current_user.username
        ):
            raise HTTPException(
                status_code=403, detail="No autorizado para modificar esta receta"
            )

        for field, value in update_data.items():
            if field == "lineas":
                db.query(RecetaLineaORM).filter(
                    RecetaLineaORM.id_receta == r.id
                ).delete()
                for l in value:
                    rl = RecetaLineaORM(
                        id_receta=r.id,
                        medicamento=l.get("medicamento"),
                        dosis=l.get("dosis"),
                        frecuencia=l.get("frecuencia"),
                        duracion=l.get("duracion"),
                    )
                    db.add(rl)
            else:
                setattr(r, field, value)

        if current_user.role == "veterinario":
            r.veterinario = current_user.username

        db.add(r)
        from database.db import set_audit_fields

        set_audit_fields(r, current_user.id, creating=False)
        db.commit()
        db.refresh(r)
        cita = db.get(CitaORM, r.id_cita)
        mascota = db.get(MascotaORM, cita.id_mascota) if cita else None
        lineas = db.query(RecetaLineaORM).filter(RecetaLineaORM.id_receta == r.id).all()
        lineas_out = [
            {
                "medicamento": l.medicamento,
                "dosis": l.dosis,
                "frecuencia": l.frecuencia,
                "duracion": l.duracion,
            }
            for l in lineas
        ]
        owner = None
        if mascota and mascota.propietario:
            owner = (
                db.query(UsuarioORM)
                .filter(UsuarioORM.username == mascota.propietario)
                .one_or_none()
            )
        return {
            "id_receta": r.id,
            "id_cita": r.id_cita,
            "id_mascota": cita.id_mascota if cita else None,
            "mascota_nombre": mascota.nombre if mascota else None,
            "fecha_emision": r.fecha_emision,
            "veterinario": r.veterinario,
            "indicaciones": r.indicaciones,
            "lineas": lineas_out,
            "propietario_username": (
                owner.username if owner else (mascota.propietario if mascota else None)
            ),
            "propietario_nombre": owner.nombre if owner else None,
            "propietario_telefono": owner.telefono if owner else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        pass


@router.patch("/{receta_id}", response_model=Receta)
async def patch_receta(
    receta_id: str,
    receta_update: RecetaUpdate,
    current_user=Depends(require_roles("veterinario", "admin")),
):
    """PATCH: proxy a PUT pero con merge parcial (exclude_unset).

    La implementación actual delega en `actualizar_receta`.
    """
    return await actualizar_receta(receta_id, receta_update, current_user)


@router.delete("/{receta_id}")
async def eliminar_receta(
    receta_id: str, current_user=Depends(require_roles("veterinario", "admin")), db: Session = Depends(get_db)
):
    try:
        r = db.get(RecetaORM, str(receta_id))
        if not r:
            raise HTTPException(status_code=404, detail="Receta no encontrada")
        # veterinario solo puede eliminar sus propias recetas
        if (
            current_user.role == "veterinario"
            and r.veterinario != current_user.username
        ):
            raise HTTPException(
                status_code=403, detail="No autorizado para eliminar esta receta"
            )
        db.query(RecetaLineaORM).filter(RecetaLineaORM.id_receta == r.id).delete()
        db.delete(r)
        db.commit()
        return {"message": "Receta eliminada exitosamente"}
    except HTTPException:
        raise
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
