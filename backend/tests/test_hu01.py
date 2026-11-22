from fastapi.testclient import TestClient
from app.main import app
import uuid

client = TestClient(app)

def datos_vendedor():
    dni = str(10000000 + (uuid.uuid4().int % 89999999))
    return {
        "nombre": "Vendedor de prueba",
        "documento": dni,
        "telefono": "999888777",
        "puesto": "Puesto de prueba",
        "ubicacion": "Lima",
        "licencia": "Pendiente"
    }

def test_hu01_registro_exitoso():
    response = client.post("/api/vendedores", json=datos_vendedor())
    assert response.status_code == 201
    assert response.json()["id"] is not None

def test_hu01_campos_obligatorios_vacios():
    response = client.post("/api/vendedores", json={
        "nombre": "",
        "documento": "",
        "puesto": ""
    })
    assert response.status_code == 422

def test_hu01_dni_invalido():
    datos = datos_vendedor()
    datos["documento"] = "12345"
    response = client.post("/api/vendedores", json=datos)
    assert response.status_code == 422

def test_hu01_dni_duplicado():
    datos = datos_vendedor()
    primera = client.post("/api/vendedores", json=datos)
    segunda = client.post("/api/vendedores", json=datos)
    assert primera.status_code == 201
    assert segunda.status_code == 409

def test_hu01_consultar_vendedor():
    datos = datos_vendedor()
    registro = client.post("/api/vendedores", json=datos)
    vendedor_id = registro.json()["id"]
    response = client.get(f"/api/vendedores/{vendedor_id}")
    assert response.status_code == 200
    assert response.json()["documento"] == datos["documento"]
