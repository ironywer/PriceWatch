import aiohttp
import json
from typing import List, Dict, Optional
import logging
from urllib.parse import quote

logger = logging.getLogger(__name__)



class SteamDataService:
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.base_url = "https://store.steampowered.com/api"
        self.featured_url = "https://store.steampowered.com/api/featuredcategories"
        self.search_url = "https://store.steampowered.com/api/storesearch"
    
    async def search_games(self, query: str) -> List[Dict]:
        """Поиск игр по названию в Steam"""
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    'term': query,
                    'l': 'russian',
                    'cc': 'ru'
                }
                
                async with session.get(self.search_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return await self._parse_search_results(data)
                    else:
                        logger.error(f"Steam search API error: {response.status}")
                        return await self._get_fallback_games()
        except Exception as e:
            logger.error(f"Error searching games: {e}")
            return await self._get_fallback_games()
    
    async def _parse_search_results(self, data: Dict) -> List[Dict]:
        """Обработка"""
        games = []
        
        if 'items' in data:
            for item in data['items']:
                if len(games) >= 20:  # Ограничим 20 играми
                    break
                
                game_data = await self._extract_game_from_search(item)
                if game_data:
                    games.append(game_data)
        
        return games
    
    async def _extract_game_from_search(self, item: Dict) -> Optional[Dict]:
        """Извлечение информации"""
        try:
            appid = item.get('id')
            if not appid:
                return None
            
            detailed_info = await self._get_app_details(appid)
            if not detailed_info:
                return self._create_basic_game_info(item) 
            
            # Детальная информация
            name = detailed_info.get('name', item.get('name', 'Unknown Game'))
            
            # Обработка цены
            price_info = detailed_info.get('price_overview', {})
            if price_info:
                price = f"{price_info.get('final', 0) / 100:.2f} руб."
                if price_info.get('discount_percent', 0) > 0:
                    price = f"<s>{price_info.get('initial', 0) / 100:.2f} руб.</s> {price} (-{price_info['discount_percent']}%)"
            else:
                price = "Бесплатно" if detailed_info.get('is_free', False) else "Цена не указана"
            
            # Издатель
            publishers = detailed_info.get('publishers', [])
            publisher = publishers[0] if publishers else item.get('publisher', 'Неизвестный издатель')
            
            # Изображение
            image_url = detailed_info.get('header_image', 
                         item.get('tiny_image', 
                         f"https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/header.jpg"))
            
            return {
                "appid": appid,
                "name": name,
                "publisher": publisher,
                "price": price,
                "image": image_url,
                "type": detailed_info.get('type', 'game')
            }
            
        except Exception as e:
            logger.error(f"Error extracting game from search: {e}")
            return self._create_basic_game_info(item)
    
    def _create_basic_game_info(self, item: Dict) -> Optional[Dict]:
        """Базовая информация об игре из результатов поиска"""
        try:
            appid = item.get('id')
            name = item.get('name', 'Unknown Game')
            price = item.get('price', {}).get('final_formatted', 'Цена не указана')
            
            return {
                "appid": appid,
                "name": name,
                "publisher": item.get('publisher', 'Неизвестный издатель'),
                "price": price,
                "image": item.get('tiny_image', f"https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/header.jpg"),
                "type": "game"
            }
        except Exception as e:
            logger.error(f"Error creating basic game info: {e}")
            return None
    
    async def get_featured_games(self) -> List[Dict]:
        """Получение популярных игр с главной страницы Steam"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.featured_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return await self._parse_featured_games(data)
                    else:
                        logger.error(f"Steam API error: {response.status}")
                        return await self._get_fallback_games()
        except Exception as e:
            logger.error(f"Error fetching featured games: {e}")
            return await self._get_fallback_games()
    
    async def _parse_featured_games(self, data: Dict) -> List[Dict]:
        """Парсинг данных из featured categories"""
        games = []
        
        # Популярные игры (обычно в специальных категориях)
        featured_categories = [
            'specials',  # Специальные предложения
            'top_sellers',  # Топ продаж
            'new_releases',  # Новинки
            'coming_soon'  # Скоро выйдут
        ]
        
        for category in featured_categories:
            if category in data and 'items' in data[category]:
                for item in data[category]['items']:
                    if len(games) >= 24:  # максимум 24 игры
                        break
                    
                    game_data = await self._extract_game_info(item)
                    if game_data:
                        games.append(game_data)
        
        return games[:24]
    
    async def _extract_game_info(self, item: Dict) -> Optional[Dict]:
        """Извлечение информации об игре из элемента"""
        try:     
            appid = item.get('id') or item.get('appid')# Получение appid
            if not appid:
                return None
             
            detailed_info = await self._get_app_details(appid) # Получаем детальную информацию об игре
            if not detailed_info:
                return None
            
            name = detailed_info.get('name', item.get('name', 'Unknown Game'))

            price_info = detailed_info.get('price_overview', {})
            if price_info:
                price = f"{price_info.get('final', 0) / 100:.2f} руб."
                if price_info.get('discount_percent', 0) > 0:
                    price = f"<s>{price_info.get('initial', 0) / 100:.2f} руб.</s> {price} (-{price_info['discount_percent']}%)"
            else:
                price = "Бесплатно" if detailed_info.get('is_free', False) else "Цена не указана"
            
            # Издатель
            publishers = detailed_info.get('publishers', [])
            publisher = publishers[0] if publishers else "Неизвестный издатель"
            
            # Изображение
            image_url = detailed_info.get('header_image', item.get('header_image', f"https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/header.jpg"))
            
            return {
                "appid": appid,
                "name": name,
                "publisher": publisher,
                "price": price,
                "image": image_url,
                "type": detailed_info.get('type', 'game')
            }
            
        except Exception as e:
            logger.error(f"Error extracting game info: {e}")
            return None
    
    async def _get_app_details(self, appid: int) -> Optional[Dict]:
        """Получение детальной информации об игре"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/appdetails"
                params = {'appids': appid, 'l': 'russian'}
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        app_data = data.get(str(appid), {})
                        if app_data.get('success'):
                            return app_data.get('data')
            return None
        except Exception as e:
            logger.error(f"Error getting app details for {appid}: {e}")
            return None
        
    async def get_game_details(self, app_id: int) -> Optional[Dict]:
        """Получение детальной информации об игре"""
        return await self._get_app_details(app_id)