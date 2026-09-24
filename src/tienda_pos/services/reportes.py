"""Informes de ventas.

Existe para que la interfaz no llame directamente a `repositories/`. Hasta ahora
`ui/reportes_view.py` lo hacía, lo que funciona en monopuesto pero no sobrevive a `D-015`: el
servidor expone la superficie de `services/`, y cada llamada suya tiene que ser una operación
completa y no un trozo de consulta.
"""

from __future__ import annotations

import sqlite3
from datetime import date

from ..domain.models import CierreCaja, Venta
from ..repositories import ventas as repo_ventas

#: El día de la tienda ahora mismo, con la hora de corte de `config.HORA_CORTE_DIA`.
dia_comercial = repo_ventas.dia_comercial


def resumen_del_dia(conexion: sqlite3.Connection, dia: date | None = None) -> dict[str, int]:
    """Número de ventas, total vendido y artículos vendidos en el día."""
    return repo_ventas.resumen_del_dia(conexion, dia)


def ventas_del_dia(conexion: sqlite3.Connection, dia: date | None = None) -> list[Venta]:
    """Ventas del día **con sus líneas ya cargadas**, en dos consultas y no en N+1.

    Devolverlas ya completas es deliberado: quien las pinta no debería tener que volver a
    pedir nada, y contra el servidor cada petición extra es un viaje por la red.
    """
    ventas = repo_ventas.del_dia(conexion, dia)
    if not ventas:
        return []

    lineas_por_venta = repo_ventas.lineas_de_varias(
        conexion, [venta.id for venta in ventas if venta.id is not None]
    )
    for venta in ventas:
        venta.lineas = lineas_por_venta.get(venta.id, [])
    return ventas


def cierre_de_caja(
    conexion: sqlite3.Connection, dia: date | None, caja: str | None
) -> CierreCaja:
    """El cierre diario de una caja: sus ventas del día con sus productos, y la lista de cajas.

    Todo de una vez, en tres consultas: contra el servidor cada petición es un viaje por la red,
    y este informe se pide con el dueño esperando delante. Los totales los deriva `CierreCaja`
    de las mismas ventas, así que no hay una cuarta consulta que pudiera no cuadrar con ellas.

    `caja` None pide las ventas anteriores a que se registrara la caja (fase 16).
    """
    dia = dia or dia_comercial()
    ventas = repo_ventas.del_dia_de_caja(conexion, dia, caja)
    if ventas:
        lineas = repo_ventas.lineas_de_varias(conexion, [v.id for v in ventas if v.id is not None])
        for venta in ventas:
            venta.lineas = lineas.get(venta.id, [])
    return CierreCaja(
        dia=dia, caja=caja, ventas=ventas, cajas_del_dia=repo_ventas.cajas_del_dia(conexion, dia)
    )

