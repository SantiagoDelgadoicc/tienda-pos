"""Ventana principal: barra superior, pantallas y atajos de teclado."""

from __future__ import annotations

import sqlite3

from PySide6.QtCore import QDateTime, Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from ..config import NOMBRE_COMERCIAL, VERSION
from ..domain.models import Usuario
from . import dialogos
from .consulta_view import ConsultaView
from .venta_view import VentaView

_AYUDA = """<b>Atajos de teclado</b><br><br>
<table cellpadding="4">
<tr><td><b>Enter</b></td><td>Agregar el producto escaneado al carrito</td></tr>
<tr><td><b>F2</b></td><td>Consulta de precio a pantalla completa</td></tr>
<tr><td><b>F3</b></td><td>Buscar un producto por su nombre</td></tr>
<tr><td><b>F5</b></td><td>Quitar una unidad de la línea seleccionada</td></tr>
<tr><td><b>F6</b></td><td>Cancelar la venta en curso</td></tr>
<tr><td><b>F12</b></td><td>Cobrar y registrar la venta</td></tr>
<tr><td><b>Esc</b></td><td>Volver a la pantalla de venta</td></tr>
</table>
<br>El lector de códigos de barras funciona como un teclado: no hace falta configurarlo.
"""


class VentanaPrincipal(QMainWindow):
    """Contenedor de las pantallas del sistema."""

    def __init__(self, conexion: sqlite3.Connection) -> None:
        super().__init__()
        self._conexion = conexion
        self.usuario: Usuario | None = None

        self.setWindowTitle(f"{NOMBRE_COMERCIAL} {VERSION}")
        self.resize(1180, 760)
        self.setMinimumSize(940, 620)

        self._construir()
        self._registrar_atajos()
        self.mostrar_venta()

    # ------------------------------------------------------------------ construcción

    def _construir(self) -> None:
        central = QWidget()
        columna = QVBoxLayout(central)
        columna.setContentsMargins(0, 0, 0, 0)
        columna.setSpacing(0)
        columna.addWidget(self._barra_superior())

        self.pantallas = QStackedWidget()
        self.vista_venta = VentaView(self._conexion)
        self.vista_consulta = ConsultaView(self._conexion)
        self.pantallas.addWidget(self.vista_venta)
        self.pantallas.addWidget(self.vista_consulta)
        columna.addWidget(self.pantallas, stretch=1)

        self.vista_venta.consulta_solicitada.connect(self.mostrar_consulta)
        self.vista_consulta.salir_solicitado.connect(self.mostrar_venta)

        self.setCentralWidget(central)

        barra = QStatusBar()
        barra.showMessage(
            "F2 consulta de precio  ·  F3 buscar por nombre  ·  F5 quitar  ·  "
            "F6 cancelar  ·  F12 cobrar  ·  F1 ayuda"
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
        self._atajo(QKeySequence(Qt.Key.Key_F5), self._quitar_linea)
        self._atajo(QKeySequence(Qt.Key.Key_F6), self._cancelar_venta)
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

    def mostrar_ayuda(self) -> None:
        dialogos.mostrar_info(self, _AYUDA, "Ayuda")
        self._devolver_foco()

    # ------------------------------------------------------------------ acciones

    def _en_venta(self) -> bool:
        return self.pantallas.currentWidget() is self.vista_venta

    def _cobrar(self) -> None:
        if self._en_venta():
            self.vista_venta.cobrar()

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
            quien = f"{self.usuario.nombre} · {rol}"
        self.etiqueta_sesion.setText(f"{quien}     {ahora}")
