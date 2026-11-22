from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["estado"] == "operativo"

def test_public_vendedores():
    response = client.get("/api/publico/vendedores")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_dashboard():
    response = client.get("/api/dashboard")
    assert response.status_code == 200
    assert "vendedores" in response.json()
