import pytest
from fastapi.testclient import TestClient

valid_data = [
    ("user1@example.com", "Secret123", "Alice"),
    ("user2@example.com", "Qwerty777", "Bob"),
]

invalid_emails = [
    ("bademail", "Secret123", None),
    ("abc@", "Secret123", None),
    ("@example.com", "Secret123", None),
]


@pytest.mark.parametrize("email,password,full_name", valid_data)
def test_register_success(client: TestClient, email, password, full_name):
    resp = client.post(
        "/auth/register",
        data={"email": email, "password": password, "full_name": full_name},
        follow_redirects=False
    )
    assert resp.status_code == 302
    assert resp.headers["location"] == "/auth/login"


@pytest.mark.parametrize("email,password,full_name", invalid_emails)
def test_register_invalid_email(client: TestClient, email, password, full_name):
    resp = client.post(
        "/auth/register",
        data={"email": email, "password": password, "full_name": full_name},
    )
    assert resp.status_code == 400
    assert "email" in resp.text.lower() or "корректн" in resp.text.lower()
