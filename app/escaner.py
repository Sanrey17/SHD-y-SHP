"""
Escáner básico de red.
Detecta dispositivos activos en un rango de red usando ping (ICMP).
Obtiene IP, hostname (por resolución inversa) y deja MAC/tipo/sistema
como 'pendiente' para complementarse manualmente o con herramientas
adicionales como Scapy o python-nmap (ver Tecnologías sugeridas).
"""

import ipaddress
import platform
import socket
import subprocess


def hacer_ping(ip: str) -> bool:
    """Envía un ping a la IP y regresa True si respondió."""
    sistema = platform.system().lower()

    if sistema == "windows":
        comando = ["ping", "-n", "1", "-w", "1000", ip]
    else:
        comando = ["ping", "-c", "1", "-W", "1", ip]

    resultado = subprocess.run(
        comando,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    return resultado.returncode == 0


def obtener_hostname(ip: str) -> str:
    try:
        return socket.gethostbyaddr(ip)[0]
    except (socket.herror, socket.gaierror):
        return "desconocido"


def escanear_red(red: str) -> list:
    """
    Escanea un rango de red en notación CIDR (ej. 192.168.1.0/24).
    Regresa una lista de dispositivos activos detectados.
    """
    dispositivos = []
    red_objeto = ipaddress.ip_network(red, strict=False)

    for ip in red_objeto.hosts():
        ip_texto = str(ip)

        if hacer_ping(ip_texto):
            dispositivos.append({
                "ip": ip_texto,
                "hostname": obtener_hostname(ip_texto),
                "mac": "pendiente",
                "tipo": "desconocido",
                "sistema": "desconocido",
                "estado": "activo",
            })

    return dispositivos
