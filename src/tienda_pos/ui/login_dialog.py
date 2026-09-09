"""Inicio de sesión con PIN.

Se usa en dos situaciones: al arrancar el programa, y cuando un cajero intenta entrar a una
pantalla reservada al administrador. En el segundo caso se pide el PIN del administrador sin
cambiar quién está operando la caja, que es como funcionan los puntos de venta reales.
"""

from __future__ import annotations

import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from ..config import NOMBRE_COMERCIAL, PIN_LONGITUD_MAX
from ..domain.errors import ErrorDominio
from ..domain.models import Rol, Usuario
from ..repositories import usuarios as repo_usuarios
from ..services import auth


class DialogoLogin(QDialog):
    """Pide usuario y PIN, y devuelve el usuario autenticado."""

    def __init__(
        self,
        conexion: sqlite3.Connection,
        padre: QWidget | None = None,
        solo_admin: bool = False,
        mensaje: str = "",
    ) -> None:
        super().__init__(padre)
        self._conexion = conexion
        self._solo_admin = solo_admin
        self._usuario: Usuario | None = None

        self.setWindowTitle("Se requiere administrador" if solo_admin else NOMBRE_COMERCIAL)
        self.setMinimumWidth(400)
        # Sin botón de cerrar en la barra: se sale con Cancelar, para que quede claro que
        # cancelar es una decisión y no un accidente.
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        self._construir(mensaje)
        self._cargar_usuarios()

    def _construir(self, mensaje: str) -> None:
        columna = QVBoxLayout(self)
        columna.setContentsMargins(26, 24, 26, 20)
        columna.setSpacing(10)

        titulo = QLabel(
            "Ingrese el PIN de administrador" if self._solo_admin else "Iniciar sesión"
        )
        titulo.setObjectName("tituloPantalla")
        columna.addWidget(titulo)

        if mensaje:
            explicacion = QLabel(mensaje)
            explicacion.setObjectName("subtitulo")
            explicacion.setWordWrap(True)
            columna.addWidget(explicacion)

        columna.addSpacing(6)
        columna.addWidget(QLabel("Usuario"))
        self.combo_usuario = QComboBox()
        columna.addWidget(self.combo_usuario)

        columna.addWidget(QLabel("PIN"))
        self.campo_pin = QLineEdit()
        self.campo_pin.setEchoMode(QLineEdit.EchoMode.Password)
        self.campo_pin.setMaxLength(PIN_LONGITUD_MAX)
        self.campo_pin.setValidator(QIntValidator(0, 99999999, self))
        self.campo_pin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.campo_pin.returnPressed.connect(self._intentar)
        columna.addWidget(self.campo_pin)

        self.error = QLabel()
        self.error.setObjectName("mensajeError")
        self.error.setWordWrap(True)
        self.error.hide()
        columna.addWidget(self.error)

        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botones.button(QDialogButtonBox.StandardButton.Ok).setText("Entrar")
        botones.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        botones.accepted.connect(self._intentar)
        botones.rejected.connect(self.reject)
        columna.addWidget(botones)

        self.campo_pin.setFocus()

    def _cargar_usuarios(self) -> None:
        usuarios = repo_usuarios.listar(self._conexion)
        if self._solo_admin:
            usuarios = [u for u in usuarios if u.rol is Rol.ADMIN]

        for usuario in usuarios:
            rol = "Administrador" if usuario.es_admin else "Cajero"
            # Los usuarios de ejemplo se llaman igual que su rol: no se repite.
            etiqueta = usuario.nombre if usuario.nombre == rol else f"{usuario.nombre}  ·  {rol}"
            self.combo_usuario.addItem(etiqueta, usuario.nombre)

        if not usuarios:
            self._mostrar_error("No hay usuarios configurados en el sistema.")

    def _intentar(self) -> None:
        nombre = self.combo_usuario.currentData()
        if not nombre:
            return

        try:
            usuario = auth.autenticar(self._conexion, nombre, self.campo_pin.text())
        except ErrorDominio as error:
            self._mostrar_error(str(error))
            self.campo_pin.clear()
            self.campo_pin.setFocus()
            return

        if self._solo_admin and not usuario.es_admin:
            # No debería ocurrir porque la lista ya está filtrada, pero la comprobación de
            # permisos nunca se delega a la interfaz.
            self._mostrar_error("Ese usuario no es administrador.")
            return

        self._usuario = usuario
        self.accept()

    def _mostrar_error(self, texto: str) -> None:
        self.error.setText(texto)
        self.error.show()

    @property
    def usuario(self) -> Usuario | None:
        """El usuario autenticado, o None si se canceló."""
        return self._usuario

    @staticmethod
    def pedir(
        conexion: sqlite3.Connection,
        padre: QWidget | None = None,
        solo_admin: bool = False,
        mensaje: str = "",
    ) -> Usuario | None:
        """Atajo: muestra el diálogo y devuelve el usuario, o None si se canceló."""
        dialogo = DialogoLogin(conexion, padre, solo_admin=solo_admin, mensaje=mensaje)
        dialogo.exec()
        return dialogo.usuario
