"""
Administración de equipos de red (switches/routers Cisco) usando Netmiko.
"""

from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoAuthenticationException, NetmikoTimeoutException


def ejecutar_comando_red(ip, username, password, secret, device_type, comando):
    dispositivo = {
        "device_type": device_type,
        "host": ip,
        "username": username,
        "password": password,
        "secret": secret,
    }

    try:
        conexion = ConnectHandler(**dispositivo)

        if secret:
            conexion.enable()

        salida = conexion.send_command(comando)
        conexion.disconnect()

        return salida

    except NetmikoAuthenticationException:
        return "Error: credenciales inválidas para el dispositivo."
    except NetmikoTimeoutException:
        return "Error: tiempo de espera agotado, el dispositivo no responde."
    except Exception as error:
        return f"Error al ejecutar el comando: {error}"


# Ejemplos de comandos Cisco útiles:
#   show ip interface brief
#   show version
#   show running-config
#   show vlan brief
#   show interfaces status
#   show cdp neighbors
