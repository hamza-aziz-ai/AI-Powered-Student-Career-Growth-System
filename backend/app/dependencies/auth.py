import uuid

import jwt
from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User

_CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
)


async def get_current_user(
    access_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if access_token is None:
        raise _CREDENTIALS_ERROR

    try:
        payload = decode_access_token(access_token)
    except jwt.PyJWTError:
        raise _CREDENTIALS_ERROR

    if payload.get("type") != "access":
        raise _CREDENTIALS_ERROR

    subject = payload.get("sub")
    if subject is None:
        raise _CREDENTIALS_ERROR

    try:
        user_id = uuid.UUID(subject)
    except ValueError:
        raise _CREDENTIALS_ERROR

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise _CREDENTIALS_ERROR

    return user
