"""Informe de las ventas del día.

Es el reporte mínimo que hace que un punto de venta se sienta un sistema y no una
calculadora: cuánto se vendió hoy, en cuántas ventas, y qué llevaba cada una.
"""

from __future__ import annotations

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
from ..red.sesion import Sesion
from ..utils.money import formatear_clp
from . import estilos, tablas

_COLUMNAS_VENTAS = ("N°", "Hora", "Artículos", "Total", "Medio", "Atendió")
_COL_MEDIO = 4
_COLUMNAS_DETALLE = ("Producto", "Precio", "Cant.", "Subtotal")


class ReportesView(QWidget):
    """Ventas del día, con el detalle de la venta seleccionada."""

    salir_solicitado = Signal()

    def __init__(self, sesion: Sesion, padre: QWidget | None = None) -> None:
        super().__init__(padre)
        self._sesion = sesion
        self._ventas: list[Venta] = []
        self._construir()

    def _construir(self) -> None:
        columna = QVBoxLayout(self)
        columna.setContentsMargins(28, 22, 28, 24)
        columna.setSpacing(16)

        encabezado = QHBoxLayout()
        encabezado.setSpacing(10)
        encabezado.addStretch()

        boton_actualizar = QPushButton("Actualizar")
        boton_actualizar.clicked.connect(self.recargar)
        encabezado.addWidget(boton_actualizar)

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
        fila.setSpacing(16)

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
        estilos.aplicar_sombra(tarjeta)
        columna = QVBoxLayout(tarjeta)
        columna.setContentsMargins(20, 16, 20, 16)
        columna.setSpacing(2)

        # En mayúsculas, como todas las etiquetas de un bloque de métrica. Qt no entiende
        # `text-transform`, así que se hace aquí y no en la hoja de estilos.
        etiqueta = QLabel(titulo.upper())
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
        cabecera.setSectionResizeMode(_COL_MEDIO, QHeaderView.ResizeMode.ResizeToContents)
        cabecera.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        tablas.alinear_cabeceras(
            self.tabla_ventas,
            (
                tablas.CENTRO,
                tablas.CENTRO,
                tablas.CENTRO,
                tablas.DERECHA,
                tablas.IZQUIERDA,
                tablas.IZQUIERDA,
            ),
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
        resumen = self._sesion.resumen_del_dia(hoy)
        self.valor_total.setText(formatear_clp(resumen["total_clp"]))
        self.valor_ventas.setText(str(resumen["cantidad_ventas"]))
        self.valor_articulos.setText(str(resumen["articulos"]))

        # Vienen con las líneas ya cargadas: pedirlas venta por venta dentro de este bucle
        # era una ida y vuelta por venta, que contra el servidor de D-015 se nota.
        self._ventas = self._sesion.ventas_del_dia(hoy)
        self.tabla_ventas.setRowCount(len(self._ventas))

        for fila, venta in enumerate(self._ventas):
            self._celda(self.tabla_ventas, fila, 0, str(venta.folio), centrada=True)
            self._celda(self.tabla_ventas, fila, 1, venta.fecha_hora.strftime("%H:%M"), centrada=True)
            self._celda(self.tabla_ventas, fila, 2, str(venta.cantidad_articulos), centrada=True)
            self._celda(
                self.tabla_ventas, fila, 3, formatear_clp(venta.total_clp), derecha=True
            )
            self._celda(self.tabla_ventas, fila, _COL_MEDIO, _nombre_medio(venta))
            self._celda(self.tabla_ventas, fila, 5, venta.usuario_nombre or "—")
        self._colorear_medios()

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
        medio = f"  ·  {_nombre_medio(venta)}" if venta.medio_pago else ""
        self.titulo_detalle.setText(
            f"Venta N° {venta.folio}  ·  {venta.fecha_hora.strftime('%H:%M')}"
            f"  ·  {formatear_clp(venta.total_clp)}{descuento}{medio}"
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

    def repintar(self) -> None:
        """Tras un cambio de tema: el color de cada medio va celda a celda."""
        self._colorear_medios()

    def _colorear_medios(self) -> None:
        """Pinta cada medio con su color (D-034), el mismo que en el cobro y en el cierre."""
        from PySide6.QtGui import QBrush, QColor

        for fila, venta in enumerate(self._ventas):
            celda = self.tabla_ventas.item(fila, _COL_MEDIO)
            if celda is not None:
                celda.setForeground(QBrush(QColor(estilos.color_medio(venta.medio_pago))))

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


def _nombre_medio(venta) -> str:
    """El medio de una venta tal como se lee en pantalla. Las anteriores a la fase 17 no lo
    tienen registrado, y se dice así en lugar de suponer que fueron en efectivo."""
    from .venta_view import NOMBRE_MEDIO

    return NOMBRE_MEDIO.get(venta.medio_pago, "Sin registrar")
