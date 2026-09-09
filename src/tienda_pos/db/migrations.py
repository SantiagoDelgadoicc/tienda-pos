"""Versionado del esquema de la base de datos.

Se usa `PRAGMA user_version`, un entero que SQLite guarda dentro del propio archivo. Es
suficiente para un producto monopuesto y evita añadirle a un prototipo la dependencia de un
sistema de migraciones completo.

Para publicar una versión nueva: subir VERSION_ESQUEMA y registrar su función en
_MIGRACIONES. Nunca se edita una migración ya publicada, porque puede haber bases de datos
en la calle que ya la aplicaron.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path

VERSION_ESQUEMA = 1

_RUTA_ESQUEMA = Path(__file__).with_name("schema.sql")


def _version_actual(conexion: sqlite3.Connection) -> int:
    return int(conexion.execute("PRAGMA user_version").fetchone()[0])


def _sentencias(script: str) -> list[str]:
    """Trocea un script SQL en sentencias individuales.

    No se usa `executescript` porque hace un COMMIT implícito antes de ejecutar, lo que
    rompe la transacción explícita que envuelve cada migración y dejaría la base a medio
    migrar si algo fallara. `complete_statement` decide dónde termina cada sentencia sin
    confundirse con los punto y coma que aparezcan dentro de un texto.
    """
    sentencias: list[str] = []
    acumulado = ""
    for linea in script.splitlines(keepends=True):
        acumulado += linea
        if sqlite3.complete_statement(acumulado):
            sentencias.append(acumulado.strip())
            acumulado = ""
    if acumulado.strip():
        sentencias.append(acumulado.strip())

    # Un trozo formado solo por comentarios o líneas en blanco no es una sentencia y SQLite
    # lo rechazaría. Ocurre cuando el archivo termina con un comentario.
    return [s for s in sentencias if _tiene_sql(s)]


def _tiene_sql(fragmento: str) -> bool:
    return any(
        linea.strip() and not linea.strip().startswith("--") for linea in fragmento.splitlines()
    )


def _crear_esquema_inicial(conexion: sqlite3.Connection) -> None:
    for sentencia in _sentencias(_RUTA_ESQUEMA.read_text(encoding="utf-8")):
        conexion.execute(sentencia)


# Versión de destino -> función que lleva la base desde la versión anterior hasta ella.
_MIGRACIONES: dict[int, Callable[[sqlite3.Connection], None]] = {
    1: _crear_esquema_inicial,
}


def aplicar_migraciones(conexion: sqlite3.Connection) -> int:
    """Lleva la base de datos hasta la última versión del esquema.

    Devuelve la versión resultante. Es idempotente: si ya está al día, no hace nada.

    Raises:
        RuntimeError: si el archivo viene de una versión más nueva del programa. Es
            preferible negarse a abrirlo antes que corromper los datos del cliente.
    """
    version = _version_actual(conexion)
    if version > VERSION_ESQUEMA:
        raise RuntimeError(
            f"La base de datos usa la versión de esquema {version}, más nueva que la que "
            f"entiende este programa ({VERSION_ESQUEMA}). Actualice la aplicación."
        )

    while version < VERSION_ESQUEMA:
        siguiente = version + 1
        migracion = _MIGRACIONES[siguiente]
        # Cada migración es atómica: si falla a la mitad, la base queda en la versión previa
        # y no en un estado intermedio imposible de diagnosticar.
        conexion.execute("BEGIN IMMEDIATE")
        try:
            migracion(conexion)
            conexion.execute(f"PRAGMA user_version = {siguiente}")
        except BaseException:
            conexion.execute("ROLLBACK")
            raise
        else:
            conexion.execute("COMMIT")
        version = siguiente

    return version
