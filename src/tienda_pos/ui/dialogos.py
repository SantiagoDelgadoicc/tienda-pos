"""Diálogos comunes.

Se centralizan aquí para que todos los mensajes del sistema se vean y se comporten igual, y
para que ninguna pantalla invente su propia forma de dar una mala noticia.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..config import NOMBRE_COMERCIAL


def mostrar_error(padre: QWidget | None, mensaje: str, titulo: str = "No se pudo continuar") -> None:
    """Error previsible: el usuario hizo algo que no corresponde."""
    caja = QMessageBox(padre)
    caja.setIcon(QMessageBox.Icon.Warning)
    caja.setWindowTitle(titulo)
    caja.setText(mensaje)
    caja.setStandardButtons(QMessageBox.StandardButton.Ok)
    caja.button(QMessageBox.StandardButton.Ok).setText("Entendido")
    caja.exec()


def mostrar_info(padre: QWidget | None, mensaje: str, titulo: str = NOMBRE_COMERCIAL) -> None:
    caja = QMessageBox(padre)
    caja.setIcon(QMessageBox.Icon.Information)
    caja.setWindowTitle(titulo)
    caja.setText(mensaje)
    caja.setStandardButtons(QMessageBox.StandardButton.Ok)
    caja.button(QMessageBox.StandardButton.Ok).setText("Aceptar")
    caja.exec()


def confirmar(padre: QWidget | None, titulo: str, mensaje: str, texto_si: str = "Sí") -> bool:
    """Pregunta de sí o no. El botón por defecto es siempre el que no destruye nada."""
    caja = QMessageBox(padre)
    caja.setIcon(QMessageBox.Icon.Question)
    caja.setWindowTitle(titulo)
    caja.setText(mensaje)
    caja.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    caja.button(QMessageBox.StandardButton.Yes).setText(texto_si)
    caja.button(QMessageBox.StandardButton.No).setText("Cancelar")
    caja.setDefaultButton(QMessageBox.StandardButton.No)
    return caja.exec() == QMessageBox.StandardButton.Yes


class DialogoCodigoNoEncontrado(QDialog):
    """Se muestra cuando se escanea un código que no está en el catálogo.

    Es el error más frecuente en la vida real de una caja, así que merece un diálogo propio
    en lugar de un mensaje genérico: muestra el código leído en grande (para poder dictarlo
    o anotarlo), explica qué se hizo con él y ofrece la salida útil, que es buscar el
    producto por su nombre.

    El resultado se consulta con `buscar_por_nombre` después de cerrar.
    """

    def __init__(self, codigo: str, padre: QWidget | None = None) -> None:
        super().__init__(padre)
        self.setWindowTitle("Producto no encontrado")
        self.setMinimumWidth(460)
        self.buscar_por_nombre = False

        disposicion = QVBoxLayout(self)
        disposicion.setContentsMargins(24, 24, 24, 20)
        disposicion.setSpacing(14)

        titulo = QLabel("Este producto no está en el catálogo")
        titulo.setStyleSheet("font-size: 18px; font-weight: 600;")
        disposicion.addWidget(titulo)

        etiqueta_codigo = QLabel(codigo)
        etiqueta_codigo.setObjectName("mensajeError")
        etiqueta_codigo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        etiqueta_codigo.setStyleSheet(
            "font-size: 26px; font-weight: 700; letter-spacing: 2px;"
            " background-color: #FEE2E2; color: #B91C1C;"
            " border-radius: 8px; padding: 14px;"
        )
        etiqueta_codigo.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        disposicion.addWidget(etiqueta_codigo)

        explicacion = QLabel(
            "El código quedó anotado en la lista de pendientes para que el administrador "
            "lo cargue más tarde.\n\nSi el producto existe pero su código está dañado, "
            "búsquelo por su nombre."
        )
        explicacion.setWordWrap(True)
        explicacion.setObjectName("subtitulo")
        disposicion.addWidget(explicacion)

        botones = QHBoxLayout()
        botones.addStretch()

        boton_buscar = QPushButton("Buscar por nombre")
        boton_buscar.clicked.connect(self._buscar)
        botones.addWidget(boton_buscar)

        boton_cerrar = QPushButton("Continuar")
        boton_cerrar.setDefault(True)
        boton_cerrar.clicked.connect(self.accept)
        botones.addWidget(boton_cerrar)

        disposicion.addLayout(botones)

    def _buscar(self) -> None:
        self.buscar_por_nombre = True
        self.accept()


class DialogoTexto(QDialog):
    """Pide un dato corto: un monto, un porcentaje, una cantidad.

    Existe en lugar de QInputDialog porque este hereda la hoja de estilos y permite mostrar
    una explicación bajo el campo, que es donde se avisa de los límites del valor.
    """

    def __init__(
        self,
        titulo: str,
        etiqueta: str,
        padre: QWidget | None = None,
        ayuda: str = "",
        valor_inicial: str = "",
    ) -> None:
        from PySide6.QtWidgets import QLineEdit

        super().__init__(padre)
        self.setWindowTitle(titulo)
        self.setMinimumWidth(380)

        disposicion = QVBoxLayout(self)
        disposicion.setContentsMargins(24, 24, 24, 20)
        disposicion.setSpacing(12)

        disposicion.addWidget(QLabel(etiqueta))

        self.campo = QLineEdit(valor_inicial)
        self.campo.selectAll()
        disposicion.addWidget(self.campo)

        if ayuda:
            nota = QLabel(ayuda)
            nota.setObjectName("subtitulo")
            nota.setWordWrap(True)
            disposicion.addWidget(nota)

        caja = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        caja.button(QDialogButtonBox.StandardButton.Ok).setText("Aceptar")
        caja.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        caja.accepted.connect(self.accept)
        caja.rejected.connect(self.reject)
        disposicion.addWidget(caja)

    @property
    def texto(self) -> str:
        return self.campo.text().strip()
