import pytest
from fastapi.testclient import TestClient
from calendar_service.main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "Welcome" in response.json()["message"]

def test_get_calendar_punjab_rice():
    response = client.get("/calendar?state=Punjab&crop=rice&month=5")
    assert response.status_code == 200
    data = response.json()
    assert data["state"] == "Punjab"
    assert data["crop"] == "rice"
    assert data["month"] == "may"
    assert data["stage"] == "seed_treatment"

def test_get_calendar_auto_month():
    # Since current month is May (based on system time in prompt)
    response = client.get("/calendar?state=Tamil Nadu&crop=rice")
    assert response.status_code == 200
    data = response.json()
    assert data["month"] == "may"
    assert data["stage"] == "seed_treatment"

def test_invalid_state():
    response = client.get("/calendar?state=UnknownState&crop=rice")
    assert response.status_code == 404
    assert "not supported" in response.json()["detail"]

def test_invalid_crop():
    response = client.get("/calendar?state=Punjab&crop=unknown_crop")
    assert response.status_code == 404
    assert "not supported" in response.json()["detail"]
