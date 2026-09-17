"""Pantalla de consulta de precio.

Esta es, literalmente, lo único que el cliente pidió: escanear un producto y ver su precio.
Por eso es la pantalla más grande y más limpia del programa. Un solo dato, enorme, legible
desde el otro lado del mostrador.

Se limpia sola pasados unos segundos, para que el precio del cliente anterior no siga en
pantalla cuando llegue el siguiente.
"""

from __future__ import annotations


from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..domain.errors import ErrorDominio, ProductoNoEncontrado
from ..red.sesion import Sesion
from ..utils import sonido
from ..utils.money import formatear_clp

#: Tiempo que un precio permanece en pantalla antes de volver al estado de espera.
_LIMPIEZA_MS = 15000


class ConsultaView(QWidget):
    """Verificador de precios a pantalla completa."""

    #: Se emite cuando el usuario quiere volver a la pantalla de venta.
    salir_solicitado = Signal()

    def __init__(self, sesion: Sesion, padre: QWidget | None = None) -> None:
        super().__init__(padre)
        self._sesion = sesion
        self._temporizador = QTimer(self)
        self._temporizador.setSingleShot(True)
        self._temporizador.timeout.connect(self.limpiar)

        self._construir()
        self.limpiar()

    def _construir(self) -> None:
        columna = QVBoxLayout(self)
        columna.setContentsMargins(40, 28, 40, 32)
        columna.setSpacing(18)

        titulo = QLabel("Consulta de precio")
        titulo.setObjectName("tituloPantalla")
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        columna.addWidget(titulo)

        # La instrucción va en una etiqueta propia y no en el texto de ayuda del campo por
        # dos motivos. Uno práctico: Qt oculta el texto de ayuda cuando el campo está
        # centrado y tiene el foco, que es exactamente esta situación. Y otro de diseño:
        # así la instrucción sigue visible mientras se escribe, que es cuando hace falta.
        instruccion = QLabel("Escanee el producto o escriba su código y pulse Enter")
        instruccion.setObjectName("subtitulo")
        instruccion.setAlignment(Qt.AlignmentFlag.AlignCenter)
        columna.addWidget(instruccion)

        self.campo_codigo = QLineEdit()
        self.campo_codigo.setObjectName("campoEscaneo")
        self.campo_codigo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Con alignment en el layout, el campo tomaría su ancho natural, que es muy estrecho.
        self.campo_codigo.setMinimumWidth(560)
        self.campo_codigo.setMaximumWidth(620)
        self.campo_codigo.returnPressed.connect(self._consultar)
        columna.addWidget(self.campo_codigo, alignment=Qt.AlignmentFlag.AlignHCenter)

        columna.addWidget(self._tarjeta_resultado(), stretch=1)

        boton_volver = QPushButton("Volver a la venta   (Esc)")
        boton_volver.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        boton_volver.clicked.connect(self.salir_solicitado.emit)
        boton_volver.setMaximumWidth(280)
        columna.addWidget(boton_volver, alignment=Qt.AlignmentFlag.AlignHCenter)

    def _tarjeta_resultado(self) -> QWidget:
        tarjeta = QFrame()
        tarjeta.setObjectName("tarjeta")

        columna = QVBoxLayout(tarjeta)
        columna.setContentsMargins(40, 30, 40, 30)
        columna.setSpacing(10)
        columna.addStretch()

        self.etiqueta_espera = QLabel("Esperando un producto…")
        self.etiqueta_espera.setObjectName("consultaVacio")
        self.etiqueta_espera.setAlignment(Qt.AlignmentFlag.AlignCenter)
        columna.addWidget(self.etiqueta_espera)

        self.etiqueta_nombre = QLabel()
        self.etiqueta_nombre.setObjectName("consultaNombre")
        self.etiqueta_nombre.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.etiqueta_nombre.setWordWrap(True)
        columna.addWidget(self.etiqueta_nombre)

        self.etiqueta_precio = QLabel()
        self.etiqueta_precio.setObjectName("consultaPrecio")
        self.etiqueta_precio.setAlignment(Qt.AlignmentFlag.AlignCenter)
        columna.addWidget(self.etiqueta_precio)

        self.etiqueta_detalle = QLabel()
        self.etiqueta_detalle.setObjectName("consultaDetalle")
        self.etiqueta_detalle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        columna.addWidget(self.etiqueta_detalle)

        columna.addStretch()
        return tarjeta

    # ------------------------------------------------------------------ acciones

    def enfocar_escaneo(self) -> None:
        self.campo_codigo.setFocus()
        self.campo_codigo.selectAll()

    def _consultar(self) -> None:
        codigo = self.campo_codigo.text().strip()
        if not codigo:
            return
        self.campo_codigo.clear()
        self.consultar(codigo)

    def consultar(self, codigo: str) -> None:
        """Busca el código y muestra el resultado. Separado de la lectura del campo para
        poder invocarlo desde las pruebas y desde la herramienta de capturas."""
        try:
            producto = self._sesion.consultar_por_codigo(codigo)
        except ProductoNoEncontrado:
            self._mostrar_no_encontrado(codigo)
            return
        except ErrorDominio as error:
            self._mostrar_aviso(str(error))
            return

        sonido.exito()
        self.etiqueta_espera.hide()
        self.etiqueta_nombre.setText(producto.nombre)
        self.etiqueta_nombre.show()
        self.etiqueta_precio.setStyleSheet("")
        self.etiqueta_precio.setText(formatear_clp(producto.precio_clp))
        self.etiqueta_precio.show()

        disponibilidad = (
            f"Quedan {producto.stock} unidades" if producto.stock > 0 else "Sin stock"
        )
        self.etiqueta_detalle.setText(f"{producto.codigo_barras}  ·  {disponibilidad}")
        self.etiqueta_detalle.show()

        self._temporizador.start(_LIMPIEZA_MS)
        self.enfocar_escaneo()

    def _mostrar_no_encontrado(self, codigo: str) -> None:
        sonido.error()
        self.etiqueta_espera.hide()
        self.etiqueta_nombre.setText("Producto no encontrado")
        self.etiqueta_nombre.show()
        self.etiqueta_precio.setText(codigo)
        # El código pasa a rojo y a un tamaño menor: sigue siendo legible para dictarlo,
        # pero no se confunde con un precio.
        self.etiqueta_precio.setStyleSheet("font-size: 54px; color: #B91C1C;")
        self.etiqueta_precio.show()
        self.etiqueta_detalle.setText("Este código no está en el catálogo.")
        self.etiqueta_detalle.show()
        self._temporizador.start(_LIMPIEZA_MS)
        self.enfocar_escaneo()

    def _mostrar_aviso(self, mensaje: str) -> None:
        sonido.error()
        self.etiqueta_espera.setText(mensaje)
        self.etiqueta_espera.show()
        self.etiqueta_nombre.hide()
        self.etiqueta_precio.hide()
        self.etiqueta_detalle.hide()
        self._temporizador.start(_LIMPIEZA_MS)
        self.enfocar_escaneo()

    def limpiar(self) -> None:
        """Vuelve al estado de espera."""
        self._temporizador.stop()
        self.etiqueta_espera.setText("Esperando un producto…")
        self.etiqueta_espera.show()
        self.etiqueta_nombre.hide()
        self.etiqueta_precio.hide()
        self.etiqueta_precio.setStyleSheet("")
        self.etiqueta_detalle.hide()
