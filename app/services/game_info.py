import asyncio
from app.services.steam_service import SteamDataService

steam = SteamDataService()


async def get_game_info_by_app_id_async(appid: int):
    async with steam:
        async with steam.get_session() as session:
            # 1) получить детальную инфу
            detailed = await steam._get_app_details(appid, session)

            # 2) если нет — fallback
            if not detailed:
                return {
                    "appid": appid,
                    "name": f"Game {appid}",
                    "price": None,
                    "image": f"https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/header.jpg",
                    "url": f"https://store.steampowered.com/app/{appid}",
                }

            # 3) простейший mock fallback_item
            fallback_item = {"name": detailed.get("name", f"Game {appid}")}

            game = await steam._build_game_data(detailed, fallback_item, appid)

            # 4) добавляем ссылку, если её нет
            game["url"] = f"https://store.steampowered.com/app/{appid}"

            return game


def get_game_info_by_app_id(appid: int):
    """Синхронная обёртка — можно вызывать из обычных view-функций."""
    return asyncio.run(get_game_info_by_app_id_async(appid))
