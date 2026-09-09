"""Acceso a datos de productos.

Esta capa solo traduce entre filas de SQLite y objetos del dominio. No valida reglas de
negocio ni decide permisos: de eso se encarga `services/`. Mantener la frontera limpia es lo
que permitiría cambiar SQLite por un servidor sin tocar la lógica.
"""

from __future__ import annotations

import sqlite3

from ..domain.errors import ProductoDuplicado
from ..domain.models import Producto

_COLUMNAS = "id, codigo_barras, nombre, precio_clp, stock, activo, creado_en, actualizado_en"


def _a_producto(fila: sqlite3.Row) -> Producto:
    return Producto(
        id=fila["id"],
        codigo_barras=fila["codigo_barras"],
        nombre=fila["nombre"],
        precio_clp=fila["precio_clp"],
        stock=fila["stock"],
        activo=bool(fila["activo"]),
        creado_en=fila["creado_en"],
        actualizado_en=fila["actualizado_en"],
    )


def obtener_por_codigo(
    conexion: sqlite3.Connection, codigo: str, incluir_inactivos: bool = False
) -> Producto | None:
    """Busca por código de barras exacto. Es la consulta más usada del sistema."""
    sql = f"SELECT {_COLUMNAS} FROM producto WHERE codigo_barras = ?"
    if not incluir_inactivos:
        sql += " AND activo = 1"
    fila = conexion.execute(sql, (codigo,)).fetchone()
    return _a_producto(fila) if fila else None


def obtener_por_id(conexion: sqlite3.Connection, producto_id: int) -> Producto | None:
    fila = conexion.execute(
        f"SELECT {_COLUMNAS} FROM producto WHERE id = ?", (producto_id,)
    ).fetchone()
    return _a_producto(fila) if fila else None


def buscar_por_nombre(
    conexion: sqlite3.Connection, texto: str, limite: int = 50
) -> list[Producto]:
    """Búsqueda parcial por nombre, sin distinguir mayúsculas.

    Es el recurso del cajero cuando el código de barras está borrado o el producto no lo
    trae impreso. El patrón se pasa como parámetro, nunca concatenado, para que un nombre
    con comillas no rompa la consulta.
    """
    patron = f"%{texto.strip()}%"
    filas = conexion.execute(
        f"SELECT {_COLUMNAS} FROM producto "
        "WHERE activo = 1 AND nombre LIKE ? COLLATE NOCASE "
        "ORDER BY nombre LIMIT ?",
        (patron, limite),
    ).fetchall()
    return [_a_producto(f) for f in filas]


def listar(conexion: sqlite3.Connection, incluir_inactivos: bool = False) -> list[Producto]:
    sql = f"SELECT {_COLUMNAS} FROM producto"
    if not incluir_inactivos:
        sql += " WHERE activo = 1"
    sql += " ORDER BY nombre"
    return [_a_producto(f) for f in conexion.execute(sql).fetchall()]


def contar(conexion: sqlite3.Connection) -> int:
    return int(conexion.execute("SELECT COUNT(*) FROM producto WHERE activo = 1").fetchone()[0])


def crear(conexion: sqlite3.Connection, producto: Producto) -> Producto:
    """Inserta un producto y devuelve una copia con su id asignado.

    Raises:
        ProductoDuplicado: si el código de barras ya existe. Se traduce el error de SQLite a
            un error del dominio para que la interfaz no tenga que interpretar mensajes de
            la base de datos.
    """
    try:
        cursor = conexion.execute(
            "INSERT INTO producto (codigo_barras, nombre, precio_clp, stock, activo) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                producto.codigo_barras,
                producto.nombre,
                producto.precio_clp,
                producto.stock,
                int(producto.activo),
            ),
        )
    except sqlite3.IntegrityError as exc:
        if "codigo_barras" in str(exc) or "UNIQUE" in str(exc).upper():
            raise ProductoDuplicado(producto.codigo_barras) from exc
        raise
    producto.id = int(cursor.lastrowid)
    return producto


def actualizar(conexion: sqlite3.Connection, producto: Producto) -> None:
    """Guarda los cambios de un producto existente."""
    try:
        conexion.execute(
            "UPDATE producto SET codigo_barras = ?, nombre = ?, precio_clp = ?, stock = ?, "
            "activo = ?, actualizado_en = datetime('now', 'localtime') WHERE id = ?",
            (
                producto.codigo_barras,
                producto.nombre,
                producto.precio_clp,
                producto.stock,
                int(producto.activo),
                producto.id,
            ),
        )
    except sqlite3.IntegrityError as exc:
        raise ProductoDuplicado(producto.codigo_barras) from exc


def desactivar(conexion: sqlite3.Connection, producto_id: int) -> None:
    """Baja lógica.

    No se borra la fila porque las ventas históricas la referencian: borrarla dejaría el
    historial huérfano. Un producto desactivado desaparece de las búsquedas pero su pasado
    sigue siendo consultable.
    """
    conexion.execute(
        "UPDATE producto SET activo = 0, actualizado_en = datetime('now', 'localtime') "
        "WHERE id = ?",
        (producto_id,),
    )


def descontar_stock(conexion: sqlite3.Connection, producto_id: int, cantidad: int) -> None:
    """Resta unidades del stock. Debe llamarse dentro de una transacción."""
    conexion.execute(
        "UPDATE producto SET stock = stock - ?, "
        "actualizado_en = datetime('now', 'localtime') WHERE id = ?",
        (cantidad, producto_id),
    )
