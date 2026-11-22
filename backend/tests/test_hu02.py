from fastapi.testclient import TestClient
from app.main import app
import uuid

client = TestClient(app)

def registrar_vendedor():
    dni = str(10000000 + (uuid.uuid4().int % 89999999))
    response = client.post("/api/vendedores", json={
        "nombre": "Vendedor HU02",
        "documento": dni,
        "telefono": "999888777",
        "puesto": "Puesto principal",
        "ubicacion": "Lima",
        "licencia": "Pendiente"
    })
    assert response.status_code == 201
    return response.json()["id"]

def test_hu02_registro_puesto_asociado():
    vendedor_id = registrar_vendedor()
    response = client.post("/api/puestos", json={
        "vendedor_id": vendedor_id,
        "nombre_puesto": "Puesto Mercado Central",
        "ubicacion": "Lima Centro"
    })
    assert response.status_code == 201
    assert response.json()["vendedor_id"] == vendedor_id
    assert response.json()["id"] is not None

def test_hu02_advertir_puesto_duplicado():
    vendedor_id = registrar_vendedor()
    datos = {
        "vendedor_id": vendedor_id,
        "nombre_puesto": "Puesto Mercado",
        "ubicacion": "Lima"
    }
    assert client.post("/api/puestos", json=datos).status_code == 201
    segunda = client.post("/api/puestos", json=datos)
    assert segunda.status_code == 409
    assert "ya está registrado" in segunda.json()["detail"]

def test_hu02_vendedor_no_registrado():
    response = client.post("/api/puestos", json={
        "vendedor_id": 999999,
        "nombre_puesto": "Puesto de prueba",
        "ubicacion": "Lima"
    })
    assert response.status_code == 404

def test_hu02_campos_obligatorios():
    response = client.post("/api/puestos", json={
        "vendedor_id": 1,
        "nombre_puesto": "",
        "ubicacion": ""
    })
    assert response.status_code == 422

def test_hu02_listar_puestos():
    response = client.get("/api/puestos")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
