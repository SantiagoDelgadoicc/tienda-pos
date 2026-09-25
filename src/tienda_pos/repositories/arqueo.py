"""Acceso a datos del arqueo de caja: turnos y movimientos de efectivo (fase 19, D-036)."""

from __future__ import annotations

import sqlite3
from datetime import datetime

from ..domain.models import EstadoVenta, MedioPago, MovimientoEfectivo, TipoMovimiento, TurnoCaja

_FORMATO_FECHA_HORA = "%Y-%m-%d %H:%M:%S"

_SELECT_TURNO = (
    "SELECT t.*, a.nombre AS abierto_por_nombre, c.nombre AS cerrado_por_nombre "
    "FROM turno_caja t "
    "LEFT JOIN usuario a ON a.id = t.abierto_por "
    "LEFT JOIN usuario c ON c.id = t.cerrado_por "
)


def _fecha(texto: str | None) -> datetime | None:
    return datetime.strptime(texto, _FORMATO_FECHA_HORA) if texto else None


def a_texto(momento: datetime) -> str:
    return momento.strftime(_FORMATO_FECHA_HORA)


def _a_turno(fila: sqlite3.Row) -> TurnoCaja:
    return TurnoCaja(
        id=fila["id"],
        caja=fila["caja"],
        abierto_en=_fecha(fila["abierto_en"]),
        abierto_por_id=fila["abierto_por"],
        abierto_por_nombre=fila["abierto_por_nombre"],
        apertura_clp=fila["apertura_clp"],
        cerrado_en=_fecha(fila["cerrado_en"]),
        cerrado_por_id=fila["cerrado_por"],
        cerrado_por_nombre=fila["cerrado_por_nombre"],
        esperado_al_cerrar_clp=fila["esperado_clp"],
        contado_clp=fila["contado_clp"],
        nota=fila["nota"],
    )


def _a_movimiento(fila: sqlite3.Row) -> MovimientoEfectivo:
    return MovimientoEfectivo(
        id=fila["id"],
        turno_id=fila["turno_id"],
        tipo=TipoMovimiento.leer(fila["tipo"]),
        monto_clp=fila["monto_clp"],
        motivo=fila["motivo"],
        usuario_id=fila["usuario_id"],
        usuario_nombre=fila["usuario_nombre"],
        fecha_hora=_fecha(fila["fecha_hora"]),
        intento_id=fila["intento_id"],
    )


# --------------------------------------------------------------------------- turnos


def turno_abierto(conexion: sqlite3.Connection, caja: str) -> TurnoCaja | None:
    """El turno abierto de una caja, si lo hay. Nunca hay más de uno: lo impide un índice."""
    fila = conexion.execute(
        _SELECT_TURNO + "WHERE t.caja = ? AND t.cerrado_en IS NULL", (caja,)
    ).fetchone()
    return _a_turno(fila) if fila else None


def id_turno_abierto(conexion: sqlite3.Connection, caja: str) -> int | None:
    """Solo el identificador. Es lo que necesita el cobro, dentro de su transacción."""
    fila = conexion.execute(
        "SELECT id FROM turno_caja WHERE caja = ? AND cerrado_en IS NULL", (caja,)
    ).fetchone()
    return int(fila["id"]) if fila else None


def obtener_turno(conexion: sqlite3.Connection, turno_id: int) -> TurnoCaja | None:
    fila = conexion.execute(_SELECT_TURNO + "WHERE t.id = ?", (turno_id,)).fetchone()
    return _a_turno(fila) if fila else None


def turno_por_intento(conexion: sqlite3.Connection, intento_id: str) -> TurnoCaja | None:
    fila = conexion.execute(
        _SELECT_TURNO + "WHERE t.intento_apertura = ?", (intento_id,)
    ).fetchone()
    return _a_turno(fila) if fila else None


def turnos_recientes(conexion: sqlite3.Connection, limite: int) -> list[TurnoCaja]:
    """Los últimos turnos de todas las cajas, del más reciente al más antiguo."""
    filas = conexion.execute(
        _SELECT_TURNO + "ORDER BY t.abierto_en DESC, t.id DESC LIMIT ?", (limite,)
    ).fetchall()
    return [_a_turno(f) for f in filas]


def insertar_turno(
    conexion: sqlite3.Connection,
    caja: str,
    abierto_en: datetime,
    abierto_por: int,
    apertura_clp: int,
    intento_id: str | None,
) -> int:
    """Abre un turno. Debe ir dentro de una transacción.

    Raises:
        sqlite3.IntegrityError: si la caja ya tiene un turno abierto, o el intento ya existe.
    """
    cursor = conexion.execute(
        "INSERT INTO turno_caja (caja, abierto_en, abierto_por, apertura_clp, intento_apertura) "
        "VALUES (?, ?, ?, ?, ?)",
        (caja, a_texto(abierto_en), abierto_por, apertura_clp, intento_id),
    )
    return int(cursor.lastrowid)


def cerrar_turno(
    conexion: sqlite3.Connection,
    turno_id: int,
    cerrado_en: datetime,
    cerrado_por: int,
    esperado_clp: int,
    contado_clp: int,
    nota: str | None,
) -> None:
    """Cierra el turno si seguía abierto. Debe ir dentro de una transacción."""
    conexion.execute(
        "UPDATE turno_caja SET cerrado_en = ?, cerrado_por = ?, esperado_clp = ?, "
        "contado_clp = ?, nota = ? WHERE id = ? AND cerrado_en IS NULL",
        (a_texto(cerrado_en), cerrado_por, esperado_clp, contado_clp, nota, turno_id),
    )


def ventas_en_efectivo(conexion: sqlite3.Connection, turno_id: int) -> tuple[int, int]:
    """Total y número de las ventas completadas en efectivo de un turno."""
    fila = conexion.execute(
        "SELECT COALESCE(SUM(total_clp), 0) AS total, COUNT(*) AS cantidad FROM venta "
        "WHERE turno_id = ? AND estado = ? AND medio_pago = ?",
        (turno_id, str(EstadoVenta.COMPLETADA), str(MedioPago.EFECTIVO)),
    ).fetchone()
    return int(fila["total"]), int(fila["cantidad"])


# --------------------------------------------------------------------------- movimientos


_SELECT_MOVIMIENTO = (
    "SELECT m.*, u.nombre AS usuario_nombre FROM movimiento_efectivo m "
    "LEFT JOIN usuario u ON u.id = m.usuario_id "
)


def movimientos_de(conexion: sqlite3.Connection, turno_id: int) -> list[MovimientoEfectivo]:
    """Los movimientos de un turno, del más antiguo al más reciente."""
    filas = conexion.execute(
        _SELECT_MOVIMIENTO + "WHERE m.turno_id = ? ORDER BY m.fecha_hora, m.id", (turno_id,)
    ).fetchall()
    return [_a_movimiento(f) for f in filas]


def movimientos_de_varios(
    conexion: sqlite3.Connection, turno_ids: list[int]
) -> dict[int, list[MovimientoEfectivo]]:
    """Los movimientos de varios turnos en una consulta, agrupados por turno."""
    if not turno_ids:
        return {}
    marcadores = ",".join("?" for _ in turno_ids)
    filas = conexion.execute(
        _SELECT_MOVIMIENTO
        + f"WHERE m.turno_id IN ({marcadores}) ORDER BY m.turno_id, m.fecha_hora, m.id",
        tuple(turno_ids),
    ).fetchall()
    agrupados: dict[int, list[MovimientoEfectivo]] = {}
    for fila in filas:
        agrupados.setdefault(fila["turno_id"], []).append(_a_movimiento(fila))
    return agrupados


def movimiento_por_intento(
    conexion: sqlite3.Connection, intento_id: str
) -> MovimientoEfectivo | None:
    fila = conexion.execute(
        _SELECT_MOVIMIENTO + "WHERE m.intento_id = ?", (intento_id,)
    ).fetchone()
    return _a_movimiento(fila) if fila else None


def obtener_movimiento(conexion: sqlite3.Connection, movimiento_id: int) -> MovimientoEfectivo:
    fila = conexion.execute(_SELECT_MOVIMIENTO + "WHERE m.id = ?", (movimiento_id,)).fetchone()
    return _a_movimiento(fila)


def insertar_movimiento(
    conexion: sqlite3.Connection,
    turno_id: int,
    tipo: TipoMovimiento,
    monto_clp: int,
    motivo: str,
    usuario_id: int,
    fecha_hora: datetime,
    intento_id: str | None,
) -> int:
    """Anota un movimiento. Debe ir dentro de una transacción."""
    cursor = conexion.execute(
        "INSERT INTO movimiento_efectivo "
        "(turno_id, tipo, monto_clp, motivo, usuario_id, fecha_hora, intento_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (turno_id, str(tipo), monto_clp, motivo, usuario_id, a_texto(fecha_hora), intento_id),
    )
    return int(cursor.lastrowid)
