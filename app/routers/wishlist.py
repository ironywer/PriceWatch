from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse
from starlette.templating import Jinja2Templates

from app.db.database import get_db
from app.models.wishlist import Wishlist
from app.models.user import User
from app.deps import get_current_user
from app.services.game_info import get_game_info_by_app_id
from starlette.datastructures import URL

router = APIRouter(prefix="/wishlist")
templates = Jinja2Templates(directory="app/templates")


def redirect_back(request: Request, **params):
    referer = request.headers.get("referer", "/search")
    url = URL(referer).include_query_params(**params)
    return RedirectResponse(url, status_code=303)


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

    enriched = []
    for item in items:
        game = get_game_info_by_app_id(item.steam_app_id)
        enriched.append({
            "wishlist_id": item.id,
            "appid": item.steam_app_id,
            "name": game.get("name"),
            "price": game.get("price"),
            "image": game.get("image"),
            "url": game.get("url"),
        })

    return templates.TemplateResponse(
        request,
        "wishlist.html",
        {"items": enriched, "user": current_user},
    )


@router.post("/add")
def add_game(
        request: Request,
        steam_app_id: int = Form(...),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    # Проверяем существование игры в Steam
    game = get_game_info_by_app_id(steam_app_id)
    if not game:
        # остаёмся на той же странице и показываем ошибку
        return redirect_back(
            request,
            status="error",
            message="Игра не найдена в Steam",
        )

    exists = (
        db.query(Wishlist)
        .filter(
            Wishlist.owner_id == current_user.id,
            Wishlist.steam_app_id == steam_app_id,
        )
        .first()
    )

    if exists:
        return redirect_back(
            request,
            status="error",
            message="Игра уже в вишлисте",
        )

    item = Wishlist(steam_app_id=steam_app_id, owner_id=current_user.id)
    db.add(item)
    db.commit()

    return redirect_back(
        request,
        status="ok",
        message="Игра добавлена в вишлист",
    )


@router.post("/{item_id}/delete")
def delete_game(
        request: Request,
        item_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    item = (
        db.query(Wishlist)
        .filter(Wishlist.id == item_id, Wishlist.owner_id == current_user.id)
        .first()
    )

    if not item:
        # можно и 404 оставить, но если хочешь "мягко":
        return redirect_back(
            request,
            status="error",
            message="Запись в вишлисте не найдена",
        )

    db.delete(item)
    db.commit()

    return redirect_back(
        request,
        status="ok",
        message="Игра удалена из вишлиста",
    )
