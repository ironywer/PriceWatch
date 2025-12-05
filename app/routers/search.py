import os
from fastapi import APIRouter, Request, Depends, Query, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.services.steam_service import SteamDataService
from app.deps import get_current_user
from app.models import User, Wishlist
import requests
import xml.etree.ElementTree as ET
import logging

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger(__name__)


def read_steam_key():
    """Чтение Steam API ключа из файла"""
    try:
        key_path = os.path.join(os.path.dirname(__file__), '..', '..', 'steam_key.txt')
        key_path = os.path.abspath(key_path)
        with open(key_path, 'r', encoding='utf-8') as f:
            key = f.read().strip()
        if not key:
            raise ValueError("Файл с ключем Steam пуст")
        return key
    except FileNotFoundError:
        logger.error("Файл с ключем Steam не найден: steam_key.txt")
        raise
    except Exception as e:
        logger.error(f"Ошибка чтения файла: {e}")
        raise


def get_steam_service():
    """Фабрика для создания SteamDataService с ключом из файла"""
    try:
        steam_key = read_steam_key()
        return SteamDataService(steam_key)
    except Exception as e:
        logger.error(f"Ошибка инициализации Steam сервиса: {e}")
        return SteamDataService(None)


# Инициализация сервиса с ключом из файла
steam_service = get_steam_service()


@router.get("/search", response_class=HTMLResponse)
async def search_page(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Главная страница поиска - показывает популярные игры"""
    try:
        featured_games = await steam_service.get_featured_games()
        # Загружаем вишлист пользователя
        wishlist_items = (
            db.query(Wishlist)
            .filter(Wishlist.owner_id == user.id)
            .all()
        )

        # Множество appid, чтобы быстро проверять "в вишлисте ли игра"
        wishlist_app_ids = {w.steam_app_id for w in wishlist_items}

        # Для удаления нужен id записи
        wishlist_by_appid = {w.steam_app_id: w.id for w in wishlist_items}

        return templates.TemplateResponse("search.html", {
            "request": request,
            "featured_games": featured_games,
            "user": user,
            "wishlist_app_ids": wishlist_app_ids,
            "wishlist_by_appid": wishlist_by_appid,
        })

    except Exception:
        logger.error("Error fetching featured games")
        return templates.TemplateResponse("search.html", {
            "request": request,
            "featured_games": [],
            "user": user,
            "wishlist_app_ids": set(),
            "wishlist_by_appid": {},
        })


@router.get("/api/search")
async def search_games_api(query: str = Query(..., min_length=2)):
    """API endpoint для поиска игр"""
    try:
        games_data = await steam_service.search_games(query)
        return JSONResponse(content=games_data)
    except Exception as e:
        logger.error(f"Error searching games: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/api/exchange-rates")
async def get_exchange_rates():
    """API endpoint для получения курсов валют с ЦБ РФ"""
    try:
        response = requests.get("https://www.cbr.ru/scripts/XML_daily.asp")
        root = ET.fromstring(response.content)

        rates = {}

        # Доллары и евро
        for currency in root.findall('Valute'):
            char_code = currency.find('CharCode').text
            if char_code in ['USD', 'EUR']:
                value = currency.find('Value').text
                nominal = currency.find('Nominal').text
                rate = float(value.replace(',', '.')) / float(nominal)
                rates[char_code] = rate

        return rates
    except Exception:
        logger.error("Error fetching exchange rates")
        # Возвращает примерные курсы в случае ошибки
        return {"USD": 90.0, "EUR": 98.0}


@router.on_event("shutdown")
async def shutdown_event():
    """Закрытие сессии при завершении работы"""
    if hasattr(steam_service, '_session') and steam_service._session:
        await steam_service._session.close()
        logger.info("Steam service session closed")
