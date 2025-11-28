import asyncio

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse
from starlette.templating import Jinja2Templates
from starlette.datastructures import URL

from app.db.database import get_db
from app.models.user import User
from app.deps import get_current_user
from app.services.game_info import get_game_info_by_app_id_async
from app.services.wishlist_service import WishlistService

router = APIRouter(prefix="/wishlist")
templates = Jinja2Templates(directory="app/templates")


def redirect_back(request: Request, **params):
    referer = request.headers.get("referer", "/search")
    url = URL(referer).include_query_params(**params)
    return RedirectResponse(url, status_code=303)


@router.get("/", response_class=HTMLResponse)
async def view_wishlist(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    wishlist_service = WishlistService(db)
    items = wishlist_service.get_user_wishlist(current_user.id)

    # собираем appid’ы
    app_ids = [item.steam_app_id for item in items]

    # параллельно тянем инфу об играх
    tasks = [get_game_info_by_app_id_async(appid) for appid in app_ids]
    games = await asyncio.gather(*tasks)

    enriched = []
    for item, game in zip(items, games):
        if not game:
            continue
        enriched.append({
            "wishlist_id": item.id,
            "appid": item.steam_app_id,
            "name": game.get("name"),
            "price": game.get("price"),
            "image": game.get("image"),
            "url": game.get("url"),
        })

    return templates.TemplateResponse(
        "wishlist.html",
        {
            "request": request,
            "items": enriched,
            "user": current_user,
        },
    )


@router.post("/add")
async def add_game(
        request: Request,
        steam_app_id: int = Form(...),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    wishlist_service = WishlistService(db)

    game = await get_game_info_by_app_id_async(steam_app_id)
    if not game:
        return redirect_back(
            request,
            status="error",
            message="Игра не найдена в Steam",
        )

    exists = wishlist_service.find_by_app_id(current_user.id, steam_app_id)
    if exists:
        return redirect_back(
            request,
            status="error",
            message="Игра уже есть в списке желаемого",
        )

    wishlist_service.add_item(current_user.id, steam_app_id)

    return redirect_back(
        request,
        status="ok",
        message="Игра добавлена в список желаемого",
    )


@router.post("/{item_id}/delete")
def delete_game(
        request: Request,
        item_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    wishlist_service = WishlistService(db)
    deleted = wishlist_service.delete_item(current_user.id, item_id)

    if not deleted:
        return redirect_back(
            request,
            status="error",
            message="Элемент списка желаемого не найден",
        )

    return redirect_back(
        request,
        status="ok",
        message="Игра удалена из списка желаемого",
    )
