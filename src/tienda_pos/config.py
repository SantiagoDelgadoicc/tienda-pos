"""Configuración global: rutas de datos y constantes del sistema.

Las rutas se resuelven en tiempo de ejecución y no al importar el módulo, para que las
pruebas puedan redirigirlas mediante la variable de entorno TIENDA_POS_HOME.
"""

from __future__ import annotations

import os
from pathlib import Path

NOMBRE_APP = "TiendaPOS"
NOMBRE_COMERCIAL = "Tienda POS"
VERSION = "0.1.0"

#: Cuántos respaldos automáticos se conservan antes de borrar el más antiguo.
RESPALDOS_A_CONSERVAR = 7

#: Longitud mínima y máxima del PIN de acceso.
PIN_LONGITUD_MIN = 4
PIN_LONGITUD_MAX = 8

#: Si es False, una venta que dejaría el stock en negativo se rechaza.
#: Se deja como constante y no como opción de interfaz porque cambiarlo es una decisión
#: de negocio del cliente, no del cajero. Ver D-009 en docs/DECISIONES.md.
PERMITIR_STOCK_NEGATIVO = False

#: Longitud máxima aceptada para un código de barras leído.
CODIGO_LONGITUD_MAX = 32


def directorio_datos() -> Path:
    """Carpeta donde viven la base de datos, los respaldos y los logs.

    En Windows es %LOCALAPPDATA%\TiendaPOS. Nunca se usa la carpeta del programa porque
    Windows bloquea la escritura dentro de "Archivos de Programa".
    """
    personalizado = os.environ.get("TIENDA_POS_HOME")
    if personalizado:
        return Path(personalizado)

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / NOMBRE_APP

    # Linux y macOS: solo relevante para desarrollo y para la ejecución de pruebas.
    return Path.home() / f".{NOMBRE_APP.lower()}"


def ruta_base_datos() -> Path:
    return directorio_datos() / "tienda.db"


def directorio_respaldos() -> Path:
    return directorio_datos() / "backups"


def directorio_logs() -> Path:
    return directorio_datos() / "logs"


def asegurar_directorios() -> None:
    """Crea las carpetas de datos si no existen. Es idempotente."""
    for carpeta in (directorio_datos(), directorio_respaldos(), directorio_logs()):
        carpeta.mkdir(parents=True, exist_ok=True)
