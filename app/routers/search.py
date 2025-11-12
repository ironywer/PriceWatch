from fastapi import APIRouter, Request, Depends, Query, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services.steam_service import SteamDataService
from app.deps import get_current_user
from app.models import User

from datetime import datetime
import requests
import xml.etree.ElementTree as ET

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

steam_service = SteamDataService("79DCEEEC80EB29431B88CA479CA11E56") # Инициализация сервиса

@router.get("/search", response_class=HTMLResponse)
async def search_page(request: Request, user: User = Depends(get_current_user)):
    """Главная страница поиска - показывает популярные игры"""
    featured_games = await steam_service.get_featured_games()  # Получение популярных игр с главной страницы Steam
    try:
        featured_games = await steam_service.get_featured_games()  # Получение популярных игр с главной страницы Steam
        return templates.TemplateResponse("search.html", {
            "request": request,
            "featured_games": featured_games,
            "user": user
        })
    except Exception as e:
        # В случае ошибки
        return templates.TemplateResponse("search.html", {
            "request": request,
            "featured_games": [],
            "user": user
        })

@router.get("/api/search")
async def search_games_api(query: str = Query(..., min_length=2)):
    """API endpoint для поиска игр"""
    try:
        games_data = await steam_service.search_games(query)
        return JSONResponse(content=games_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/exchange-rates")
async def get_exchange_rates():
    """API endpoint для получения курсов валют с ЦБ РФ"""
    try:
        response = requests.get("https://www.cbr.ru/scripts/XML_daily.asp")
        root = ET.fromstring(response.content)
        
        rates = {}
        
        # Ищем доллары США и евро
        for currency in root.findall('Valute'):
            char_code = currency.find('CharCode').text
            if char_code in ['USD', 'EUR']:
                value = currency.find('Value').text
                nominal = currency.find('Nominal').text
                # Конвертируем в число (заменяем запятую на точку)
                rate = float(value.replace(',', '.')) / float(nominal)
                rates[char_code] = rate
        
        return rates
    except Exception as e:
        # Возвращаем примерные курсы в случае ошибки
        return {"USD": 90.0, "EUR": 98.0}
