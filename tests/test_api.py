"""
Pruebas unitarias para NetAdmin API usando pytest + TestClient de FastAPI.
Ejecutar con: pytest -v
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.inventario import inventario

client = TestClient(app)


@pytest.fixture(autouse=True)
def limpiar_inventario():
    """Limpia el inventario en memoria antes de cada prueba."""
    inventario.clear()
    yield
    inventario.clear()


def test_raiz():
    respuesta = client.get("/")
    assert respuesta.status_code == 200
    assert respuesta.json()["mensaje"] == "NetAdmin API funcionando correctamente"


def test_crear_dispositivo():
    payload = {
        "ip": "192.168.1.1",
        "hostname": "router-principal",
        "mac": "00:11:22:33:44:55",
        "tipo": "router",
        "sistema": "Cisco IOS",
        "estado": "activo",
    }
    respuesta = client.post("/dispositivos", json=payload)
    assert respuesta.status_code == 201
    assert respuesta.json()["dispositivo"]["ip"] == "192.168.1.1"


def test_crear_dispositivo_duplicado():
    payload = {"ip": "192.168.1.1"}
    client.post("/dispositivos", json=payload)
    respuesta = client.post("/dispositivos", json=payload)
    assert respuesta.status_code == 400


def test_listar_dispositivos():
    client.post("/dispositivos", json={"ip": "192.168.1.2"})
    respuesta = client.get("/dispositivos")
    assert respuesta.status_code == 200
    assert len(respuesta.json()) == 1


def test_obtener_dispositivo_existente():
    client.post("/dispositivos", json={"ip": "192.168.1.3"})
    respuesta = client.get("/dispositivos/192.168.1.3")
    assert respuesta.status_code == 200
    assert respuesta.json()["ip"] == "192.168.1.3"


def test_obtener_dispositivo_inexistente():
    respuesta = client.get("/dispositivos/10.0.0.99")
    assert respuesta.status_code == 404


def test_actualizar_dispositivo():
    client.post("/dispositivos", json={"ip": "192.168.1.4", "tipo": "desconocido"})
    respuesta = client.put("/dispositivos/192.168.1.4", json={"tipo": "switch"})
    assert respuesta.status_code == 200
    assert respuesta.json()["dispositivo"]["tipo"] == "switch"


def test_actualizar_dispositivo_inexistente():
    respuesta = client.put("/dispositivos/10.0.0.99", json={"tipo": "switch"})
    assert respuesta.status_code == 404


def test_eliminar_dispositivo():
    client.post("/dispositivos", json={"ip": "192.168.1.5"})
    respuesta = client.delete("/dispositivos/192.168.1.5")
    assert respuesta.status_code == 200

    respuesta_verificacion = client.get("/dispositivos/192.168.1.5")
    assert respuesta_verificacion.status_code == 404


def test_eliminar_dispositivo_inexistente():
    respuesta = client.delete("/dispositivos/10.0.0.99")
    assert respuesta.status_code == 404


def test_exportar_inventario():
    client.post("/dispositivos", json={"ip": "192.168.1.6"})
    respuesta = client.get("/exportar")
    assert respuesta.status_code == 200
    assert respuesta.json()["formatos"] == ["JSON", "YAML", "XML"]
