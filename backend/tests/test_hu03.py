from fastapi.testclient import TestClient
from app.main import app
import uuid

client = TestClient(app)


def crear_vendedor_prueba():
    documento = str(
        10000000 + uuid.uuid4().int % 89999999
    )

    response = client.post(
        "/api/vendedores",
        json={
            "nombre": "Vendedor HU03",
            "documento": documento,
            "telefono": "999888777",
            "puesto": "Puesto de prueba",
            "ubicacion": "Lima",
            "licencia": "Pendiente"
        }
    )

    assert response.status_code == 201
    return response.json()["id"]


def test_hu03_marcar_licencia_vigente():
    vendedor_id = crear_vendedor_prueba()

    response = client.patch(
        f"/api/vendedores/{vendedor_id}/licencia",
        json={"estado": "Vigente"}
    )

    assert response.status_code == 200
    assert response.json()["estado"] == "Vigente"


def test_hu03_marcar_licencia_observada():
    vendedor_id = crear_vendedor_prueba()

    response = client.patch(
        f"/api/vendedores/{vendedor_id}/licencia",
        json={"estado": "Observada"}
    )

    assert response.status_code == 200
    assert response.json()["estado"] == "Observada"


def test_hu03_marcar_licencia_vencida_y_consultar_perfil():
    vendedor_id = crear_vendedor_prueba()

    actualizacion = client.patch(
        f"/api/vendedores/{vendedor_id}/licencia",
        json={"estado": "Vencida"}
    )

    assert actualizacion.status_code == 200

    perfil = client.get(
        f"/api/vendedores/{vendedor_id}"
    )

    assert perfil.status_code == 200
    assert perfil.json()["licencia"] == "Vencida"


def test_hu03_rechazar_estado_invalido():
    vendedor_id = crear_vendedor_prueba()

    response = client.patch(
        f"/api/vendedores/{vendedor_id}/licencia",
        json={"estado": "Aprobada"}
    )

    assert response.status_code == 422


def test_hu03_vendedor_inexistente():
    response = client.patch(
        "/api/vendedores/999999/licencia",
        json={"estado": "Vencida"}
    )

    assert response.status_code == 404
