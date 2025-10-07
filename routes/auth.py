from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from database import UsuarioORM, verify_password
from database.db import get_db
from sqlalchemy.orm import Session
from auth import create_access_token, oauth2_scheme

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = (
        db.query(UsuarioORM)
        .filter(UsuarioORM.username == form_data.username)
        .one_or_none()
    )
    if not user:
        raise HTTPException(status_code=400, detail="Usuario o clave incorrectos")
    if not verify_password(
        user.password_salt, user.password_hash, form_data.password
    ):
        raise HTTPException(status_code=400, detail="Usuario o clave incorrectos")
    token = create_access_token(
        {"sub": user.id, "username": user.username, "role": user.role}
    )
    return {"access_token": token, "token_type": "bearer"}
