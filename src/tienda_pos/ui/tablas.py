"""Utilidades comunes de las tablas.

Existen para que las tres tablas del sistema (carrito, catálogo y ventas del día) se vean y
se comporten igual sin repetir el mismo bloque de configuración en cada pantalla.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QTableWidget, QTableWidgetItem

IZQUIERDA = Qt.AlignmentFlag.AlignLeft
CENTRO = Qt.AlignmentFlag.AlignCenter
DERECHA = Qt.AlignmentFlag.AlignRight


@contextmanager
def rellenar(tabla: QTableWidget, filas: int) -> Iterator[None]:
    """Deja la tabla vacía con `filas` filas nuevas, y el dibujo parado hasta llenarlas.

    Es la forma de volver a llenar una tabla **que ya tenía filas** (fase 23). Con las columnas
    en `ResizeToContents`, reemplazar una celda hace que Qt vuelva a medir la columna entera:
    con 2.000 productos eran unos 8.000 reemplazos por 2.000 filas medidas cada vez, y entrar
    por segunda vez a Productos congelaba la caja dos minutos. Vaciando primero, cada celda
    entra en una fila vacía, como la primera vez, y la medida se hace una sola vez al final.
    """
    tabla.setUpdatesEnabled(False)
    try:
        tabla.setRowCount(0)
        tabla.setRowCount(filas)
        yield
    finally:
        tabla.setUpdatesEnabled(True)


def preparar(tabla: QTableWidget, seleccionable: bool = True) -> None:
    """Aplica la configuración común: sin rejilla, selección por filas y sin edición directa.

    Las celdas no se editan a mano en ninguna tabla: los cambios pasan siempre por un
    formulario o por una acción, de modo que no exista forma de dejar un dato en un estado
    que la aplicación no conozca.
    """
    tabla.verticalHeader().setVisible(False)
    tabla.setShowGrid(False)
    tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    if seleccionable:
        tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        tabla.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    else:
        tabla.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)


def alinear_cabeceras(tabla: QTableWidget, alineaciones: tuple[Qt.AlignmentFlag, ...]) -> None:
    """Alinea cada cabecera igual que los datos de su columna.

    Qt centra las cabeceras por defecto, así que una columna de importes alineados a la
    derecha queda con el título descolocado sobre ellos y la tabla se lee torcida.
    """
    for columna, alineacion in enumerate(alineaciones):
        cabecera = tabla.horizontalHeaderItem(columna)
        if cabecera is not None:
            cabecera.setTextAlignment(alineacion | Qt.AlignmentFlag.AlignVCenter)


def celda(
    texto: str,
    alineacion: Qt.AlignmentFlag = IZQUIERDA,
    fuerte: bool = False,
) -> QTableWidgetItem:
    """Crea una celda ya alineada, y opcionalmente en negrita."""
    item = QTableWidgetItem(texto)
    item.setTextAlignment(alineacion | Qt.AlignmentFlag.AlignVCenter)
    if fuerte:
        fuente = item.font()
        fuente.setBold(True)
        item.setFont(fuente)
    return item
