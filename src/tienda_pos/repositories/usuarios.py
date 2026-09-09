"""Acceso a datos de usuarios.

El hash del PIN y su salt se devuelven solo en `obtener_credenciales`, que es la única
función que los necesita. El resto del sistema trabaja con objetos `Usuario` que no
contienen ningún dato secreto, de modo que un descuido al registrar en el log o al mostrar
un objeto no puede filtrar credenciales.
"""

from __future__ import annotations

import sqlite3

from ..domain.models import Rol, Usuario


def _a_usuario(fila: sqlite3.Row) -> Usuario:
    return Usuario(
        id=fila["id"],
        nombre=fila["nombre"],
        rol=Rol(fila["rol"]),
        activo=bool(fila["activo"]),
    )


def obtener_por_nombre(conexion: sqlite3.Connection, nombre: str) -> Usuario | None:
    fila = conexion.execute(
        "SELECT id, nombre, rol, activo FROM usuario WHERE nombre = ? AND activo = 1",
        (nombre,),
    ).fetchone()
    return _a_usuario(fila) if fila else None


def obtener_credenciales(conexion: sqlite3.Connection, nombre: str) -> tuple[str, str] | None:
    """Devuelve (pin_hash, salt) de un usuario activo, o None si no existe."""
    fila = conexion.execute(
        "SELECT pin_hash, salt FROM usuario WHERE nombre = ? AND activo = 1", (nombre,)
    ).fetchone()
    return (fila["pin_hash"], fila["salt"]) if fila else None


def listar(conexion: sqlite3.Connection) -> list[Usuario]:
    filas = conexion.execute(
        "SELECT id, nombre, rol, activo FROM usuario WHERE activo = 1 ORDER BY nombre"
    ).fetchall()
    return [_a_usuario(f) for f in filas]


def contar(conexion: sqlite3.Connection) -> int:
    return int(conexion.execute("SELECT COUNT(*) FROM usuario WHERE activo = 1").fetchone()[0])


def crear(
    conexion: sqlite3.Connection, nombre: str, rol: Rol, pin_hash: str, salt: str
) -> Usuario:
    cursor = conexion.execute(
        "INSERT INTO usuario (nombre, rol, pin_hash, salt) VALUES (?, ?, ?, ?)",
        (nombre, str(rol), pin_hash, salt),
    )
    return Usuario(id=int(cursor.lastrowid), nombre=nombre, rol=rol)


def actualizar_pin(
    conexion: sqlite3.Connection, usuario_id: int, pin_hash: str, salt: str
) -> None:
    conexion.execute(
        "UPDATE usuario SET pin_hash = ?, salt = ? WHERE id = ?", (pin_hash, salt, usuario_id)
    )
