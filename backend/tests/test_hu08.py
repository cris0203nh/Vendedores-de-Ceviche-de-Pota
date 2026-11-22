from fastapi.testclient import TestClient
from app.main import app
import uuid

client = TestClient(app)


def crear_proveedor():
    response = client.post("/api/proveedores", json={
        "nombre": "Proveedor HU08",
        "documento": str(uuid.uuid4().int)[:11],
        "telefono": "999888777",
        "procedencia": "Callao"
    })

    assert response.status_code == 201
    return response.json()["id"]


def crear_lote(proveedor_id):
    return client.post("/api/lotes", json={
        "proveedor_id": proveedor_id,
        "fecha_ingreso": "2026-11-21",
        "especie_declarada": "Pota",
        "cantidad": 50,
        "unidad": "kg",
        "procedencia": "Puerto del Callao"
    })


def test_hu08_registrar_lote_y_generar_codigo():
    proveedor_id = crear_proveedor()
    response = crear_lote(proveedor_id)

    assert response.status_code == 201
    assert response.json()["codigo"].startswith("LOTE-")
    assert len(response.json()["codigo"]) == 17


def test_hu08_generar_codigos_unicos():
    proveedor_id = crear_proveedor()

    primero = crear_lote(proveedor_id)
    segundo = crear_lote(proveedor_id)

    assert primero.status_code == 201
    assert segundo.status_code == 201
    assert primero.json()["codigo"] != segundo.json()["codigo"]


def test_hu08_rechazar_proveedor_inexistente():
    response = crear_lote(999999999)
    assert response.status_code == 404


def test_hu08_consultar_procedencia_y_fecha():
    proveedor_id = crear_proveedor()
    registro = crear_lote(proveedor_id)

    assert registro.status_code == 201

    lotes = client.get("/api/lotes")
    assert lotes.status_code == 200

    lote = next(
        x for x in lotes.json()
        if x["id"] == registro.json()["id"]
    )

    assert lote["fecha_ingreso"] == "2026-11-21"
    assert lote["procedencia"] == "Puerto del Callao"
    assert lote["proveedor_id"] == proveedor_id
    assert lote["codigo"] == registro.json()["codigo"]


def test_hu08_rechazar_cantidad_invalida():
    proveedor_id = crear_proveedor()

    response = client.post("/api/lotes", json={
        "proveedor_id": proveedor_id,
        "fecha_ingreso": "2026-11-21",
        "especie_declarada": "Pota",
        "cantidad": -5,
        "procedencia": "Callao"
    })

    assert response.status_code == 422