"""Conexión a SQLite y control de transacciones.

Toda la aplicación usa una única conexión. SQLite no la necesita compartida entre hilos y la
interfaz es de un solo hilo, así que mantenerla simple evita una clase entera de errores.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

# Tiempo que espera SQLite si la base está bloqueada antes de rendirse. Cinco segundos son
# de sobra en monopuesto y evitan el error "database is locked" si el respaldo automático
# está copiando el archivo justo en ese instante.
_TIMEOUT_BLOQUEO_MS = 5000

_EN_MEMORIA = ":memory:"


def conectar(ruta: Path | str) -> sqlite3.Connection:
    """Abre la base de datos y la deja configurada para uso transaccional.

    isolation_level=None desactiva el manejo automático de transacciones de Python, que abre
    transacciones implícitas donde uno no las espera. Aquí se controlan explícitamente con
    el gestor de contexto `transaccion`.
    """
    es_memoria = str(ruta) == _EN_MEMORIA
    if not es_memoria:
        Path(ruta).parent.mkdir(parents=True, exist_ok=True)

    conexion = sqlite3.connect(str(ruta), isolation_level=None)
    conexion.row_factory = sqlite3.Row

    if not es_memoria:
        # WAL permite leer mientras se escribe y sobrevive mucho mejor a un corte de luz,
        # que en una tienda es un escenario real y no teórico.
        conexion.execute("PRAGMA journal_mode = WAL")
        conexion.execute("PRAGMA synchronous = FULL")
    conexion.execute("PRAGMA foreign_keys = ON")
    conexion.execute(f"PRAGMA busy_timeout = {_TIMEOUT_BLOQUEO_MS}")
    return conexion


@contextmanager
def transaccion(conexion: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Ejecuta un bloque dentro de una transacción: o se guarda todo, o no se guarda nada.

    BEGIN IMMEDIATE toma el bloqueo de escritura de entrada en vez de esperar al primer
    INSERT. Así, si la base está ocupada, se falla al principio y no a mitad de una venta ya
    escrita parcialmente.
    """
    conexion.execute("BEGIN IMMEDIATE")
    try:
        yield conexion
    except BaseException:
        conexion.execute("ROLLBACK")
        raise
    else:
        conexion.execute("COMMIT")


def leer_meta(
    conexion: sqlite3.Connection, clave: str, por_defecto: str | None = None
) -> str | None:
    fila = conexion.execute("SELECT valor FROM meta WHERE clave = ?", (clave,)).fetchone()
    return fila["valor"] if fila else por_defecto


def escribir_meta(conexion: sqlite3.Connection, clave: str, valor: str) -> None:
    conexion.execute(
        "INSERT INTO meta (clave, valor) VALUES (?, ?) "
        "ON CONFLICT (clave) DO UPDATE SET valor = excluded.valor",
        (clave, valor),
    )
