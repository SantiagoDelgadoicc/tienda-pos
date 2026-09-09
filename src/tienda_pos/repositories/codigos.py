"""Registro de códigos escaneados que no existen en el catálogo.

Es una sugerencia nuestra, no un requisito del cliente: sirve para que el dueño vea al final
del día qué productos le faltan por cargar, en lugar de descubrirlo cuando un cliente ya
está esperando en la caja.
"""

from __future__ import annotations

import sqlite3

from ..domain.models import CodigoNoEncontrado


def registrar(conexion: sqlite3.Connection, codigo: str) -> None:
    """Anota el código, o incrementa el contador si ya estaba anotado.

    Si el mismo código aparece muchas veces, el contador delata cuál es el producto que más
    urge cargar. Un código que ya fue resuelto y vuelve a fallar se reabre.
    """
    conexion.execute(
        "INSERT INTO codigo_no_encontrado (codigo, intentos, primera_vez, ultima_vez) "
        "VALUES (?, 1, datetime('now', 'localtime'), datetime('now', 'localtime')) "
        "ON CONFLICT (codigo) DO UPDATE SET "
        "intentos = intentos + 1, "
        "ultima_vez = datetime('now', 'localtime'), "
        "resuelto = 0",
        (codigo,),
    )


def marcar_resuelto(conexion: sqlite3.Connection, codigo: str) -> None:
    """Se llama cuando el producto termina siendo dado de alta con ese código."""
    conexion.execute(
        "UPDATE codigo_no_encontrado SET resuelto = 1 WHERE codigo = ?", (codigo,)
    )


def listar_pendientes(conexion: sqlite3.Connection, limite: int = 100) -> list[CodigoNoEncontrado]:
    filas = conexion.execute(
        "SELECT codigo, intentos, primera_vez, ultima_vez, resuelto "
        "FROM codigo_no_encontrado WHERE resuelto = 0 "
        "ORDER BY intentos DESC, ultima_vez DESC LIMIT ?",
        (limite,),
    ).fetchall()
    return [
        CodigoNoEncontrado(
            codigo=f["codigo"],
            intentos=f["intentos"],
            primera_vez=f["primera_vez"],
            ultima_vez=f["ultima_vez"],
            resuelto=bool(f["resuelto"]),
        )
        for f in filas
    ]
