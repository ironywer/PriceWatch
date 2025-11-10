from fastapi import APIRouter, Depends, Request, HTTPException, Form
from fastapi.responses import HTMLResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette import status
from starlette.responses import RedirectResponse
from starlette.templating import Jinja2Templates

from app.db.database import get_db
from app.models.wishlist import Wishlist
from app.models.user import User
from app.deps import get_current_user

router = APIRouter(prefix="/wishlist")
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def view_wishlist(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    items = (
        db.query(Wishlist)
        .filter(Wishlist.owner_id == current_user.id)
        .order_by(Wishlist.id.desc())
        .all()
    )

    return templates.TemplateResponse(
        request,
        "wishlist.html",
        {"items": items, "user": current_user},
    )


@router.post("/add")
def add_game(
    request: Request,
    steam_app_id: int = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    exists = (
        db.query(Wishlist)
        .filter(Wishlist.owner_id == current_user.id,
                Wishlist.steam_app_id == steam_app_id)
        .first()
    )
    if exists:

        items = (
            db.query(Wishlist)
            .filter(Wishlist.owner_id == current_user.id)
            .order_by(Wishlist.id.desc())
            .all()
        )
        return templates.TemplateResponse(
            request,
            "wishlist.html",
            {"items": items, "user": current_user, "error": "Игра уже в вишлисте"},
            status_code=400,
        )

    item = Wishlist(steam_app_id=steam_app_id, owner_id=current_user.id)
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()

        items = (
            db.query(Wishlist)
            .filter(Wishlist.owner_id == current_user.id)
            .order_by(Wishlist.id.desc())
            .all()
        )
        return templates.TemplateResponse(
            request,
            "wishlist.html",
            {"items": items, "user": current_user, "error": "Игра уже в вишлисте"},
            status_code=400,
        )

    return RedirectResponse(url="/wishlist", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{item_id}/delete")
def delete_game(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    item = (
        db.query(Wishlist)
        .filter(Wishlist.id == item_id, Wishlist.owner_id == current_user.id)
        .first()
    )

    if not item:
        raise HTTPException(status_code=404, detail="Запись не найдена")

    db.delete(item)
    db.commit()

    return RedirectResponse("/wishlist", status_code=302)
