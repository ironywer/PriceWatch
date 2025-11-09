import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize("password", ["WrongPass", "", "abcd"])
def test_login_wrong_password(client: TestClient, password):
    email = "tester@example.com"
    client.post("/auth/register", data={"email": email, "password": "Secret123"})

    resp = client.post("/auth/login", data={"email": email, "password": password})
    assert resp.status_code == 400


login_cases = [
    ("test1@example.com", "Secret123", 302),  # success
    ("test1@example.com", "WrongPass", 400),  # wrong password
    ("not_exists@example.com", "Any", 400),  # no user
]


@pytest.mark.parametrize("email,password,status_code", login_cases)
def test_login_parametrized(client: TestClient, email, password, status_code):
    client.post("/auth/register", data={"email": "test1@example.com", "password": "Secret123"})

    resp = client.post("/auth/login", data={"email": email, "password": password}, follow_redirects=False)
    assert resp.status_code == status_code
