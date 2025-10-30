import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_main_page():
    """Главная страница загружена?"""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

def test_search_page():
    """Страница поиска загружена?"""
    response = client.get("/search")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

def test_api_search_validation():
    """Проверка API поиска"""
    response = client.get("/api/search")
    assert response.status_code == 422
    
    response = client.get("/api/search?query=a")
    assert response.status_code == 422
    