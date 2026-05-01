"""Sistema de autenticación y autorización."""

from datetime import datetime, timedelta, timezone
from typing import Literal

import jwt
from fastapi import HTTPException, Header
from pydantic import BaseModel

# Cambiar esto en producción
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 horas


class TokenData(BaseModel):
    """Datos del token JWT."""
    username: str
    user_type: Literal["admin", "user"]
    exp: datetime


class UserCredentials(BaseModel):
    """Credenciales de usuario."""
    username: str
    password: str
    user_type: Literal["admin", "user"]


# Base de datos simulada de usuarios (en producción usar base de datos real)
USERS_DB = {
    "admin": {
        "password": "Germany10",
        "user_type": "admin",
    },
    "user": {
        "password": "user123",
        "user_type": "user",
    },
}


def authenticate_user(username: str, password: str) -> TokenData | None:
    """Autenticar usuario y retornar datos del token."""
    user = USERS_DB.get(username)
    if not user or user["password"] != password:
        return None
    
    return TokenData(
        username=username,
        user_type=user["user_type"],
        exp=datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_access_token(token_data: TokenData) -> str:
    """Crear JWT token."""
    payload = {
        "username": token_data.username,
        "user_type": token_data.user_type,
        "exp": token_data.exp,
    }
    encoded_jwt = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> TokenData | None:
    """Verificar y decodificar JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("username")
        user_type: str = payload.get("user_type")
        if username is None or user_type is None:
            return None
        return TokenData(
            username=username,
            user_type=user_type,
            exp=datetime.fromtimestamp(payload.get("exp")),
        )
    except jwt.InvalidTokenError:
        return None


def is_admin(token_data: TokenData) -> bool:
    """Verificar si el usuario es administrador."""
    return token_data.user_type == "admin"


async def get_current_user(authorization: str | None = Header(None)) -> TokenData:
    """Extraer y verificar el token JWT del header Authorization."""
    if not authorization:
        raise HTTPException(status_code=401, detail="No autorizado")
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Esquema de autenticación inválido")
    except ValueError:
        raise HTTPException(status_code=401, detail="Formato de autorización inválido")
    
    token_data = verify_token(token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")
    
    return token_data
