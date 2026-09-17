"""Apertura e inicialización de la base de datos.

Un único punto de entrada para el resto del programa: `abrir_base_datos()` deja la base
conectada, migrada y con datos utilizables, sin que quien la llame tenga que saber en qué
orden ocurren esas cosas.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .. import config
from .connection import conectar, transaccion
from .migrations import aplicar_migraciones
from .seed import cargar_datos_demo


def abrir_base_datos(
    ruta: Path | str | None = None,
    con_datos_demo: bool = True,
    compartida_entre_hilos: bool = False,
) -> sqlite3.Connection:
    """Abre (y crea si hace falta) la base de datos lista para usar.

    Args:
        ruta: ubicación del archivo. Si se omite, se usa la carpeta de datos de la
            aplicación. Las pruebas pasan ":memory:".
        con_datos_demo: carga el catálogo de ejemplo cuando la base está vacía. En una
            instalación real del cliente esto se pondría en False.
        compartida_entre_hilos: solo en modo servidor, donde el hilo que atiende a la caja
            secundaria comparte la conexión con la interfaz. `SesionLocal` serializa los
            accesos con un cerrojo; sin esa garantía, esto no debe activarse.

    Returns:
        Una conexión ya migrada y con las claves foráneas activas.
    """
    if ruta is None:
        config.asegurar_directorios()
        ruta = config.ruta_base_datos()

    conexion = conectar(ruta, compartida_entre_hilos=compartida_entre_hilos)
    aplicar_migraciones(conexion)

    if con_datos_demo:
        with transaccion(conexion):
            cargar_datos_demo(conexion)

    return conexion
