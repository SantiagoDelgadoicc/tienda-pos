"""Ventana principal: barra superior, pantallas y atajos de teclado."""

from __future__ import annotations


from PySide6.QtCore import QDateTime, Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from ..config import NOMBRE_COMERCIAL, VERSION
from ..domain.models import Usuario
from ..red.sesion import Sesion
from ..services import preferencias as servicio_preferencias
from ..services.preferencias import Preferencias
from ..utils import sonido
from . import dialogos, estilos
from .configuracion_dialog import DialogoConfiguracion
from .consulta_view import ConsultaView
from .login_dialog import DialogoLogin
from .productos_view import ProductosView
from .reportes_view import ReportesView
from .venta_view import VentaView

_AYUDA = """<b>Atajos de teclado</b><br><br>
<table cellpadding="4">
<tr><td><b>Enter</b></td><td>Agregar el producto escaneado al carrito</td></tr>
<tr><td><b>F2</b></td><td>Consulta de precio a pantalla completa</td></tr>
<tr><td><b>F3</b></td><td>Buscar un producto por su nombre</td></tr>
<tr><td><b>F4</b></td><td>Aplicar un descuento a la venta</td></tr>
<tr><td><b>F5</b></td><td>Quitar una unidad de la línea seleccionada</td></tr>
<tr><td><b>↑ ↓</b></td><td>Moverse entre las líneas del carrito</td></tr>
<tr><td><b>→</b> o <b>+</b></td><td>Agregar una unidad a la línea seleccionada</td></tr>
<tr><td><b>←</b> o <b>−</b></td><td>Quitar una unidad de la línea seleccionada</td></tr>
<tr><td><b>Ctrl+C</b></td><td>Copiar el código de la línea seleccionada</td></tr>
<tr><td><b>F6</b></td><td>Cancelar la venta en curso</td></tr>
<tr><td><b>F12</b></td><td>Cobrar y registrar la venta</td></tr>
<tr><td><b>F7</b></td><td>Administrar productos <i>(administrador)</i></td></tr>
<tr><td><b>F8</b></td><td>Ventas del día <i>(administrador)</i></td></tr>
<tr><td><b>F9</b></td><td>Configuración</td></tr>
<tr><td><b>F10</b></td><td>Cambiar de usuario</td></tr>
<tr><td><b>Esc</b></td><td>Volver a la pantalla de venta</td></tr>
</table>
<br>Las flechas y las teclas + y − actúan sobre el carrito cuando el campo de escaneo
está vacío; si hay un código a medio escribir, sirven para corregirlo.
<br><br>El lector de códigos de barras funciona como un teclado: no hace falta configurarlo.
"""


class VentanaPrincipal(QMainWindow):
    """Contenedor de las pantallas del sistema."""

    def __init__(self, sesion: Sesion) -> None:
        super().__init__()
        self._sesion = sesion
        self.usuario: Usuario | None = None
        # Las preferencias se leen antes de construir nada: el tema y la barra de atajos
        # cambian cómo se monta la ventana.
        self.preferencias = servicio_preferencias.cargar()

        self.setWindowTitle(f"{NOMBRE_COMERCIAL} {VERSION}")
        self.resize(1180, 760)
        self.setMinimumSize(940, 620)

        self._construir()
        self._registrar_atajos()
        self.aplicar_preferencias(self.preferencias)
        self.mostrar_venta()

    # ------------------------------------------------------------------ construcción

    def _construir(self) -> None:
        central = QWidget()
        columna = QVBoxLayout(central)
        columna.setContentsMargins(0, 0, 0, 0)
        columna.setSpacing(0)
        columna.addWidget(self._barra_superior())

        self.pantallas = QStackedWidget()
        self.vista_venta = VentaView(self._sesion)
        self.vista_consulta = ConsultaView(self._sesion)
        self.vista_productos = ProductosView(self._sesion)
        self.vista_reportes = ReportesView(self._sesion)
        for vista in (
            self.vista_venta,
            self.vista_consulta,
            self.vista_productos,
            self.vista_reportes,
        ):
            self.pantallas.addWidget(vista)
        columna.addWidget(self.pantallas, stretch=1)

        self.vista_venta.consulta_solicitada.connect(self.mostrar_consulta)
        self.vista_consulta.salir_solicitado.connect(self.mostrar_venta)
        self.vista_productos.salir_solicitado.connect(self.mostrar_venta)
        self.vista_reportes.salir_solicitado.connect(self.mostrar_venta)

        self.setCentralWidget(central)

        barra = QStatusBar()
        barra.showMessage(
            "F2 consulta  ·  F3 buscar  ·  F4 descuento  ·  F5 quitar  ·  F6 cancelar  ·  "
            "F7 productos  ·  F8 ventas del día  ·  F9 configuración  ·  F10 cambiar usuario"
            "  ·  F12 cobrar  ·  F1 ayuda"
        )
        self.setStatusBar(barra)

    def _barra_superior(self) -> QWidget:
        barra = QFrame()
        barra.setObjectName("barraSuperior")
        barra.setFixedHeight(62)

        fila = QHBoxLayout(barra)
        fila.setContentsMargins(22, 0, 22, 0)

        marca = QLabel(NOMBRE_COMERCIAL)
        marca.setObjectName("marca")
        fila.addWidget(marca)
        fila.addStretch()

        self.etiqueta_sesion = QLabel()
        self.etiqueta_sesion.setObjectName("datosSesion")
        self.etiqueta_sesion.setAlignment(Qt.AlignmentFlag.AlignRight)
        fila.addWidget(self.etiqueta_sesion)

        self.boton_configuracion = QPushButton("⚙")
        self.boton_configuracion.setObjectName("botonConfiguracion")
        self.boton_configuracion.setToolTip("Configuración   (F9)")
        self.boton_configuracion.setCursor(Qt.CursorShape.PointingHandCursor)
        self.boton_configuracion.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.boton_configuracion.clicked.connect(self.abrir_configuracion)
        fila.addSpacing(14)
        fila.addWidget(self.boton_configuracion)

        # El reloj no es decorativo: en una caja se necesita saber la hora sin soltar nada.
        self._reloj = QTimer(self)
        self._reloj.timeout.connect(self._actualizar_sesion)
        self._reloj.start(1000)
        self._actualizar_sesion()
        return barra

    def _registrar_atajos(self) -> None:
        """Los atajos viven en la ventana para que funcionen mire donde mire el foco."""
        self._atajo(QKeySequence(Qt.Key.Key_F1), self.mostrar_ayuda)
        self._atajo(QKeySequence(Qt.Key.Key_F2), self.alternar_consulta)
        self._atajo(QKeySequence(Qt.Key.Key_F3), self._buscar_por_nombre)
        self._atajo(QKeySequence(Qt.Key.Key_F4), self._descuento)
        self._atajo(QKeySequence(Qt.Key.Key_F5), self._quitar_linea)
        self._atajo(QKeySequence(Qt.Key.Key_F6), self._cancelar_venta)
        self._atajo(QKeySequence(Qt.Key.Key_F7), self.mostrar_productos)
        self._atajo(QKeySequence(Qt.Key.Key_F8), self.mostrar_reportes)
        self._atajo(QKeySequence(Qt.Key.Key_F9), self.abrir_configuracion)
        self._atajo(QKeySequence(Qt.Key.Key_F10), self.cambiar_usuario)
        self._atajo(QKeySequence(Qt.Key.Key_F12), self._cobrar)
        self._atajo(QKeySequence(Qt.Key.Key_Escape), self.mostrar_venta)

    def _atajo(self, secuencia: QKeySequence, destino) -> None:
        atajo = QShortcut(secuencia, self)
        atajo.setContext(Qt.ShortcutContext.ApplicationShortcut)
        atajo.activated.connect(destino)

    # ------------------------------------------------------------------ navegación

    def mostrar_venta(self) -> None:
        self.pantallas.setCurrentWidget(self.vista_venta)
        self.vista_venta.enfocar_escaneo()

    def mostrar_consulta(self) -> None:
        self.vista_consulta.limpiar()
        self.pantallas.setCurrentWidget(self.vista_consulta)
        self.vista_consulta.enfocar_escaneo()

    def alternar_consulta(self) -> None:
        """F2 entra a la consulta y F2 de nuevo vuelve: una sola tecla para ir y volver."""
        if self.pantallas.currentWidget() is self.vista_consulta:
            self.mostrar_venta()
        else:
            self.mostrar_consulta()

    def mostrar_productos(self) -> None:
        """Catálogo. Si quien opera no es administrador, se le pide el PIN de uno."""
        administrador = self._asegurar_admin("administrar los productos")
        if administrador is None:
            return
        self.vista_productos.usuario = administrador
        self.vista_productos.recargar()
        self.pantallas.setCurrentWidget(self.vista_productos)

    def mostrar_reportes(self) -> None:
        if self._asegurar_admin("ver las ventas del día") is None:
            return
        self.vista_reportes.recargar()
        self.pantallas.setCurrentWidget(self.vista_reportes)

    def _asegurar_admin(self, accion: str):
        """Devuelve un usuario administrador, pidiendo su PIN si hace falta.

        El cajero que está operando la caja no cambia: se autoriza la acción puntual y la
        sesión sigue siendo suya. Es como funcionan los puntos de venta reales cuando el
        encargado se acerca a autorizar algo.
        """
        if self.usuario is not None and self.usuario.es_admin:
            return self.usuario

        administrador = DialogoLogin.pedir(
            self._sesion,
            self,
            solo_admin=True,
            mensaje=f"Se necesita autorización de un administrador para {accion}.",
        )
        if administrador is None:
            self._devolver_foco()
        return administrador

    def cambiar_usuario(self) -> None:
        """Cierra la sesión actual y pide una nueva.

        Si hay una venta a medio armar se avisa antes: cambiar de cajero con el carrito
        lleno es la forma más fácil de cobrarle a alguien lo de otro.
        """
        if not self.vista_venta.carrito.esta_vacio and not dialogos.confirmar(
            self,
            "Cambiar de usuario",
            "Hay una venta sin cobrar. Si cambia de usuario se perderá.\n\n¿Desea continuar?",
            texto_si="Sí, cambiar",
        ):
            self._devolver_foco()
            return

        usuario = DialogoLogin.pedir(self._sesion, self)
        if usuario is None:
            self._devolver_foco()
            return

        self.vista_venta.carrito.vaciar()
        self.vista_venta._refrescar()
        self.establecer_usuario(usuario)
        self.mostrar_venta()

    def mostrar_ayuda(self) -> None:
        dialogos.mostrar_info(self, _AYUDA, "Ayuda")
        self._devolver_foco()

    # ------------------------------------------------------------------ acciones

    def _en_venta(self) -> bool:
        return self.pantallas.currentWidget() is self.vista_venta

    def _cobrar(self) -> None:
        if self._en_venta():
            self.vista_venta.cobrar()

    def _descuento(self) -> None:
        if self._en_venta():
            self.vista_venta.aplicar_descuento()

    def _quitar_linea(self) -> None:
        if self._en_venta():
            self.vista_venta.quitar_linea_seleccionada()

    def _cancelar_venta(self) -> None:
        if self._en_venta():
            self.vista_venta.cancelar_venta()

    def _buscar_por_nombre(self) -> None:
        if self._en_venta():
            self.vista_venta.buscar_por_nombre()

    def _devolver_foco(self) -> None:
        pantalla = self.pantallas.currentWidget()
        if hasattr(pantalla, "enfocar_escaneo"):
            pantalla.enfocar_escaneo()

    # ------------------------------------------------------------------ configuración

    def abrir_configuracion(self) -> None:
        """Abre la rueda de configuración y aplica lo que se elija."""
        elegidas = DialogoConfiguracion.abrir(
            self.preferencias, self, al_previsualizar_tema=self.aplicar_tema
        )
        if elegidas is not None:
            self.aplicar_preferencias(elegidas)
        self._devolver_foco()

    def aplicar_preferencias(self, preferencias: Preferencias) -> None:
        """Deja la aplicación en el estado que describen las preferencias."""
        self.preferencias = preferencias
        self.aplicar_tema(preferencias.tema)
        sonido.habilitado = preferencias.sonido
        self.vista_venta.preferencias = preferencias
        if self.statusBar() is not None:
            self.statusBar().setVisible(preferencias.mostrar_atajos)

    def aplicar_tema(self, tema: str) -> None:
        """Repinta toda la aplicación con el tema indicado, sin reiniciar.

        Se aplica sobre la QApplication y no sobre esta ventana porque los diálogos son
        ventanas aparte: si el estilo viviera aquí, seguirían saliendo con el tema anterior.
        """
        app = QApplication.instance()
        if app is not None:
            estilos.aplicar(app, tema)
        # La hoja de estilos no alcanza a los colores que las pantallas fijan celda a celda.
        self.vista_venta.repintar()

    # ------------------------------------------------------------------ sesión

    def establecer_usuario(self, usuario: Usuario | None) -> None:
        self.usuario = usuario
        self.vista_venta.usuario = usuario
        self._actualizar_sesion()

    def _actualizar_sesion(self) -> None:
        ahora = QDateTime.currentDateTime().toString("dd/MM/yyyy HH:mm:ss")
        if self.usuario is None:
            quien = "Sesión no iniciada"
        else:
            rol = "Administrador" if self.usuario.es_admin else "Cajero"
            # Los usuarios de ejemplo se llaman igual que su rol; repetirlo ("Administrador
            # · Administrador") solo hace ruido.
            quien = self.usuario.nombre if self.usuario.nombre == rol else f"{self.usuario.nombre} · {rol}"
        self.etiqueta_sesion.setText(f"{quien}     {ahora}")
