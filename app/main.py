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
    GET    /estado           (versión y tiempo activo del servidor)
    GET    /dashboard        (panel web de monitoreo)
    /data/*                  (descarga de inventario.json / .yaml / .xml exportados)
"""

import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

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
    version="1.0.0",
)

# Momento en que arrancó el proceso; usado por /estado para calcular el uptime real.
INICIO_SERVIDOR = datetime.now(timezone.utc)

# Sirve los archivos exportados (data/inventario.json, .yaml, .xml) para poder
# descargarlos directamente desde el panel web.
os.makedirs("data", exist_ok=True)
app.mount("/data", StaticFiles(directory="data"), name="data")


@app.get("/")
def inicio():
    return {"mensaje": "NetAdmin API funcionando correctamente"}


@app.get("/estado")
def estado():
    """Versión y tiempo real que lleva corriendo el proceso, usado por el
    panel lateral del dashboard (sin datos inventados: si el proceso
    reinicia, el uptime vuelve a cero, como debe ser)."""
    ahora = datetime.now(timezone.utc)
    segundos = int((ahora - INICIO_SERVIDOR).total_seconds())
    return {
        "en_linea": True,
        "version": app.version,
        "uptime_segundos": segundos,
    }


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
    """Panel web de administración: dashboard, CRUD de dispositivos, escaneo
    de red, comandos remotos (Netmiko/Paramiko), exportación y acceso a la
    documentación — todo conectado a los endpoints reales de arriba."""
    return _HTML_DASHBOARD


_HTML_DASHBOARD = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>NetAdmin API · Panel de administración</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

  :root {
    --bg: #0A0E14;
    --sidebar: #0D1119;
    --panel: #121822;
    --panel-2: #0E1420;
    --border: #202836;
    --text: #E6EDF3;
    --muted: #7C8798;
    --primary: #3B82F6;
    --primary-dim: rgba(59,130,246,0.12);
    --signal: #22C55E;
    --signal-dim: rgba(34,197,94,0.12);
    --alert: #F59E0B;
    --alert-dim: rgba(245,158,11,0.12);
    --danger: #EF4444;
    --danger-dim: rgba(239,68,68,0.12);
    --purple: #A78BFA;
    --purple-dim: rgba(167,139,250,0.12);
    --mono: 'JetBrains Mono', ui-monospace, Menlo, monospace;
    --sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    --display: 'Space Grotesk', var(--sans);
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; height: 100%; }
  body {
    font-family: var(--sans);
    background: var(--bg);
    color: var(--text);
    display: flex;
    min-height: 100vh;
  }
  a { color: var(--primary); text-decoration: none; }
  svg { display: block; }

  /* ---------- Sidebar ---------- */
  .sidebar {
    width: 240px;
    flex-shrink: 0;
    background: var(--sidebar);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    padding: 20px 14px;
    position: sticky;
    top: 0;
    height: 100vh;
  }
  .marca { display: flex; align-items: center; gap: 10px; padding: 6px 8px 20px; }
  .marca .icono {
    width: 36px; height: 36px; border-radius: 9px;
    background: var(--primary-dim); display: flex; align-items: center; justify-content: center;
    color: var(--primary);
  }
  .marca h1 { font-family: var(--display); font-size: 15px; font-weight: 700; margin: 0; }
  .marca small { display: block; color: var(--muted); font-size: 11px; margin-top: 1px; }

  nav { display: flex; flex-direction: column; gap: 2px; }
  .nav-item {
    display: flex; align-items: center; gap: 11px;
    padding: 9px 12px; border-radius: 8px;
    color: var(--muted); font-size: 13.5px; font-weight: 500;
    cursor: pointer; border: none; background: transparent; width: 100%; text-align: left;
    font-family: var(--sans);
  }
  .nav-item:hover { background: #161D29; color: var(--text); }
  .nav-item.activo { background: var(--primary-dim); color: var(--primary); font-weight: 600; }
  .nav-item svg { width: 17px; height: 17px; flex-shrink: 0; }

  .sidebar-footer {
    margin-top: auto;
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 12px 14px;
    font-size: 12px;
  }
  .estado-linea { display: flex; align-items: center; gap: 7px; color: var(--signal); font-weight: 600; margin-bottom: 8px; }
  .estado-linea .punto {
    width: 7px; height: 7px; border-radius: 50%; background: var(--signal);
    box-shadow: 0 0 0 0 rgba(34,197,94,0.6); animation: pulso 2s infinite;
  }
  @keyframes pulso {
    0%   { box-shadow: 0 0 0 0 rgba(34,197,94,0.5); }
    70%  { box-shadow: 0 0 0 7px rgba(34,197,94,0); }
    100% { box-shadow: 0 0 0 0 rgba(34,197,94,0); }
  }
  .sidebar-footer .fila { display: flex; justify-content: space-between; color: var(--muted); padding: 2px 0; font-family: var(--mono); font-size: 11.5px; }
  .sidebar-footer .fila span:last-child { color: var(--text); }

  /* ---------- Contenido ---------- */
  .contenido { flex: 1; padding: 26px 32px 60px; max-width: 1400px; }

  .encabezado {
    display: flex; align-items: flex-start; justify-content: space-between;
    margin-bottom: 24px; flex-wrap: wrap; gap: 12px;
  }
  .encabezado h2 { font-family: var(--display); font-size: 23px; font-weight: 700; margin: 0 0 4px; }
  .encabezado .subtitulo { color: var(--muted); font-size: 13px; }
  .encabezado .subtitulo .punto-verde { color: var(--signal); }
  .encabezado-derecha { display: flex; align-items: center; gap: 14px; }
  .reloj { font-family: var(--mono); color: var(--muted); font-size: 13px; display: flex; align-items: center; gap: 6px; }
  .btn-icono {
    width: 36px; height: 36px; border-radius: 8px; border: 1px solid var(--border);
    background: var(--panel); color: var(--muted); display: flex; align-items: center; justify-content: center;
    cursor: pointer;
  }
  .btn-icono:hover { color: var(--text); border-color: #33404f; }
  .btn-icono svg { width: 16px; height: 16px; }
  .btn-icono.girando svg { animation: girar 0.6s linear; }
  @keyframes girar { to { transform: rotate(360deg); } }

  /* Cards */
  .tarjetas { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 22px; }
  @media (max-width: 1050px) { .tarjetas { grid-template-columns: repeat(2, 1fr); } }
  .tarjeta {
    background: var(--panel); border: 1px solid var(--border); border-radius: 12px;
    padding: 18px 18px 16px; display: flex; gap: 14px; align-items: flex-start;
  }
  .tarjeta .icono {
    width: 46px; height: 46px; border-radius: 10px; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center;
  }
  .tarjeta .icono svg { width: 22px; height: 22px; }
  .tarjeta.total .icono { background: var(--primary-dim); color: var(--primary); }
  .tarjeta.activos .icono { background: var(--signal-dim); color: var(--signal); }
  .tarjeta.inactivos .icono { background: var(--alert-dim); color: var(--alert); }
  .tarjeta.tipos .icono { background: var(--purple-dim); color: var(--purple); }
  .tarjeta .valor { font-family: var(--display); font-size: 26px; font-weight: 700; line-height: 1.1; }
  .tarjeta .etiqueta { color: var(--muted); font-size: 12.5px; margin-top: 2px; }
  .tarjeta .extra { font-size: 11.5px; margin-top: 6px; color: var(--muted); }
  .barra-mini { height: 4px; border-radius: 3px; background: #1B2330; margin-top: 8px; overflow: hidden; }
  .barra-mini .relleno { height: 100%; border-radius: 3px; }

  /* Panel principal / tablas */
  .panel {
    background: var(--panel); border: 1px solid var(--border); border-radius: 12px; overflow: hidden;
  }
  .panel + .panel { margin-top: 18px; }
  .panel-titulo {
    padding: 14px 18px; border-bottom: 1px solid var(--border);
    font-family: var(--display); font-weight: 600; font-size: 14.5px;
  }
  .panel-titulo .desc { color: var(--muted); font-weight: 400; font-size: 12px; font-family: var(--sans); margin-top: 2px; }

  .barra-filtros { display: flex; gap: 10px; padding: 14px 18px; flex-wrap: wrap; border-bottom: 1px solid var(--border); }
  .campo-busqueda { position: relative; flex: 1; min-width: 220px; }
  .campo-busqueda svg { position: absolute; left: 11px; top: 50%; transform: translateY(-50%); width: 15px; height: 15px; color: var(--muted); }
  .campo-busqueda input { width: 100%; padding-left: 34px; }

  input, select, textarea {
    background: var(--panel-2); border: 1px solid var(--border); color: var(--text);
    padding: 9px 12px; border-radius: 7px; font-size: 13px; font-family: var(--mono);
  }
  select { font-family: var(--sans); cursor: pointer; }
  input:focus, select:focus, textarea:focus { outline: none; border-color: var(--primary); }
  input::placeholder { color: var(--muted); font-family: var(--sans); }

  button.btn {
    border: none; border-radius: 7px; padding: 9px 16px; font-size: 13px; font-weight: 600;
    cursor: pointer; font-family: var(--sans); transition: filter .15s, transform .1s;
    display: inline-flex; align-items: center; gap: 7px;
  }
  button.btn:hover { filter: brightness(1.12); }
  button.btn:active { transform: scale(0.97); }
  button.btn svg { width: 14px; height: 14px; }
  .btn-primario { background: var(--primary); color: #fff; }
  .btn-exito { background: var(--signal); color: #04140D; }
  .btn-secundario { background: transparent; color: var(--text); border: 1px solid var(--border); }
  .btn-peligro { background: transparent; color: var(--danger); border: 1px solid #402028; padding: 5px 11px; font-size: 11.5px; }

  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  thead th {
    text-align: left; padding: 10px 18px; color: var(--muted); font-size: 10.5px;
    text-transform: uppercase; letter-spacing: 0.6px; font-weight: 600; border-bottom: 1px solid var(--border);
  }
  tbody td { padding: 11px 18px; border-bottom: 1px solid #182030; font-family: var(--mono); }
  tbody tr:hover td { background: #151C28; }
  tbody td:first-child { color: var(--primary); }
  tbody td.col-acciones { display: flex; gap: 6px; font-family: var(--sans); }

  .pill { display: inline-flex; align-items: center; gap: 6px; padding: 3px 10px; border-radius: 999px; font-size: 11px; font-weight: 600; font-family: var(--sans); }
  .pill.activo { background: var(--signal-dim); color: var(--signal); }
  .pill.inactivo { background: var(--alert-dim); color: var(--alert); }
  .pill::before { content: ""; width: 6px; height: 6px; border-radius: 50%; background: currentColor; }

  .vacio { color: var(--muted); text-align: center; padding: 40px; font-family: var(--sans); }

  .paginacion { display: flex; align-items: center; justify-content: space-between; padding: 12px 18px; font-size: 12.5px; color: var(--muted); }
  .paginacion .paginas { display: flex; gap: 4px; }
  .paginacion button {
    width: 28px; height: 28px; border-radius: 6px; border: 1px solid var(--border); background: var(--panel-2);
    color: var(--muted); cursor: pointer; font-family: var(--mono); font-size: 12px;
  }
  .paginacion button.activo { background: var(--primary); color: #fff; border-color: var(--primary); }
  .paginacion button:disabled { opacity: 0.4; cursor: default; }

  /* Formularios */
  .form-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; padding: 18px; }
  @media (max-width: 900px) { .form-grid { grid-template-columns: repeat(2, 1fr); } }
  .campo { display: flex; flex-direction: column; gap: 5px; }
  .campo label { font-size: 11.5px; color: var(--muted); font-weight: 600; text-transform: uppercase; letter-spacing: 0.4px; }
  .form-acciones { padding: 0 18px 18px; display: flex; gap: 10px; }

  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
  @media (max-width: 900px) { .grid-2 { grid-template-columns: 1fr; } }

  pre.salida {
    background: var(--panel-2); border: 1px solid var(--border); border-radius: 8px;
    padding: 14px; font-family: var(--mono); font-size: 12.5px; color: var(--signal);
    white-space: pre-wrap; word-break: break-word; margin: 0 18px 18px; max-height: 280px; overflow-y: auto;
  }

  .aviso { margin: 0 18px 18px; padding: 10px 14px; border-radius: 8px; font-size: 12.5px; font-family: var(--mono); }
  .aviso.ok { background: var(--signal-dim); color: var(--signal); }
  .aviso.error { background: var(--danger-dim); color: var(--danger); }

  .lista-descargas { display: flex; gap: 10px; padding: 0 18px 18px; flex-wrap: wrap; }
  .lista-descargas a {
    display: flex; align-items: center; gap: 8px; background: var(--panel-2); border: 1px solid var(--border);
    padding: 10px 14px; border-radius: 8px; color: var(--text); font-family: var(--mono); font-size: 12.5px;
  }
  .lista-descargas a:hover { border-color: var(--primary); color: var(--primary); }
  .lista-descargas a svg { width: 14px; height: 14px; }

  .vista { display: none; }
  .vista.activa { display: block; }

  .barra-tipo { display: flex; align-items: center; gap: 10px; padding: 9px 18px; }
  .barra-tipo .nombre { width: 110px; font-size: 12.5px; text-transform: capitalize; }
  .barra-tipo .pista { flex: 1; height: 8px; border-radius: 4px; background: #1B2330; overflow: hidden; }
  .barra-tipo .pista .relleno { height: 100%; background: var(--primary); border-radius: 4px; }
  .barra-tipo .cantidad { width: 34px; text-align: right; font-family: var(--mono); font-size: 12.5px; color: var(--muted); }

  ::-webkit-scrollbar { width: 8px; height: 8px; }
  ::-webkit-scrollbar-thumb { background: #26303F; border-radius: 4px; }
</style>
</head>
<body>

  <aside class="sidebar">
    <div class="marca">
      <span class="icono">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="14" width="8" height="8" rx="1.5"/><circle cx="18" cy="6" r="3"/><path d="M6 14V9a2 2 0 0 1 2-2h6"/><circle cx="6" cy="18" r="0" /></svg>
      </span>
      <div>
        <h1>NetAdmin API</h1>
        <small>Gestión de inventario de red</small>
      </div>
    </div>

    <nav>
      <button class="nav-item activo" data-vista="dashboard" onclick="cambiarVista('dashboard', this)">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/></svg>
        Dashboard
      </button>
      <button class="nav-item" data-vista="dispositivos" onclick="cambiarVista('dispositivos', this)">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="5" rx="1.5"/><rect x="2" y="15" width="20" height="5" rx="1.5"/><line x1="6" y1="6.5" x2="6" y2="6.5"/><line x1="6" y1="17.5" x2="6" y2="17.5"/></svg>
        Dispositivos
      </button>
      <button class="nav-item" data-vista="escaneo" onclick="cambiarVista('escaneo', this)">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 12 L18 7"/><circle cx="12" cy="12" r="1.5" fill="currentColor"/></svg>
        Escaneo de red
      </button>
      <button class="nav-item" data-vista="comandos" onclick="cambiarVista('comandos', this)">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="M6 9l4 3-4 3"/><line x1="12" y1="15" x2="17" y2="15"/></svg>
        Comandos
      </button>
      <button class="nav-item" data-vista="reportes" onclick="cambiarVista('reportes', this)">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 2h9l5 5v15H6z"/><line x1="9" y1="13" x2="15" y2="13"/><line x1="9" y1="17" x2="15" y2="17"/></svg>
        Reportes
      </button>
      <button class="nav-item" data-vista="exportaciones" onclick="cambiarVista('exportaciones', this)">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v12"/><path d="M7 10l5 5 5-5"/><path d="M4 19h16"/></svg>
        Exportaciones
      </button>
      <button class="nav-item" data-vista="documentacion" onclick="cambiarVista('documentacion', this)">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20V4H6.5A2.5 2.5 0 0 0 4 6.5v13z"/><line x1="8" y1="7" x2="15" y2="7"/><line x1="8" y1="11" x2="15" y2="11"/></svg>
        Documentación API
      </button>
    </nav>

    <div class="sidebar-footer">
      <div class="estado-linea"><span class="punto"></span> API en línea</div>
      <div class="fila"><span>Versión</span><span id="pieVersion">—</span></div>
      <div class="fila"><span>Uptime</span><span id="pieUptime">—</span></div>
    </div>
  </aside>

  <main class="contenido">

    <div class="encabezado">
      <div>
        <h2 id="tituloVista">Dashboard</h2>
        <div class="subtitulo" id="subtituloVista">Panel de monitoreo del inventario de red · <span class="punto-verde">se actualiza cada 10s</span></div>
      </div>
      <div class="encabezado-derecha">
        <span class="reloj">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 3"/></svg>
          <span id="reloj">--:--:--</span>
        </span>
        <button class="btn-icono" id="btnRefrescar" onclick="refrescarManual()" title="Actualizar">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 1 1-3-6.7"/><path d="M21 4v5h-5"/></svg>
        </button>
      </div>
    </div>

    <!-- ============ VISTA: DASHBOARD ============ -->
    <section class="vista activa" id="vista-dashboard">
      <div class="tarjetas">
        <div class="tarjeta total">
          <span class="icono"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="6" rx="1.5"/><rect x="2" y="15" width="20" height="6" rx="1.5"/><line x1="6" y1="6" x2="6" y2="6"/><line x1="6" y1="18" x2="6" y2="18"/></svg></span>
          <div><div class="valor" id="v-total">0</div><div class="etiqueta">Dispositivos totales</div></div>
        </div>
        <div class="tarjeta activos">
          <span class="icono"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M8 12l2.5 2.5L16 9"/></svg></span>
          <div>
            <div class="valor" id="v-activos">0</div><div class="etiqueta">Activos</div>
            <div class="extra" id="v-activos-pct">0% del total</div>
            <div class="barra-mini"><div class="relleno" id="barra-activos" style="width:0%;background:var(--signal)"></div></div>
          </div>
        </div>
        <div class="tarjeta inactivos">
          <span class="icono"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><line x1="9" y1="9" x2="15" y2="15"/><line x1="15" y1="9" x2="9" y2="15"/></svg></span>
          <div>
            <div class="valor" id="v-inactivos">0</div><div class="etiqueta">Inactivos</div>
            <div class="extra" id="v-inactivos-pct">0% del total</div>
            <div class="barra-mini"><div class="relleno" id="barra-inactivos" style="width:0%;background:var(--alert)"></div></div>
          </div>
        </div>
        <div class="tarjeta tipos">
          <span class="icono"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg></span>
          <div><div class="valor" id="v-tipos">0</div><div class="etiqueta">Tipos distintos</div><div class="extra">Diversidad de dispositivos</div></div>
        </div>
      </div>

      <div class="panel">
        <div class="barra-filtros">
          <div class="campo-busqueda">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            <input id="filtroTexto" placeholder="Buscar por IP, hostname o MAC...">
          </div>
          <select id="filtroTipo"><option value="">Filtrar por tipo...</option></select>
          <select id="filtroEstado">
            <option value="">Filtrar por estado...</option>
            <option value="activo">Activo</option>
            <option value="inactivo">Inactivo</option>
          </select>
        </div>

        <table>
          <thead>
            <tr><th>IP</th><th>Hostname</th><th>MAC</th><th>Tipo</th><th>Sistema</th><th>Estado</th><th></th></tr>
          </thead>
          <tbody id="cuerpoTabla">
            <tr><td colspan="7" class="vacio">Cargando dispositivos...</td></tr>
          </tbody>
        </table>

        <div class="paginacion">
          <span id="resumenPaginacion">Mostrando 0 de 0 dispositivos</span>
          <div class="paginas" id="paginasContenedor"></div>
        </div>
      </div>
    </section>

    <!-- ============ VISTA: DISPOSITIVOS (alta / edición) ============ -->
    <section class="vista" id="vista-dispositivos">
      <div class="panel">
        <div class="panel-titulo">
          Agregar / editar dispositivo
          <div class="desc">Completa la IP para agregar uno nuevo, o usa "Editar" en la tabla para modificar uno existente.</div>
        </div>
        <div class="form-grid">
          <div class="campo"><label>IP</label><input id="f-ip" placeholder="192.168.1.50"></div>
          <div class="campo"><label>Hostname</label><input id="f-hostname" placeholder="pc-recepcion"></div>
          <div class="campo"><label>MAC</label><input id="f-mac" placeholder="AA:BB:CC:DD:EE:FF"></div>
          <div class="campo">
            <label>Tipo</label>
            <select id="f-tipo">
              <option value="router">router</option>
              <option value="switch">switch</option>
              <option value="servidor">servidor</option>
              <option value="pc" selected>pc</option>
              <option value="impresora">impresora</option>
              <option value="ap">ap</option>
              <option value="desconocido">desconocido</option>
            </select>
          </div>
          <div class="campo"><label>Sistema</label><input id="f-sistema" placeholder="Windows 11"></div>
          <div class="campo">
            <label>Estado</label>
            <select id="f-estado"><option value="activo" selected>activo</option><option value="inactivo">inactivo</option></select>
          </div>
        </div>
        <div class="form-acciones">
          <button class="btn btn-primario" id="btnGuardarDispositivo" onclick="guardarDispositivo()">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
            Agregar dispositivo
          </button>
          <button class="btn btn-secundario" onclick="limpiarFormulario()">Cancelar edición</button>
        </div>
        <div id="avisoFormulario"></div>
      </div>

      <div class="panel">
        <div class="panel-titulo">Todos los dispositivos</div>
        <table>
          <thead><tr><th>IP</th><th>Hostname</th><th>MAC</th><th>Tipo</th><th>Sistema</th><th>Estado</th><th></th></tr></thead>
          <tbody id="cuerpoTablaDispositivos"><tr><td colspan="7" class="vacio">Cargando...</td></tr></tbody>
        </table>
      </div>
    </section>

    <!-- ============ VISTA: ESCANEO ============ -->
    <section class="vista" id="vista-escaneo">
      <div class="panel">
        <div class="panel-titulo">
          Escanear una red
          <div class="desc">Hace ping a cada IP del rango y agrega automáticamente los equipos que respondan.</div>
        </div>
        <div class="form-grid" style="grid-template-columns: 2fr 1fr;">
          <div class="campo"><label>Red (CIDR)</label><input id="f-red-escaneo" placeholder="192.168.1.0/24"></div>
        </div>
        <div class="form-acciones">
          <button class="btn btn-primario" id="btnEscanear" onclick="escanearRed()">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            Escanear red
          </button>
        </div>
        <div id="avisoEscaneo"></div>
      </div>

      <div class="panel" id="panelResultadoEscaneo" style="display:none;">
        <div class="panel-titulo">Equipos detectados</div>
        <table>
          <thead><tr><th>IP</th><th>Estado</th></tr></thead>
          <tbody id="cuerpoResultadoEscaneo"></tbody>
        </table>
      </div>
    </section>

    <!-- ============ VISTA: COMANDOS ============ -->
    <section class="vista" id="vista-comandos">
      <div class="grid-2">
        <div class="panel">
          <div class="panel-titulo">Comando en equipo Cisco <span class="desc">(Netmiko, vía SSH)</span></div>
          <div class="form-grid" style="grid-template-columns: 1fr 1fr;">
            <div class="campo"><label>IP</label><input id="cr-ip" placeholder="192.168.1.1"></div>
            <div class="campo">
              <label>Tipo de equipo</label>
              <select id="cr-device-type">
                <option value="cisco_ios">cisco_ios</option>
                <option value="cisco_xe">cisco_xe</option>
                <option value="cisco_nxos">cisco_nxos</option>
              </select>
            </div>
            <div class="campo"><label>Usuario</label><input id="cr-user" placeholder="admin"></div>
            <div class="campo"><label>Password</label><input id="cr-pass" type="password" placeholder="••••••"></div>
            <div class="campo"><label>Secret (enable)</label><input id="cr-secret" type="password" placeholder="opcional"></div>
            <div class="campo"><label>Comando</label><input id="cr-comando" placeholder="show ip interface brief"></div>
          </div>
          <div class="form-acciones">
            <button class="btn btn-primario" onclick="ejecutarComandoRed()">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9l4 3-4 3"/><line x1="12" y1="15" x2="17" y2="15"/></svg>
              Ejecutar
            </button>
          </div>
          <div id="avisoComandoRed"></div>
          <pre class="salida" id="salidaComandoRed" style="display:none;"></pre>
        </div>

        <div class="panel">
          <div class="panel-titulo">Comando en host Linux <span class="desc">(Paramiko, vía SSH)</span></div>
          <div class="form-grid" style="grid-template-columns: 1fr 1fr;">
            <div class="campo"><label>IP</label><input id="cl-ip" placeholder="192.168.1.10"></div>
            <div class="campo"><label>Usuario</label><input id="cl-user" placeholder="usuario"></div>
            <div class="campo"><label>Password</label><input id="cl-pass" type="password" placeholder="••••••"></div>
            <div class="campo"><label>Comando</label><input id="cl-comando" placeholder="hostname && uptime"></div>
          </div>
          <div class="form-acciones">
            <button class="btn btn-primario" onclick="ejecutarComandoLinux()">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9l4 3-4 3"/><line x1="12" y1="15" x2="17" y2="15"/></svg>
              Ejecutar
            </button>
          </div>
          <div id="avisoComandoLinux"></div>
          <pre class="salida" id="salidaComandoLinux" style="display:none;"></pre>
        </div>
      </div>
    </section>

    <!-- ============ VISTA: REPORTES ============ -->
    <section class="vista" id="vista-reportes">
      <div class="panel">
        <div class="panel-titulo">Distribución por tipo de dispositivo</div>
        <div id="reporteTipos" style="padding: 14px 0;"></div>
      </div>
      <div class="panel">
        <div class="panel-titulo">Dispositivos inactivos <span class="desc">requieren atención</span></div>
        <table>
          <thead><tr><th>IP</th><th>Hostname</th><th>Tipo</th></tr></thead>
          <tbody id="reporteInactivos"><tr><td colspan="3" class="vacio">Cargando...</td></tr></tbody>
        </table>
      </div>
    </section>

    <!-- ============ VISTA: EXPORTACIONES ============ -->
    <section class="vista" id="vista-exportaciones">
      <div class="panel">
        <div class="panel-titulo">
          Exportar inventario
          <div class="desc">Genera data/inventario.json, .yaml y .xml en el servidor y los deja listos para descargar.</div>
        </div>
        <div class="form-acciones" style="padding-top:18px;">
          <button class="btn btn-exito" onclick="exportarInventario()">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v12"/><path d="M7 10l5 5 5-5"/><path d="M4 19h16"/></svg>
            Generar exportación
          </button>
        </div>
        <div id="avisoExportar"></div>
        <div class="lista-descargas" id="listaDescargas" style="display:none;">
          <a href="/data/inventario.json" download>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/></svg>
            inventario.json
          </a>
          <a href="/data/inventario.yaml" download>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/></svg>
            inventario.yaml
          </a>
          <a href="/data/inventario.xml" download>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/></svg>
            inventario.xml
          </a>
        </div>
      </div>
    </section>

    <!-- ============ VISTA: DOCUMENTACIÓN ============ -->
    <section class="vista" id="vista-documentacion">
      <div class="panel">
        <div class="panel-titulo">Documentación interactiva de la API</div>
        <div style="padding: 18px; color: var(--muted); font-size: 13.5px; line-height: 1.6;">
          NetAdmin API expone documentación generada automáticamente por FastAPI (Swagger UI y ReDoc),
          donde puedes probar cada endpoint directamente desde el navegador.
        </div>
        <div class="form-acciones" style="padding-top:0;">
          <a class="btn btn-primario" href="/docs" target="_blank" style="text-decoration:none;">Abrir /docs (Swagger)</a>
          <a class="btn btn-secundario" href="/redoc" target="_blank" style="text-decoration:none;">Abrir /redoc</a>
        </div>
      </div>
    </section>

  </main>

<script>
const TITULOS = {
  dashboard: ["Dashboard", 'Panel de monitoreo del inventario de red · <span class="punto-verde">se actualiza cada 10s</span>'],
  dispositivos: ["Dispositivos", "Alta, edición y baja de equipos del inventario"],
  escaneo: ["Escaneo de red", "Descubre equipos activos en un rango CIDR"],
  comandos: ["Comandos remotos", "Ejecuta comandos vía Netmiko (Cisco) y Paramiko (Linux)"],
  reportes: ["Reportes", "Resumen del estado actual de la red"],
  exportaciones: ["Exportaciones", "Descarga el inventario en JSON, YAML o XML"],
  documentacion: ["Documentación API", "Swagger y ReDoc generados automáticamente"],
};

let dispositivosCache = [];
let paginaActual = 1;
const POR_PAGINA = 8;
let editandoIp = null;

function cambiarVista(id, boton) {
  document.querySelectorAll('.vista').forEach(v => v.classList.remove('activa'));
  document.getElementById('vista-' + id).classList.add('activa');
  document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('activo'));
  boton.classList.add('activo');
  document.getElementById('tituloVista').textContent = TITULOS[id][0];
  document.getElementById('subtituloVista').innerHTML = TITULOS[id][1];

  if (id === 'dispositivos') pintarTablaDispositivos();
  if (id === 'reportes') pintarReportes();
}

function actualizarReloj() {
  document.getElementById('reloj').textContent = new Date().toLocaleTimeString('es-MX', { hour12: false });
}
setInterval(actualizarReloj, 1000);
actualizarReloj();

async function cargarEstado() {
  try {
    const r = await fetch('/estado');
    const d = await r.json();
    document.getElementById('pieVersion').textContent = 'v' + d.version;
    const h = Math.floor(d.uptime_segundos / 3600);
    const m = Math.floor((d.uptime_segundos % 3600) / 60);
    const s = d.uptime_segundos % 60;
    document.getElementById('pieUptime').textContent =
      String(h).padStart(2,'0') + ':' + String(m).padStart(2,'0') + ':' + String(s).padStart(2,'0');
  } catch (e) { /* silencioso: el pie no debe romper el panel si /estado falla */ }
}

async function cargarDispositivos() {
  const r = await fetch('/dispositivos');
  dispositivosCache = await r.json();
  poblarFiltroTipo();
  aplicarFiltrosYRenderizar();
  actualizarTarjetas();
}

function poblarFiltroTipo() {
  const select = document.getElementById('filtroTipo');
  const actual = select.value;
  const tipos = [...new Set(dispositivosCache.map(d => d.tipo))].sort();
  select.innerHTML = '<option value="">Filtrar por tipo...</option>' +
    tipos.map(t => `<option value="${t}">${t}</option>`).join('');
  select.value = actual;
}

function aplicarFiltrosYRenderizar() {
  const texto = document.getElementById('filtroTexto').value.trim().toLowerCase();
  const tipo = document.getElementById('filtroTipo').value;
  const estado = document.getElementById('filtroEstado').value;

  let filtrados = dispositivosCache.filter(d => {
    const coincideTexto = !texto || [d.ip, d.hostname, d.mac].join(' ').toLowerCase().includes(texto);
    const coincideTipo = !tipo || d.tipo === tipo;
    const coincideEstado = !estado || d.estado === estado;
    return coincideTexto && coincideTipo && coincideEstado;
  });

  if (paginaActual > Math.ceil(filtrados.length / POR_PAGINA)) paginaActual = 1;
  pintarTabla(filtrados);
  pintarPaginacion(filtrados);
}

function actualizarTarjetas() {
  const total = dispositivosCache.length;
  const activos = dispositivosCache.filter(d => d.estado === 'activo').length;
  const inactivos = total - activos;
  const tipos = new Set(dispositivosCache.map(d => d.tipo)).size;

  document.getElementById('v-total').textContent = total;
  document.getElementById('v-activos').textContent = activos;
  document.getElementById('v-inactivos').textContent = inactivos;
  document.getElementById('v-tipos').textContent = tipos;

  const pctActivos = total ? Math.round((activos / total) * 100) : 0;
  const pctInactivos = total ? Math.round((inactivos / total) * 100) : 0;
  document.getElementById('v-activos-pct').textContent = pctActivos + '% del total';
  document.getElementById('v-inactivos-pct').textContent = pctInactivos + '% del total';
  document.getElementById('barra-activos').style.width = pctActivos + '%';
  document.getElementById('barra-inactivos').style.width = pctInactivos + '%';
}

function pintarTabla(lista) {
  const cuerpo = document.getElementById('cuerpoTabla');
  if (lista.length === 0) {
    cuerpo.innerHTML = '<tr><td colspan="7" class="vacio">No hay dispositivos que coincidan</td></tr>';
    return;
  }
  const inicio = (paginaActual - 1) * POR_PAGINA;
  const pagina = lista.slice(inicio, inicio + POR_PAGINA);

  cuerpo.innerHTML = pagina.map(d => `
    <tr>
      <td>${d.ip}</td>
      <td>${d.hostname ?? '—'}</td>
      <td>${d.mac ?? '—'}</td>
      <td>${d.tipo ?? '—'}</td>
      <td>${d.sistema ?? '—'}</td>
      <td><span class="pill ${d.estado === 'activo' ? 'activo' : 'inactivo'}">${d.estado ?? 'desconocido'}</span></td>
      <td class="col-acciones">
        <button class="btn-peligro" onclick="eliminarDispositivo('${d.ip}')">Eliminar</button>
      </td>
    </tr>
  `).join('');

  document.getElementById('resumenPaginacion').textContent =
    `Mostrando ${pagina.length ? inicio + 1 : 0} a ${inicio + pagina.length} de ${lista.length} dispositivos`;
}

function pintarPaginacion(lista) {
  const totalPaginas = Math.max(1, Math.ceil(lista.length / POR_PAGINA));
  const cont = document.getElementById('paginasContenedor');
  let html = `<button ${paginaActual === 1 ? 'disabled' : ''} onclick="irPagina(${paginaActual - 1})">‹</button>`;
  for (let p = 1; p <= totalPaginas; p++) {
    html += `<button class="${p === paginaActual ? 'activo' : ''}" onclick="irPagina(${p})">${p}</button>`;
  }
  html += `<button ${paginaActual === totalPaginas ? 'disabled' : ''} onclick="irPagina(${paginaActual + 1})">›</button>`;
  cont.innerHTML = html;
}

function irPagina(p) {
  paginaActual = p;
  aplicarFiltrosYRenderizar();
}

document.getElementById('filtroTexto').addEventListener('input', () => { paginaActual = 1; aplicarFiltrosYRenderizar(); });
document.getElementById('filtroTipo').addEventListener('change', () => { paginaActual = 1; aplicarFiltrosYRenderizar(); });
document.getElementById('filtroEstado').addEventListener('change', () => { paginaActual = 1; aplicarFiltrosYRenderizar(); });

async function eliminarDispositivo(ip) {
  if (!confirm(`¿Eliminar el dispositivo ${ip} del inventario?`)) return;
  await fetch(`/dispositivos/${ip}`, { method: 'DELETE' });
  await cargarDispositivos();
  if (document.getElementById('vista-dispositivos').classList.contains('activa')) pintarTablaDispositivos();
}

async function refrescarManual() {
  const boton = document.getElementById('btnRefrescar');
  boton.classList.add('girando');
  await Promise.all([cargarDispositivos(), cargarEstado()]);
  setTimeout(() => boton.classList.remove('girando'), 600);
}

/* ---------- Vista: Dispositivos (alta / edición) ---------- */
function pintarTablaDispositivos() {
  const cuerpo = document.getElementById('cuerpoTablaDispositivos');
  if (dispositivosCache.length === 0) {
    cuerpo.innerHTML = '<tr><td colspan="7" class="vacio">No hay dispositivos registrados</td></tr>';
    return;
  }
  cuerpo.innerHTML = dispositivosCache.map(d => `
    <tr>
      <td>${d.ip}</td>
      <td>${d.hostname ?? '—'}</td>
      <td>${d.mac ?? '—'}</td>
      <td>${d.tipo ?? '—'}</td>
      <td>${d.sistema ?? '—'}</td>
      <td><span class="pill ${d.estado === 'activo' ? 'activo' : 'inactivo'}">${d.estado ?? 'desconocido'}</span></td>
      <td class="col-acciones">
        <button class="btn btn-secundario" style="padding:5px 11px;font-size:11.5px;" onclick='cargarEnFormulario(${JSON.stringify(d)})'>Editar</button>
        <button class="btn-peligro" onclick="eliminarDispositivo('${d.ip}')">Eliminar</button>
      </td>
    </tr>
  `).join('');
}

function cargarEnFormulario(d) {
  editandoIp = d.ip;
  document.getElementById('f-ip').value = d.ip;
  document.getElementById('f-ip').disabled = true;
  document.getElementById('f-hostname').value = d.hostname ?? '';
  document.getElementById('f-mac').value = d.mac ?? '';
  document.getElementById('f-tipo').value = d.tipo ?? 'desconocido';
  document.getElementById('f-sistema').value = d.sistema ?? '';
  document.getElementById('f-estado').value = d.estado ?? 'activo';
  document.getElementById('btnGuardarDispositivo').lastChild.textContent = ' Guardar cambios';
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function limpiarFormulario(mantenerAviso) {
  editandoIp = null;
  document.getElementById('f-ip').value = '';
  document.getElementById('f-ip').disabled = false;
  document.getElementById('f-hostname').value = '';
  document.getElementById('f-mac').value = '';
  document.getElementById('f-tipo').value = 'pc';
  document.getElementById('f-sistema').value = '';
  document.getElementById('f-estado').value = 'activo';
  document.getElementById('btnGuardarDispositivo').lastChild.textContent = ' Agregar dispositivo';
  if (!mantenerAviso) document.getElementById('avisoFormulario').innerHTML = '';
}

function mostrarAviso(idContenedor, mensaje, esError) {
  document.getElementById(idContenedor).innerHTML =
    `<div class="aviso ${esError ? 'error' : 'ok'}">${mensaje}</div>`;
}

async function guardarDispositivo() {
  const ip = document.getElementById('f-ip').value.trim();
  if (!ip) { mostrarAviso('avisoFormulario', 'La IP es obligatoria', true); return; }

  const cuerpo = {
    ip,
    hostname: document.getElementById('f-hostname').value.trim() || 'desconocido',
    mac: document.getElementById('f-mac').value.trim() || 'desconocida',
    tipo: document.getElementById('f-tipo').value,
    sistema: document.getElementById('f-sistema').value.trim() || 'desconocido',
    estado: document.getElementById('f-estado').value,
  };

  const editando = !!editandoIp;
  const respuesta = await fetch(editando ? `/dispositivos/${ip}` : '/dispositivos', {
    method: editando ? 'PUT' : 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(cuerpo),
  });
  const datos = await respuesta.json();

  if (!respuesta.ok) {
    mostrarAviso('avisoFormulario', datos.detail || 'No se pudo guardar el dispositivo', true);
    return;
  }

  mostrarAviso('avisoFormulario', editando ? `Dispositivo ${ip} actualizado` : `Dispositivo ${ip} agregado`, false);
  limpiarFormulario(true);
  await cargarDispositivos();
  pintarTablaDispositivos();
}

/* ---------- Vista: Escaneo ---------- */
async function escanearRed() {
  const red = document.getElementById('f-red-escaneo').value.trim();
  if (!red) { mostrarAviso('avisoEscaneo', 'Indica un rango CIDR, ej. 192.168.1.0/24', true); return; }

  mostrarAviso('avisoEscaneo', `Escaneando ${red}… esto puede tardar unos segundos`, false);
  const respuesta = await fetch(`/escanear?red=${encodeURIComponent(red)}`, { method: 'POST' });
  const datos = await respuesta.json();

  if (!respuesta.ok) {
    mostrarAviso('avisoEscaneo', datos.detail || 'Error al escanear', true);
    return;
  }

  mostrarAviso('avisoEscaneo', `Escaneo completo: ${datos.equipos_detectados} equipo(s) activo(s) agregados al inventario`, false);
  document.getElementById('panelResultadoEscaneo').style.display = 'block';
  document.getElementById('cuerpoResultadoEscaneo').innerHTML = datos.dispositivos.length
    ? datos.dispositivos.map(d => `<tr><td>${d.ip}</td><td><span class="pill activo">${d.estado}</span></td></tr>`).join('')
    : '<tr><td colspan="2" class="vacio">No se detectaron equipos activos</td></tr>';

  await cargarDispositivos();
}

/* ---------- Vista: Comandos ---------- */
async function ejecutarComandoRed() {
  const cuerpo = {
    ip: document.getElementById('cr-ip').value.trim(),
    username: document.getElementById('cr-user').value.trim(),
    password: document.getElementById('cr-pass').value,
    secret: document.getElementById('cr-secret').value,
    device_type: document.getElementById('cr-device-type').value,
    comando: document.getElementById('cr-comando').value.trim(),
  };
  document.getElementById('avisoComandoRed').innerHTML = '';
  document.getElementById('salidaComandoRed').style.display = 'none';

  try {
    const r = await fetch('/red/comando', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(cuerpo),
    });
    const datos = await r.json();
    if (!r.ok) { mostrarAviso('avisoComandoRed', datos.detail || 'Error al ejecutar el comando', true); return; }
    const pre = document.getElementById('salidaComandoRed');
    pre.style.display = 'block';
    pre.textContent = datos.salida;
  } catch (e) {
    mostrarAviso('avisoComandoRed', 'No se pudo contactar al equipo. Revisa IP/credenciales/conectividad.', true);
  }
}

async function ejecutarComandoLinux() {
  const cuerpo = {
    ip: document.getElementById('cl-ip').value.trim(),
    username: document.getElementById('cl-user').value.trim(),
    password: document.getElementById('cl-pass').value,
    comando: document.getElementById('cl-comando').value.trim(),
  };
  document.getElementById('avisoComandoLinux').innerHTML = '';
  document.getElementById('salidaComandoLinux').style.display = 'none';

  try {
    const r = await fetch('/linux/comando', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(cuerpo),
    });
    const datos = await r.json();
    if (!r.ok) { mostrarAviso('avisoComandoLinux', datos.detail || 'Error al ejecutar el comando', true); return; }
    const pre = document.getElementById('salidaComandoLinux');
    pre.style.display = 'block';
    pre.textContent = datos.salida;
  } catch (e) {
    mostrarAviso('avisoComandoLinux', 'No se pudo contactar al host. Revisa IP/credenciales/conectividad.', true);
  }
}

/* ---------- Vista: Reportes ---------- */
function pintarReportes() {
  const conteoTipos = {};
  dispositivosCache.forEach(d => { conteoTipos[d.tipo] = (conteoTipos[d.tipo] || 0) + 1; });
  const maximo = Math.max(1, ...Object.values(conteoTipos));

  const contenedor = document.getElementById('reporteTipos');
  const entradas = Object.entries(conteoTipos).sort((a, b) => b[1] - a[1]);
  contenedor.innerHTML = entradas.length
    ? entradas.map(([tipo, cantidad]) => `
        <div class="barra-tipo">
          <span class="nombre">${tipo}</span>
          <span class="pista"><span class="relleno" style="width:${(cantidad / maximo) * 100}%"></span></span>
          <span class="cantidad">${cantidad}</span>
        </div>`).join('')
    : '<div class="vacio">Sin datos todavía</div>';

  const inactivos = dispositivosCache.filter(d => d.estado !== 'activo');
  const cuerpo = document.getElementById('reporteInactivos');
  cuerpo.innerHTML = inactivos.length
    ? inactivos.map(d => `<tr><td>${d.ip}</td><td>${d.hostname ?? '—'}</td><td>${d.tipo ?? '—'}</td></tr>`).join('')
    : '<tr><td colspan="3" class="vacio">Todos los dispositivos están activos 🎉</td></tr>';
}

/* ---------- Vista: Exportaciones ---------- */
async function exportarInventario() {
  document.getElementById('avisoExportar').innerHTML = '';
  const r = await fetch('/exportar');
  const datos = await r.json();
  if (!r.ok) { mostrarAviso('avisoExportar', 'No se pudo exportar el inventario', true); return; }
  mostrarAviso('avisoExportar', `Inventario exportado correctamente en: ${datos.formatos.join(', ')}`, false);
  document.getElementById('listaDescargas').style.display = 'flex';
}

/* ---------- Arranque ---------- */
async function refrescoPeriodico() {
  await cargarDispositivos();
  await cargarEstado();
}
refrescoPeriodico();
setInterval(refrescoPeriodico, 10000);
</script>

</body>
</html>
"""
