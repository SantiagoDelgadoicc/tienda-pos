"""Selección de un producto entre varios resultados de búsqueda.

Es la salida cuando el código de barras está borrado, arrancado o el producto no lo trae.
Sin esto, un producto sin etiqueta legible sería invendible.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..domain.models import Producto
from ..utils.money import formatear_clp


class DialogoResultados(QDialog):
    """Lista los productos encontrados y devuelve el elegido."""

    def __init__(self, resultados: list[Producto], padre: QWidget | None = None) -> None:
        super().__init__(padre)
        self.setWindowTitle("Elegir producto")
        self.resize(620, 420)
        self._resultados = resultados

        disposicion = QVBoxLayout(self)
        disposicion.setContentsMargins(22, 22, 22, 18)
        disposicion.setSpacing(12)

        encabezado = QLabel(f"{len(resultados)} productos encontrados")
        encabezado.setObjectName("subtitulo")
        disposicion.addWidget(encabezado)

        self.tabla = QTableWidget(len(resultados), 3)
        self.tabla.setHorizontalHeaderLabels(("Producto", "Precio", "Stock"))
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.setShowGrid(False)
        # Doble clic elige directamente: es el gesto que espera cualquiera ante una lista.
        self.tabla.doubleClicked.connect(self.accept)

        cabecera = self.tabla.horizontalHeader()
        cabecera.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        cabecera.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        cabecera.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

        for fila, producto in enumerate(resultados):
            self.tabla.setItem(fila, 0, QTableWidgetItem(producto.nombre))

            precio = QTableWidgetItem(formatear_clp(producto.precio_clp))
            precio.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.tabla.setItem(fila, 1, precio)

            stock = QTableWidgetItem(str(producto.stock))
            stock.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tabla.setItem(fila, 2, stock)

        if resultados:
            self.tabla.selectRow(0)
        disposicion.addWidget(self.tabla)

        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botones.button(QDialogButtonBox.StandardButton.Ok).setText("Agregar al carrito")
        botones.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        disposicion.addWidget(botones)

        self.tabla.setFocus()

    def elegir(self) -> Producto | None:
        """Muestra el diálogo y devuelve el producto elegido, o None si se canceló."""
        if not self.exec():
            return None
        fila = self.tabla.currentRow()
        if fila < 0:
            return None
        return self._resultados[fila]
