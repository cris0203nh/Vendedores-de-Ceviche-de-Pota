from fastapi.testclient import TestClient
from app.main import app
import uuid

client = TestClient(app)


def crear_lote():
    proveedor = client.post("/api/proveedores", json={
        "nombre": "Proveedor HU09",
        "documento": str(uuid.uuid4().int)[:11],
        "telefono": "999888777",
        "procedencia": "Callao"
    })

    assert proveedor.status_code == 201

    lote = client.post("/api/lotes", json={
        "proveedor_id": proveedor.json()["id"],
        "fecha_ingreso": "2026-11-21",
        "especie_declarada": "Pota",
        "cantidad": 50,
        "unidad": "kg",
        "procedencia": "Puerto del Callao"
    })

    assert lote.status_code == 201
    return lote.json()["id"]


def datos_verificacion(**cambios):
    datos = {
        "documento_tipo": "Certificado de procedencia",
        "documento_referencia": "CERT-HU09-001",
        "especie_documentada": "Pota",
        "procedencia_documentada": "Puerto del Callao",
        "verificacion": "Verificado",
        "observaciones": "Documentacion revisada"
    }
    datos.update(cambios)
    return datos


def test_hu09_registrar_verificacion_documental():
    lote_id = crear_lote()
    response = client.post(
        f"/api/lotes/{lote_id}/verificaciones",
        json=datos_verificacion()
    )
    assert response.status_code == 201
    assert response.json()["resultado"] == "Verificado"


def test_hu09_detectar_especie_inconsistente():
    lote_id = crear_lote()
    response = client.post(
        f"/api/lotes/{lote_id}/verificaciones",
        json=datos_verificacion(especie_documentada="Calamar")
    )
    assert response.status_code == 201
    assert response.json()["resultado"] == "Observado"
    assert "especie" in response.json()["observaciones"].lower()


def test_hu09_detectar_procedencia_inconsistente():
    lote_id = crear_lote()
    response = client.post(
        f"/api/lotes/{lote_id}/verificaciones",
        json=datos_verificacion(
            procedencia_documentada="Puerto de Paita"
        )
    )
    assert response.status_code == 201
    assert response.json()["resultado"] == "Observado"
    assert "procedencia" in response.json()["observaciones"].lower()


def test_hu09_consultar_historial_documental():
    lote_id = crear_lote()
    client.post(
        f"/api/lotes/{lote_id}/verificaciones",
        json=datos_verificacion()
    )

    response = client.get(
        f"/api/lotes/{lote_id}/verificaciones"
    )

    assert response.status_code == 200
    assert response.json()["total_verificaciones"] == 1
    assert response.json()["historial"][0]["documento_referencia"] == "CERT-HU09-001"


def test_hu09_rechazar_lote_inexistente():
    response = client.post(
        "/api/lotes/999999999/verificaciones",
        json=datos_verificacion()
    )
    assert response.status_code == 404


def test_hu09_rechazar_resultado_invalido():
    lote_id = crear_lote()
    response = client.post(
        f"/api/lotes/{lote_id}/verificaciones",
        json=datos_verificacion(verificacion="Rechazado")
    )
    assert response.status_code == 422


def test_hu09_rechazar_datos_incompletos():
    lote_id = crear_lote()
    response = client.post(
        f"/api/lotes/{lote_id}/verificaciones",
        json={"documento_tipo": "Certificado"}
    )
    assert response.status_code == 422


def test_hu09_rechazar_historial_lote_inexistente():
    response = client.get("/api/lotes/999999999/verificaciones")
    assert response.status_code == 404
