"""
Modelos de datos (Pydantic) para NetAdmin API.
Definen la forma y validación de los datos que entran y salen de la API.
"""

from pydantic import BaseModel
from typing import Optional


class Dispositivo(BaseModel):
    ip: str
    hostname: Optional[str] = "desconocido"
    mac: Optional[str] = "desconocida"
    tipo: Optional[str] = "desconocido"  # router, switch, servidor, PC, impresora, AP, desconocido
    sistema: Optional[str] = "desconocido"
    estado: Optional[str] = "activo"


class DispositivoActualizar(BaseModel):
    """Modelo para actualizaciones parciales (PUT) de un dispositivo."""
    hostname: Optional[str] = None
    mac: Optional[str] = None
    tipo: Optional[str] = None
    sistema: Optional[str] = None
    estado: Optional[str] = None


class ComandoRed(BaseModel):
    ip: str
    username: str
    password: str
    secret: Optional[str] = ""
    device_type: str = "cisco_ios"
    comando: str


class ComandoLinux(BaseModel):
    ip: str
    username: str
    password: str
    comando: str
