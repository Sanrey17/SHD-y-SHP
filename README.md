<<<<<<< HEAD
# NetAdmin API

Sistema de inventario, monitoreo y administración de red desarrollado en Python
con FastAPI. Permite escanear una red, guardar el inventario en JSON/YAML/XML,
administrar dispositivos (CRUD) y ejecutar comandos remotos en equipos Cisco
(Netmiko) y Linux (Paramiko).

## Objetivo

Desarrollar una aplicación en Python que recabe información de una red, la
almacene en formatos estructurados y la administre mediante una API REST.

## Arquitectura

```
API REST
   │
 ┌─┴──────────┐
 │            │
Inventario   Base de datos
 │
 ┌───┴──────────┐
 │              │
Descubrimiento  Administración
 │              │
Scapy/Ping   ┌──┴───────┐
             │          │
          Netmiko    Paramiko
         (Switches)   (Linux)
```

| Función                          | Librería            |
|-----------------------------------|----------------------|
| Descubrir equipos                 | ping / Scapy / python-nmap |
| Administrar equipos Cisco         | Netmiko              |
| Conexión SSH genérica             | Paramiko             |
| API REST                          | FastAPI              |
| Exportación                       | JSON, YAML, XML      |
| Pruebas                           | Pytest / Postman     |

## Estructura del proyecto

```
netadmin_api/
│
├── app/
│   ├── main.py            # API REST (endpoints)
│   ├── modelos.py         # Modelos Pydantic
│   ├── inventario.py      # CRUD en memoria
│   ├── escaner.py         # Escaneo de red (ping sweep)
│   ├── netmiko_admin.py   # Administración de equipos Cisco
│   ├── paramiko_admin.py  # Administración de equipos Linux (SSH)
│   └── exportador.py      # Exportación JSON / YAML / XML
│
├── data/                  # Inventario exportado
├── tests/
│   └── test_api.py        # Pruebas unitarias (pytest)
├── requirements.txt
└── README.md
```

## Instalación

### 1. Crear y activar entorno virtual

**Windows:**

```bash
python -m venv venv
venv\Scripts\activate
```

**Linux / macOS:**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

# Uso

## Ejecutar el servidor

```bash
uvicorn app.main:app --reload
```

Servicios disponibles:

- API:
```
http://127.0.0.1:8000
```

- Dashboard web del inventario:
```
http://127.0.0.1:8000/dashboard
```

- Documentación interactiva Swagger:
```
http://127.0.0.1:8000/docs
```

- Documentación alternativa ReDoc:
```
http://127.0.0.1:8000/redoc
```

### Ejecutar pruebas unitarias

```bash
pytest -v
```

# Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/` | Verifica que la API está funcionando |
| GET | `/dashboard` | Dashboard web del inventario |
| GET | `/dispositivos` | Lista todos los dispositivos (admite filtros `?tipo=` y `?estado=`) |
| GET | `/dispositivos/{ip}` | Obtiene un dispositivo por IP |
| POST | `/dispositivos` | Agrega un dispositivo manualmente |
| PUT | `/dispositivos/{ip}` | Actualiza datos de un dispositivo |
| DELETE | `/dispositivos/{ip}` | Elimina un dispositivo del inventario |
| POST | `/escanear?red=CIDR` | Escanea una red (ej. `192.168.1.0/24`) |
| POST | `/red/comando` | Ejecuta un comando en un equipo Cisco (Netmiko) |
| POST | `/linux/comando` | Ejecuta un comando en un equipo Linux (Paramiko) |
| GET | `/exportar` | Exporta el inventario a JSON, YAML y XML |

## Ejemplos de prueba en Postman

### Agregar dispositivo — `POST /dispositivos`

```json
{
    "ip": "192.168.1.1",
    "hostname": "router-principal",
    "mac": "00:11:22:33:44:55",
    "tipo": "router",
    "sistema": "Cisco IOS",
    "estado": "activo"
}
```

### Comando en Cisco — `POST /red/comando`

```json
{
    "ip": "192.168.1.1",
    "username": "admin",
    "password": "cisco",
    "secret": "class",
    "device_type": "cisco_ios",
    "comando": "show ip interface brief"
}
```

### Comando en Linux — `POST /linux/comando`

```json
{
    "ip": "192.168.1.10",
    "username": "usuario",
    "password": "password",
    "comando": "hostname && uptime && df -h"
}
```

## Tabla de diagnóstico de errores HTTP

| Código | Significado | Cuándo ocurre |
|--------|-------------|---------------|
| 200 | OK | Petición GET/PUT/DELETE exitosa |
| 201 | Created | Dispositivo creado correctamente |
| 400 | Bad Request | Datos inválidos o IP duplicada |
| 401 | Unauthorized | Autenticación pendiente |
| 403 | Forbidden | Permisos insuficientes |
| 404 | Not Found | Dispositivo no encontrado |
| 500 | Internal Server Error | Error interno del servidor |

## Alcance recomendado

Limitar las pruebas a una red local o simulada, por ejemplo:

```
192.168.1.0/24
```

administrando únicamente dispositivos detectados o registrados manualmente.

## Mejoras futuras

- Base de datos SQLite en lugar de inventario en memoria.
- Autenticación por token (JWT / API Key).
- Escaneo automático programado.
- Histórico de cambios.
- Reportes PDF y alertas.

## Trabajo colaborativo

- Repositorio GitHub con ramas por equipo.
- Uso de issues, commits y pull requests.
- Documentación completa del proyecto.

## Autor / Equipo

_Completar con nombres del equipo._