from fastapi.testclient import TestClient
from app.main import app
import uuid

client = TestClient(app)

def datos_vendedor():
    return {
        "nombre": "Vendedor de prueba",
        "documento": str(10000000 + uuid.uuid4().int % 89999999),
        "telefono": "999888777",
        "puesto": "Puesto de prueba",
        "ubicacion": "Lima",
        "licencia": "Pendiente"
    }

def test_hu01_registro_exitoso():
    r = client.post("/api/vendedores", json=datos_vendedor())
    assert r.status_code == 201
    assert r.json()["id"] is not None

def test_hu01_campos_obligatorios_vacios():
    r = client.post("/api/vendedores", json={
        "nombre": "",
        "documento": "",
        "puesto": ""
    })
    assert r.status_code == 422

def test_hu01_dni_invalido():
    datos = datos_vendedor()
    datos["documento"] = "12345"
    assert client.post("/api/vendedores", json=datos).status_code == 422

def test_hu01_dni_duplicado():
    datos = datos_vendedor()
    assert client.post("/api/vendedores", json=datos).status_code == 201
    assert client.post("/api/vendedores", json=datos).status_code == 409

def test_hu01_consultar_vendedor():
    datos = datos_vendedor()
    r = client.post("/api/vendedores", json=datos)
    vendedor_id = r.json()["id"]
    consulta = client.get(f"/api/vendedores/{vendedor_id}")
    assert consulta.status_code == 200
    assert consulta.json()["documento"] == datos["documento"]
