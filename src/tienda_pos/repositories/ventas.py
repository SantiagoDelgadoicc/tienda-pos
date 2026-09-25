"""Acceso a datos de ventas y sus líneas."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, time, timedelta

from .. import config
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
        turno_id=fila["turno_id"] if "turno_id" in fila.keys() else None,
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
        gramos=fila["gramos"],
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
        "total_clp, estado, intento_id, caja, medio_pago, turno_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
            venta.turno_id,
        ),
    )
    venta.id = int(cursor.lastrowid)

    for linea in venta.lineas:
        linea.venta_id = venta.id
        cursor = conexion.execute(
            "INSERT INTO venta_linea (venta_id, producto_id, codigo_barras, nombre, "
            "precio_unit_clp, cantidad, subtotal_clp, descuento_clp, gramos) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                venta.id,
                linea.producto_id,
                linea.codigo_barras,
                linea.nombre,
                linea.precio_unit_clp,
                linea.cantidad,
                linea.subtotal_clp,
                linea.descuento_clp,
                linea.gramos,
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


def dia_comercial(ahora: datetime | None = None) -> date:
    """El día de la tienda en este momento. Con corte a medianoche, el de hoy.

    Con `HORA_CORTE_DIA` en 6, a las 01:30 del sábado todavía es viernes: es la noche que el
    dueño cuenta como del viernes.
    """
    ahora = ahora or datetime.now()
    return (ahora - timedelta(hours=config.HORA_CORTE_DIA)).date()


def rango_del_dia(dia: date) -> tuple[str, str]:
    """Desde y hasta —este último excluido— del día de la tienda, en el formato guardado.

    Un rango y no `date(fecha_hora) = ?` por dos motivos: permite que el día no empiece a
    medianoche (`HORA_CORTE_DIA`, pregunta H10), y compara el texto ISO tal cual, que es lo
    que deja usar el índice por fecha en lugar de recorrer la tabla entera.

    La hora se lee de `config` en cada llamada, no se copia al importar: así cambiarla afecta
    a todas las consultas a la vez, y las pruebas pueden probar otro corte.
    """
    desde = datetime.combine(dia, time(config.HORA_CORTE_DIA))
    hasta = desde + timedelta(days=1)
    return desde.strftime(_FORMATO_FECHA_HORA), hasta.strftime(_FORMATO_FECHA_HORA)


def del_dia(conexion: sqlite3.Connection, dia: date | None = None) -> list[Venta]:
    """Ventas de un día de la tienda, de la más reciente a la más antigua."""
    desde, hasta = rango_del_dia(dia or dia_comercial())
    filas = conexion.execute(
        "SELECT v.*, u.nombre AS usuario_nombre FROM venta v "
        "LEFT JOIN usuario u ON u.id = v.usuario_id "
        "WHERE v.fecha_hora >= ? AND v.fecha_hora < ? ORDER BY v.fecha_hora DESC, v.id DESC",
        (desde, hasta),
    ).fetchall()
    return [_a_venta(f) for f in filas]


def del_dia_de_caja(conexion: sqlite3.Connection, dia: date, caja: str | None) -> list[Venta]:
    """Ventas completadas de una caja en un día, de la más reciente a la más antigua.

    Es una función aparte y no un parámetro opcional de `del_dia`: con `caja=None` por defecto
    no se podría distinguir "todas las cajas" de "las ventas sin caja registrada", y ese es uno
    de los casos reales. `IS ?` compara bien contra NULL con un parámetro, así que la misma
    consulta sirve para ese grupo.
    """
    desde, hasta = rango_del_dia(dia)
    filas = conexion.execute(
        "SELECT v.*, u.nombre AS usuario_nombre FROM venta v "
        "LEFT JOIN usuario u ON u.id = v.usuario_id "
        "WHERE v.fecha_hora >= ? AND v.fecha_hora < ? AND v.caja IS ? AND v.estado = ? "
        "ORDER BY v.fecha_hora DESC, v.id DESC",
        (desde, hasta, caja, str(EstadoVenta.COMPLETADA)),
    ).fetchall()
    return [_a_venta(f) for f in filas]


def cajas_del_dia(conexion: sqlite3.Connection, dia: date) -> list[str | None]:
    """Las cajas que vendieron ese día, por nombre; la de las ventas sin caja, al final."""
    desde, hasta = rango_del_dia(dia)
    filas = conexion.execute(
        "SELECT DISTINCT caja FROM venta "
        "WHERE fecha_hora >= ? AND fecha_hora < ? AND estado = ? "
        "ORDER BY caja IS NULL, caja",
        (desde, hasta, str(EstadoVenta.COMPLETADA)),
    ).fetchall()
    return [f["caja"] for f in filas]


def resumen_del_dia(conexion: sqlite3.Connection, dia: date | None = None) -> dict[str, int]:
    """Número de ventas, total vendido y artículos vendidos en el día."""
    desde, hasta = rango_del_dia(dia or dia_comercial())
    fila = conexion.execute(
        "SELECT COUNT(*) AS cantidad, COALESCE(SUM(total_clp), 0) AS total FROM venta "
        "WHERE fecha_hora >= ? AND fecha_hora < ? AND estado = 'completada'",
        (desde, hasta),
    ).fetchone()
    articulos = conexion.execute(
        "SELECT COALESCE(SUM(l.cantidad), 0) AS articulos FROM venta_linea l "
        "JOIN venta v ON v.id = l.venta_id "
        "WHERE v.fecha_hora >= ? AND v.fecha_hora < ? AND v.estado = 'completada'",
        (desde, hasta),
    ).fetchone()
    return {
        "cantidad_ventas": int(fila["cantidad"]),
        "total_clp": int(fila["total"]),
        "articulos": int(articulos["articulos"]),
    }
