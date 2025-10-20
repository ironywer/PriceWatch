from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.services.steam_service import SteamDataService

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

steam_service = SteamDataService("79DCEEEC80EB29431B88CA479CA11E56") # Инициализация сервиса

@router.get("/search", response_class=HTMLResponse)
async def search_page(request: Request):
    """Главная страница поиска - показывает популярные игры"""
    try:
        featured_games = await steam_service.get_featured_games() #Получение популярных игр с главной страницы Steam
        return templates.TemplateResponse("search.html", {
            "request": request,
            "featured_games": featured_games
        })
    except Exception as e:
        # В случае ошибки
        return templates.TemplateResponse("search.html", {
            "request": request,
            "featured_games": []
        })

@router.get("/api/search")
async def search_games_api(query: str = Query(..., min_length=2)):
    """API endpoint для поиска игр"""
    try:
        games_data = await steam_service.search_games(query)
        return JSONResponse(content=games_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))