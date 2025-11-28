from typing import Optional, Dict, List

from app.services.steam_service import SteamDataService


async def get_game_info_by_app_id_async(appid: int) -> Dict:
    """Получить информацию об одной игре по appid."""
    steam = SteamDataService()
    async with steam:
        async with steam.get_session() as session:
            detailed = await steam._get_app_details(appid, session)

            if not detailed:
                # fallback, если Steam не дал деталей
                return {
                    "appid": appid,
                    "name": f"Game {appid}",
                    "price": None,
                    "image": f"https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/header.jpg",
                    "url": f"https://store.steampowered.com/app/{appid}",
                }

            fallback_item = {"name": detailed.get("name", f"Game {appid}")}

            game = await steam._build_game_data(detailed, fallback_item, appid)
            game["url"] = f"https://store.steampowered.com/app/{appid}"
            return game


async def get_games_info_by_app_ids_async(appids: List[int]) -> List[Dict]:
    """
    Получить информацию сразу о нескольких играх.
    Здесь можно использовать _get_multiple_app_details, который уже есть в SteamDataService.
    """
    if not appids:
        return []

    steam = SteamDataService()
    async with steam:
        async with steam.get_session() as session:
            # получаем детали пачкой с лимитом по семафору
            detailed_map = await steam._get_multiple_app_details(appids, session)

            games: List[Dict] = []
            for appid in appids:
                detailed = detailed_map.get(appid)

                if not detailed:
                    games.append({
                        "appid": appid,
                        "name": f"Game {appid}",
                        "price": None,
                        "image": f"https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/header.jpg",
                        "url": f"https://store.steampowered.com/app/{appid}",
                    })
                    continue

                fallback_item = {"name": detailed.get("name", f"Game {appid}")}
                game = await steam._build_game_data(detailed, fallback_item, appid)
                game["url"] = f"https://store.steampowered.com/app/{appid}"
                games.append(game)

            return games
