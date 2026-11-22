from fastapi.testclient import TestClient
from app.main import app
import uuid

client = TestClient(app)


def crear_vendedor():
    dni = str(10000000 + (uuid.uuid4().int % 89999999))
    response = client.post("/api/vendedores", json={
        "nombre": "Vendedor HU06",
        "documento": dni,
        "telefono": "999888777",
        "puesto": "Puesto HU06",
        "ubicacion": "Lima",
        "licencia": "Pendiente"
    })
    assert response.status_code == 201
    return response.json()["id"]


def crear_inspeccion(vendedor_id):
    response = client.post("/api/inspecciones", json={
        "vendedor_id": vendedor_id,
        "inspector": "Inspector HU06",
        "higiene": "Adecuada"
    })
    assert response.status_code == 201
    return response.json()["id"]


def crear_incumplimiento(inspeccion_id):
    return client.post("/api/incumplimientos", json={
        "inspeccion_id": inspeccion_id,
        "descripcion": "Deficiencia en higiene del puesto",
        "evidencia": "Fotografia de prueba"
    })


def test_hu06_registrar_incumplimiento():
    vendedor_id = crear_vendedor()
    inspeccion_id = crear_inspeccion(vendedor_id)

    response = crear_incumplimiento(inspeccion_id)

    assert response.status_code == 201
    assert response.json()["estado"] == "Pendiente"


def test_hu06_rechazar_inspeccion_inexistente():
    response = crear_incumplimiento(999999999)
    assert response.status_code == 404


def test_hu06_actualizar_estado_seguimiento():
    vendedor_id = crear_vendedor()
    inspeccion_id = crear_inspeccion(vendedor_id)
    registro = crear_incumplimiento(inspeccion_id)

    incumplimiento_id = registro.json()["id"]

    response = client.patch(
        f"/api/incumplimientos/{incumplimiento_id}",
        json={"estado": "En proceso"}
    )

    assert response.status_code == 200
    assert response.json()["estado"] == "En proceso"


def test_hu06_rechazar_estado_invalido():
    vendedor_id = crear_vendedor()
    inspeccion_id = crear_inspeccion(vendedor_id)
    registro = crear_incumplimiento(inspeccion_id)

    response = client.patch(
        f"/api/incumplimientos/{registro.json()['id']}",
        json={"estado": "Cerrado"}
    )

    assert response.status_code == 422


def test_hu06_consultar_historial_del_vendedor():
    vendedor_id = crear_vendedor()
    inspeccion_id = crear_inspeccion(vendedor_id)

    crear_incumplimiento(inspeccion_id)
    crear_incumplimiento(inspeccion_id)

    response = client.get(
        f"/api/vendedores/{vendedor_id}/incumplimientos"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_incumplimientos"] == 2
    assert len(data["historial"]) == 2
    assert all(x["estado"] == "Pendiente" for x in data["historial"])


def test_hu06_vendedor_inexistente():
    response = client.get(
        "/api/vendedores/999999999/incumplimientos"
    )
    assert response.status_code == 404


def test_hu06_consultar_lista_general():
    vendedor_id = crear_vendedor()
    inspeccion_id = crear_inspeccion(vendedor_id)
    crear_incumplimiento(inspeccion_id)

    response = client.get("/api/incumplimientos")

    assert response.status_code == 200
    assert any(
        x["vendedor_id"] == vendedor_id
        for x in response.json()
    )


def test_hu06_actualizar_incumplimiento_inexistente():
    response = client.patch(
        "/api/incumplimientos/999999999",
        json={"estado": "Subsanado"}
    )
    assert response.status_code == 404
