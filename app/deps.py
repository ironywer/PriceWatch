from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from jose import JWTError

from app.db.database import get_db
from app.models.user import User
from app.security import decode_access_token


def _extract_bearer_from_header_or_cookie(request: Request) -> str | None:
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        return auth.split(" ", 1)[1]
    cookie = request.cookies.get("access_token")
    if cookie and cookie.startswith("Bearer "):
        return cookie.split(" ", 1)[1]
    return None


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = _extract_bearer_from_header_or_cookie(request)
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exc
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    user = db.query(User).get(int(user_id))
    if not user:
        raise credentials_exc
    return user


def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        return get_current_user(request=request, db=db)
    except Exception:
        return None
