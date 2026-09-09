"""Pantalla de venta: escanear, armar el carrito y cobrar.

Toda la pantalla está pensada para operarse sin ratón. El foco vuelve al campo de escaneo
después de cualquier acción, porque en una caja el cajero mira al cliente, no a la pantalla,
y si el foco se pierde el siguiente escaneo se pierde con él.
"""

from __future__ import annotations

import sqlite3

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
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

from ..domain.errors import ErrorDominio, ProductoNoEncontrado
from ..domain.models import Usuario
from ..services import catalogo
from ..services import venta as servicio_venta
from ..services.venta import Carrito
from ..utils import sonido
from ..utils.money import formatear_clp
from ..utils.scanner import DetectorLector
from . import dialogos, tablas

# Cuánto tiempo permanece visible un mensaje de éxito o de error antes de desvanecerse.
_MENSAJE_MS = 5000

# Margen que se espera tras una ráfaga de lector antes de confirmar sin Enter. Suficiente
# para que llegue el Enter si el lector lo envía, e imperceptible si no lo hace.
_ESPERA_LECTOR_MS = 120

_COLUMNAS = ("Código", "Producto", "Precio", "Cant.", "Subtotal")


class VentaView(QWidget):
    """Pantalla principal del punto de venta."""

    #: Se emite cuando el usuario pide la pantalla de consulta de precio.
    consulta_solicitada = Signal()
    #: Se emite tras cerrar una venta, para que la ventana actualice sus indicadores.
    venta_registrada = Signal()

    def __init__(self, conexion: sqlite3.Connection, padre: QWidget | None = None) -> None:
        super().__init__(padre)
        self._conexion = conexion
        self._carrito = Carrito()
        self.usuario: Usuario | None = None
        self._detector = DetectorLector()
        self._auto = QTimer(self)
        self._auto.setSingleShot(True)
        self._auto.timeout.connect(self._confirmar_automatico)

        self._construir()
        self._refrescar()

    # ------------------------------------------------------------------ construcción

    def _construir(self) -> None:
        raiz = QHBoxLayout(self)
        raiz.setContentsMargins(20, 20, 20, 20)
        raiz.setSpacing(18)
        raiz.addWidget(self._panel_izquierdo(), stretch=3)
        raiz.addWidget(self._panel_totales(), stretch=0)

    def _panel_izquierdo(self) -> QWidget:
        contenedor = QWidget()
        columna = QVBoxLayout(contenedor)
        columna.setContentsMargins(0, 0, 0, 0)
        columna.setSpacing(12)

        titulo = QLabel("Escanee el producto")
        titulo.setObjectName("tituloPantalla")
        columna.addWidget(titulo)

        ayuda = QLabel(
            "Pase el producto por el lector, o escriba el código y pulse Enter."
        )
        ayuda.setObjectName("subtitulo")
        columna.addWidget(ayuda)

        self.campo_codigo = QLineEdit()
        self.campo_codigo.setObjectName("campoEscaneo")
        self.campo_codigo.setPlaceholderText("Código de barras")
        self.campo_codigo.setClearButtonEnabled(True)
        self.campo_codigo.returnPressed.connect(self._procesar_codigo)
        self.campo_codigo.textEdited.connect(self._teclear)
        columna.addWidget(self.campo_codigo)

        self.mensaje = QLabel()
        self.mensaje.setWordWrap(True)
        self.mensaje.hide()
        columna.addWidget(self.mensaje)

        columna.addWidget(self._tabla_carrito(), stretch=1)
        return contenedor

    def _tabla_carrito(self) -> QTableWidget:
        self.tabla = QTableWidget(0, len(_COLUMNAS))
        self.tabla.setHorizontalHeaderLabels(_COLUMNAS)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        # La tabla no se edita a mano: las cantidades se cambian con las acciones, para que
        # no exista forma de dejar una línea en un estado que el carrito no conozca.
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.tabla.setAlternatingRowColors(False)
        self.tabla.setShowGrid(False)

        cabecera = self.tabla.horizontalHeader()
        cabecera.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        cabecera.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for columna in (2, 3, 4):
            cabecera.setSectionResizeMode(columna, QHeaderView.ResizeMode.ResizeToContents)

        tablas.alinear_cabeceras(
            self.tabla,
            (tablas.IZQUIERDA, tablas.IZQUIERDA, tablas.DERECHA, tablas.CENTRO, tablas.DERECHA),
        )
        return self.tabla

    def _panel_totales(self) -> QWidget:
        tarjeta = QFrame()
        tarjeta.setObjectName("tarjeta")
        tarjeta.setFixedWidth(330)

        columna = QVBoxLayout(tarjeta)
        columna.setContentsMargins(22, 22, 22, 22)
        columna.setSpacing(6)

        self.etiqueta_articulos = QLabel("0 artículos")
        self.etiqueta_articulos.setObjectName("subtitulo")
        columna.addWidget(self.etiqueta_articulos)

        columna.addSpacing(10)
        columna.addWidget(self._etiqueta_pequena("Subtotal"))
        self.valor_subtotal = QLabel("$0")
        self.valor_subtotal.setObjectName("valorSubtotal")
        columna.addWidget(self.valor_subtotal)

        self.fila_descuento = QWidget()
        fila = QVBoxLayout(self.fila_descuento)
        fila.setContentsMargins(0, 8, 0, 0)
        fila.setSpacing(2)
        fila.addWidget(self._etiqueta_pequena("Descuento"))
        self.valor_descuento = QLabel("$0")
        self.valor_descuento.setObjectName("valorDescuento")
        fila.addWidget(self.valor_descuento)
        columna.addWidget(self.fila_descuento)
        self.fila_descuento.hide()

        columna.addSpacing(14)
        columna.addWidget(self._etiqueta_pequena("TOTAL A PAGAR"))
        self.valor_total = QLabel("$0")
        self.valor_total.setObjectName("valorTotal")
        columna.addWidget(self.valor_total)

        columna.addStretch()

        self.boton_cobrar = QPushButton("Cobrar   (F12)")
        self.boton_cobrar.setObjectName("botonPrincipal")
        self.boton_cobrar.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.boton_cobrar.clicked.connect(self.cobrar)
        columna.addWidget(self.boton_cobrar)

        self.boton_quitar = QPushButton("Quitar línea   (F5)")
        self.boton_quitar.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.boton_quitar.clicked.connect(self.quitar_linea_seleccionada)
        columna.addWidget(self.boton_quitar)

        self.boton_descuento = QPushButton("Descuento   (F4)")
        self.boton_descuento.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.boton_descuento.clicked.connect(self.aplicar_descuento)
        columna.addWidget(self.boton_descuento)

        self.boton_vaciar = QPushButton("Cancelar venta   (F6)")
        self.boton_vaciar.setObjectName("botonPeligro")
        self.boton_vaciar.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.boton_vaciar.clicked.connect(self.cancelar_venta)
        columna.addWidget(self.boton_vaciar)

        return tarjeta

    @staticmethod
    def _etiqueta_pequena(texto: str) -> QLabel:
        etiqueta = QLabel(texto)
        etiqueta.setObjectName("etiquetaTotal")
        return etiqueta

    # ------------------------------------------------------------------ acciones

    def enfocar_escaneo(self) -> None:
        """Devuelve el foco al campo de escaneo y deja el campo listo para el siguiente."""
        self.campo_codigo.setFocus()
        self.campo_codigo.selectAll()

    def _teclear(self, texto: str) -> None:
        """Sigue la cadencia de escritura para reconocer una pistola sin Enter.

        Muchos lectores vienen configurados para enviar Enter al final, pero no todos. Si no
        lo hacen, el codigo se queda en el campo y parece que el lector no funciona. Al
        detectar una rafaga imposible para una persona, se confirma solo.
        """
        self._auto.stop()
        if not texto:
            self._detector.reiniciar()
            return

        self._detector.registrar()
        if self._detector.es_lector:
            self._auto.start(_ESPERA_LECTOR_MS)

    def _confirmar_automatico(self) -> None:
        if self.campo_codigo.text().strip():
            self._procesar_codigo()

    def _procesar_codigo(self) -> None:
        codigo = self.campo_codigo.text().strip()
        if not codigo:
            return
        self._auto.stop()
        self._detector.reiniciar()
        self.campo_codigo.clear()
        self.agregar_por_codigo(codigo)

    def agregar_por_codigo(self, codigo: str) -> None:
        """Busca el producto y lo añade al carrito, o explica por qué no se pudo."""
        try:
            producto = catalogo.consultar_por_codigo(self._conexion, codigo)
        except ProductoNoEncontrado:
            self._codigo_no_encontrado(codigo)
            return
        except ErrorDominio as error:
            self._avisar(str(error), exito=False)
            return

        try:
            self._carrito.agregar(producto)
        except ErrorDominio as error:
            self._avisar(str(error), exito=False)
            return

        self._refrescar()
        self._seleccionar(producto.codigo_barras)
        self._avisar(
            f"{producto.nombre} · {formatear_clp(producto.precio_clp)}", exito=True
        )
        self.enfocar_escaneo()

    def _codigo_no_encontrado(self, codigo: str) -> None:
        dialogo = dialogos.DialogoCodigoNoEncontrado(codigo.strip(), self)
        dialogo.exec()
        if dialogo.buscar_por_nombre:
            self.buscar_por_nombre()
        else:
            self.enfocar_escaneo()

    def buscar_por_nombre(self) -> None:
        dialogo = dialogos.DialogoTexto(
            "Buscar producto",
            "Escriba parte del nombre del producto:",
            self,
            ayuda="Por ejemplo: leche, papas, detergente.",
        )
        if not dialogo.exec():
            self.enfocar_escaneo()
            return

        resultados = catalogo.buscar_por_nombre(self._conexion, dialogo.texto)
        if not resultados:
            self._avisar("No se encontró ningún producto con ese nombre.", exito=False)
            self.enfocar_escaneo()
            return

        from .buscador import DialogoResultados

        seleccion = DialogoResultados(resultados, self).elegir()
        if seleccion is not None:
            self.agregar_por_codigo(seleccion.codigo_barras)
        else:
            self.enfocar_escaneo()

    def quitar_linea_seleccionada(self) -> None:
        fila = self.tabla.currentRow()
        if fila < 0:
            self._avisar("Seleccione primero una línea del carrito.", exito=False)
            self.enfocar_escaneo()
            return

        codigo = self.tabla.item(fila, 0).text()
        linea = next((l for l in self._carrito.lineas if l.codigo_barras == codigo), None)
        if linea is None:  # pragma: no cover - la tabla siempre refleja el carrito
            return

        # Con varias unidades se quita una sola: es lo que ocurre cuando el cliente se
        # arrepiente de uno de tres yogures, y es más frecuente que anular la línea entera.
        if linea.cantidad > 1:
            self._carrito.cambiar_cantidad(codigo, linea.cantidad - 1)
            self._avisar(f"Se quitó una unidad de {linea.nombre}.", exito=True)
        else:
            self._carrito.quitar(codigo)
            self._avisar(f"Se quitó {linea.nombre} del carrito.", exito=True)

        self._refrescar()
        self.enfocar_escaneo()

    def aplicar_descuento(self) -> None:
        """Aplica, cambia o quita el descuento de la venta en curso."""
        if self._carrito.esta_vacio:
            self._avisar("Agregue productos antes de aplicar un descuento.", exito=False)
            self.enfocar_escaneo()
            return

        dialogo = dialogos.DialogoDescuento(self._carrito.subtotal_clp, self)
        if not dialogo.exec():
            self.enfocar_escaneo()
            return

        try:
            if dialogo.quitar:
                self._carrito.quitar_descuento()
                self._avisar("Descuento retirado.", exito=True)
            elif dialogo.es_porcentaje:
                self._carrito.aplicar_descuento_porcentaje(dialogo.valor)
                self._avisar(f"Descuento del {dialogo.valor:g}% aplicado.", exito=True)
            else:
                self._carrito.aplicar_descuento_monto(int(dialogo.valor))
                self._avisar(
                    f"Descuento de {formatear_clp(int(dialogo.valor))} aplicado.", exito=True
                )
        except ErrorDominio as error:
            self._avisar(str(error), exito=False)

        self._refrescar()
        self.enfocar_escaneo()

    def cancelar_venta(self) -> None:
        if self._carrito.esta_vacio:
            self.enfocar_escaneo()
            return
        if dialogos.confirmar(
            self,
            "Cancelar venta",
            f"Se quitarán los {self._carrito.cantidad_articulos} artículos del carrito.\n"
            "¿Desea cancelar la venta?",
            texto_si="Sí, cancelar",
        ):
            self._carrito.vaciar()
            self._refrescar()
            self._avisar("Venta cancelada.", exito=True)
        self.enfocar_escaneo()

    def cobrar(self) -> None:
        """Cierra la venta previa confirmación."""
        if self._carrito.esta_vacio:
            self._avisar("No hay productos que cobrar.", exito=False)
            self.enfocar_escaneo()
            return

        total = formatear_clp(self._carrito.total_clp)
        if not dialogos.confirmar(
            self,
            "Confirmar venta",
            f"Total a cobrar: {total}\n"
            f"{self._carrito.cantidad_articulos} artículos en {len(self._carrito.lineas)} "
            f"líneas.\n\n¿Confirma la venta?",
            texto_si="Sí, cobrar",
        ):
            self.enfocar_escaneo()
            return

        try:
            venta = servicio_venta.cerrar_venta(self._conexion, self._carrito, self.usuario)
        except ErrorDominio as error:
            dialogos.mostrar_error(self, str(error))
            self.enfocar_escaneo()
            return

        self._carrito.vaciar()
        self._refrescar()
        self._avisar(
            f"Venta N° {venta.folio} registrada por {formatear_clp(venta.total_clp)}.",
            exito=True,
        )
        self.venta_registrada.emit()
        self.enfocar_escaneo()

    # ------------------------------------------------------------------ presentación

    def _refrescar(self) -> None:
        """Vuelve a dibujar la tabla y los totales a partir del carrito."""
        self.tabla.setRowCount(len(self._carrito.lineas))
        for fila, linea in enumerate(self._carrito.lineas):
            self._celda(fila, 0, linea.codigo_barras)
            self._celda(fila, 1, linea.nombre)
            self._celda(fila, 2, formatear_clp(linea.precio_unit_clp), derecha=True)
            self._celda(fila, 3, str(linea.cantidad), centrada=True)
            self._celda(fila, 4, formatear_clp(linea.subtotal_clp), derecha=True, fuerte=True)

        self.etiqueta_articulos.setText(
            "Carrito vacío"
            if self._carrito.esta_vacio
            else f"{self._carrito.cantidad_articulos} artículos"
        )
        self.valor_subtotal.setText(formatear_clp(self._carrito.subtotal_clp))
        self.valor_total.setText(formatear_clp(self._carrito.total_clp))

        descuento = self._carrito.descuento_clp
        self.fila_descuento.setVisible(descuento > 0)
        self.valor_descuento.setText(f"-{formatear_clp(descuento)}")

        hay_productos = not self._carrito.esta_vacio
        self.boton_cobrar.setEnabled(hay_productos)
        self.boton_quitar.setEnabled(hay_productos)
        self.boton_descuento.setEnabled(hay_productos)
        self.boton_vaciar.setEnabled(hay_productos)

    def _celda(
        self,
        fila: int,
        columna: int,
        texto: str,
        derecha: bool = False,
        centrada: bool = False,
        fuerte: bool = False,
    ) -> None:
        celda = QTableWidgetItem(texto)
        if derecha:
            celda.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        elif centrada:
            celda.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        if fuerte:
            fuente = celda.font()
            fuente.setBold(True)
            celda.setFont(fuente)
        self.tabla.setItem(fila, columna, celda)

    def _seleccionar(self, codigo_barras: str) -> None:
        for fila in range(self.tabla.rowCount()):
            if self.tabla.item(fila, 0).text() == codigo_barras:
                self.tabla.selectRow(fila)
                self.tabla.scrollToItem(self.tabla.item(fila, 0))
                return

    def _avisar(self, texto: str, exito: bool) -> None:
        """Muestra un mensaje breve bajo el campo de escaneo.

        Se usa un mensaje en línea y no un diálogo porque interrumpir el flujo con una
        ventana modal por cada producto escaneado haría el sistema inusable.
        """
        sonido.exito() if exito else sonido.error()
        self.mensaje.setText(texto)
        self.mensaje.setObjectName("mensajeExito" if exito else "mensajeError")
        # Qt no reevalúa la hoja de estilos al cambiar el objectName; hay que forzarlo.
        self.mensaje.style().unpolish(self.mensaje)
        self.mensaje.style().polish(self.mensaje)
        self.mensaje.show()
        QTimer.singleShot(_MENSAJE_MS, self.mensaje.hide)

    # ------------------------------------------------------------------ consultas

    @property
    def carrito(self) -> Carrito:
        return self._carrito
