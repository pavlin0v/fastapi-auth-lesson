from enum import verify

from datetime import datetime, timedelta, UTC
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError
from fastapi import HTTPException, Depends
from starlette import status

from .database import get_user
from duroveswall.config import get_settings
from duroveswall.models import User
from duroveswall.db import get_session
from duroveswall.schemas.auth.token import TokenData


def create_access_token(
        data: dict,
        expires_delta: timedelta | None = None,
):
    settings = get_settings()
    to_ecode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_ecode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_ecode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

async def authenticate_user(
        session: AsyncSession,
        username: str,
        password: str
) -> User | None:
    user = await get_user(session, username)
    if not user:
        return None
    if not verify_password(password, user.password):
        return None
    return  user

def verify_password(
    plain_password: str,
    hashed_password: str,
):
    pwd_context = get_settings().PWD_CONTEXT
    return pwd_context.verify(plain_password, hashed_password)

async def get_current_user(
        session: AsyncSession = Depends(get_session),
        token: str = Depends(get_settings().OAUTH2_SCHEME),
) -> User:
    credentials_expcetion = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )
    try:
        payload = jwt.decode(token, get_settings().SECRET_KEY, algorithms=[get_settings().ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_expcetion
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_expcetion
    user = await get_user(session, token_data.username)
    if user is None:
        raise credentials_expcetion
    return user