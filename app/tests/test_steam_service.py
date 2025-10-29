import pytest
from app.services.steam_service import SteamDataService

def test_steam_service_initialization():
    """Проверить инициализацию службы steam"""
    service = SteamDataService("79DCEEEC80EB29431B88CA479CA11E56")
    assert service is not None
    assert hasattr(service, 'get_featured_games')
    assert hasattr(service, 'search_games')