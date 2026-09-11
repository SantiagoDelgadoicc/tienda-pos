"""Pantalla de venta: escanear, armar el carrito y cobrar.

Toda la pantalla está pensada para operarse sin ratón. El foco vuelve al campo de escaneo
después de cualquier acción, porque en una caja el cajero mira al cliente, no a la pantalla,
y si el foco se pierde el siguiente escaneo se pierde con él.
"""

from __future__ import annotations

import sqlite3

from PySide6.QtCore import QEvent, Qt, QTimer, Signal
from PySide6.QtGui import QGuiApplication, QKeyEvent
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
from ..services.preferencias import Preferencias
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

# Las columnas sin título son celdas de acción: copiar el código y ajustar la cantidad. Se
# resuelven con celdas normales y no con botones dentro de la tabla porque Qt deja vivos los
# widgets de las filas que desaparecen, y quedan flotando sobre la tabla.
_COLUMNAS = ("Código", "", "Producto", "Precio", "", "Cant.", "", "Desc.", "Subtotal")

COL_CODIGO = 0
COL_COPIAR = 1
COL_NOMBRE = 2
COL_PRECIO = 3
COL_MENOS = 4
COL_CANTIDAD = 5
COL_MAS = 6
COL_DESCUENTO = 7
COL_SUBTOTAL = 8

#: Símbolos de las celdas de acción.
_COPIAR = "⧉"
_MENOS = "−"
_MAS = "+"


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
        self.preferencias = Preferencias()
        self._detector = DetectorLector()
        self._auto = QTimer(self)
        self._auto.setSingleShot(True)
        self._auto.timeout.connect(self._confirmar_automatico)

        self._construir()
        self._refrescar()
        # El campo de escaneo se queda con el foco toda la sesión, así que es ahí donde hay
        # que interceptar las teclas que gobiernan el carrito.
        self.campo_codigo.installEventFilter(self)

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
        # Solo el nombre del producto se estira; el resto ocupa lo que necesita, que en una
        # tabla de caja es lo que permite leerla de un vistazo.
        for columna in range(len(_COLUMNAS)):
            modo = (
                QHeaderView.ResizeMode.Stretch
                if columna == COL_NOMBRE
                else QHeaderView.ResizeMode.ResizeToContents
            )
            cabecera.setSectionResizeMode(columna, modo)

        tablas.alinear_cabeceras(
            self.tabla,
            (
                tablas.IZQUIERDA,   # código
                tablas.CENTRO,      # copiar
                tablas.IZQUIERDA,   # producto
                tablas.DERECHA,     # precio
                tablas.CENTRO,      # quitar una unidad
                tablas.CENTRO,      # cantidad
                tablas.CENTRO,      # agregar una unidad
                tablas.DERECHA,     # descuento
                tablas.DERECHA,     # subtotal
            ),
        )
        # Un clic en las celdas de acción ejecuta su acción; en cualquier otra, solo
        # selecciona la línea.
        self.tabla.cellClicked.connect(self._celda_pulsada)
        # La columna de descuentos solo aparece cuando hay alguno: una columna vacía en cada
        # venta normal sería ruido permanente por un caso ocasional.
        self.tabla.setColumnHidden(COL_DESCUENTO, True)
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
        self.etiqueta_descuento = self._etiqueta_pequena("Descuento")
        fila.addWidget(self.etiqueta_descuento)
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

    def repintar(self) -> None:
        """Vuelve a dibujar la tabla con los colores del tema actual.

        Los colores de las celdas de acción se fijan al crearlas, así que un cambio de tema
        no las alcanza: sin esto, quedarían con el fondo del tema anterior.
        """
        self._refrescar()

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

    # ------------------------------------------------------------------ teclado

    def eventFilter(self, objeto, evento) -> bool:  # noqa: N802 - lo nombra Qt
        """Convierte las teclas de dirección en acciones sobre el carrito.

        El cajero tiene una mano en el lector y la otra en el producto: obligarle a soltar
        algo para buscar el ratón es lo que hace lento un punto de venta. Las flechas y las
        teclas + y - solo se interceptan con el campo de escaneo vacío, que es su estado
        habitual; si hay un código a medio escribir, siguen sirviendo para editarlo.
        """
        if objeto is self.campo_codigo and evento.type() == QEvent.Type.KeyPress:
            if self._atajo_de_carrito(evento):
                return True
        return super().eventFilter(objeto, evento)

    def _atajo_de_carrito(self, evento: QKeyEvent) -> bool:
        """Devuelve True si la tecla se consumió como acción del carrito."""
        tecla = evento.key()
        con_control = bool(evento.modifiers() & Qt.KeyboardModifier.ControlModifier)

        if con_control and tecla == Qt.Key.Key_C and not self.campo_codigo.hasSelectedText():
            self.copiar_codigo_seleccionado()
            return True

        # Arriba y abajo no hacen nada dentro de un campo de una sola línea, así que se
        # pueden tomar siempre.
        if tecla == Qt.Key.Key_Up:
            self.mover_seleccion(-1)
            return True
        if tecla == Qt.Key.Key_Down:
            self.mover_seleccion(1)
            return True

        # Con el carrito vacío las flechas no son un error del cajero, así que no se las
        # responde con un aviso: simplemente no hacen nada.
        if self.campo_codigo.text() or self._carrito.esta_vacio:
            return False

        if tecla in (Qt.Key.Key_Right, Qt.Key.Key_Plus):
            self.aumentar_cantidad()
            return True
        if tecla in (Qt.Key.Key_Left, Qt.Key.Key_Minus):
            self.disminuir_cantidad()
            return True
        return False

    def mover_seleccion(self, paso: int) -> None:
        """Mueve la línea seleccionada del carrito sin tocar el foco del campo."""
        filas = self.tabla.rowCount()
        if filas == 0:
            return
        actual = self.tabla.currentRow()
        # Sin nada seleccionado, abajo empieza por la primera y arriba por la última.
        destino = (0 if paso > 0 else filas - 1) if actual < 0 else actual + paso
        destino = max(0, min(filas - 1, destino))
        self.tabla.selectRow(destino)
        self.tabla.scrollToItem(self.tabla.item(destino, COL_CODIGO))

    # ------------------------------------------------------------------ cantidades

    def _codigo_seleccionado(self, aviso: bool = True) -> str | None:
        fila = self.tabla.currentRow()
        if fila < 0 or self.tabla.item(fila, COL_CODIGO) is None:
            if aviso:
                self._avisar("Seleccione primero una línea del carrito.", exito=False)
                self.enfocar_escaneo()
            return None
        return self.tabla.item(fila, COL_CODIGO).text()

    def aumentar_cantidad(self, codigo: str | None = None) -> None:
        """Suma una unidad a la línea indicada, o a la seleccionada."""
        codigo = codigo or self._codigo_seleccionado()
        if codigo is None:
            return
        linea = self._carrito.linea_de(codigo)
        if linea is None:  # pragma: no cover - la tabla siempre refleja el carrito
            return

        try:
            self._carrito.cambiar_cantidad(codigo, linea.cantidad + 1)
        except ErrorDominio as error:
            self._avisar(str(error), exito=False)
            self.enfocar_escaneo()
            return

        self._refrescar()
        self._seleccionar(codigo)
        self._avisar(f"{linea.nombre}: {linea.cantidad} unidades.", exito=True)
        self.enfocar_escaneo()

    def disminuir_cantidad(self, codigo: str | None = None) -> None:
        """Quita una unidad. Al llegar a cero, la línea desaparece del carrito.

        Con varias unidades se quita una sola: es lo que ocurre cuando el cliente se
        arrepiente de uno de tres yogures, y es más frecuente que anular la línea entera.
        """
        codigo = codigo or self._codigo_seleccionado()
        if codigo is None:
            return
        linea = self._carrito.linea_de(codigo)
        if linea is None:  # pragma: no cover - la tabla siempre refleja el carrito
            return

        nombre = linea.nombre
        if linea.cantidad > 1:
            self._carrito.cambiar_cantidad(codigo, linea.cantidad - 1)
            self._avisar(f"Se quitó una unidad de {nombre}.", exito=True)
            self._refrescar()
            self._seleccionar(codigo)
        else:
            self._carrito.quitar(codigo)
            self._avisar(f"Se quitó {nombre} del carrito.", exito=True)
            self._refrescar()
        self.enfocar_escaneo()

    def copiar_codigo_seleccionado(self, codigo: str | None = None) -> None:
        """Deja el código de barras en el portapapeles.

        Sirve para pegarlo en el buscador del proveedor, en una planilla o en un mensaje al
        administrador, que es lo que se hace cuando un producto tiene el precio equivocado.
        """
        codigo = codigo or self._codigo_seleccionado()
        if codigo is None:
            return

        portapapeles = QGuiApplication.clipboard()
        if portapapeles is None:  # pragma: no cover - solo en entornos sin escritorio
            self._avisar("Este equipo no tiene portapapeles disponible.", exito=False)
            self.enfocar_escaneo()
            return

        portapapeles.setText(codigo)
        self._avisar(f"Código {codigo} copiado.", exito=True)
        self.enfocar_escaneo()

    def quitar_linea_seleccionada(self) -> None:
        """F5. Hace lo mismo que la flecha izquierda: quitar una unidad."""
        self.disminuir_cantidad()

    def aplicar_descuento(self) -> None:
        """Aplica, cambia o quita un descuento, sobre toda la venta o sobre un producto.

        El diálogo ofrece los dos ámbitos y llega con el de la venta marcado: es el caso
        frecuente, y el que ya conocía quien usaba la versión anterior.
        """
        if self._carrito.esta_vacio:
            self._avisar("Agregue productos antes de aplicar un descuento.", exito=False)
            self.enfocar_escaneo()
            return

        codigo = self._codigo_seleccionado(aviso=False)
        linea = self._carrito.linea_de(codigo) if codigo else None

        dialogo = dialogos.DialogoDescuento(
            self._carrito.base_descontable_clp, self, linea=linea
        )
        if not dialogo.exec():
            self.enfocar_escaneo()
            return

        try:
            if dialogo.ambito == dialogos.AMBITO_PRODUCTO and linea is not None:
                self._descuento_de_linea(dialogo, linea)
            else:
                self._descuento_de_venta(dialogo)
        except ErrorDominio as error:
            self._avisar(str(error), exito=False)

        self._refrescar()
        if codigo:
            self._seleccionar(codigo)
        self.enfocar_escaneo()

    def _descuento_de_venta(self, dialogo) -> None:
        if dialogo.quitar:
            self._carrito.quitar_descuento()
            self._avisar("Descuento de la venta retirado.", exito=True)
        elif dialogo.es_porcentaje:
            self._carrito.aplicar_descuento_porcentaje(dialogo.valor)
            self._avisar(f"Descuento del {dialogo.valor:g}% aplicado a la venta.", exito=True)
        else:
            self._carrito.aplicar_descuento_monto(int(dialogo.valor))
            self._avisar(
                f"Descuento de {formatear_clp(int(dialogo.valor))} aplicado a la venta.",
                exito=True,
            )

    def _descuento_de_linea(self, dialogo, linea) -> None:
        codigo = linea.codigo_barras
        if dialogo.quitar:
            self._carrito.quitar_descuento_linea(codigo)
            self._avisar(f"Descuento de {linea.nombre} retirado.", exito=True)
        elif dialogo.es_porcentaje:
            self._carrito.aplicar_descuento_linea_porcentaje(codigo, dialogo.valor)
            self._avisar(
                f"Descuento del {dialogo.valor:g}% aplicado a {linea.nombre}.", exito=True
            )
        else:
            self._carrito.aplicar_descuento_linea_monto(codigo, int(dialogo.valor))
            self._avisar(
                f"Descuento de {formatear_clp(int(dialogo.valor))} aplicado a "
                f"{linea.nombre}.",
                exito=True,
            )

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
        # La confirmación se puede desactivar desde la configuración: en una caja con mucho
        # movimiento, un diálogo por venta son cientos de pulsaciones al día.
        if self.preferencias.confirmar_cobro and not dialogos.confirmar(
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
        hay_descuento_de_linea = any(linea.tiene_descuento for linea in self._carrito.lineas)
        # La columna de descuentos solo aparece cuando hay alguno: una columna vacía en cada
        # venta normal sería ruido permanente por un caso ocasional.
        self.tabla.setColumnHidden(COL_DESCUENTO, not hay_descuento_de_linea)

        tope = servicio_venta.CANTIDAD_MAX_POR_LINEA
        for fila, linea in enumerate(self._carrito.lineas):
            self._celda(fila, COL_CODIGO, linea.codigo_barras)
            self._celda(fila, COL_NOMBRE, linea.nombre)
            self._celda(fila, COL_PRECIO, formatear_clp(linea.precio_unit_clp), derecha=True)
            self._celda(fila, COL_CANTIDAD, str(linea.cantidad), centrada=True, fuerte=True)
            self._celda(
                fila,
                COL_DESCUENTO,
                f"-{formatear_clp(linea.descuento_clp)}" if linea.tiene_descuento else "",
                derecha=True,
            )
            self._celda(
                fila, COL_SUBTOTAL, formatear_clp(linea.total_clp), derecha=True, fuerte=True
            )

            self._celda_accion(
                fila, COL_COPIAR, _COPIAR, f"Copiar el código {linea.codigo_barras}   (Ctrl+C)"
            )
            self._celda_accion(
                fila,
                COL_MENOS,
                _MENOS,
                f"Quitar una unidad de {linea.nombre}   (flecha izquierda)",
            )
            self._celda_accion(
                fila,
                COL_MAS,
                _MAS,
                f"Agregar una unidad de {linea.nombre}   (flecha derecha)",
                activa=linea.cantidad < tope,
            )

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
        # Cuando el descuento viene de varios sitios, el panel dice de dónde: si no, un
        # total más bajo de lo esperado no tendría explicación a la vista.
        self.etiqueta_descuento.setText(self._titulo_descuento(hay_descuento_de_linea))

        hay_productos = not self._carrito.esta_vacio
        self.boton_cobrar.setEnabled(hay_productos)
        self.boton_quitar.setEnabled(hay_productos)
        self.boton_descuento.setEnabled(hay_productos)
        self.boton_vaciar.setEnabled(hay_productos)

    def _titulo_descuento(self, hay_descuento_de_linea: bool) -> str:
        if not hay_descuento_de_linea:
            return "Descuento"
        if self._carrito.descuento_venta_clp > 0:
            return "Descuento (venta y productos)"
        return "Descuento en productos"

    def _celda_accion(self, fila: int, columna: int, simbolo: str, ayuda: str, activa: bool = True) -> None:
        """Celda que se comporta como un botón: un símbolo centrado sobre un fondo suave.

        Se usa una celda y no un QPushButton porque los widgets incrustados en una tabla que
        se redibuja entera en cada escaneo dejan restos visibles, y en una caja eso se
        traduce en botones que no hacen nada donde ya no hay producto.
        """
        from PySide6.QtGui import QBrush, QColor

        from . import estilos

        celda = QTableWidgetItem(simbolo if activa else "")
        celda.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        celda.setToolTip(ayuda if activa else "")
        if activa:
            paleta = estilos.actual
            celda.setBackground(QBrush(QColor(paleta.superficie_alterna)))
            celda.setForeground(QBrush(QColor(paleta.primario)))
            fuente = celda.font()
            fuente.setBold(True)
            celda.setFont(fuente)
        self.tabla.setItem(fila, columna, celda)

    def _celda_pulsada(self, fila: int, columna: int) -> None:
        """Ejecuta la acción de la celda pulsada, si es una de las de acción."""
        item = self.tabla.item(fila, COL_CODIGO)
        if item is None:  # pragma: no cover - la tabla siempre refleja el carrito
            return
        codigo = item.text()

        if columna == COL_COPIAR:
            self.copiar_codigo_seleccionado(codigo)
        elif columna == COL_MENOS:
            self.disminuir_cantidad(codigo)
        elif columna == COL_MAS:
            self.aumentar_cantidad(codigo)

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
            if self.tabla.item(fila, COL_CODIGO).text() == codigo_barras:
                self.tabla.selectRow(fila)
                self.tabla.scrollToItem(self.tabla.item(fila, COL_CODIGO))
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
