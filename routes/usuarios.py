from fastapi import APIRouter, HTTPException, Depends
from typing import List
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from models import (
    Usuario,
    UsuarioCreate,
    Role,
    UsuarioUpdateResponse,
    UsuarioUpdateRequest,
)
from database import UsuarioORM, hash_password, verify_password
from database.db import get_db
from sqlalchemy.orm import Session
from auth import get_current_user_dep

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


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


@router.post("/", response_model=Usuario, status_code=201)
async def crear_usuario(payload: UsuarioCreate, db: Session = Depends(get_db)):
    """Crear usuario (username único). role opcional (cliente|veterinario)."""
    try:
        existing = (
            db.query(UsuarioORM)
            .filter(UsuarioORM.username == payload.username)
            .one_or_none()
        )
        if existing:
            raise HTTPException(status_code=400, detail="Username ya existe")
        new_id = str(uuid4())
        salt_hex, hash_hex = hash_password(payload.password)
        u = UsuarioORM(
            id=new_id,
            username=payload.username,
            nombre=payload.nombre,
            edad=payload.edad,
            telefono=payload.telefono,
            role=(payload.role.value if payload.role else "cliente"),
            password_salt=salt_hex,
            password_hash=hash_hex,
        )
        db.add(u)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=400, detail="Username ya existe")
        db.refresh(u)
        return {
            "id_usuario": u.id,
            "username": u.username,
            "nombre": u.nombre,
            "edad": u.edad,
            "telefono": u.telefono,
            "role": u.role,
            "fecha_creacion": u.fecha_creacion,
        }
    except HTTPException:
        raise
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[Usuario])
async def listar_usuarios(
    current_user=Depends(get_current_user_dep), db: Session = Depends(get_db)
):
    rows = db.query(UsuarioORM).all()
    return [
        {
            "id_usuario": r.id,
            "username": r.username,
            "nombre": r.nombre,
            "edad": r.edad,
            "telefono": r.telefono,
            "role": r.role,
            "fecha_creacion": r.fecha_creacion,
        }
        for r in rows
    ]


@router.get("/me", response_model=Usuario)
async def obtener_mi_usuario(
    current_user=Depends(get_current_user_dep), db: Session = Depends(get_db)
):
    """Obtener los datos del usuario autenticado."""
    r = db.get(UsuarioORM, current_user.id)
    if not r:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return {
        "id_usuario": r.id,
        "username": r.username,
        "nombre": r.nombre,
        "edad": r.edad,
        "telefono": r.telefono,
        "role": r.role,
        "fecha_creacion": r.fecha_creacion,
    }


@router.get("/{usuario_id}", response_model=Usuario)
async def obtener_usuario(
    usuario_id: str,
    current_user=Depends(get_current_user_dep),
    db: Session = Depends(get_db),
):
    uid = _validate_uuid(usuario_id, "usuario_id")
    r = db.get(UsuarioORM, uid)
    if not r:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return {
        "id_usuario": r.id,
        "username": r.username,
        "nombre": r.nombre,
        "edad": r.edad,
        "telefono": r.telefono,
        "role": r.role,
        "fecha_creacion": r.fecha_creacion,
    }


@router.put("/me", response_model=UsuarioUpdateResponse)
async def actualizar_mi_usuario(
    payload: UsuarioUpdateRequest,
    current_user=Depends(get_current_user_dep),
    db: Session = Depends(get_db),
):
    """Actualizar los 4 campos editables del usuario autenticado sin pasar id."""
    try:
        r = db.get(UsuarioORM, current_user.id)
        if not r:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        update_data = payload.model_dump(exclude_unset=True)
        if "username" in update_data:
            other = (
                db.query(UsuarioORM)
                .filter(
                    UsuarioORM.username == update_data["username"],
                    UsuarioORM.id != current_user.id,
                )
                .one_or_none()
            )
            if other:
                raise HTTPException(status_code=400, detail="Username ya en uso")
            r.username = update_data["username"]
        if "nombre" in update_data:
            r.nombre = update_data["nombre"]
        if "edad" in update_data:
            r.edad = update_data["edad"]
        if "telefono" in update_data:
            r.telefono = update_data["telefono"]
        db.add(r)
        db.commit()
        db.refresh(r)
        return {
            "username": r.username,
            "nombre": r.nombre,
            "edad": r.edad,
            "telefono": r.telefono,
        }
    except HTTPException:
        raise
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/me")
async def eliminar_mi_usuario(
    current_user=Depends(get_current_user_dep), db: Session = Depends(get_db)
):
    """Eliminar la cuenta del usuario autenticado."""
    try:
        r = db.get(UsuarioORM, current_user.id)
        if not r:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        db.delete(r)
        db.commit()
        return {"message": "Usuario eliminado exitosamente"}
    except HTTPException:
        raise
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))
