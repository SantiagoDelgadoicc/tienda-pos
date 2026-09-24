"""Pantalla de venta: escanear, armar el carrito y cobrar.

Toda la pantalla está pensada para operarse sin ratón. El foco vuelve al campo de escaneo
después de cualquier acción, porque en una caja el cajero mira al cliente, no a la pantalla,
y si el foco se pierde el siguiente escaneo se pierde con él.
"""

from __future__ import annotations

import uuid


from PySide6.QtCore import QEvent, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QGuiApplication, QKeyEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..domain.errors import ErrorDominio, ProductoNoEncontrado
from ..domain.models import MedioPago, Usuario
from ..red.sesion import Sesion
from ..services import venta as servicio_venta
from ..services.preferencias import Preferencias
from ..services.venta import Carrito
from ..utils import sonido
from ..utils.money import formatear_clp
from ..utils.scanner import DetectorLector
from . import dialogos, estilos, iconos, movimiento, tablas

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

#: Los medios de pago, en el orden en que los recorre F11 y en que aparecen en pantalla.
#: Efectivo primero: es lo más frecuente y a lo que se vuelve tras cada venta.
MEDIOS = (MedioPago.EFECTIVO, MedioPago.DEBITO, MedioPago.CREDITO)
NOMBRE_MEDIO = {
    MedioPago.EFECTIVO: "Efectivo",
    MedioPago.DEBITO: "Débito",
    MedioPago.CREDITO: "Crédito",
}

#: Tamaños que puede tomar el total, de mayor a menor. Se usa el primero que quepa entero.
#: Medidos, no supuestos: a 62 px cabe un total de seis cifras —$480.000— en los 256 px útiles
#: de la tarjeta de cobro, y a 66 px ya no. Los de abajo son la red para una venta de siete
#: cifras, que se saldría a cualquier tamaño por encima de 52.
_TAMANOS_TOTAL = (62, 54, 48, 42)

#: Ancho útil dentro de la tarjeta de cobro: su ancho menos los dos márgenes laterales.
_ANCHO_TOTAL = 300 - 22 * 2

#: Proporción del interletrado respecto al tamaño. Cuanto más grande es la cifra, más se
#: aprieta, que es lo que pide la escala tipográfica de `docs/DESIGN.md`.
_INTERLETRADO_TOTAL = -0.035

#: Símbolos de las celdas de acción.
_COPIAR = "⧉"
_MENOS = "−"
_MAS = "+"


class _DelegadoDestello(QStyledItemDelegate):
    """Pinta la línea que acaba de cambiar con un lavado verde que se apaga.

    El carrito ya selecciona la línea tocada, pero la selección es un gris casi igual al
    papel y además se queda: no distingue «acaba de pasar» de «está ahí desde antes». El
    destello dura 700 ms, en el verde de «salió bien», y responde a lo que el cajero busca al
    oír el pitido: ¿cuál de todas se movió?

    Se pinta con un delegado y no cambiando el fondo de las celdas porque la selección de la
    hoja de estilos taparía cualquier fondo. Mientras dura el destello, la fila se dibuja
    como no seleccionada sobre el color mezclado; al terminar vuelve a su gris.
    """

    def __init__(self, vista: "VentaView") -> None:
        super().__init__(vista.tabla)
        self._vista = vista

    def paint(self, pintor, opcion, indice) -> None:  # noqa: D401 - lo nombra Qt
        intensidad = self._vista.intensidad_destello(indice.row())
        if intensidad <= 0:
            super().paint(pintor, opcion, indice)
            return

        paleta = estilos.actual
        seleccionada = bool(opcion.state & QStyle.StateFlag.State_Selected)
        base = QColor(paleta.seleccion if seleccionada else paleta.superficie)
        verde = QColor(paleta.exito_suave)
        mezcla = QColor(
            round(base.red() + (verde.red() - base.red()) * intensidad),
            round(base.green() + (verde.green() - base.green()) * intensidad),
            round(base.blue() + (verde.blue() - base.blue()) * intensidad),
        )
        pintor.fillRect(opcion.rect, mezcla)

        sin_seleccion = QStyleOptionViewItem(opcion)
        sin_seleccion.state &= ~QStyle.StateFlag.State_Selected
        super().paint(pintor, sin_seleccion, indice)


class VentaView(QWidget):
    """Pantalla principal del punto de venta."""

    #: Se emite cuando el usuario pide la pantalla de consulta de precio.
    consulta_solicitada = Signal()
    #: Se emite tras cerrar una venta, para que la ventana actualice sus indicadores.
    venta_registrada = Signal()

    def __init__(self, sesion: Sesion, padre: QWidget | None = None) -> None:
        super().__init__(padre)
        self._sesion = sesion
        #: Intento de cobro en curso. Ver `cobrar`.
        self._intento_cobro: str | None = None
        self._carrito = Carrito()
        self.usuario: Usuario | None = None
        self.preferencias = Preferencias()
        self._detector = DetectorLector()
        self._auto = QTimer(self)
        self._auto.setSingleShot(True)
        self._auto.timeout.connect(self._confirmar_automatico)
        #: Último tamaño aplicado al total. Evita repintar la etiqueta en cada escaneo.
        self._tamano_total: int | None = None
        # Un único temporizador para el aviso, reutilizado en cada mensaje. Ver `_avisar`.
        self._temporizador_mensaje = QTimer(self)
        self._temporizador_mensaje.setSingleShot(True)
        #: Línea que destella y cuánto le queda, de 1 a 0. Ver `_DelegadoDestello`.
        self._fila_destello = -1
        self._intensidad_destello = 0.0
        self._anim_destello = movimiento.animacion(self, movimiento.DESTELLO_MS)
        # Se sostiene un instante en el verde lleno y después se apaga desacelerando: si
        # empezara a apagarse de inmediato, en una fila corta casi no se vería.
        self._anim_destello.setKeyValueAt(0.0, 1.0)
        self._anim_destello.setKeyValueAt(0.2, 1.0)
        self._anim_destello.setKeyValueAt(1.0, 0.0)
        self._anim_destello.valueChanged.connect(self._pintar_destello)

        self._construir()
        self.repintar()
        # El campo de escaneo se queda con el foco toda la sesión, así que es ahí donde hay
        # que interceptar las teclas que gobiernan el carrito.
        self.campo_codigo.installEventFilter(self)

    # ------------------------------------------------------------------ construcción

    def _construir(self) -> None:
        raiz = QHBoxLayout(self)
        raiz.setContentsMargins(24, 22, 24, 22)
        raiz.setSpacing(20)
        raiz.addWidget(self._panel_izquierdo(), stretch=1)
        raiz.addWidget(self._panel_totales(), stretch=0)

    def _panel_izquierdo(self) -> QWidget:
        contenedor = QWidget()
        contenedor.setObjectName("transparente")
        columna = QVBoxLayout(contenedor)
        columna.setContentsMargins(0, 0, 0, 0)
        columna.setSpacing(14)

        columna.addWidget(self._campo_de_escaneo())
        columna.addWidget(self._tarjeta_carrito(), stretch=1)
        return contenedor

    def _campo_de_escaneo(self) -> QWidget:
        """El campo grande, con el icono del lector dentro.

        Va suelto sobre el lienzo y no dentro de una tarjeta: es el único sitio donde el
        cajero escribe, y meterlo en una caja dentro de otra caja solo le quitaba peso.
        """
        self.campo_codigo = QLineEdit()
        self.campo_codigo.setObjectName("campoEscaneo")
        self.campo_codigo.setPlaceholderText("Escanee o escriba el código de barras")
        self.campo_codigo.setClearButtonEnabled(True)
        self.campo_codigo.returnPressed.connect(self._procesar_codigo)
        self.campo_codigo.textEdited.connect(self._teclear)
        # Qt coloca la acción dentro del campo y desplaza el texto: es la forma de tener el
        # icono ahí dentro sin montar un contenedor con el campo sin borde.
        self._icono_campo = self.campo_codigo.addAction(
            iconos.icono("escanear", 24, estilos.actual.texto_apagado),
            QLineEdit.ActionPosition.LeadingPosition,
        )
        return self.campo_codigo

    def _tarjeta_carrito(self) -> QWidget:
        tarjeta = QFrame()
        tarjeta.setObjectName("tarjeta")
        estilos.aplicar_sombra(tarjeta)

        columna = QVBoxLayout(tarjeta)
        columna.setContentsMargins(20, 16, 20, 12)
        columna.setSpacing(0)

        cabecera = QHBoxLayout()
        cabecera.setContentsMargins(0, 0, 0, 0)
        titulo = QLabel("Carrito")
        titulo.setObjectName("tituloTarjeta")
        cabecera.addWidget(titulo)
        cabecera.addStretch()
        self.etiqueta_articulos = QLabel("Carrito vacío")
        self.etiqueta_articulos.setObjectName("ficha")
        cabecera.addWidget(self.etiqueta_articulos)
        columna.addLayout(cabecera)
        columna.addSpacing(14)

        # Carrito vacío y carrito con líneas son dos estados, no uno con la tabla a cero:
        # una cabecera de tabla sobre un vacío blanco no dice nada, y lo primero que ve un
        # cajero al abrir la caja es justamente esto.
        self._pila_carrito = QStackedWidget()
        self._pila_carrito.setObjectName("transparente")
        self._pila_carrito.addWidget(self._carrito_vacio())
        self._pila_carrito.addWidget(self._tabla_carrito())
        columna.addWidget(self._pila_carrito, stretch=1)
        return tarjeta

    def _carrito_vacio(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("transparente")
        columna = QVBoxLayout(panel)
        columna.setContentsMargins(0, 0, 0, 0)
        columna.setSpacing(10)
        columna.addStretch()

        self._icono_vacio = QLabel()
        self._icono_vacio.setAlignment(Qt.AlignmentFlag.AlignCenter)
        columna.addWidget(self._icono_vacio)

        titulo = QLabel("Todavía no hay productos")
        titulo.setObjectName("consultaVacio")
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        columna.addWidget(titulo)

        pista = QLabel("Pase el primero por el lector para empezar la venta.")
        pista.setObjectName("subtitulo")
        pista.setAlignment(Qt.AlignmentFlag.AlignCenter)
        columna.addWidget(pista)

        columna.addStretch()
        return panel

    def _tabla_carrito(self) -> QTableWidget:
        self.tabla = QTableWidget(0, len(_COLUMNAS))
        # Sin marco propio: el marco ya lo pone la tarjeta que la contiene.
        self.tabla.setObjectName("tablaLimpia")
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
        self.tabla.verticalHeader().setDefaultSectionSize(46)

        cabecera = self.tabla.horizontalHeader()
        cabecera.setHighlightSections(False)
        cabecera.setFixedHeight(34)
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
        self.tabla.setItemDelegate(_DelegadoDestello(self))
        return self.tabla

    def _panel_totales(self) -> QWidget:
        """La columna derecha: lo que se está sumando arriba, lo que se cobra abajo.

        Son dos tarjetas y no una porque una sola, estirada a todo el alto, dejaba un hueco
        blanco enorme entre el título y las cifras. Partida en dos, ese hueco deja de ser un
        vacío y pasa a ser la separación entre dos cosas distintas: el detalle de la cuenta y
        el acto de cobrarla. El botón de cobrar sigue anclado abajo, que es donde la mano ya
        está y donde el cajero lo busca sin mirar.
        """
        panel = QWidget()
        panel.setObjectName("transparente")
        panel.setFixedWidth(300)

        columna = QVBoxLayout(panel)
        columna.setContentsMargins(0, 0, 0, 0)
        columna.setSpacing(14)
        self.tarjeta_detalle = self._tarjeta_detalle()
        columna.addWidget(self.tarjeta_detalle)
        columna.addStretch()
        columna.addWidget(self._aviso())
        columna.addWidget(self._tarjeta_cobro())
        return panel

    def _aviso(self) -> QWidget:
        """El mensaje que confirma o rechaza cada escaneo.

        Vive en el hueco de esta columna y no bajo el campo de escaneo, que sería su sitio
        natural, por una razón práctica: ahí abajo empujaba el carrito hacia abajo al
        aparecer y lo subía al desvanecerse, de modo que la tabla daba un salto en cada
        producto. Aquí crece hacia arriba contra un espacio que ya estaba vacío, así que ni
        el carrito ni el botón de cobrar se mueven nunca. De paso queda al lado del total,
        que es lo otro que el cajero mira al terminar de pasar un producto.

        Se usa un mensaje en línea y no un diálogo porque interrumpir el flujo con una
        ventana modal por cada producto escaneado haría el sistema inusable.
        """
        self.mensaje = QLabel()
        # El id se fija ya en la construcción, y no solo al mostrar un aviso: Qt calcula el
        # relleno y el radio la primera vez que poliza el widget, y si entonces no hay
        # ninguna regla por id, el mensaje se queda para siempre pegado al borde. Las dos
        # variantes comparten geometría, así que alternarlas después solo cambia colores.
        self.mensaje.setObjectName("mensajeExito")
        self.mensaje.setWordWrap(True)
        self.mensaje.hide()
        # Entra con un fundido corto y se va con otro. Si llega un aviso con el anterior aún
        # a la vista, no vuelve a entrar: parpadea, que es lo que dice «esto es nuevo».
        self._fundido_mensaje = movimiento.Fundido(self.mensaje)
        self._temporizador_mensaje.timeout.connect(self._fundido_mensaje.ocultar)
        return self.mensaje

    def _tarjeta_detalle(self) -> QWidget:
        """Lo que se lleva sumado: subtotal y, si lo hay, el descuento.

        Con el carrito vacío no se muestra: una tarjeta que solo dice «SUBTOTAL $0» no
        informa de nada y deja la columna con un recuadro huérfano arriba. Aparece con el
        primer producto, que es cuando el número empieza a significar algo.
        """
        tarjeta = QFrame()
        tarjeta.setObjectName("tarjeta")
        estilos.aplicar_sombra(tarjeta)

        columna = QVBoxLayout(tarjeta)
        columna.setContentsMargins(22, 18, 22, 18)
        columna.setSpacing(0)

        self.valor_subtotal = QLabel("$0")
        self.valor_subtotal.setObjectName("valorSubtotal")
        columna.addLayout(self._renglon(self._etiqueta_pequena("Subtotal"), self.valor_subtotal))

        # Renglón del descuento: aparece solo cuando hay uno, para que una venta normal no
        # arrastre una línea a cero.
        self.fila_descuento = QWidget()
        self.fila_descuento.setObjectName("transparente")
        interior = QVBoxLayout(self.fila_descuento)
        interior.setContentsMargins(0, 12, 0, 0)
        interior.setSpacing(0)
        self.etiqueta_descuento = self._etiqueta_pequena("Descuento")
        # El rótulo dice de dónde sale el descuento y a veces no cabe en un renglón de 300 px.
        # Se parte en dos líneas antes que recortar la explicación, que es justo lo que evita
        # que un total más bajo de lo esperado parezca un error (D-012).
        self.etiqueta_descuento.setWordWrap(True)
        self.valor_descuento = QLabel("$0")
        self.valor_descuento.setObjectName("valorDescuento")
        interior.addLayout(self._renglon(self.etiqueta_descuento, self.valor_descuento))
        columna.addWidget(self.fila_descuento)
        self.fila_descuento.hide()

        return tarjeta

    def _tarjeta_cobro(self) -> QWidget:
        """El total y las cuatro acciones que cierran o deshacen la venta."""
        tarjeta = QFrame()
        tarjeta.setObjectName("tarjeta")
        estilos.aplicar_sombra(tarjeta)

        columna = QVBoxLayout(tarjeta)
        columna.setContentsMargins(22, 20, 22, 20)
        columna.setSpacing(0)

        etiqueta = self._etiqueta_pequena("Total a pagar")
        etiqueta.setObjectName("etiquetaTotalFuerte")
        columna.addWidget(etiqueta)
        columna.addSpacing(2)

        self.valor_total = QLabel("$0")
        self.valor_total.setObjectName("valorTotal")
        columna.addWidget(self.valor_total)
        columna.addSpacing(14)

        columna.addLayout(self._selector_de_pago())
        columna.addSpacing(12)

        self.boton_cobrar = QPushButton("Cobrar   ·   F12")
        self.boton_cobrar.setObjectName("botonPrincipal")
        self.boton_cobrar.setMinimumHeight(56)
        self.boton_cobrar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.boton_cobrar.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.boton_cobrar.clicked.connect(self.cobrar)
        columna.addWidget(self.boton_cobrar)
        columna.addSpacing(10)

        # Las dos acciones intermedias van en una fila: bajan de peso frente a cobrar y
        # dejan sitio para que el total respire.
        pareja = QHBoxLayout()
        pareja.setContentsMargins(0, 0, 0, 0)
        pareja.setSpacing(8)
        self.boton_quitar = QPushButton("Quitar")
        self.boton_quitar.setToolTip("Quitar una unidad de la línea seleccionada   (F5)")
        self.boton_quitar.clicked.connect(self.quitar_linea_seleccionada)
        self.boton_descuento = QPushButton("Descuento")
        self.boton_descuento.setToolTip("Aplicar un descuento   (F4)")
        self.boton_descuento.clicked.connect(self.aplicar_descuento)
        for boton in (self.boton_quitar, self.boton_descuento):
            boton.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            boton.setCursor(Qt.CursorShape.PointingHandCursor)
            pareja.addWidget(boton)
        columna.addLayout(pareja)
        columna.addSpacing(8)

        self.boton_vaciar = QPushButton("Cancelar venta   ·   F6")
        self.boton_vaciar.setObjectName("botonPeligro")
        self.boton_vaciar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.boton_vaciar.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.boton_vaciar.clicked.connect(self.cancelar_venta)
        columna.addWidget(self.boton_vaciar)

        return tarjeta

    def _selector_de_pago(self) -> QHBoxLayout:
        """Efectivo, débito o crédito, sobre el botón de cobrar (fase 17).

        Siempre a la vista y nunca dentro del diálogo de confirmación, porque ese diálogo se
        puede desactivar y el medio quedaría inalcanzable justo en la caja con más movimiento.
        Los botones no toman el foco: el campo de escaneo tiene que seguir recibiendo la
        pistola. Con el teclado, F11 los recorre.
        """
        fila = QHBoxLayout()
        fila.setContentsMargins(0, 0, 0, 0)
        fila.setSpacing(6)
        self._grupo_medios = QButtonGroup(self)
        self._grupo_medios.setExclusive(True)
        self._botones_medio: dict[MedioPago, QPushButton] = {}
        for medio in MEDIOS:
            boton = QPushButton(NOMBRE_MEDIO[medio])
            boton.setObjectName("segmentoPago")
            # El color del elegido lo pone la hoja de estilos según el medio (D-034).
            boton.setProperty("medio", str(medio))
            boton.setCheckable(True)
            boton.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            boton.setCursor(Qt.CursorShape.PointingHandCursor)
            boton.setToolTip("Con qué paga el cliente   (F11 cambia)")
            boton.clicked.connect(lambda _=False, m=medio: self._pulsar_medio(m))
            self._grupo_medios.addButton(boton)
            self._botones_medio[medio] = boton
            fila.addWidget(boton)
        self._medio = MedioPago.EFECTIVO
        self._botones_medio[self._medio].setChecked(True)
        return fila

    @property
    def medio_pago(self) -> MedioPago:
        """El medio con que se cobrará la venta en curso."""
        return self._medio

    def elegir_medio_pago(self, medio: MedioPago) -> None:
        self._medio = medio
        self._botones_medio[medio].setChecked(True)

    def alternar_medio_pago(self) -> None:
        """F11: efectivo, débito, crédito y vuelta a empezar. Dos pulsaciones como mucho."""
        siguiente = MEDIOS[(MEDIOS.index(self._medio) + 1) % len(MEDIOS)]
        self.elegir_medio_pago(siguiente)

    def _pulsar_medio(self, medio: MedioPago) -> None:
        self.elegir_medio_pago(medio)
        self.enfocar_escaneo()

    def _empezar_venta_nueva(self) -> None:
        """Deja la pantalla como para el próximo cliente.

        El medio vuelve a efectivo: un selector que se quedara en débito cobraría mal la
        primera venta de la mañana siguiente, que casi siempre es en efectivo.
        """
        self.elegir_medio_pago(MedioPago.EFECTIVO)

    @staticmethod
    def _renglon(etiqueta: QLabel, valor: QLabel) -> QHBoxLayout:
        """Rótulo a la izquierda, cifra a la derecha, como en un recibo.

        Apilados uno sobre otro ocupaban el doble de alto y obligaban a leer en zigzag; en un
        renglón, la vista baja por la columna de cifras y ya está.
        """
        fila = QHBoxLayout()
        fila.setContentsMargins(0, 0, 0, 0)
        fila.setSpacing(12)
        fila.addWidget(etiqueta, alignment=Qt.AlignmentFlag.AlignVCenter)
        fila.addStretch()
        valor.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        fila.addWidget(valor)
        return fila

    @staticmethod
    def _separador() -> QFrame:
        """Filete de 1 px. El alto se fija aquí: un QFrame sin forma no tiene tamaño propio
        y la hoja de estilos sola lo dejaría en nada."""
        linea = QFrame()
        linea.setObjectName("separador")
        linea.setFixedHeight(1)
        return linea

    @staticmethod
    def _etiqueta_pequena(texto: str) -> QLabel:
        """Etiqueta de un bloque de métrica: pequeña, gris y en mayúsculas.

        Las mayúsculas se ponen aquí y no en la hoja de estilos porque Qt no entiende
        `text-transform`.
        """
        etiqueta = QLabel(texto.upper())
        etiqueta.setObjectName("etiquetaTotal")
        return etiqueta

    # ------------------------------------------------------------------ acciones

    def repintar(self) -> None:
        """Vuelve a dibujar con los colores del tema actual lo que la hoja no alcanza.

        Son dos cosas: los colores de las celdas de acción, que se fijan al crearlas, y el
        icono del campo de escaneo, que es un mapa de píxeles ya pintado.
        """
        self._icono_campo.setIcon(
            iconos.icono("escanear", 24, estilos.actual.texto_apagado)
        )
        self._icono_vacio.setPixmap(
            iconos.pixmap("escanear", 44, estilos.actual.texto_apagado)
        )
        # El estilo del total lleva su propio color, así que hay que rehacerlo: si no, el
        # verde del tema anterior se quedaría puesto.
        self._tamano_total = None
        # Con la letra agrandada, el código de barras cede su columna al nombre del producto.
        # Medido a 1600 px de ancho: la tabla tiene 638 px útiles y, con letra normal, el
        # nombre ya solo se lleva 199; al agrandar crecen precio, cantidad y subtotal, y el
        # nombre quedaba en 137 px, con **todos** los productos cortados en "Bebida ...". El
        # código es lo que menos lee el cajero —ya lo escaneó— y sigue a mano en la ayuda del
        # botón de copiar y en la consulta de precio. La celda no se borra, solo se oculta:
        # las acciones de cada línea la usan para saber de qué producto se trata.
        self.tabla.setColumnHidden(COL_CODIGO, estilos.escala > 1.0)
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
            producto = self._sesion.consultar_por_codigo(codigo)
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
        self._destellar(producto.codigo_barras)
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

        resultados = self._sesion.buscar_por_nombre(dialogo.texto)
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
        self._destellar(codigo)
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
            self._empezar_venta_nueva()
            self._refrescar()
            self._avisar("Venta cancelada.", exito=True)
        self.enfocar_escaneo()

    def cobrar(self) -> None:
        """Cierra la venta previa confirmación."""
        # Red de seguridad: el arranque ya no deja entrar sin usuario, pero una venta sin
        # autor rompería el cierre por empleado que pidió el cliente, así que tampoco se cobra
        # sin uno. El servicio sigue aceptando `usuario=None` porque la regla "aquí siempre
        # hay sesión" es de la aplicación, no del negocio.
        if self.usuario is None:
            self._avisar("Inicie sesión antes de cobrar (F10).", exito=False)
            self.enfocar_escaneo()
            return
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
            f"Pago: {NOMBRE_MEDIO[self._medio]}\n"
            f"{self._carrito.cantidad_articulos} artículos en {len(self._carrito.lineas)} "
            f"líneas.\n\n¿Confirma la venta?",
            texto_si="Sí, cobrar",
        ):
            self.enfocar_escaneo()
            return

        # Un identificador por intento de cobro, no por pulsación: si el primer intento
        # falla por la red y el cajero vuelve a pulsar, el servidor reconoce que es el mismo
        # cobro y devuelve la venta original en lugar de cobrar dos veces (D-024). Solo se
        # renueva cuando una venta se cierra de verdad.
        if self._intento_cobro is None:
            self._intento_cobro = str(uuid.uuid4())

        try:
            venta = self._sesion.cerrar_venta(
                self._carrito, self.usuario, self._intento_cobro, medio_pago=self._medio
            )
        except ErrorDominio as error:
            dialogos.mostrar_error(self, str(error))
            self.enfocar_escaneo()
            return

        self._intento_cobro = None
        self._carrito.vaciar()
        self._empezar_venta_nueva()
        self._refrescar()
        # El medio del aviso es el de la venta que devolvió la base, no el que está marcado:
        # en un reintento el servidor devuelve la venta original, con el medio con que se
        # guardó, y es eso lo que el cajero tiene que ver.
        medio = f" · {NOMBRE_MEDIO[venta.medio_pago]}" if venta.medio_pago else ""
        self._avisar(
            f"Venta N° {venta.folio} registrada por {formatear_clp(venta.total_clp)}{medio}.",
            exito=True,
        )
        self.venta_registrada.emit()
        self.enfocar_escaneo()

    # ------------------------------------------------------------------ presentación

    def _refrescar(self) -> None:
        """Vuelve a dibujar la tabla y los totales a partir del carrito."""
        # Un destello en curso apunta a un número de fila, que tras redibujar puede ser de
        # otro producto. Se corta; quien acaba de agregar algo lo vuelve a encender.
        self._anim_destello.stop()
        self._intensidad_destello = 0.0
        self._fila_destello = -1
        self.tabla.setRowCount(len(self._carrito.lineas))
        hay_descuento_de_linea = any(linea.tiene_descuento for linea in self._carrito.lineas)
        # La columna de descuentos solo aparece cuando hay alguno: una columna vacía en cada
        # venta normal sería ruido permanente por un caso ocasional.
        self.tabla.setColumnHidden(COL_DESCUENTO, not hay_descuento_de_linea)

        tope = servicio_venta.CANTIDAD_MAX_POR_LINEA
        for fila, linea in enumerate(self._carrito.lineas):
            # El código es referencia y no sigue al tamaño de letra: si creciera, le quitaría
            # ancho al nombre, que es lo que el cajero necesita leer.
            self._celda(fila, COL_CODIGO, linea.codigo_barras, fija=True)
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

        hay_algo = not self._carrito.esta_vacio
        self._pila_carrito.setCurrentIndex(0 if not hay_algo else 1)
        self.tarjeta_detalle.setVisible(hay_algo)
        self.etiqueta_articulos.setText(
            "Carrito vacío"
            if self._carrito.esta_vacio
            else f"{self._carrito.cantidad_articulos} artículos"
        )
        self.valor_subtotal.setText(formatear_clp(self._carrito.subtotal_clp))
        self.valor_total.setText(formatear_clp(self._carrito.total_clp))
        self._ajustar_total()

        descuento = self._carrito.descuento_clp
        self.fila_descuento.setVisible(descuento > 0)
        self.valor_descuento.setText(f"-{formatear_clp(descuento)}")
        # Cuando el descuento viene de varios sitios, el panel dice de dónde: si no, un
        # total más bajo de lo esperado no tendría explicación a la vista.
        self.etiqueta_descuento.setText(self._titulo_descuento(hay_descuento_de_linea).upper())

        hay_productos = not self._carrito.esta_vacio
        self.boton_cobrar.setEnabled(hay_productos)
        self.boton_quitar.setEnabled(hay_productos)
        self.boton_descuento.setEnabled(hay_productos)
        self.boton_vaciar.setEnabled(hay_productos)

    def _ajustar_total(self) -> None:
        """Pinta el total al mayor tamaño que quepa dentro de la tarjeta.

        Es la cifra que el cajero lee de lejos y la que el cliente busca en la pantalla, así
        que se le da todo el tamaño que admite la tarjeta. El tope son 62 px, que es lo que
        aguanta un total de seis cifras; una venta de siete baja un escalón en lugar de
        salirse del borde, que es justo lo que no puede pasar delante de un cliente.

        El tamaño se aplica sobre la etiqueta y no desde la hoja de estilos porque depende
        del texto, no del tema. Solo se repinta cuando cambia de escalón: una venta corriente
        no lo toca en ningún escaneo.

        Tampoco sigue al ajuste de tamaño de letra de la configuración: ya es el mayor que
        cabe en la tarjeta, y agrandarlo más solo haría que un total de seis cifras se saliera
        del borde.
        """
        texto = self.valor_total.text()
        # La fuente de medir se arma entera aquí, con el peso y el interletrado que se van a
        # aplicar. Partir de la que tenga puesta la etiqueta haría que la medida dependiera
        # del tamaño anterior, y la elección saldría distinta según el orden de los totales.
        fuente = QFont(self.valor_total.font())
        fuente.setWeight(QFont.Weight.Bold)

        elegido = _TAMANOS_TOTAL[-1]
        for tamano in _TAMANOS_TOTAL:
            fuente.setPixelSize(tamano)
            fuente.setLetterSpacing(
                QFont.SpacingType.AbsoluteSpacing, tamano * _INTERLETRADO_TOTAL
            )
            if QFontMetrics(fuente).horizontalAdvance(texto) <= _ANCHO_TOTAL:
                elegido = tamano
                break

        if elegido == self._tamano_total:
            return
        self._tamano_total = elegido
        self.valor_total.setStyleSheet(
            f"font-size: {elegido}px;"
            f" font-weight: 700;"
            f" letter-spacing: {elegido * _INTERLETRADO_TOTAL:.2f}px;"
            f" color: {estilos.actual.exito};"
        )

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
            celda.setForeground(QBrush(QColor(paleta.texto_suave)))
            fuente = celda.font()
            fuente.setBold(True)
            # Son botones, no datos: no siguen al tamaño de letra (ver `estilos.ESCALA_TEXTO`).
            fuente.setPixelSize(estilos.LETRA_BASE)
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
        fija: bool = False,
    ) -> None:
        celda = QTableWidgetItem(texto)
        if derecha:
            celda.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        elif centrada:
            celda.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        if fuerte or fija:
            fuente = celda.font()
            if fuerte:
                fuente.setBold(True)
            if fija:
                fuente.setPixelSize(estilos.LETRA_BASE)
            celda.setFont(fuente)
        self.tabla.setItem(fila, columna, celda)

    def _seleccionar(self, codigo_barras: str) -> None:
        for fila in range(self.tabla.rowCount()):
            if self.tabla.item(fila, COL_CODIGO).text() == codigo_barras:
                self.tabla.selectRow(fila)
                self.tabla.scrollToItem(self.tabla.item(fila, COL_CODIGO))
                return

    def _destellar(self, codigo_barras: str) -> None:
        """Hace destellar la línea de ese producto. Solo al agregar o sumar unidades: quitar
        no destella, porque el verde dice «entró» y ahí no entró nada."""
        if not movimiento.activo():
            return
        self._pintar_destello(0.0)
        for fila in range(self.tabla.rowCount()):
            item = self.tabla.item(fila, COL_CODIGO)
            if item is not None and item.text() == codigo_barras:
                self._fila_destello = fila
                self._anim_destello.stop()
                self._anim_destello.start()
                # La animación da su primer valor en el siguiente fotograma; el verde tiene
                # que estar ya en el repintado que sigue al escaneo, no 16 ms después.
                self._pintar_destello(1.0)
                return

    def intensidad_destello(self, fila: int) -> float:
        """Cuánto verde lleva la fila, de 0 a 1. Lo consulta el delegado al pintar."""
        return self._intensidad_destello if fila == self._fila_destello else 0.0

    def _pintar_destello(self, valor) -> None:
        self._intensidad_destello = float(valor)
        if self._intensidad_destello <= 0:
            fila, self._fila_destello = self._fila_destello, -1
        else:
            fila = self._fila_destello
        if 0 <= fila < self.tabla.rowCount():
            # Solo se repinta la franja de esa fila, no la tabla entera: el destello corre
            # a la vez que el siguiente escaneo, y ahí cada milisegundo cuenta (D-022).
            modelo = self.tabla.model()
            rect = self.tabla.visualRect(modelo.index(fila, 0))
            rect.setLeft(0)
            rect.setRight(self.tabla.viewport().width())
            self.tabla.viewport().update(rect)

    def _avisar(self, texto: str, exito: bool) -> None:
        """Muestra un mensaje breve en la columna de totales. Ver `_aviso`."""
        sonido.exito() if exito else sonido.error()
        self.mensaje.setText(texto)
        self.mensaje.setObjectName("mensajeExito" if exito else "mensajeError")
        # Qt no reevalúa la hoja de estilos al cambiar el objectName; hay que forzarlo.
        self.mensaje.style().unpolish(self.mensaje)
        self.mensaje.style().polish(self.mensaje)
        self._fundido_mensaje.mostrar()
        # La cuenta atrás se reinicia, no se acumula. Antes cada aviso programaba un
        # temporizador nuevo sin cancelar el anterior, así que escanear un producto a los
        # 4,8 s del anterior hacía que el temporizador viejo escondiera el mensaje nuevo a
        # los 200 ms. Parecía un fallo de pintado y era un temporizador de más.
        self._temporizador_mensaje.start(_MENSAJE_MS)

    # ------------------------------------------------------------------ consultas

    @property
    def carrito(self) -> Carrito:
        return self._carrito
