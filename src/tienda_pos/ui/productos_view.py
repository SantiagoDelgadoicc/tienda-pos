"""Administración del catálogo: alta, edición y baja de productos.

Reservada al administrador. La comprobación de permisos no vive aquí sino en la capa de
servicios: ocultar un botón no es control de acceso.
"""

from __future__ import annotations

import sqlite3

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..domain.errors import ErrorDominio
from ..domain.models import Producto, Usuario
from ..services import catalogo
from ..utils.money import formatear_clp, parsear_clp
from . import dialogos, tablas

_COLUMNAS = ("Código de barras", "Producto", "Precio", "Stock")

# Umbral por debajo del cual el stock se muestra en rojo. Es un aviso visual, no una regla
# de negocio: el cliente todavía no ha dicho cuándo considera que le falta un producto.
_STOCK_BAJO = 5


class DialogoProducto(QDialog):
    """Formulario de alta y edición de un producto."""

    def __init__(self, padre: QWidget | None = None, producto: Producto | None = None) -> None:
        super().__init__(padre)
        self._producto = producto
        self.setWindowTitle("Editar producto" if producto else "Nuevo producto")
        self.setMinimumWidth(430)

        columna = QVBoxLayout(self)
        columna.setContentsMargins(26, 24, 26, 20)
        columna.setSpacing(8)

        columna.addWidget(QLabel("Código de barras"))
        self.campo_codigo = QLineEdit(producto.codigo_barras if producto else "")
        self.campo_codigo.setPlaceholderText("Escanéelo con el lector o escríbalo")
        columna.addWidget(self.campo_codigo)

        columna.addWidget(QLabel("Nombre del producto"))
        self.campo_nombre = QLineEdit(producto.nombre if producto else "")
        columna.addWidget(self.campo_nombre)

        columna.addWidget(QLabel("Precio de venta"))
        self.campo_precio = QLineEdit(str(producto.precio_clp) if producto else "")
        self.campo_precio.setPlaceholderText("Solo el número, por ejemplo 1290")
        columna.addWidget(self.campo_precio)

        columna.addWidget(QLabel("Stock"))
        self.campo_stock = QLineEdit(str(producto.stock) if producto else "0")
        self.campo_stock.setValidator(QIntValidator(0, 999999, self))
        columna.addWidget(self.campo_stock)

        self.error = QLabel()
        self.error.setObjectName("mensajeError")
        self.error.setWordWrap(True)
        self.error.hide()
        columna.addWidget(self.error)

        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        botones.button(QDialogButtonBox.StandardButton.Save).setText("Guardar")
        botones.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        botones.accepted.connect(self._validar)
        botones.rejected.connect(self.reject)
        columna.addWidget(botones)

        # Al crear, el foco va al código porque lo normal es escanearlo. Al editar va al
        # precio, porque cambiar precios es el 90% de las ediciones reales.
        (self.campo_precio if producto else self.campo_codigo).setFocus()

    def _validar(self) -> None:
        """Valida el formato antes de cerrar; las reglas de negocio las revisa el servicio."""
        if not self.campo_codigo.text().strip():
            return self._fallar("Escanee o escriba el código de barras.")
        if not self.campo_nombre.text().strip():
            return self._fallar("Escriba el nombre del producto.")
        try:
            precio = parsear_clp(self.campo_precio.text())
        except ValueError:
            return self._fallar("El precio debe ser un número, por ejemplo 1290.")
        if precio < 0:
            return self._fallar("El precio no puede ser negativo.")
        self.accept()

    def _fallar(self, mensaje: str) -> None:
        self.error.setText(mensaje)
        self.error.show()

    @property
    def datos(self) -> tuple[str, str, int, int]:
        return (
            self.campo_codigo.text().strip(),
            self.campo_nombre.text().strip(),
            parsear_clp(self.campo_precio.text()),
            int(self.campo_stock.text() or 0),
        )


class ProductosView(QWidget):
    """Listado y mantenimiento del catálogo."""

    salir_solicitado = Signal()

    def __init__(self, conexion: sqlite3.Connection, padre: QWidget | None = None) -> None:
        super().__init__(padre)
        self._conexion = conexion
        self.usuario: Usuario | None = None
        self._productos: list[Producto] = []

        self._construir()

    def _construir(self) -> None:
        columna = QVBoxLayout(self)
        columna.setContentsMargins(20, 20, 20, 20)
        columna.setSpacing(12)

        titulo = QLabel("Productos")
        titulo.setObjectName("tituloPantalla")
        columna.addWidget(titulo)

        self.resumen = QLabel()
        self.resumen.setObjectName("subtitulo")
        columna.addWidget(self.resumen)

        fila = QHBoxLayout()
        self.campo_filtro = QLineEdit()
        self.campo_filtro.setPlaceholderText("Filtrar por nombre o código")
        self.campo_filtro.setClearButtonEnabled(True)
        self.campo_filtro.textChanged.connect(self._pintar)
        fila.addWidget(self.campo_filtro, stretch=1)

        for texto, destino in (
            ("Nuevo producto", self.crear),
            ("Editar", self.editar),
            ("Códigos pendientes", self.ver_pendientes),
        ):
            boton = QPushButton(texto)
            boton.clicked.connect(destino)
            fila.addWidget(boton)

        self.boton_eliminar = QPushButton("Dar de baja")
        self.boton_eliminar.setObjectName("botonPeligro")
        self.boton_eliminar.clicked.connect(self.dar_de_baja)
        fila.addWidget(self.boton_eliminar)

        boton_volver = QPushButton("Volver   (Esc)")
        boton_volver.clicked.connect(self.salir_solicitado.emit)
        fila.addWidget(boton_volver)
        columna.addLayout(fila)

        self.tabla = QTableWidget(0, len(_COLUMNAS))
        self.tabla.setHorizontalHeaderLabels(_COLUMNAS)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.setShowGrid(False)
        self.tabla.doubleClicked.connect(self.editar)

        cabecera = self.tabla.horizontalHeader()
        cabecera.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        cabecera.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        cabecera.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        cabecera.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        tablas.alinear_cabeceras(
            self.tabla, (tablas.IZQUIERDA, tablas.IZQUIERDA, tablas.DERECHA, tablas.CENTRO)
        )
        columna.addWidget(self.tabla, stretch=1)

    # ------------------------------------------------------------------ datos

    def recargar(self) -> None:
        self._productos = catalogo.listar(self._conexion)
        self._pintar()
        self.campo_filtro.setFocus()

    def _visibles(self) -> list[Producto]:
        texto = self.campo_filtro.text().strip().lower()
        if not texto:
            return self._productos
        return [
            p
            for p in self._productos
            if texto in p.nombre.lower() or texto in p.codigo_barras.lower()
        ]

    def _pintar(self) -> None:
        visibles = self._visibles()
        self.tabla.setRowCount(len(visibles))

        for fila, producto in enumerate(visibles):
            self.tabla.setItem(fila, 0, QTableWidgetItem(producto.codigo_barras))
            self.tabla.setItem(fila, 1, QTableWidgetItem(producto.nombre))

            precio = QTableWidgetItem(formatear_clp(producto.precio_clp))
            precio.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.tabla.setItem(fila, 2, precio)

            stock = QTableWidgetItem(str(producto.stock))
            stock.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if producto.stock <= _STOCK_BAJO:
                from PySide6.QtGui import QBrush, QColor

                from .estilos import ERROR

                stock.setForeground(QBrush(QColor(ERROR)))
            self.tabla.setItem(fila, 3, stock)

        total = len(self._productos)
        mostrados = len(visibles)
        self.resumen.setText(
            f"{total} productos en el catálogo"
            if total == mostrados
            else f"{mostrados} de {total} productos"
        )

    def _seleccionado(self) -> Producto | None:
        fila = self.tabla.currentRow()
        visibles = self._visibles()
        if fila < 0 or fila >= len(visibles):
            return None
        return visibles[fila]

    # ------------------------------------------------------------------ acciones

    def crear(self) -> None:
        dialogo = DialogoProducto(self)
        if not dialogo.exec():
            return
        codigo, nombre, precio, stock = dialogo.datos
        try:
            catalogo.crear_producto(self._conexion, self.usuario, codigo, nombre, precio, stock)
        except ErrorDominio as error:
            dialogos.mostrar_error(self, str(error))
            return
        self.recargar()

    def editar(self) -> None:
        producto = self._seleccionado()
        if producto is None:
            dialogos.mostrar_error(self, "Seleccione primero un producto de la lista.")
            return

        dialogo = DialogoProducto(self, producto)
        if not dialogo.exec():
            return
        codigo, nombre, precio, stock = dialogo.datos
        try:
            catalogo.actualizar_producto(
                self._conexion, self.usuario, producto.id, codigo, nombre, precio, stock
            )
        except ErrorDominio as error:
            dialogos.mostrar_error(self, str(error))
            return
        self.recargar()

    def dar_de_baja(self) -> None:
        producto = self._seleccionado()
        if producto is None:
            dialogos.mostrar_error(self, "Seleccione primero un producto de la lista.")
            return

        if not dialogos.confirmar(
            self,
            "Dar de baja",
            f"{producto.nombre}\n\nDejará de aparecer en las búsquedas y no se podrá "
            "vender.\nLas ventas anteriores no se modifican.\n\n¿Desea darlo de baja?",
            texto_si="Sí, dar de baja",
        ):
            return

        try:
            catalogo.desactivar_producto(self._conexion, self.usuario, producto.id)
        except ErrorDominio as error:
            dialogos.mostrar_error(self, str(error))
            return
        self.recargar()

    def ver_pendientes(self) -> None:
        """Códigos que se escanearon y no existen en el catálogo."""
        try:
            pendientes = catalogo.codigos_pendientes(self._conexion, self.usuario)
        except ErrorDominio as error:
            dialogos.mostrar_error(self, str(error))
            return

        if not pendientes:
            dialogos.mostrar_info(
                self,
                "No hay códigos pendientes.\n\nAquí aparecen los productos que se "
                "escanearon en la caja y todavía no están cargados en el catálogo.",
                "Códigos pendientes",
            )
            return

        lineas = "\n".join(
            f"  {p.codigo}      {p.intentos} intento(s)      último: {p.ultima_vez}"
            for p in pendientes
        )
        dialogos.mostrar_info(
            self,
            f"Estos códigos se escanearon en la caja y no están en el catálogo:\n\n{lineas}",
            "Códigos pendientes",
        )
