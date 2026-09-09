"""Informe de las ventas del día.

Es el reporte mínimo que hace que un punto de venta se sienta un sistema y no una
calculadora: cuánto se vendió hoy, en cuántas ventas, y qué llevaba cada una.
"""

from __future__ import annotations

import sqlite3
from datetime import date

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..domain.models import Venta
from ..repositories import ventas as repo_ventas
from ..utils.money import formatear_clp
from . import tablas

_COLUMNAS_VENTAS = ("N°", "Hora", "Artículos", "Total", "Atendió")
_COLUMNAS_DETALLE = ("Producto", "Precio", "Cant.", "Subtotal")


class ReportesView(QWidget):
    """Ventas del día, con el detalle de la venta seleccionada."""

    salir_solicitado = Signal()

    def __init__(self, conexion: sqlite3.Connection, padre: QWidget | None = None) -> None:
        super().__init__(padre)
        self._conexion = conexion
        self._ventas: list[Venta] = []
        self._construir()

    def _construir(self) -> None:
        columna = QVBoxLayout(self)
        columna.setContentsMargins(20, 20, 20, 20)
        columna.setSpacing(14)

        encabezado = QHBoxLayout()
        titulo = QLabel("Ventas del día")
        titulo.setObjectName("tituloPantalla")
        encabezado.addWidget(titulo)
        encabezado.addStretch()

        boton_actualizar = QPushButton("Actualizar")
        boton_actualizar.clicked.connect(self.recargar)
        encabezado.addWidget(boton_actualizar)

        boton_volver = QPushButton("Volver   (Esc)")
        boton_volver.clicked.connect(self.salir_solicitado.emit)
        encabezado.addWidget(boton_volver)
        columna.addLayout(encabezado)

        columna.addWidget(self._tarjetas_resumen())

        cuerpo = QHBoxLayout()
        cuerpo.setSpacing(16)
        cuerpo.addWidget(self._panel_ventas(), stretch=3)
        cuerpo.addWidget(self._panel_detalle(), stretch=2)
        columna.addLayout(cuerpo, stretch=1)

    def _tarjetas_resumen(self) -> QWidget:
        contenedor = QWidget()
        fila = QHBoxLayout(contenedor)
        fila.setContentsMargins(0, 0, 0, 0)
        fila.setSpacing(14)

        self.valor_total, tarjeta_total = self._tarjeta("Total vendido hoy", "valorTotal")
        self.valor_ventas, tarjeta_ventas = self._tarjeta("Ventas realizadas", "valorSubtotal")
        self.valor_articulos, tarjeta_art = self._tarjeta("Artículos vendidos", "valorSubtotal")

        for tarjeta in (tarjeta_total, tarjeta_ventas, tarjeta_art):
            fila.addWidget(tarjeta)
        return contenedor

    @staticmethod
    def _tarjeta(titulo: str, estilo_valor: str) -> tuple[QLabel, QFrame]:
        tarjeta = QFrame()
        tarjeta.setObjectName("tarjeta")
        columna = QVBoxLayout(tarjeta)
        columna.setContentsMargins(20, 16, 20, 16)
        columna.setSpacing(2)

        etiqueta = QLabel(titulo)
        etiqueta.setObjectName("etiquetaTotal")
        columna.addWidget(etiqueta)

        valor = QLabel("—")
        valor.setObjectName(estilo_valor)
        columna.addWidget(valor)
        return valor, tarjeta

    def _panel_ventas(self) -> QWidget:
        self.tabla_ventas = QTableWidget(0, len(_COLUMNAS_VENTAS))
        self.tabla_ventas.setHorizontalHeaderLabels(_COLUMNAS_VENTAS)
        self.tabla_ventas.verticalHeader().setVisible(False)
        self.tabla_ventas.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla_ventas.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tabla_ventas.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla_ventas.setShowGrid(False)
        self.tabla_ventas.itemSelectionChanged.connect(self._mostrar_detalle)

        cabecera = self.tabla_ventas.horizontalHeader()
        cabecera.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        cabecera.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        cabecera.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        cabecera.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        cabecera.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        tablas.alinear_cabeceras(
            self.tabla_ventas,
            (tablas.CENTRO, tablas.CENTRO, tablas.CENTRO, tablas.DERECHA, tablas.IZQUIERDA),
        )
        return self.tabla_ventas

    def _panel_detalle(self) -> QWidget:
        contenedor = QWidget()
        columna = QVBoxLayout(contenedor)
        columna.setContentsMargins(0, 0, 0, 0)
        columna.setSpacing(8)

        self.titulo_detalle = QLabel("Seleccione una venta")
        self.titulo_detalle.setObjectName("subtitulo")
        columna.addWidget(self.titulo_detalle)

        self.tabla_detalle = QTableWidget(0, len(_COLUMNAS_DETALLE))
        self.tabla_detalle.setHorizontalHeaderLabels(_COLUMNAS_DETALLE)
        self.tabla_detalle.verticalHeader().setVisible(False)
        self.tabla_detalle.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla_detalle.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.tabla_detalle.setShowGrid(False)

        cabecera = self.tabla_detalle.horizontalHeader()
        cabecera.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for indice in (1, 2, 3):
            cabecera.setSectionResizeMode(indice, QHeaderView.ResizeMode.ResizeToContents)
        tablas.alinear_cabeceras(
            self.tabla_detalle,
            (tablas.IZQUIERDA, tablas.DERECHA, tablas.CENTRO, tablas.DERECHA),
        )
        columna.addWidget(self.tabla_detalle, stretch=1)
        return contenedor

    # ------------------------------------------------------------------ datos

    def recargar(self) -> None:
        hoy = date.today()
        resumen = repo_ventas.resumen_del_dia(self._conexion, hoy)
        self.valor_total.setText(formatear_clp(resumen["total_clp"]))
        self.valor_ventas.setText(str(resumen["cantidad_ventas"]))
        self.valor_articulos.setText(str(resumen["articulos"]))

        self._ventas = repo_ventas.del_dia(self._conexion, hoy)
        self.tabla_ventas.setRowCount(len(self._ventas))

        for fila, venta in enumerate(self._ventas):
            lineas = repo_ventas.lineas_de(self._conexion, venta.id)
            venta.lineas = lineas

            self._celda(self.tabla_ventas, fila, 0, str(venta.folio), centrada=True)
            self._celda(self.tabla_ventas, fila, 1, venta.fecha_hora.strftime("%H:%M"), centrada=True)
            self._celda(self.tabla_ventas, fila, 2, str(venta.cantidad_articulos), centrada=True)
            self._celda(
                self.tabla_ventas, fila, 3, formatear_clp(venta.total_clp), derecha=True
            )
            self._celda(self.tabla_ventas, fila, 4, venta.usuario_nombre or "—")

        self._limpiar_detalle()
        if self._ventas:
            self.tabla_ventas.selectRow(0)

    def _mostrar_detalle(self) -> None:
        fila = self.tabla_ventas.currentRow()
        if fila < 0 or fila >= len(self._ventas):
            self._limpiar_detalle()
            return

        venta = self._ventas[fila]
        descuento = (
            f"  ·  descuento {formatear_clp(venta.descuento_clp)}"
            if venta.descuento_clp
            else ""
        )
        self.titulo_detalle.setText(
            f"Venta N° {venta.folio}  ·  {venta.fecha_hora.strftime('%H:%M')}"
            f"  ·  {formatear_clp(venta.total_clp)}{descuento}"
        )

        self.tabla_detalle.setRowCount(len(venta.lineas))
        for indice, linea in enumerate(venta.lineas):
            self._celda(self.tabla_detalle, indice, 0, linea.nombre)
            self._celda(
                self.tabla_detalle, indice, 1, formatear_clp(linea.precio_unit_clp), derecha=True
            )
            self._celda(self.tabla_detalle, indice, 2, str(linea.cantidad), centrada=True)
            self._celda(
                self.tabla_detalle, indice, 3, formatear_clp(linea.subtotal_clp), derecha=True
            )

    def _limpiar_detalle(self) -> None:
        self.titulo_detalle.setText(
            "Todavía no hay ventas hoy" if not self._ventas else "Seleccione una venta"
        )
        self.tabla_detalle.setRowCount(0)

    @staticmethod
    def _celda(
        tabla: QTableWidget,
        fila: int,
        columna: int,
        texto: str,
        derecha: bool = False,
        centrada: bool = False,
    ) -> None:
        celda = QTableWidgetItem(texto)
        if derecha:
            celda.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        elif centrada:
            celda.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        tabla.setItem(fila, columna, celda)
