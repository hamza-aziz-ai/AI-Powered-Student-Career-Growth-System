import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    refresh_token_expiry,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.user import UserRegister


class EmailAlreadyRegisteredError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class InvalidRefreshTokenError(Exception):
    pass


async def register_user(db: AsyncSession, data: UserRegister) -> User:
    email = data.email.lower()
    existing = await db.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise EmailAlreadyRegisteredError()

    user = User(email=email, hashed_password=hash_password(data.password), full_name=data.full_name)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User:
    user = await db.scalar(select(User).where(User.email == email.lower()))
    if user is None or not user.is_active or not verify_password(password, user.hashed_password):
        raise InvalidCredentialsError()
    return user


async def issue_token_pair(db: AsyncSession, user: User, user_agent: str | None = None) -> tuple[str, str]:
    access_token = create_access_token(subject=str(user.id))
    raw_refresh_token = generate_refresh_token()

    token_row = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(raw_refresh_token),
        expires_at=refresh_token_expiry(),
        user_agent=user_agent[:255] if user_agent else None,
    )
    db.add(token_row)
    await db.commit()
    return access_token, raw_refresh_token


async def rotate_refresh_token(
    db: AsyncSession, raw_refresh_token: str, user_agent: str | None = None
) -> tuple[str, str]:
    token_hash = hash_refresh_token(raw_refresh_token)
    token_row = await db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))

    if token_row is None:
        raise InvalidRefreshTokenError()

    now = datetime.now(timezone.utc)
    if token_row.revoked_at is not None:
        # Reuse of an already-rotated/revoked token indicates possible theft — revoke the
        # whole session family for this user rather than trusting the presented token.
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == token_row.user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        await db.commit()
        raise InvalidRefreshTokenError()

    if token_row.expires_at.replace(tzinfo=timezone.utc) < now:
        raise InvalidRefreshTokenError()

    user = await db.get(User, token_row.user_id)
    if user is None or not user.is_active:
        raise InvalidRefreshTokenError()

    new_access_token = create_access_token(subject=str(user.id))
    new_raw_refresh_token = generate_refresh_token()
    new_token_row = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(new_raw_refresh_token),
        expires_at=refresh_token_expiry(),
        user_agent=user_agent[:255] if user_agent else None,
    )
    db.add(new_token_row)
    await db.flush()

    token_row.revoked_at = now
    token_row.replaced_by_id = new_token_row.id
    await db.commit()

    return new_access_token, new_raw_refresh_token


async def revoke_refresh_token(db: AsyncSession, raw_refresh_token: str) -> None:
    token_hash = hash_refresh_token(raw_refresh_token)
    token_row = await db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    if token_row is not None and token_row.revoked_at is None:
        token_row.revoked_at = datetime.now(timezone.utc)
        await db.commit()


async def get_user_by_id(db: AsyncSession, user_id: str | uuid.UUID) -> User | None:
    return await db.get(User, user_id)
