"""
NetAdmin API
Sistema de inventario, monitoreo y administración de red.

Endpoints principales:
    GET    /dispositivos
    GET    /dispositivos/{ip}
    POST   /dispositivos
    PUT    /dispositivos/{ip}
    DELETE /dispositivos/{ip}
    POST   /escanear
    POST   /red/comando
    POST   /linux/comando
    GET    /exportar
    GET    /dashboard   (panel web de monitoreo)
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from typing import Optional

from app.modelos import Dispositivo, DispositivoActualizar, ComandoRed, ComandoLinux
from app.inventario import (
    agregar_dispositivo,
    listar_dispositivos,
    buscar_dispositivo,
    actualizar_dispositivo,
    eliminar_dispositivo,
    buscar_por_tipo_o_estado,
)
from app.escaner import escanear_red
from app.netmiko_admin import ejecutar_comando_red
from app.paramiko_admin import ejecutar_comando_linux
from app.exportador import exportar_json, exportar_yaml, exportar_xml

app = FastAPI(
    title="NetAdmin API",
    description="Sistema automatizado de inventario y administración de red",
    version="1.0",
)


@app.get("/")
def inicio():
    return {"mensaje": "NetAdmin API funcionando correctamente"}


@app.get("/dispositivos")
def obtener_dispositivos(
    tipo: Optional[str] = Query(None, description="Filtrar por tipo de dispositivo"),
    estado: Optional[str] = Query(None, description="Filtrar por estado (activo/inactivo)"),
):
    if tipo or estado:
        return buscar_por_tipo_o_estado(tipo=tipo, estado=estado)
    return listar_dispositivos()


@app.get("/dispositivos/{ip}")
def obtener_dispositivo(ip: str):
    dispositivo = buscar_dispositivo(ip)

    if dispositivo is None:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    return dispositivo


@app.post("/dispositivos", status_code=201)
def crear_dispositivo(dispositivo: Dispositivo):
    if buscar_dispositivo(dispositivo.ip) is not None:
        raise HTTPException(
            status_code=400,
            detail="Ya existe un dispositivo registrado con esa IP",
        )

    nuevo = dispositivo.model_dump()
    agregar_dispositivo(nuevo)

    return {
        "mensaje": "Dispositivo agregado correctamente",
        "dispositivo": nuevo,
    }


@app.put("/dispositivos/{ip}")
def modificar_dispositivo(ip: str, cambios: DispositivoActualizar):
    actualizado = actualizar_dispositivo(ip, cambios.model_dump())

    if actualizado is None:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    return {
        "mensaje": "Dispositivo actualizado correctamente",
        "dispositivo": actualizado,
    }


@app.delete("/dispositivos/{ip}")
def borrar_dispositivo(ip: str):
    eliminado = eliminar_dispositivo(ip)

    if not eliminado:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    return {"mensaje": "Dispositivo eliminado correctamente"}


@app.post("/escanear")
def escanear(red: str):
    try:
        resultado = escanear_red(red)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Formato de red inválido. Usa notación CIDR, ej. 192.168.1.0/24",
        )

    for dispositivo in resultado:
        agregar_dispositivo(dispositivo)

    return {
        "red": red,
        "equipos_detectados": len(resultado),
        "dispositivos": resultado,
    }


@app.post("/red/comando")
def comando_equipo_red(datos: ComandoRed):
    salida = ejecutar_comando_red(
        datos.ip,
        datos.username,
        datos.password,
        datos.secret,
        datos.device_type,
        datos.comando,
    )

    return {
        "ip": datos.ip,
        "comando": datos.comando,
        "salida": salida,
    }


@app.post("/linux/comando")
def comando_linux(datos: ComandoLinux):
    salida = ejecutar_comando_linux(
        datos.ip,
        datos.username,
        datos.password,
        datos.comando,
    )

    return {
        "ip": datos.ip,
        "comando": datos.comando,
        "salida": salida,
    }


@app.get("/exportar")
def exportar():
    datos = listar_dispositivos()

    exportar_json(datos)
    exportar_yaml(datos)
    exportar_xml({"dispositivos": datos})

    return {
        "mensaje": "Inventario exportado correctamente",
        "formatos": ["JSON", "YAML", "XML"],
    }


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    """
    Panel web de monitoreo del inventario de red.
    Consume /dispositivos vía JavaScript (fetch) y se actualiza cada 10s.
    Mejora sugerida en la Fase 13 (SHP/SHD): 'Crear dashboard web'.
    """
    return """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>NetAdmin API · Dashboard</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  :root {
    --bg: #0f172a;
    --panel: #161f38;
    --border: #263252;
    --text: #e5e9f5;
    --muted: #8b95b3;
    --accent: #4f8cff;
    --ok: #34d399;
    --off: #f87171;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    font-family: -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
    background: var(--bg);
    color: var(--text);
    padding: 32px;
  }
  h1 { margin: 0 0 4px; font-size: 22px; }
  .subtitulo { color: var(--muted); margin-bottom: 24px; font-size: 14px; }

  .tarjetas {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 16px;
    margin-bottom: 28px;
  }
  .tarjeta {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px 18px;
  }
  .tarjeta .valor { font-size: 28px; font-weight: 600; }
  .tarjeta .etiqueta { color: var(--muted); font-size: 13px; margin-top: 4px; }

  .barra {
    display: flex;
    gap: 10px;
    margin-bottom: 16px;
    flex-wrap: wrap;
  }
  input, button {
    background: var(--panel);
    border: 1px solid var(--border);
    color: var(--text);
    padding: 8px 12px;
    border-radius: 8px;
    font-size: 14px;
  }
  button {
    background: var(--accent);
    border: none;
    cursor: pointer;
    font-weight: 600;
  }
  button:hover { opacity: 0.9; }
  button.secundario {
    background: transparent;
    border: 1px solid var(--border);
  }

  table {
    width: 100%;
    border-collapse: collapse;
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 10px;
    overflow: hidden;
  }
  th, td {
    text-align: left;
    padding: 10px 14px;
    font-size: 14px;
    border-bottom: 1px solid var(--border);
  }
  th {
    color: var(--muted);
    font-weight: 600;
    text-transform: uppercase;
    font-size: 11px;
    letter-spacing: 0.04em;
  }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: rgba(79,140,255,0.06); }

  .pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 3px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
  }
  .pill.activo { background: rgba(52,211,153,0.12); color: var(--ok); }
  .pill.inactivo { background: rgba(248,113,113,0.12); color: var(--off); }
  .pill::before {
    content: "";
    width: 6px; height: 6px;
    border-radius: 50%;
    background: currentColor;
  }
  .vacio { color: var(--muted); text-align: center; padding: 30px; }
  .accion { color: var(--off); cursor: pointer; background: none; border: none; font-size: 13px; padding: 4px 8px; }
</style>
</head>
<body>

  <h1>NetAdmin API</h1>
  <div class="subtitulo">Panel de monitoreo del inventario de red · se actualiza cada 10s</div>

  <div class="tarjetas">
    <div class="tarjeta"><div class="valor" id="totalDispositivos">0</div><div class="etiqueta">Dispositivos totales</div></div>
    <div class="tarjeta"><div class="valor" id="totalActivos">0</div><div class="etiqueta">Activos</div></div>
    <div class="tarjeta"><div class="valor" id="totalInactivos">0</div><div class="etiqueta">Inactivos</div></div>
    <div class="tarjeta"><div class="valor" id="totalTipos">0</div><div class="etiqueta">Tipos distintos</div></div>
  </div>

  <div class="barra">
    <input id="filtroIp" placeholder="Buscar por IP...">
    <input id="filtroTipo" placeholder="Filtrar por tipo...">
    <button onclick="cargarDispositivos()">Actualizar</button>
    <button class="secundario" onclick="exportarInventario()">Exportar (JSON/YAML/XML)</button>
  </div>

  <table>
    <thead>
      <tr>
        <th>IP</th><th>Hostname</th><th>MAC</th><th>Tipo</th><th>Sistema</th><th>Estado</th><th></th>
      </tr>
    </thead>
    <tbody id="cuerpoTabla">
      <tr><td colspan="7" class="vacio">Cargando dispositivos...</td></tr>
    </tbody>
  </table>

<script>
async function cargarDispositivos() {
  const ip = document.getElementById('filtroIp').value.trim();
  const tipo = document.getElementById('filtroTipo').value.trim();

  const params = new URLSearchParams();
  if (tipo) params.set('tipo', tipo);

  const respuesta = await fetch('/dispositivos?' + params.toString());
  let dispositivos = await respuesta.json();

  if (ip) {
    dispositivos = dispositivos.filter(d => d.ip.includes(ip));
  }

  actualizarTarjetas(dispositivos);
  pintarTabla(dispositivos);
}

function actualizarTarjetas(dispositivos) {
  const activos = dispositivos.filter(d => d.estado === 'activo').length;
  const tipos = new Set(dispositivos.map(d => d.tipo)).size;

  document.getElementById('totalDispositivos').textContent = dispositivos.length;
  document.getElementById('totalActivos').textContent = activos;
  document.getElementById('totalInactivos').textContent = dispositivos.length - activos;
  document.getElementById('totalTipos').textContent = tipos;
}

function pintarTabla(dispositivos) {
  const cuerpo = document.getElementById('cuerpoTabla');

  if (dispositivos.length === 0) {
    cuerpo.innerHTML = '<tr><td colspan="7" class="vacio">No hay dispositivos registrados</td></tr>';
    return;
  }

  cuerpo.innerHTML = dispositivos.map(d => `
    <tr>
      <td>${d.ip}</td>
      <td>${d.hostname ?? '—'}</td>
      <td>${d.mac ?? '—'}</td>
      <td>${d.tipo ?? '—'}</td>
      <td>${d.sistema ?? '—'}</td>
      <td><span class="pill ${d.estado === 'activo' ? 'activo' : 'inactivo'}">${d.estado ?? 'desconocido'}</span></td>
      <td><button class="accion" onclick="eliminarDispositivo('${d.ip}')">Eliminar</button></td>
    </tr>
  `).join('');
}

async function eliminarDispositivo(ip) {
  if (!confirm(`¿Eliminar el dispositivo ${ip} del inventario?`)) return;
  await fetch(`/dispositivos/${ip}`, { method: 'DELETE' });
  cargarDispositivos();
}

async function exportarInventario() {
  const respuesta = await fetch('/exportar');
  const datos = await respuesta.json();
  alert('Inventario exportado: ' + datos.formatos.join(', '));
}

document.getElementById('filtroIp').addEventListener('input', cargarDispositivos);
document.getElementById('filtroTipo').addEventListener('input', cargarDispositivos);

cargarDispositivos();
setInterval(cargarDispositivos, 10000);
</script>

</body>
</html>
"""
