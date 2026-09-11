"""Acceso a datos de ventas y sus líneas."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime

from ..domain.models import EstadoVenta, LineaVenta, Venta

_FORMATO_FECHA_HORA = "%Y-%m-%d %H:%M:%S"


def _a_venta(fila: sqlite3.Row) -> Venta:
    return Venta(
        id=fila["id"],
        folio=fila["folio"],
        usuario_id=fila["usuario_id"],
        usuario_nombre=fila["usuario_nombre"] if "usuario_nombre" in fila.keys() else None,
        fecha_hora=datetime.strptime(fila["fecha_hora"], _FORMATO_FECHA_HORA),
        subtotal_clp=fila["subtotal_clp"],
        descuento_clp=fila["descuento_clp"],
        total_clp=fila["total_clp"],
        estado=EstadoVenta(fila["estado"]),
    )


def _a_linea(fila: sqlite3.Row) -> LineaVenta:
    return LineaVenta(
        id=fila["id"],
        venta_id=fila["venta_id"],
        producto_id=fila["producto_id"],
        codigo_barras=fila["codigo_barras"],
        nombre=fila["nombre"],
        precio_unit_clp=fila["precio_unit_clp"],
        cantidad=fila["cantidad"],
        subtotal_clp=fila["subtotal_clp"],
        descuento_clp=fila["descuento_clp"],
    )


def siguiente_folio(conexion: sqlite3.Connection) -> int:
    """Calcula el folio de la próxima venta.

    Debe llamarse dentro de la misma transacción que la inserción; de lo contrario, dos
    ventas simultáneas podrían recibir el mismo número. Hoy el sistema es monopuesto, pero
    la restricción UNIQUE sobre folio hace que el error sea imposible de pasar por alto si
    algún día deja de serlo.
    """
    fila = conexion.execute("SELECT COALESCE(MAX(folio), 0) + 1 AS siguiente FROM venta").fetchone()
    return int(fila["siguiente"])


def insertar(conexion: sqlite3.Connection, venta: Venta) -> Venta:
    """Inserta la venta y todas sus líneas. Debe ejecutarse dentro de una transacción."""
    cursor = conexion.execute(
        "INSERT INTO venta (folio, usuario_id, fecha_hora, subtotal_clp, descuento_clp, "
        "total_clp, estado) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            venta.folio,
            venta.usuario_id,
            venta.fecha_hora.strftime(_FORMATO_FECHA_HORA),
            venta.subtotal_clp,
            venta.descuento_clp,
            venta.total_clp,
            str(venta.estado),
        ),
    )
    venta.id = int(cursor.lastrowid)

    for linea in venta.lineas:
        linea.venta_id = venta.id
        cursor = conexion.execute(
            "INSERT INTO venta_linea (venta_id, producto_id, codigo_barras, nombre, "
            "precio_unit_clp, cantidad, subtotal_clp, descuento_clp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                venta.id,
                linea.producto_id,
                linea.codigo_barras,
                linea.nombre,
                linea.precio_unit_clp,
                linea.cantidad,
                linea.subtotal_clp,
                linea.descuento_clp,
            ),
        )
        linea.id = int(cursor.lastrowid)

    return venta


def obtener(conexion: sqlite3.Connection, venta_id: int) -> Venta | None:
    """Devuelve una venta con sus líneas cargadas."""
    fila = conexion.execute(
        "SELECT v.*, u.nombre AS usuario_nombre FROM venta v "
        "LEFT JOIN usuario u ON u.id = v.usuario_id WHERE v.id = ?",
        (venta_id,),
    ).fetchone()
    if not fila:
        return None
    venta = _a_venta(fila)
    venta.lineas = lineas_de(conexion, venta_id)
    return venta


def lineas_de(conexion: sqlite3.Connection, venta_id: int) -> list[LineaVenta]:
    filas = conexion.execute(
        "SELECT * FROM venta_linea WHERE venta_id = ? ORDER BY id", (venta_id,)
    ).fetchall()
    return [_a_linea(f) for f in filas]


def del_dia(conexion: sqlite3.Connection, dia: date | None = None) -> list[Venta]:
    """Ventas de un día, de la más reciente a la más antigua.

    Se compara solo la parte de fecha del texto ISO, que es exactamente lo que permite
    guardar las fechas en ese formato: ordenar y filtrar sin conversiones.
    """
    dia = dia or date.today()
    filas = conexion.execute(
        "SELECT v.*, u.nombre AS usuario_nombre FROM venta v "
        "LEFT JOIN usuario u ON u.id = v.usuario_id "
        "WHERE date(v.fecha_hora) = ? ORDER BY v.fecha_hora DESC, v.id DESC",
        (dia.isoformat(),),
    ).fetchall()
    return [_a_venta(f) for f in filas]


def resumen_del_dia(conexion: sqlite3.Connection, dia: date | None = None) -> dict[str, int]:
    """Número de ventas, total vendido y artículos vendidos en el día."""
    dia = dia or date.today()
    fila = conexion.execute(
        "SELECT COUNT(*) AS cantidad, COALESCE(SUM(total_clp), 0) AS total FROM venta "
        "WHERE date(fecha_hora) = ? AND estado = 'completada'",
        (dia.isoformat(),),
    ).fetchone()
    articulos = conexion.execute(
        "SELECT COALESCE(SUM(l.cantidad), 0) AS articulos FROM venta_linea l "
        "JOIN venta v ON v.id = l.venta_id "
        "WHERE date(v.fecha_hora) = ? AND v.estado = 'completada'",
        (dia.isoformat(),),
    ).fetchone()
    return {
        "cantidad_ventas": int(fila["cantidad"]),
        "total_clp": int(fila["total"]),
        "articulos": int(articulos["articulos"]),
    }
