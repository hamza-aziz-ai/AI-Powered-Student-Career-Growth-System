import jwt
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.security import decode_access_token


def _rate_limit_key(request: Request) -> str:
    """Rate-limits authenticated requests per-user (so one parent can't starve
    another's quota) and falls back to per-IP for unauthenticated requests like
    /auth/login and /auth/register, where no user identity exists yet."""
    token = request.cookies.get("access_token")
    if token:
        try:
            payload = decode_access_token(token)
        except jwt.PyJWTError:
            payload = {}
        subject = payload.get("sub")
        if subject:
            return f"user:{subject}"
    return get_remote_address(request)


limiter = Limiter(key_func=_rate_limit_key)
