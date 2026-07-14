"""
Administración de equipos Linux vía SSH usando Paramiko.
"""

import paramiko


def ejecutar_comando_linux(ip, username, password, comando):
    cliente = paramiko.SSHClient()
    cliente.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        cliente.connect(
            hostname=ip,
            username=username,
            password=password,
            timeout=10,
        )

        stdin, stdout, stderr = cliente.exec_command(comando)

        salida = stdout.read().decode()
        error = stderr.read().decode()

        cliente.close()

        if error:
            return error

        return salida

    except paramiko.AuthenticationException:
        return "Error: credenciales inválidas para el dispositivo."
    except (paramiko.SSHException, TimeoutError, OSError) as error:
        return f"Error de conexión SSH: {error}"


# Ejemplos de comandos Linux útiles:
#   hostname
#   uptime
#   df -h
#   free -m
#   ip a
#   cat /etc/os-release
#   systemctl status ssh
