from fastapi.testclient import TestClient
from app.main import app
import uuid

client = TestClient(app)


def crear_vendedor():
    dni = str(10000000 + (uuid.uuid4().int % 89999999))
    response = client.post("/api/vendedores", json={
        "nombre": "Vendedor HU04",
        "documento": dni,
        "telefono": "999888777",
        "puesto": "Puesto de prueba",
        "ubicacion": "Lima",
        "licencia": "Pendiente"
    })
    assert response.status_code == 201
    return response.json()["id"]


def crear_inspeccion(vendedor_id, observaciones):
    return client.post("/api/inspecciones", json={
        "vendedor_id": vendedor_id,
        "inspector": "Inspector HU04",
        "higiene": "Adecuada",
        "temperatura": 3.5,
        "conservacion": "Adecuada",
        "observaciones": observaciones,
        "resultado": "Aprobado"
    })


def test_hu04_registrar_inspeccion():
    vendedor_id = crear_vendedor()
    response = crear_inspeccion(vendedor_id, "Sin observaciones")
    assert response.status_code == 201


def test_hu04_vendedor_inexistente():
    response = crear_inspeccion(999999999, "Prueba")
    assert response.status_code == 404


def test_hu04_campos_obligatorios():
    response = client.post("/api/inspecciones", json={
        "vendedor_id": 1
    })
    assert response.status_code == 422


def test_hu04_historial_y_observaciones():
    vendedor_id = crear_vendedor()

    crear_inspeccion(vendedor_id, "Observación de higiene")
    crear_inspeccion(vendedor_id, "Revisar conservación")

    response = client.get(
        f"/api/vendedores/{vendedor_id}/inspecciones"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_inspecciones"] == 2

    observaciones = [
        x["observaciones"] for x in data["historial"]
    ]
    assert "Observación de higiene" in observaciones
    assert "Revisar conservación" in observaciones


def test_hu04_historial_vendedor_inexistente():
    response = client.get(
        "/api/vendedores/999999999/inspecciones"
    )
    assert response.status_code == 404