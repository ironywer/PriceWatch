from fastapi import APIRouter, Depends, Request, Form
from pydantic import BaseModel, EmailStr, ValidationError
from sqlalchemy.orm import Session
from starlette.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.db.database import get_db
from app.models.user import User
from app.security import get_password_hash, verify_password, create_access_token
from app.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory="app/templates")


class _RegisterValidate(BaseModel):
    email: EmailStr


MIN_PASSWORD_LENGTH = 6
MAX_PASSWORD_LENGTH = 72


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@router.post("/register")
def register(
        request: Request,
        email: str = Form(...),
        password: str = Form(...),
        full_name: str | None = Form(None),
        db: Session = Depends(get_db)
):
    try:
        _RegisterValidate(email=email)
    except ValidationError:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Пожалуйста, укажите корректный email."},
            status_code=400,
        )
    if len(password) < MIN_PASSWORD_LENGTH:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": f"Пароль должен быть ≥ {MIN_PASSWORD_LENGTH} символов."},
            status_code=400,
        )

    if len(password.encode("utf-8")) > MAX_PASSWORD_LENGTH:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": f"Пароль слишком длинный. Максимум {MAX_PASSWORD_LENGTH} байт."},
            status_code=400,
        )

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Этот email уже используется"},
            status_code=400,
        )
    user = User(
        email=email,
        full_name=full_name,
        hashed_password=get_password_hash(password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return RedirectResponse(url="/auth/login", status_code=302)


@router.post("/login")
def login(
        request: Request,
        email: str = Form(...),
        password: str = Form(...),
        db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Неверный email или пароль"},
            status_code=400,
        )

    token = create_access_token(subject=user.id)

    resp = RedirectResponse(url="/auth/me", status_code=302)
    resp.set_cookie(
        key="access_token",
        value=f"Bearer {token}",
        httponly=True,
        samesite="lax",
        secure=False
    )
    return resp


@router.get("/logout")
def logout():
    resp = RedirectResponse(url="/auth/login")
    resp.delete_cookie("access_token")
    return resp


@router.get("/me", response_class=HTMLResponse)
def me(request: Request, current: User = Depends(get_current_user)):
    return templates.TemplateResponse(
        "me.html",
        {"request": request, "user": current}
    )
