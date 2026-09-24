"""Acceso a datos de ventas y sus líneas."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime

from ..domain.models import EstadoVenta, LineaVenta, MedioPago, Venta

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
        intento_id=fila["intento_id"] if "intento_id" in fila.keys() else None,
        caja=fila["caja"] if "caja" in fila.keys() else None,
        medio_pago=MedioPago.leer(fila["medio_pago"]) if "medio_pago" in fila.keys() else None,
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
        "total_clp, estado, intento_id, caja, medio_pago) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            venta.folio,
            venta.usuario_id,
            venta.fecha_hora.strftime(_FORMATO_FECHA_HORA),
            venta.subtotal_clp,
            venta.descuento_clp,
            venta.total_clp,
            str(venta.estado),
            venta.intento_id,
            venta.caja,
            str(venta.medio_pago) if venta.medio_pago else None,
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


def obtener_por_intento(conexion: sqlite3.Connection, intento_id: str) -> Venta | None:
    """Busca una venta por el identificador del intento de cobro que la creó.

    Es la pieza que hace idempotente el cobro: si la caja reintenta porque no supo si su
    primera petición llegó, esto devuelve la venta original en lugar de crear otra.
    """
    fila = conexion.execute(
        "SELECT v.*, u.nombre AS usuario_nombre FROM venta v "
        "LEFT JOIN usuario u ON u.id = v.usuario_id WHERE v.intento_id = ?",
        (intento_id,),
    ).fetchone()
    if not fila:
        return None
    venta = _a_venta(fila)
    venta.lineas = lineas_de(conexion, int(fila["id"]))
    return venta


def lineas_de(conexion: sqlite3.Connection, venta_id: int) -> list[LineaVenta]:
    filas = conexion.execute(
        "SELECT * FROM venta_linea WHERE venta_id = ? ORDER BY id", (venta_id,)
    ).fetchall()
    return [_a_linea(f) for f in filas]


def lineas_de_varias(
    conexion: sqlite3.Connection, venta_ids: list[int]
) -> dict[int, list[LineaVenta]]:
    """Líneas de varias ventas en una sola consulta, agrupadas por venta.

    Existe para no pedir las líneas venta por venta dentro de un bucle. En local esa
    diferencia no se nota; contra el servidor de `D-015` son N idas y vueltas por la red en
    lugar de una, y eso sí se siente en pantalla.

    Las ventas sin líneas no aparecen en el resultado: quien lo use debe tratar la ausencia
    como lista vacía.
    """
    if not venta_ids:
        return {}

    # Los marcadores se generan por número de parámetros, nunca interpolando valores.
    marcadores = ",".join("?" for _ in venta_ids)
    filas = conexion.execute(
        f"SELECT * FROM venta_linea WHERE venta_id IN ({marcadores}) ORDER BY venta_id, id",
        tuple(venta_ids),
    ).fetchall()

    agrupadas: dict[int, list[LineaVenta]] = {}
    for fila in filas:
        agrupadas.setdefault(fila["venta_id"], []).append(_a_linea(fila))
    return agrupadas


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
