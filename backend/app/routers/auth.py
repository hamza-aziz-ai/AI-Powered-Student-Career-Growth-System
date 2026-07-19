from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.dependencies.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.user import UserLogin, UserRead, UserRegister
from app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()

_ACCESS_COOKIE = "access_token"
_REFRESH_COOKIE = "refresh_token"


def _cookie_kwargs(path: str = "/") -> dict:
    return {
        "httponly": True,
        "secure": settings.environment != "development",
        "samesite": "strict",
        "path": path,
    }


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(
        _ACCESS_COOKIE,
        access_token,
        max_age=settings.access_token_expire_minutes * 60,
        **_cookie_kwargs(path="/"),
    )
    response.set_cookie(
        _REFRESH_COOKIE,
        refresh_token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        **_cookie_kwargs(path="/api/auth"),
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(_ACCESS_COOKIE, path="/")
    response.delete_cookie(_REFRESH_COOKIE, path="/api/auth")


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/hour")
async def register(data: UserRegister, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    try:
        user = await auth_service.register_user(db, data)
    except auth_service.EmailAlreadyRegisteredError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    access_token, refresh_token = await auth_service.issue_token_pair(db, user, request.headers.get("user-agent"))
    _set_auth_cookies(response, access_token, refresh_token)
    return user


@router.post("/login", response_model=UserRead)
@limiter.limit("5/minute")
async def login(data: UserLogin, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    try:
        user = await auth_service.authenticate_user(db, data.email, data.password)
    except auth_service.InvalidCredentialsError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    access_token, refresh_token = await auth_service.issue_token_pair(db, user, request.headers.get("user-agent"))
    _set_auth_cookies(response, access_token, refresh_token)
    return user


@router.post("/refresh", response_model=MessageResponse)
async def refresh(
    request: Request,
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    if refresh_token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        new_access_token, new_refresh_token = await auth_service.rotate_refresh_token(
            db, refresh_token, request.headers.get("user-agent")
        )
    except auth_service.InvalidRefreshTokenError:
        _clear_auth_cookies(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired, please log in again")

    _set_auth_cookies(response, new_access_token, new_refresh_token)
    return MessageResponse(message="Token refreshed")


@router.post("/logout", response_model=MessageResponse)
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    if refresh_token is not None:
        await auth_service.revoke_refresh_token(db, refresh_token)
    _clear_auth_cookies(response)
    return MessageResponse(message="Logged out")


@router.get("/me", response_model=UserRead)
async def me(current_user: User = Depends(get_current_user)):
    return current_user
