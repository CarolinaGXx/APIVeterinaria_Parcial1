import logging
from datetime import datetime, timedelta
from typing import Optional

from jose import jwt, JWTError, ExpiredSignatureError
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status

from database import UsuarioORM
from database.db import get_db
from sqlalchemy.orm import Session
from config import settings

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token including standard claims (sub, iat, exp, iss, aud).

    `data` should include an identifier under the "sub" key (user id).
    """
    to_encode = data.copy()
    now = datetime.utcnow()
    expire = now + (expires_delta or timedelta(minutes=settings.jwt_access_minutes))
    # Ensure standard claims
    if "sub" not in to_encode:
        raise ValueError("`data` must include `sub` (subject / user id)")
    to_encode.update({
        "exp": expire,
        "iat": now,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience
    })
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token.

    Validates signature, expiration, issuer and audience. Raises HTTPException(401)
    for any invalid token state.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
        )
        return payload
    except ExpiredSignatureError:
        logger.info("Token expirado")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expirado")
    except JWTError as e:
        logger.info(f"Token inválido o claim mismatch: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido o expirado")


def get_current_user(token: str = None, db: Session | None = None):
    """Helper no-dependencia que devuelve UsuarioORM o None.

    Decodifica el token usando `decode_token` para aprovechar la validación de claims.
    """
    if token is None:
        return None
    payload = decode_token(token)
    user_id = payload.get("sub")
    if not user_id:
        return None
    if db is None:
        from database import SessionLocal

        db_local = SessionLocal()
        try:
            return db_local.get(UsuarioORM, str(user_id))
        finally:
            db_local.close()
    return db.get(UsuarioORM, str(user_id))


def get_current_user_dep(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = decode_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido: sub faltante")
    user = db.get(UsuarioORM, str(user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado")
    return user


def require_roles(*allowed_roles):
    """Dependency factory that ensures the current user has one of the allowed roles.

    Usage in route: current_user = Depends(require_roles('veterinario', 'admin'))
    """

    def _dependency(current_user=Depends(get_current_user_dep)):
        if not current_user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Autenticación requerida")
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permisos insuficientes")
        return current_user

    return _dependency
