from fastapi.testclient import TestClient
from app.main import app
import uuid

client = TestClient(app)


def crear_vendedor():
    dni = str(10000000 + (uuid.uuid4().int % 89999999))

    response = client.post("/api/vendedores", json={
        "nombre": "Vendedor HU05",
        "documento": dni,
        "telefono": "999888777",
        "puesto": "Puesto HU05",
        "ubicacion": "Lima",
        "licencia": "Pendiente"
    })

    assert response.status_code == 201
    return response.json()["id"]


def test_hu05_registrar_temperatura():
    vendedor_id = crear_vendedor()

    response = client.post("/api/inspecciones", json={
        "vendedor_id": vendedor_id,
        "inspector": "Inspector HU05",
        "higiene": "Adecuada",
        "temperatura": 3.5,
        "conservacion": "Refrigerado",
        "observaciones": "Temperatura registrada",
        "resultado": "Aprobado"
    })

    assert response.status_code == 201

    registros = client.get("/api/inspecciones")
    assert registros.status_code == 200

    inspeccion = next(
        x for x in registros.json()
        if x["id"] == response.json()["id"]
    )

    assert inspeccion["temperatura"] == 3.5
    assert inspeccion["conservacion"] == "Refrigerado"


def test_hu05_conservar_condiciones_de_conservacion():
    vendedor_id = crear_vendedor()

    response = client.post("/api/inspecciones", json={
        "vendedor_id": vendedor_id,
        "inspector": "Inspector HU05",
        "higiene": "Adecuada",
        "temperatura": 2.0,
        "conservacion": "Cadena de frío mantenida",
        "observaciones": "Producto conservado correctamente",
        "resultado": "Aprobado"
    })

    assert response.status_code == 201

    registros = client.get("/api/inspecciones").json()

    inspeccion = next(
        x for x in registros
        if x["id"] == response.json()["id"]
    )

    assert inspeccion["conservacion"] == "Cadena de frío mantenida"
    assert inspeccion["observaciones"] == "Producto conservado correctamente"


def test_hu05_rechazar_temperatura_no_numerica():
    vendedor_id = crear_vendedor()

    response = client.post("/api/inspecciones", json={
        "vendedor_id": vendedor_id,
        "inspector": "Inspector HU05",
        "higiene": "Adecuada",
        "temperatura": "temperatura incorrecta",
        "conservacion": "Refrigerado"
    })

    assert response.status_code == 422