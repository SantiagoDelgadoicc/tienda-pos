"""Acceso a datos de usuarios.

El hash del PIN y su salt se devuelven solo en `obtener_credenciales`, que es la única
función que los necesita. El resto del sistema trabaja con objetos `Usuario` que no
contienen ningún dato secreto, de modo que un descuido al registrar en el log o al mostrar
un objeto no puede filtrar credenciales.
"""

from __future__ import annotations

import sqlite3

from ..domain.errors import DatosInvalidos
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


def obtener_por_id(conexion: sqlite3.Connection, usuario_id: int) -> Usuario | None:
    """Un usuario por su id, **esté activo o dado de baja**.

    Hace falta ver a los dados de baja: para reactivarlos, y para que el histórico de ventas
    siga mostrando quién vendió aunque ya no trabaje en la tienda.
    """
    fila = conexion.execute(
        "SELECT id, nombre, rol, activo FROM usuario WHERE id = ?", (usuario_id,)
    ).fetchone()
    return _a_usuario(fila) if fila else None


def buscar_por_nombre(conexion: sqlite3.Connection, nombre: str) -> Usuario | None:
    """Un usuario por su nombre exacto, esté activo o no. Para diagnosticar un duplicado."""
    fila = conexion.execute(
        "SELECT id, nombre, rol, activo FROM usuario WHERE nombre = ?", (nombre,)
    ).fetchone()
    return _a_usuario(fila) if fila else None


def listar(conexion: sqlite3.Connection, incluir_inactivos: bool = False) -> list[Usuario]:
    """Usuarios por nombre. Por defecto solo los activos, que es lo que ve el acceso."""
    if incluir_inactivos:
        consulta = (
            "SELECT id, nombre, rol, activo FROM usuario ORDER BY activo DESC, nombre"
        )
    else:
        consulta = "SELECT id, nombre, rol, activo FROM usuario WHERE activo = 1 ORDER BY nombre"
    return [_a_usuario(f) for f in conexion.execute(consulta).fetchall()]


def contar_admins_activos(conexion: sqlite3.Connection) -> int:
    return int(
        conexion.execute(
            "SELECT COUNT(*) FROM usuario WHERE activo = 1 AND rol = ?", (str(Rol.ADMIN),)
        ).fetchone()[0]
    )


def contar_todos(conexion: sqlite3.Connection) -> int:
    """Usuarios que existen, activos o no. Cero solo en una instalación recién hecha."""
    return int(conexion.execute("SELECT COUNT(*) FROM usuario").fetchone()[0])


def cambiar_activo(conexion: sqlite3.Connection, usuario_id: int, activo: bool) -> None:
    """Da de baja o reactiva. **Nunca se borra un usuario**: sus ventas lo referencian."""
    conexion.execute(
        "UPDATE usuario SET activo = ? WHERE id = ?", (1 if activo else 0, usuario_id)
    )


def contar(conexion: sqlite3.Connection) -> int:
    return int(conexion.execute("SELECT COUNT(*) FROM usuario WHERE activo = 1").fetchone()[0])


def crear(
    conexion: sqlite3.Connection, nombre: str, rol: Rol, pin_hash: str, salt: str
) -> Usuario:
    """Inserta un usuario.

    Raises:
        DatosInvalidos: si el nombre ya existe. Se traduce el error de SQLite aquí, como hace
            `repositories/productos.py` con los códigos repetidos: si subiera crudo, la pantalla
            mostraría "UNIQUE constraint failed: usuario.nombre" al dueño de la tienda.
    """
    try:
        cursor = conexion.execute(
            "INSERT INTO usuario (nombre, rol, pin_hash, salt) VALUES (?, ?, ?, ?)",
            (nombre, str(rol), pin_hash, salt),
        )
    except sqlite3.IntegrityError as exc:
        raise DatosInvalidos(f"Ya existe un usuario llamado {nombre}.") from exc
    return Usuario(id=int(cursor.lastrowid), nombre=nombre, rol=rol)


def actualizar_pin(
    conexion: sqlite3.Connection, usuario_id: int, pin_hash: str, salt: str
) -> None:
    conexion.execute(
        "UPDATE usuario SET pin_hash = ?, salt = ? WHERE id = ?", (pin_hash, salt, usuario_id)
    )
