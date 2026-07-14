"""
Módulo de inventario: maneja el CRUD de dispositivos en memoria.
"""

inventario = []


def agregar_dispositivo(dispositivo: dict) -> dict:
    """Agrega un dispositivo nuevo. Si la IP ya existe, la actualiza."""
    existente = buscar_dispositivo(dispositivo["ip"])
    if existente:
        existente.update(dispositivo)
        return existente

    inventario.append(dispositivo)
    return dispositivo


def listar_dispositivos() -> list:
    return inventario


def buscar_dispositivo(ip: str) -> dict | None:
    for dispositivo in inventario:
        if dispositivo["ip"] == ip:
            return dispositivo
    return None


def actualizar_dispositivo(ip: str, datos: dict) -> dict | None:
    """Actualiza campos de un dispositivo existente. datos solo trae los campos no nulos."""
    dispositivo = buscar_dispositivo(ip)
    if dispositivo is None:
        return None

    for clave, valor in datos.items():
        if valor is not None:
            dispositivo[clave] = valor

    return dispositivo


def eliminar_dispositivo(ip: str) -> bool:
    for dispositivo in inventario:
        if dispositivo["ip"] == ip:
            inventario.remove(dispositivo)
            return True
    return False


def buscar_por_tipo_o_estado(tipo: str | None = None, estado: str | None = None) -> list:
    """Filtra el inventario por tipo y/o estado (Fase 3: buscar dispositivos por tipo o estado)."""
    resultado = inventario
    if tipo:
        resultado = [d for d in resultado if d.get("tipo") == tipo]
    if estado:
        resultado = [d for d in resultado if d.get("estado") == estado]
    return resultado
