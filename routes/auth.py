from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from pydantic import BaseModel
from database import UsuarioORM, verify_password
from database.db import get_db
from sqlalchemy.orm import Session
from auth import create_access_token, oauth2_scheme

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    """Request model for JSON login."""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Response model for login with user data."""
    access_token: str
    token_type: str
    usuario: dict


@router.post("/login", response_model=LoginResponse)
def login_with_json(login_data: LoginRequest, db: Session = Depends(get_db)):
    """
    Login endpoint that accepts JSON and returns user data.
    Compatible with Blazor frontend.
    """
    user = (
        db.query(UsuarioORM)
        .filter(UsuarioORM.username == login_data.username)
        .one_or_none()
    )
    if not user:
        raise HTTPException(status_code=400, detail="Usuario o contraseña incorrectos")
    
    # Verificar que el usuario no esté eliminado (soft delete)
    if user.is_deleted:
        raise HTTPException(
            status_code=403,
            detail="Esta cuenta ha sido desactivada. Contacte al administrador para restaurarla."
        )
    
    if not verify_password(
        user.password_salt, user.password_hash, login_data.password
    ):
        raise HTTPException(status_code=400, detail="Usuario o contraseña incorrectos")
    
    token = create_access_token(
        {"sub": user.id, "username": user.username, "role": user.role}
    )
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "usuario": {
            "idUsuario": user.id,
            "username": user.username,
            "nombre": user.nombre,
            "edad": user.edad,
            "telefono": user.telefono,
            "role": user.role,
            "fechaCreacion": user.fecha_creacion.isoformat() if user.fecha_creacion else None,
            "isDeleted": user.is_deleted
        }
    }


@router.post("/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    OAuth2 compatible token endpoint (form-data).
    Used by Swagger UI and OAuth2 clients.
    """
    user = (
        db.query(UsuarioORM)
        .filter(UsuarioORM.username == form_data.username)
        .one_or_none()
    )
    if not user:
        raise HTTPException(status_code=400, detail="Usuario o clave incorrectos")
    
    # Verificar que el usuario no esté eliminado (soft delete)
    if user.is_deleted:
        raise HTTPException(
            status_code=403,
            detail="Esta cuenta ha sido desactivada. Contacte al administrador para restaurarla."
        )
    
    if not verify_password(
        user.password_salt, user.password_hash, form_data.password
    ):
        raise HTTPException(status_code=400, detail="Usuario o clave incorrectos")
    token = create_access_token(
        {"sub": user.id, "username": user.username, "role": user.role}
    )
    return {"access_token": token, "token_type": "bearer"}
