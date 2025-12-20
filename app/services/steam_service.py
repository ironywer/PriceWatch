import asyncio
import aiohttp
import logging
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional
from contextlib import asynccontextmanager

# Импорт генератора игр
from app.services.generator_games import GameGenerator


logger = logging.getLogger(__name__)

class SteamDataService:
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.base_url = "https://store.steampowered.com/api"
        self.featured_url = "https://store.steampowered.com/api/featuredcategories"
        self.search_url = "https://store.steampowered.com/api/storesearch"
        self.price_formatter = PriceFormatter()
        self.use_fallback = False  # Флаг для генаратора игр
        self._session = None

    async def __aenter__(self):
        """Запуск сессии"""
        self._session = aiohttp.ClientSession(
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/121.0.0.0 Safari/537.36"
                )
            },
            cookies={
                "mature_content": "1",
                "birthtime": "568022401",
                "lastagecheckage": "1-January-1988",
                "steamCountry": "RU|1234567890123",
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Окончание сессии"""
        if self._session:
            await self._session.close()

    @asynccontextmanager
    async def get_session(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        try:
            yield self._session
        finally:
            pass

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def search_games(self, query: str) -> List[Dict]:
        """Поиск игр по названию в Steam"""
        async with self.get_session() as session:
            try:
                params = {
                    'term': query,
                    'l': 'russian',
                    'cc': 'ru'
                }

                async with session.get(self.search_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return await self._parse_search_results(data, session)
                    else:
                        logger.error(f"Steam search API error: {response.status}")
                        return []
            except Exception:
                logger.exception("Unexpected error in search_games")
                return []

    async def _parse_search_results(self, data: Dict, session: aiohttp.ClientSession) -> List[Dict]:
        """Обработка результатов поиска"""
        games = []
        if 'items' in data:
            appids = []
            items_map = {}
            for item in data['items']:
                if len(appids) >= 20:  # ограничение на 20 игр
                    break
                appid = item.get('id')
                price = item.get('price')
                if appid and price:
                    appids.append(appid)
                    items_map[appid] = item

            # Параллельные запросы
            detailed_infos = await self._get_multiple_app_details(appids, session, max_concurrent=3)
            for appid, detailed_info in detailed_infos.items():
                item = items_map[appid]
                if detailed_info:
                    game_data = await self._build_game_data(detailed_info, item, appid)
                else:
                    game_data = self._create_basic_game_info(item)
                if game_data:
                    games.append(game_data)
        return games

    async def _get_multiple_app_details(
            self,
            appids: List[int],
            session: aiohttp.ClientSession,
            max_concurrent: int = 5
    ) -> Dict[int, Optional[Dict]]:
        """Параллельное получение детальной информации"""
        if not appids:
            return {}

        semaphore = asyncio.Semaphore(max_concurrent)

        async def bounded_get_app_details(appid: int) -> tuple[int, Optional[Dict]]:
            async with semaphore:
                try:
                    result = await self._get_app_details(appid, session)
                    return appid, result
                except Exception as e:
                    logger.error(f"Error: получение результатов для {appid}: {e}")
                    return appid, None

        tasks = [bounded_get_app_details(appid) for appid in appids]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        detailed_infos = {}
        for appid, result in results:
            detailed_infos[appid] = result

        return detailed_infos

    def _create_basic_game_info(self, item: Dict) -> Optional[Dict]:
        """Базовая информация об игре"""
        try:
            appid = item.get('id')
            name = item.get('name', 'Unknown Game')
            price = item.get('price', {}).get('final_formatted', 'Цена не указана')

            return {
                "appid": appid,
                "name": name,
                "publisher": item.get('publisher', 'Неизвестный издатель'),
                "price": price,
                "image": item.get(
                    'tiny_image',
                    f"https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/header.jpg"
                ),
                "type": "game"
            }
        except Exception:
            logger.error("Error creating basic game info")
            return None

    async def get_featured_games(self) -> List[Dict]:
        """Получение популярных игр с главной страницы Steam"""
        async with self.get_session() as session:
            try:
                if self.use_fallback:
                    logger.info("Используется генератор популярных игр")
                    return GameGenerator.get_featured_games()

                async with session.get(self.featured_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return await self._parse_featured_games(data, session)
                    else:
                        logger.error(f"Steam API error: {response.status}")
                        return []

            except aiohttp.ClientError as e:
                logger.error(f"Error fetching featured games: {e}")
                self.use_fallback = True
                return GameGenerator.get_featured_games()
            except Exception:
                return []

    async def _parse_featured_games(self, data: Dict, session: aiohttp.ClientSession) -> List[Dict]:
        """Парсинг данных из featured categories"""
        games = []
        appids = []
        items_map = {}

        # Категории игр
        featured_categories = [
            'specials',  # Специальные предложения
            'top_sellers',  # Топ продаж
            'new_releases',  # Новинки
            'coming_soon'  # Скоро выйдут
        ]

        for category in featured_categories:
            if category in data and 'items' in data[category]:
                for item in data[category]['items']:
                    if len(appids) >= 20:  # максимум 20 игр
                        break
                    appid = item.get('id') or item.get('appid')
                    if appid:
                        appids.append(appid)
                        items_map[appid] = item

        detailed_infos = await self._get_multiple_app_details(appids, session, max_concurrent=3)
        for appid, detailed_info in detailed_infos.items():
            item = items_map[appid]
            game_data = False
            if detailed_info:
                game_data = await self._build_game_data(detailed_info, item, appid)
            if game_data:
                games.append(game_data)
        return games[:20]

    async def _extract_game_info(self, item: Dict) -> Optional[Dict]:
        """Извлечение информации об игре из элемента"""
        try:
            # Получение appid
            appid = item.get('id') or item.get('appid')
            if not appid:
                return None

            detailed_info = await self._get_app_details(appid)
            if not detailed_info:
                return None

            return await self._build_game_data(detailed_info, item, appid)

        except Exception:
            logger.error("Error extracting game info")
            return None

    async def _extract_game_from_search(self, item: Dict) -> Optional[Dict]:
        """Извлечение информации из результата поиска"""
        try:
            appid = item.get('id')
            if not appid:
                return None

            detailed_info = await self._get_app_details(appid)
            if not detailed_info:
                return self._create_basic_game_info(item)

            return await self._build_game_data(detailed_info, item, appid)

        except Exception:
            logger.error("Error extracting game from search")
            return self._create_basic_game_info(item)

    async def _build_game_data(self, detailed_info: Dict, fallback_item: Dict, appid: int) -> Dict:
        """Сборка данных игры из информации"""
        name = detailed_info.get('name', fallback_item.get('name', 'Unknown Game'))

        # Цена
        price = self.price_formatter.format(detailed_info)

        # Издатель
        publishers = detailed_info.get('publishers', [])
        publisher = (
            publishers[0]
            if publishers
            else fallback_item.get('publisher', 'Неизвестный издатель')
        )

        # Изображение
        header_image = detailed_info.get('header_image')
        default_image = f"https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/header.jpg"
        image_url = header_image or default_image

        return {
            "appid": appid,
            "name": name,
            "publisher": publisher,
            "price": price,
            "image": image_url,
            "type": detailed_info.get('type', 'game')
        }

    async def _get_app_details(self, appid: int, session: aiohttp.ClientSession) -> Optional[Dict]:
        """Получение детальной информации об игре"""
        try:
            url = f"{self.base_url}/appdetails"
            params = {'appids': appid, 'l': 'russian'}

            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    app_data = data.get(str(appid), {})
                    if app_data.get('success'):
                        return app_data.get('data')
        except Exception:
            return None


class PriceFormatter:
    def format(self, detailed_info: Dict) -> str:
        """Форматирование цены игры"""
        price_info = detailed_info.get('price_overview', {})
        if price_info:
            return self._format_paid_game(price_info)
        else:
            return self._format_free_game(detailed_info)

    def _format_paid_game(self, price_info: Dict) -> str:
        """Форматирование цены платной игры"""
        price = f"{price_info.get('final', 0) / 100:.2f} руб."
        if price_info.get('discount_percent', 0) > 0:
            initial_price = f"{price_info.get('initial', 0) / 100:.2f} руб."
            discount = price_info['discount_percent']
            price = f"<s>{initial_price}</s> {price} (-{discount}%)"
        return price

    def _format_free_game(self, detailed_info: Dict) -> str:
        """Форматирование цены бесплатной игры"""
        if detailed_info.get('is_free', False):
            return "Бесплатно"
        else:
            return "Цена не указана"
