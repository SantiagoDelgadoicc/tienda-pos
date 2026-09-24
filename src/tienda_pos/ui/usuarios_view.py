"""Administración de usuarios: un usuario por empleado, cada uno con su PIN.

Lo pidió el cliente el 2026-09-18: en una misma caja venden varios empleados el mismo día, y
el cierre tiene que decir quién vendió qué. Reservada al administrador. Como en el resto del
programa, la comprobación de permisos y las reglas —no darse de baja a uno mismo, no dejar la
tienda sin administrador— viven en `services/auth.py`, no aquí: ocultar un botón no es control
de acceso, y en modo red esta pantalla está en otro PC.

**El PIN lo genera el sistema**, no lo escribe nadie. Se enseña una sola vez, en grande, para
que se anote; después solo queda su huella en la base. Si se pierde, se genera otro. Así no hay
dos empleados con `1234`, que es lo que pasa cuando cada uno elige el suyo.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
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
from ..domain.models import Rol, Usuario
from ..red.sesion import Sesion
from . import dialogos, estilos, movimiento, tablas
from .widgets.desplegable import Desplegable

_COLUMNAS = ("Nombre", "Rol", "Estado")
_NOMBRE_ROL = {Rol.CAJERO: "Cajero", Rol.ADMIN: "Administrador"}


class DialogoUsuario(QDialog):
    """Alta de un empleado: nombre y rol. El PIN no se pide: lo genera el sistema."""

    def __init__(self, padre: QWidget | None = None) -> None:
        super().__init__(padre)
        movimiento.aparecer_al_abrir(self)
        self.setWindowTitle("Nuevo usuario")
        self.setMinimumWidth(430)

        columna = QVBoxLayout(self)
        columna.setContentsMargins(26, 24, 26, 20)
        columna.setSpacing(8)

        columna.addWidget(QLabel("Nombre"))
        self.campo_nombre = QLineEdit()
        self.campo_nombre.setPlaceholderText("Como aparecerá en el acceso y en el cierre")
        self.campo_nombre.setMaxLength(40)
        columna.addWidget(self.campo_nombre)

        columna.addWidget(QLabel("Rol"))
        self.combo_rol = Desplegable()
        # Cajero primero: es lo que se da de alta casi siempre, y así es lo que queda elegido.
        for rol in (Rol.CAJERO, Rol.ADMIN):
            self.combo_rol.addItem(_NOMBRE_ROL[rol], rol)
        columna.addWidget(self.combo_rol)

        nota = QLabel(
            "El administrador puede además cambiar precios, dar de alta usuarios y ver las "
            "ventas. El PIN lo genera el sistema al guardar."
        )
        nota.setObjectName("subtitulo")
        nota.setWordWrap(True)
        columna.addWidget(nota)

        self.error = QLabel()
        self.error.setObjectName("mensajeError")
        self.error.setWordWrap(True)
        self.error.hide()
        columna.addWidget(self.error)

        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        botones.button(QDialogButtonBox.StandardButton.Save).setText("Guardar")
        botones.button(QDialogButtonBox.StandardButton.Save).setObjectName("botonAccion")
        botones.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        botones.accepted.connect(self._validar)
        botones.rejected.connect(self.reject)
        columna.addWidget(botones)

        self.campo_nombre.setFocus()

    def _validar(self) -> None:
        """Solo el formato; que el nombre no esté repetido lo dice el servicio."""
        if not self.nombre:
            self.error.setText("Escriba el nombre del empleado.")
            self.error.show()
            return
        self.accept()

    @property
    def nombre(self) -> str:
        return self.campo_nombre.text().strip()

    @property
    def rol(self) -> Rol:
        return self.combo_rol.currentData()


class DialogoPrimerAdministrador(QDialog):
    """Pide el nombre del administrador de una instalación que todavía no tiene usuarios.

    Sustituye a la entrada sin sesión que había antes: una caja recién instalada ya no deja
    vender a nadie sin identificar. El PIN no se pide, lo genera el sistema y se muestra a
    continuación. Este diálogo solo recoge el nombre; crear el usuario lo hace el arranque
    (`app.py`), porque es una de las dos operaciones que no pueden pasar por la red.
    """

    def __init__(self, nombre_sugerido: str = "Administrador", padre: QWidget | None = None) -> None:
        super().__init__(padre)
        movimiento.aparecer_al_abrir(self)
        self.setWindowTitle("Primer administrador")
        self.setMinimumWidth(460)

        columna = QVBoxLayout(self)
        columna.setContentsMargins(26, 24, 26, 20)
        columna.setSpacing(8)

        titulo = QLabel("Esta instalación todavía no tiene usuarios")
        titulo.setObjectName("tituloTarjeta")
        columna.addWidget(titulo)

        explicacion = QLabel(
            "Cree el administrador de la tienda. Con él podrá dar de alta a cada empleado "
            "desde la pantalla de Usuarios. El PIN lo genera el sistema y se lo mostrará "
            "a continuación."
        )
        explicacion.setObjectName("subtitulo")
        explicacion.setWordWrap(True)
        columna.addWidget(explicacion)

        columna.addWidget(QLabel("Nombre"))
        self.campo_nombre = QLineEdit(nombre_sugerido)
        self.campo_nombre.setMaxLength(40)
        self.campo_nombre.selectAll()
        columna.addWidget(self.campo_nombre)

        self.error = QLabel()
        self.error.setObjectName("mensajeError")
        self.error.setWordWrap(True)
        self.error.hide()
        columna.addWidget(self.error)

        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botones.button(QDialogButtonBox.StandardButton.Ok).setText("Crear")
        botones.button(QDialogButtonBox.StandardButton.Ok).setObjectName("botonAccion")
        botones.button(QDialogButtonBox.StandardButton.Cancel).setText("Salir")
        botones.accepted.connect(self._validar)
        botones.rejected.connect(self.reject)
        columna.addWidget(botones)
        self.campo_nombre.setFocus()

    def _validar(self) -> None:
        if not self.nombre:
            self.error.setText("Escriba un nombre.")
            self.error.show()
            return
        self.accept()

    def fallar(self, mensaje: str) -> None:
        self.error.setText(mensaje)
        self.error.show()

    @property
    def nombre(self) -> str:
        return self.campo_nombre.text().strip()


class DialogoPin(QDialog):
    """Enseña un PIN recién generado, en grande, para que se anote.

    Es la única vez que se ve. No se dramatiza, porque perderlo no es grave: el administrador
    genera otro con un clic. Lo que sí se evita es que alguien lo cierre sin mirarlo, por eso
    el botón dice lo que hay que haber hecho antes de pulsarlo.
    """

    def __init__(
        self, titulo: str, usuario: Usuario, pin: str, padre: QWidget | None = None
    ) -> None:
        super().__init__(padre)
        movimiento.aparecer_al_abrir(self)
        self.setWindowTitle(titulo)
        self.setMinimumWidth(480)

        columna = QVBoxLayout(self)
        columna.setContentsMargins(28, 26, 28, 22)
        columna.setSpacing(10)

        encabezado = QLabel(f"PIN de {usuario.nombre}")
        encabezado.setObjectName("tituloTarjeta")
        columna.addWidget(encabezado)

        self.etiqueta_pin = QLabel(pin)
        self.etiqueta_pin.setObjectName("pinGenerado")
        self.etiqueta_pin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Se puede seleccionar y copiar, pero no tiene foco: Enter tiene que ir al botón.
        self.etiqueta_pin.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        columna.addWidget(self.etiqueta_pin)

        aviso = QLabel(
            "Anótelo y entrégueselo. Esta es la única vez que se muestra.\n"
            "Si se pierde, genere otro con «PIN nuevo»: el anterior deja de servir."
        )
        aviso.setObjectName("subtitulo")
        aviso.setWordWrap(True)
        aviso.setAlignment(Qt.AlignmentFlag.AlignCenter)
        columna.addWidget(aviso)

        botones = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        listo = botones.button(QDialogButtonBox.StandardButton.Ok)
        listo.setText("Ya lo anoté")
        listo.setObjectName("botonAccion")
        botones.accepted.connect(self.accept)
        columna.addWidget(botones)
        listo.setFocus()

    @staticmethod
    def mostrar(titulo: str, usuario: Usuario, pin: str, padre: QWidget | None = None) -> None:
        DialogoPin(titulo, usuario, pin, padre).exec()


class UsuariosView(QWidget):
    """Listado y mantenimiento de los usuarios de la tienda."""

    salir_solicitado = Signal()
    #: Cuántos usuarios activos hay. Lo pinta la cabecera, como en la pantalla de productos.
    resumen_cambiado = Signal(str)

    def __init__(self, sesion: Sesion, padre: QWidget | None = None) -> None:
        super().__init__(padre)
        self._sesion = sesion
        #: El administrador que autorizó la pantalla. Lo fija la ventana al entrar.
        self.usuario: Usuario | None = None
        self._usuarios: list[Usuario] = []
        self._construir()

    def _construir(self) -> None:
        columna = QVBoxLayout(self)
        columna.setContentsMargins(28, 22, 28, 24)
        columna.setSpacing(16)

        fila = QHBoxLayout()
        fila.setSpacing(10)

        self.casilla_bajas = QCheckBox("Mostrar usuarios dados de baja")
        self.casilla_bajas.toggled.connect(lambda _marcada: self.recargar())
        fila.addWidget(self.casilla_bajas)
        fila.addStretch()

        self.boton_nuevo = QPushButton("Nuevo usuario")
        self.boton_nuevo.setObjectName("botonAccion")
        self.boton_nuevo.clicked.connect(self.crear)
        fila.addWidget(self.boton_nuevo)

        self.boton_pin = QPushButton("PIN nuevo")
        self.boton_pin.setToolTip("Genera un PIN nuevo para quien lo olvidó. El anterior deja de servir.")
        self.boton_pin.clicked.connect(self.nuevo_pin)
        fila.addWidget(self.boton_pin)

        self.boton_reactivar = QPushButton("Reactivar")
        self.boton_reactivar.setToolTip("Vuelve a dar de alta a alguien dado de baja, con PIN nuevo.")
        self.boton_reactivar.clicked.connect(self.reactivar)
        fila.addWidget(self.boton_reactivar)

        self.boton_baja = QPushButton("Dar de baja")
        self.boton_baja.setObjectName("botonPeligro")
        self.boton_baja.clicked.connect(self.dar_de_baja)
        fila.addWidget(self.boton_baja)

        columna.addLayout(fila)

        self.tabla = QTableWidget(0, len(_COLUMNAS))
        self.tabla.setHorizontalHeaderLabels(_COLUMNAS)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.setShowGrid(False)
        self.tabla.itemSelectionChanged.connect(self._actualizar_botones)

        cabecera = self.tabla.horizontalHeader()
        cabecera.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        cabecera.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        cabecera.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        tablas.alinear_cabeceras(self.tabla, (tablas.IZQUIERDA, tablas.IZQUIERDA, tablas.IZQUIERDA))
        columna.addWidget(self.tabla, stretch=1)

        self._actualizar_botones()

    # ------------------------------------------------------------------ datos

    def recargar(self) -> None:
        try:
            self._usuarios = self._sesion.listar_para_administrar(
                self.usuario, incluir_inactivos=self.casilla_bajas.isChecked()
            )
        except ErrorDominio as error:
            self._usuarios = []
            dialogos.mostrar_error(self, str(error))
        self._pintar()

    def repintar(self) -> None:
        """Vuelve a pintar tras un cambio de tema: el gris de las bajas va celda a celda."""
        self._pintar()

    def _pintar(self) -> None:
        self.tabla.setRowCount(len(self._usuarios))
        apagado = QBrush(QColor(estilos.actual.texto_apagado))
        for fila, usuario in enumerate(self._usuarios):
            nombre = usuario.nombre
            # Marcar a quien está usando la pantalla evita el error más tonto de todos:
            # buscarse en la lista para darse de baja a uno mismo.
            if self.usuario is not None and usuario.id == self.usuario.id:
                nombre += "  (usted)"
            celdas = (
                QTableWidgetItem(nombre),
                QTableWidgetItem(_NOMBRE_ROL[usuario.rol]),
                QTableWidgetItem("Activo" if usuario.activo else "Dado de baja"),
            )
            for columna, celda in enumerate(celdas):
                if not usuario.activo:
                    celda.setForeground(apagado)
                self.tabla.setItem(fila, columna, celda)

        activos = sum(1 for u in self._usuarios if u.activo)
        self.resumen_cambiado.emit(
            "1 usuario activo" if activos == 1 else f"{activos} usuarios activos"
        )
        self._actualizar_botones()

    def _seleccionado(self) -> Usuario | None:
        fila = self.tabla.currentRow()
        if fila < 0 or fila >= len(self._usuarios) or not self.tabla.selectedItems():
            return None
        return self._usuarios[fila]

    def seleccionar(self, usuario_id: int) -> None:
        for fila, usuario in enumerate(self._usuarios):
            if usuario.id == usuario_id:
                self.tabla.selectRow(fila)
                return

    def _actualizar_botones(self) -> None:
        """Cada botón activo solo cuando tiene sentido para la fila elegida.

        Es cortesía, no control: el servicio vuelve a comprobarlo todo.
        """
        usuario = self._seleccionado()
        activo = usuario is not None and usuario.activo
        self.boton_pin.setEnabled(activo)
        self.boton_baja.setEnabled(activo)
        self.boton_reactivar.setEnabled(usuario is not None and not usuario.activo)

    # ------------------------------------------------------------------ acciones

    def crear(self) -> None:
        dialogo = DialogoUsuario(self)
        if not dialogo.exec():
            return
        try:
            usuario, pin = self._sesion.alta_usuario(self.usuario, dialogo.nombre, dialogo.rol)
        except ErrorDominio as error:
            dialogos.mostrar_error(self, str(error))
            return
        self.recargar()
        self.seleccionar(usuario.id)
        DialogoPin.mostrar("Usuario creado", usuario, pin, self)

    def nuevo_pin(self) -> None:
        usuario = self._seleccionado()
        if usuario is None:
            dialogos.mostrar_error(self, "Seleccione primero un usuario de la lista.")
            return
        if not dialogos.confirmar(
            self,
            "PIN nuevo",
            f"Se generará un PIN nuevo para {usuario.nombre}.\n"
            "El que tiene ahora dejará de servir.\n\n¿Continuar?",
            texto_si="Sí, generar",
        ):
            return
        try:
            pin = self._sesion.reiniciar_pin(self.usuario, usuario.id)
        except ErrorDominio as error:
            dialogos.mostrar_error(self, str(error))
            return
        DialogoPin.mostrar("PIN nuevo", usuario, pin, self)

    def reactivar(self) -> None:
        usuario = self._seleccionado()
        if usuario is None:
            dialogos.mostrar_error(self, "Seleccione primero un usuario de la lista.")
            return
        try:
            pin = self._sesion.reactivar_usuario(self.usuario, usuario.id)
        except ErrorDominio as error:
            dialogos.mostrar_error(self, str(error))
            return
        self.recargar()
        self.seleccionar(usuario.id)
        DialogoPin.mostrar("Usuario reactivado", usuario, pin, self)

    def dar_de_baja(self) -> None:
        usuario = self._seleccionado()
        if usuario is None:
            dialogos.mostrar_error(self, "Seleccione primero un usuario de la lista.")
            return
        if not dialogos.confirmar(
            self,
            "Dar de baja",
            f"{usuario.nombre}\n\nNo podrá volver a entrar a la caja.\n"
            "Sus ventas siguen a su nombre en los informes, y se puede reactivar más adelante."
            "\n\n¿Desea darlo de baja?",
            texto_si="Sí, dar de baja",
        ):
            return
        try:
            self._sesion.desactivar_usuario(self.usuario, usuario.id)
        except ErrorDominio as error:
            dialogos.mostrar_error(self, str(error))
            return
        self.recargar()
