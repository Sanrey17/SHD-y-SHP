"""
Exporta el inventario de dispositivos a JSON, YAML y XML.
"""

import json
import os
import yaml
from dicttoxml import dicttoxml


def _asegurar_carpeta(ruta: str):
    carpeta = os.path.dirname(ruta)
    if carpeta:
        os.makedirs(carpeta, exist_ok=True)


def exportar_json(datos, ruta="data/inventario.json"):
    _asegurar_carpeta(ruta)
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(datos, archivo, indent=4, ensure_ascii=False)
    return ruta


def exportar_yaml(datos, ruta="data/inventario.yaml"):
    _asegurar_carpeta(ruta)
    with open(ruta, "w", encoding="utf-8") as archivo:
        yaml.dump(datos, archivo, allow_unicode=True)
    return ruta


def exportar_xml(datos, ruta="data/inventario.xml"):
    _asegurar_carpeta(ruta)
    xml = dicttoxml(datos, custom_root="inventario", attr_type=False)
    with open(ruta, "wb") as archivo:
        archivo.write(xml)
    return ruta
