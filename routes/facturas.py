"""Rutas relacionadas con facturas.

Este módulo expone los endpoints para crear, listar, actualizar, marcar pagadas,
anular y eliminar facturas. Las funciones contienen docstrings que describen su
comportamiento, reglas de negocio y posibles errores HTTP. Los comentarios en
línea han sido convertidos a docstrings donde aportaban información útil para la
API. No deben quedar comentarios explicativos en línea en este archivo.
"""

from fastapi import APIRouter, HTTPException, Query, Header, Depends
from typing import List, Optional
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum as _PyEnum

from models import (
    Factura,
    FacturaCreate,
    FacturaUpdate,
    EstadoFactura,
    TipoServicio,
    EstadoCita,
)
from database import (
    FacturaORM,
    CitaORM,
    MascotaORM,
    generar_numero_factura_uuid,
    uuid_to_str,
    UsuarioORM,
)
from database.db import get_db
from sqlalchemy.orm import Session
from auth import get_current_user_dep, require_roles


router = APIRouter(prefix="/facturas", tags=["facturas"])


def _enum_to_value(v):
    """Devuelve el valor subyacente para las instancias de Enum.

    Este asistente acepta una instancia de Enum o un valor
    sin procesar; si se proporciona una Enum, se devuelve
    el atributo de valor; de lo contrario, la entrada se
    devuelve sin cambios. Se utiliza para normalizar las
    entradas de Pydantic/Enum al almacenarlas en una base de datos.
    """
    if isinstance(v, _PyEnum):
        return v.value
    return v


def _normalize_stored_tipo_servicio(s: str):
    """Normaliza los valores almacenados de 'tipo_servicio'.

        Algunos valores se almacenan con el nombre de la clase de
    enumeración como prefijo (p. ej., "TipoServicio.consulta_general").
    Esta función elimina el prefijo y devuelve solo la parte
    significativa después del punto. Si la entrada es "Ninguno",
    se devuelve sin cambios.
    """
    if s is None:
        return s
    if isinstance(s, str) and "." in s:
        return s.split(".", 1)[1]
    return s


def _validate_uuid(id_str: str, name: str) -> str:
    """Valida que una cadena sea un UUID válido.

    Genera HTTPException(400) si el valor no es un UUID válido.
    Devuelve la cadena original si la operación es correcta.
    """
    try:
        UUID(str(id_str))
        return str(id_str)
    except Exception:
        raise HTTPException(
            status_code=400, detail=f"{name} inválido: debe ser un UUID"
        )


@router.post("/", response_model=Factura, status_code=201)
async def crear_factura(
    factura: FacturaCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("veterinario", "admin")),
):
    """Crear una nueva factura y guardarla en la base de datos.

    Proceso resumido:
    - Verifica que el usuario autenticado exista y tenga rol de veterinario (o admin).
    - Valida que la `cita` referenciada exista y que no tenga ya una factura asociada.
    - Si la cita pertenece a otro veterinario y el usuario actual es veterinario, rechaza la operación.
    - Marca la cita como completada y calcula el total de la factura.
    - Genera un UUID y un número de factura único antes del INSERT.
    - Rellena los campos de auditoría usando `set_audit_fields`.

    Errores posibles:
    - 400: cita inexistente o ya facturada, o el usuario autenticado no es un veterinario válido.
    - 403: intento de facturar una cita asignada a otro veterinario.
    - 500: errores inesperados (se hace rollback en caso de fallo durante la transacción).
    """
    data = factura.model_dump()
    try:
        usuario_audit = current_user

        vet = db.get(UsuarioORM, usuario_audit.id)
        if not vet or vet.role != "veterinario":
            raise HTTPException(
                status_code=400,
                detail="Usuario autenticado no es un veterinario válido",
            )

        cita = db.get(CitaORM, str(data["id_cita"]))
        if not cita:
            raise HTTPException(
                status_code=400, detail="La cita especificada no existe"
            )

        existing = (
            db.query(FacturaORM)
            .filter(FacturaORM.id_cita == str(data["id_cita"]))
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Ya existe una factura asociada a la cita especificada",
            )

        if (
            usuario_audit.role == "veterinario"
            and cita.veterinario
            and cita.veterinario != usuario_audit.username
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

        cita.estado = EstadoCita.completada.value
        db.add(cita)
        db.commit()

        total = round(
            (data["valor_servicio"] - data["descuento"]) * (1 + data["iva"] / 100), 2
        )

        factura_id = str(uuid4())
        numero_factura = generar_numero_factura_uuid(factura_id)

        db_obj = FacturaORM(
            id=factura_id,
            numero_factura=numero_factura,
            id_mascota=uuid_to_str(mascota.id),
            id_cita=uuid_to_str(data.get("id_cita")),
            fecha_factura=datetime.now(),
            tipo_servicio=_enum_to_value(data["tipo_servicio"]),
            descripcion=data["descripcion"],
            veterinario=vet.username,
            valor_servicio=data["valor_servicio"],
            iva=data["iva"],
            descuento=data["descuento"],
            estado=EstadoFactura.pendiente.value,
            total=total,
        )

        from database.db import set_audit_fields

        set_audit_fields(db_obj, usuario_audit.id, creating=True)

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        # Try to include propietario (owner) details in the POST response,
        # for parity with the GET endpoints which enrich the response with
        # propietario_username, propietario_nombre and propietario_telefono.
        owner = None
        if mascota and getattr(mascota, "propietario", None):
            owner = (
                db.query(UsuarioORM)
                .filter(UsuarioORM.username == mascota.propietario)
                .one_or_none()
            )

        mascota_nombre = mascota.nombre if mascota else None

        return {
            "id_factura": db_obj.id,
            "numero_factura": db_obj.numero_factura,
            "id_mascota": db_obj.id_mascota,
            "mascota_nombre": mascota_nombre,
            "propietario_username": (owner.username if owner else (mascota.propietario if mascota else None)),
            "propietario_nombre": owner.nombre if owner else None,
            "propietario_telefono": owner.telefono if owner else None,
            "id_cita": db_obj.id_cita,
            "fecha_factura": db_obj.fecha_factura,
            "tipo_servicio": _normalize_stored_tipo_servicio(db_obj.tipo_servicio),
            "descripcion": db_obj.descripcion,
            "veterinario": db_obj.veterinario,
            "valor_servicio": db_obj.valor_servicio,
            "iva": db_obj.iva,
            "descuento": db_obj.descuento,
            "estado": db_obj.estado,
            "total": db_obj.total,
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


@router.get("/", response_model=List[Factura])
async def obtener_facturas(
    estado: Optional[EstadoFactura] = Query(
        None, description="Filtrar por estado de factura"
    ),
    tipo_servicio: Optional[TipoServicio] = Query(
        None, description="Filtrar por tipo de servicio"
    ),
    veterinario: Optional[str] = Query(None, description="Filtrar por veterinario"),
    current_user=Depends(get_current_user_dep),
    db: Session = Depends(get_db),
):
    """Obtener lista de facturas con filtros opcionales.

    Reglas por rol:
    - Clientes: muestran solo facturas de sus mascotas.
    - Veterinarios: muestran solo facturas cuyo campo `veterinario` coincide con su username.
    - Admin: ve todas las facturas.

    El endpoint carga datos adicionales (mascotas y propietarios) para enriquecer
    la respuesta y devolver nombres/telefonos cuando están disponibles.
    """
    try:
        q = db.query(FacturaORM)
        if estado:
            q = q.filter(FacturaORM.estado == estado.value)
        if tipo_servicio:
            q = q.filter(FacturaORM.tipo_servicio == _enum_to_value(tipo_servicio))
        if veterinario:
            q = q.filter(FacturaORM.veterinario.ilike(f"%{veterinario}%"))

        if current_user.role == "cliente":

            q = q.join(MascotaORM, FacturaORM.id_mascota == MascotaORM.id).filter(
                MascotaORM.propietario == current_user.username
            )
        elif current_user.role == "veterinario":
            q = q.filter(FacturaORM.veterinario == current_user.username)

        resultados = q.all()

        mascota_ids = list({r.id_mascota for r in resultados})
        mascotas = []
        mascotas_map = {}
        usuarios_map = {}
        if mascota_ids:
            mascotas = db.query(MascotaORM).filter(MascotaORM.id.in_(mascota_ids)).all()
            mascotas_map = {m.id: m for m in mascotas}
            propietarios = list({m.propietario for m in mascotas if m.propietario})
            if propietarios:
                usuarios = (
                    db.query(UsuarioORM)
                    .filter(UsuarioORM.username.in_(propietarios))
                    .all()
                )
                usuarios_map = {u.username: u for u in usuarios}

        resp = []
        for r in resultados:
            m = mascotas_map.get(r.id_mascota)
            owner = None
            if m and m.propietario:
                owner = usuarios_map.get(m.propietario)
            resp.append(
                {
                    "id_factura": r.id,
                    "numero_factura": r.numero_factura,
                    "id_mascota": r.id_mascota,
                    "mascota_nombre": m.nombre if m else None,
                    "propietario_username": (
                        owner.username if owner else (m.propietario if m else None)
                    ),
                    "propietario_nombre": owner.nombre if owner else None,
                    "propietario_telefono": owner.telefono if owner else None,
                    "id_cita": r.id_cita,
                    "fecha_factura": r.fecha_factura,
                    "tipo_servicio": _normalize_stored_tipo_servicio(r.tipo_servicio),
                    "descripcion": r.descripcion,
                    "veterinario": r.veterinario,
                    "valor_servicio": r.valor_servicio,
                    "iva": r.iva,
                    "descuento": r.descuento,
                    "estado": r.estado,
                    "total": r.total,
                }
            )
        return resp
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener facturas: {e}")
    finally:
        pass


@router.get("/{factura_id}", response_model=Factura)
async def obtener_factura(
    factura_id: str,
    current_user=Depends(get_current_user_dep),
    db: Session = Depends(get_db),
):
    """Obtener una factura específica por ID.

    Verificaciones realizadas:
    - Validación del UUID del parámetro `factura_id`.
    - Control de acceso: clientes solo pueden ver facturas de sus mascotas;
    veterinarios solo pueden ver facturas donde ellos son el veterinario.
    """
    try:
        fid = _validate_uuid(factura_id, "factura_id")
        r = db.get(FacturaORM, fid)
        if not r:
            raise HTTPException(status_code=404, detail="Factura no encontrada")
        m = db.get(MascotaORM, r.id_mascota)

        if current_user.role == "cliente":
            if not m or m.propietario != current_user.username:
                raise HTTPException(
                    status_code=403, detail="No autorizado para ver esta factura"
                )

        if current_user.role == "veterinario":
            if r.veterinario != current_user.username:
                raise HTTPException(
                    status_code=403, detail="No autorizado para ver esta factura"
                )

        owner = None
        if m and m.propietario:
            owner = (
                db.query(UsuarioORM)
                .filter(UsuarioORM.username == m.propietario)
                .one_or_none()
            )

        return {
            "id_factura": r.id,
            "numero_factura": r.numero_factura,
            "id_mascota": r.id_mascota,
            "mascota_nombre": m.nombre if m else None,
            "propietario_username": (
                owner.username if owner else (m.propietario if m else None)
            ),
            "propietario_nombre": owner.nombre if owner else None,
            "propietario_telefono": owner.telefono if owner else None,
            "id_cita": r.id_cita,
            "fecha_factura": r.fecha_factura,
            "tipo_servicio": _normalize_stored_tipo_servicio(r.tipo_servicio),
            "descripcion": r.descripcion,
            "veterinario": r.veterinario,
            "valor_servicio": r.valor_servicio,
            "iva": r.iva,
            "descuento": r.descuento,
            "estado": r.estado,
            "total": r.total,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener la factura: {e}")
    finally:
        pass


from fastapi import APIRouter as _APIRouter

mascotas_facturas_router = _APIRouter(prefix="/mascotas", tags=["mascotas-facturas"])


@mascotas_facturas_router.get("/{mascota_id}/facturas", response_model=List[Factura])
async def obtener_facturas_mascota(
    mascota_id: UUID,
    current_user=Depends(get_current_user_dep),
    db: Session = Depends(get_db),
):
    """Obtener todas las facturas de una mascota específica.

    Control de acceso:
    - Clientes: sólo pueden ver facturas de mascotas que les pertenecen.
    - Veterinarios: pueden ver sólo facturas donde sean el veterinario responsable.

    La función devuelve una lista enriquecida con datos del propietario cuando
    están disponibles.
    """
    try:
        resultados = (
            db.query(FacturaORM).filter(FacturaORM.id_mascota == str(mascota_id)).all()
        )
        resp = []

        mascota_obj = db.get(MascotaORM, str(mascota_id))
        if current_user.role == "cliente":
            if not mascota_obj or mascota_obj.propietario != current_user.username:
                raise HTTPException(
                    status_code=403,
                    detail="No autorizado para ver las facturas de esta mascota",
                )

        if current_user.role == "veterinario":
            resultados = [
                r for r in resultados if r.veterinario == current_user.username
            ]

        owner = None
        if mascota_obj and mascota_obj.propietario:
            owner = (
                db.query(UsuarioORM)
                .filter(UsuarioORM.username == mascota_obj.propietario)
                .one_or_none()
            )

        for r in resultados:
            m = db.get(MascotaORM, r.id_mascota)
            resp.append(
                {
                    "id_factura": r.id,
                    "numero_factura": r.numero_factura,
                    "id_mascota": r.id_mascota,
                    "mascota_nombre": m.nombre if m else None,
                    "propietario_username": (
                        owner.username if owner else (m.propietario if m else None)
                    ),
                    "propietario_nombre": owner.nombre if owner else None,
                    "propietario_telefono": owner.telefono if owner else None,
                    "id_cita": r.id_cita,
                    "fecha_factura": r.fecha_factura,
                    "tipo_servicio": _normalize_stored_tipo_servicio(r.tipo_servicio),
                    "descripcion": r.descripcion,
                    "veterinario": r.veterinario,
                    "valor_servicio": r.valor_servicio,
                    "iva": r.iva,
                    "descuento": r.descuento,
                    "estado": r.estado,
                    "total": r.total,
                }
            )
        return resp
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al obtener las facturas de la mascota: {e}"
        )
    finally:
        pass


@router.put("/{factura_id}", response_model=Factura)
async def actualizar_factura(
    factura_id: str,
    factura_update: FacturaUpdate,
    current_user=Depends(require_roles("veterinario", "admin")),
    db: Session = Depends(get_db),
):
    """Actualizar información de una factura"""
    update_data = factura_update.model_dump(exclude_unset=True)
    try:
        fid = _validate_uuid(factura_id, "factura_id")
        r = db.get(FacturaORM, fid)
        if not r:
            raise HTTPException(status_code=404, detail="Factura no encontrada")

        if r.estado == EstadoFactura.pagada.value:
            raise HTTPException(
                status_code=400, detail="No se puede modificar una factura pagada"
            )

        if "id_mascota" in update_data or "id_cita" in update_data:
            raise HTTPException(
                status_code=400,
                detail="No está permitido actualizar id_mascota ni id_cita mediante este endpoint",
            )

        for field, value in update_data.items():

            if isinstance(value, _PyEnum):
                setattr(r, field, value.value)
            else:
                setattr(r, field, value)

        if any(f in update_data for f in ["valor_servicio", "iva", "descuento"]):
            r.total = round((r.valor_servicio - r.descuento) * (1 + r.iva / 100), 2)

        if current_user.role == "veterinario":
            r.veterinario = current_user.username

        usuario_audit = current_user
        from database.db import set_audit_fields

        set_audit_fields(r, usuario_audit.id, creating=False)
        db.add(r)
        db.commit()
        db.refresh(r)
        m = db.get(MascotaORM, r.id_mascota)
        return {
            "id_factura": r.id,
            "numero_factura": r.numero_factura,
            "id_mascota": r.id_mascota,
            "mascota_nombre": m.nombre if m else None,
            "id_cita": r.id_cita,
            "fecha_factura": r.fecha_factura,
            "tipo_servicio": _normalize_stored_tipo_servicio(r.tipo_servicio),
            "descripcion": r.descripcion,
            "veterinario": r.veterinario,
            "valor_servicio": r.valor_servicio,
            "iva": r.iva,
            "descuento": r.descuento,
            "estado": r.estado,
            "total": r.total,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al actualizar la factura: {e}"
        )
    finally:
        pass


@router.patch("/{factura_id}/pagar")
async def marcar_factura_pagada(
    factura_id: UUID,
    current_user=Depends(require_roles("veterinario", "admin")),
    db: Session = Depends(get_db),
):
    """Marcar una factura como pagada"""
    try:
        r = db.get(FacturaORM, str(factura_id))
        if not r:
            raise HTTPException(status_code=404, detail="Factura no encontrada")
        if r.estado == EstadoFactura.pagada.value:
            raise HTTPException(
                status_code=400, detail="La factura ya est\u00e1 pagada"
            )
        if r.estado == EstadoFactura.anulada.value:
            raise HTTPException(
                status_code=400, detail="No se puede pagar una factura anulada"
            )

        usuario_audit = current_user
        r.estado = EstadoFactura.pagada.value
        from database.db import set_audit_fields

        set_audit_fields(r, usuario_audit.id, creating=False)
        db.add(r)
        db.commit()
        db.refresh(r)
        m = db.get(MascotaORM, r.id_mascota)
        return {
            "message": f"Factura {r.numero_factura} marcada como pagada",
            "factura": {
                "id_factura": r.id,
                "numero_factura": r.numero_factura,
                "id_mascota": r.id_mascota,
                "mascota_nombre": m.nombre if m else None,
                "estado": r.estado,
                "total": r.total,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al marcar la factura como pagada: {e}"
        )
    finally:
        pass


@router.patch("/{factura_id}/anular")
async def anular_factura(
    factura_id: UUID,
    current_user=Depends(require_roles("veterinario", "admin")),
    db: Session = Depends(get_db),
):
    """Anular una factura"""
    try:
        r = db.get(FacturaORM, str(factura_id))
        if not r:
            raise HTTPException(status_code=404, detail="Factura no encontrada")
        if r.estado == EstadoFactura.pagada.value:
            raise HTTPException(
                status_code=400, detail="No se puede anular una factura pagada"
            )
        usuario_audit = current_user
        r.estado = EstadoFactura.anulada.value
        from database.db import set_audit_fields

        set_audit_fields(r, usuario_audit.id, creating=False)
        db.add(r)
        db.commit()
        db.refresh(r)
        m = db.get(MascotaORM, r.id_mascota)
        return {
            "message": f"Factura {r.numero_factura} anulada",
            "factura": {
                "id_factura": r.id,
                "numero_factura": r.numero_factura,
                "id_mascota": r.id_mascota,
                "mascota_nombre": m.nombre if m else None,
                "estado": r.estado,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al anular la factura: {e}")
    finally:
        pass


@router.delete("/{factura_id}")
async def eliminar_factura(
    factura_id: str,
    current_user=Depends(require_roles("veterinario", "admin")),
    db: Session = Depends(get_db),
):
    try:
        fid = _validate_uuid(factura_id, "factura_id")
        r = db.get(FacturaORM, fid)
        if not r:
            raise HTTPException(status_code=404, detail="Factura no encontrada")

        if (
            current_user.role == "veterinario"
            and r.veterinario != current_user.username
        ):
            raise HTTPException(
                status_code=403, detail="No autorizado para eliminar esta factura"
            )
        db.delete(r)
        db.commit()
        return {"message": "Factura eliminada exitosamente"}
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
