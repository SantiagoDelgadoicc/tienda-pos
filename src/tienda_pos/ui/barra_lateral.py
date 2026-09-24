"""Barra lateral de navegación.

Sustituye a la barra superior azul de las primeras versiones. El motivo no es estético: con
cuatro pantallas y dos de ellas bajo permiso de administrador, una barra superior obligaba a
recordar qué tecla de función llevaba a dónde. Una columna con las secciones a la vista dice
en todo momento dónde está uno y qué más hay, que es lo que hace que un programa parezca un
sistema y no una sucesión de ventanas.

Se puede plegar a una tira de iconos (Ctrl+B). En un monitor pequeño, o en una caja donde lo
único que importa es el carrito, esos 232 píxeles son sitio de tabla. El estado se guarda en
las preferencias del equipo: plegarla una vez debe bastar.

El plegado se anima, en 180 ms (D-029). Los iconos no se mueven en todo el trayecto: el
margen del botón desplegado y el centrado del plegado los dejan en la misma columna, así que
lo único que se desplaza es el borde derecho, y el ojo entiende que el menú se recogió hacia
la izquierda en vez de ver una pantalla que salta.

Las teclas de función siguen funcionando exactamente igual, plegada o desplegada: la barra es
otra forma de llegar al mismo sitio, no la única.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..config import NOMBRE_COMERCIAL, RUBRO_COMERCIAL
from ..domain.models import Usuario
from . import estilos, iconos, movimiento

#: Cada entrada: clave, rótulo, icono y atajo. El orden es el de la barra.
_PRINCIPALES = (
    ("venta", "Venta", "escanear", "Esc"),
    ("consulta", "Consulta de precio", "etiqueta", "F2"),
)
_ADMINISTRACION = (
    ("productos", "Productos", "catalogo", "F7"),
    ("reportes", "Ventas del día", "informe", "F8"),
    # Sin tecla: F1 a F12 están tomadas, y es una pantalla que se abre cuando entra o se va
    # alguien, no varias veces al día.
    ("usuarios", "Usuarios", "usuario", ""),
)
_PIE = (
    ("configuracion", "Configuración", "ajustes", "F9"),
    ("usuario", "Cambiar usuario", "salir", "F10"),
)

_TAMANO_ICONO = 20
#: Lado del logotipo en la cabecera de la barra.
_TAMANO_LOGO = 34
_MARGEN = 14
#: Ancho útil de la barra plegada: lo que queda para centrar un icono dentro.
_ANCHO_PLEGADO = estilos.ANCHO_BARRA_LATERAL_PLEGADA - 2 * _MARGEN


def _conservar_sitio(widget: QWidget) -> None:
    """Hace que el widget siga ocupando su sitio en el layout aunque esté oculto."""
    politica = widget.sizePolicy()
    politica.setRetainSizeWhenHidden(True)
    widget.setSizePolicy(politica)


class _BotonNav(QPushButton):
    """Entrada del menú: icono, rótulo y la tecla que hace lo mismo.

    Es un `QPushButton` con sus tres piezas dentro en vez de un botón con texto porque el
    atajo va alineado a la derecha, y eso un botón corriente no sabe hacerlo. La contrapartida
    es que el color de las piezas no lo hereda de la hoja de estilos —una regla sobre el botón
    no alcanza a sus hijos—, así que lo fija `repintar()`.
    """

    def __init__(self, rotulo: str, icono: str, atajo: str, padre: QWidget | None = None) -> None:
        super().__init__(padre)
        self.icono = icono
        self._plegada = False
        self.setObjectName("navBoton")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setMinimumHeight(42)
        self.setToolTip(f"{rotulo}   ({atajo})")

        self._fila = QHBoxLayout(self)
        self._fila.setContentsMargins(12, 0, 10, 0)
        self._fila.setSpacing(0)

        # El icono se centra dentro de su propia etiqueta. Es lo que permite pasar de barra
        # desplegada a plegada cambiando un ancho, sin tocar el layout.
        self._icono = QLabel()
        self._icono.setFixedWidth(_TAMANO_ICONO)
        self._icono.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._fila.addWidget(self._icono)
        self._fila.addSpacing(12)

        self._rotulo = QLabel(rotulo)
        self._fila.addWidget(self._rotulo)
        self._fila.addStretch()

        self._atajo = QLabel(atajo)
        self._atajo.setObjectName("navAtajo")
        self._fila.addWidget(self._atajo)

        self.repintar()

    def plegar(self, plegada: bool) -> None:
        self._plegada = plegada
        margenes = (0, 0, 0, 0) if plegada else (12, 0, 10, 0)
        self._fila.setContentsMargins(*margenes)
        self._icono.setFixedWidth(_ANCHO_PLEGADO if plegada else _TAMANO_ICONO)
        self.repintar()

    def repintar(self) -> None:
        """Vuelve a pintar icono y rótulo con el color que toca según el estado."""
        paleta = estilos.actual
        color = paleta.acento_fuerte if self.isChecked() else paleta.texto_suave
        self._icono.setPixmap(iconos.pixmap(self.icono, _TAMANO_ICONO, color))

        peso = 700 if self.isChecked() else 500
        # Tamaño fijo: el menú se usa de cerca y no sigue al ajuste de tamaño de letra
        # (ver `estilos.ESCALA_TEXTO`). Con la barra de ancho fijo, crecer lo montaría
        # sobre el atajo.
        self._rotulo.setStyleSheet(f"color: {color}; font-weight: {peso}; font-size: 15px;")
        self._rotulo.setVisible(not self._plegada)
        self._atajo.setVisible(not self._plegada and not self.isChecked())

    def setChecked(self, marcado: bool) -> None:  # noqa: N802 - lo nombra Qt
        super().setChecked(marcado)
        self.repintar()


class BarraLateral(QFrame):
    """Columna de navegación: marca arriba, secciones en medio, usuario abajo."""

    #: Se emite con la clave de la entrada pulsada.
    navegacion_solicitada = Signal(str)
    #: Se emite al plegar o desplegar, con el estado nuevo.
    plegado_cambiado = Signal(bool)

    def __init__(self, padre: QWidget | None = None) -> None:
        super().__init__(padre)
        self.setObjectName("barraLateral")
        self._plegada = False
        self._botones: dict[str, _BotonNav] = {}
        self._secciones: list[QLabel] = []
        self._construir()
        self.setFixedWidth(estilos.ANCHO_BARRA_LATERAL)

        self._anim_ancho = movimiento.animacion(self, movimiento.BARRA_MS)
        self._anim_ancho.valueChanged.connect(self.setFixedWidth)
        self._anim_ancho.finished.connect(self._terminar_plegado)

    # ------------------------------------------------------------------ construcción

    def _construir(self) -> None:
        columna = QVBoxLayout(self)
        columna.setContentsMargins(_MARGEN, 16, _MARGEN, _MARGEN)
        columna.setSpacing(0)

        columna.addWidget(self._fila_plegar())
        columna.addSpacing(10)
        columna.addWidget(self._marca())
        columna.addSpacing(22)

        columna.addWidget(self._rotulo_seccion("CAJA"))
        columna.addSpacing(6)
        for clave, rotulo, icono, atajo in _PRINCIPALES:
            columna.addWidget(self._boton(clave, rotulo, icono, atajo))

        columna.addSpacing(18)
        columna.addWidget(self._rotulo_seccion("ADMINISTRACIÓN"))
        columna.addSpacing(6)
        for clave, rotulo, icono, atajo in _ADMINISTRACION:
            columna.addWidget(self._boton(clave, rotulo, icono, atajo))

        columna.addStretch()

        columna.addWidget(self._ficha_usuario())
        columna.addSpacing(10)
        for clave, rotulo, icono, atajo in _PIE:
            boton = self._boton(clave, rotulo, icono, atajo)
            # Ni la configuración ni el cambio de usuario son un sitio donde uno *está*: son
            # acciones. Marcarlas dejaría la barra mintiendo sobre en qué pantalla estás.
            boton.setCheckable(False)
            columna.addWidget(boton)

        #: La rueda de configuración vive aquí desde que desapareció la barra superior.
        self.boton_configuracion = self._botones["configuracion"]

    def _fila_plegar(self) -> QWidget:
        """El botón de plegar, arriba del todo.

        Va a la derecha cuando la barra está desplegada y ocupa la tira entera cuando está
        plegada, de modo que su icono queda centrado sin tocar el layout: un `QPushButton`
        ya centra su propio icono.
        """
        fila = QWidget()
        fila.setObjectName("transparente")
        caja = QHBoxLayout(fila)
        caja.setContentsMargins(0, 0, 0, 0)
        caja.setSpacing(0)
        caja.addStretch()

        self.boton_plegar = QPushButton()
        self.boton_plegar.setObjectName("botonPlegar")
        self.boton_plegar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.boton_plegar.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.boton_plegar.setFixedSize(30, 30)
        self.boton_plegar.clicked.connect(self.alternar_plegado)
        caja.addWidget(self.boton_plegar)
        return fila

    def _marca(self) -> QWidget:
        fila = QWidget()
        fila.setObjectName("transparente")
        caja = QHBoxLayout(fila)
        caja.setContentsMargins(0, 0, 0, 0)
        caja.setSpacing(11)

        self._logotipo = QLabel()
        self._logotipo.setFixedWidth(_TAMANO_LOGO)
        self._logotipo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        caja.addWidget(self._logotipo)

        self._textos_marca = QWidget()
        self._textos_marca.setObjectName("transparente")
        # El nombre del negocio ocupa dos renglones y el logotipo menos: sin esto, plegar
        # encogería la cabecera y subiría todo el menú unos píxeles.
        _conservar_sitio(self._textos_marca)
        textos = QVBoxLayout(self._textos_marca)
        textos.setContentsMargins(0, 0, 0, 0)
        textos.setSpacing(1)
        nombre = QLabel(NOMBRE_COMERCIAL)
        nombre.setObjectName("marca")
        textos.addWidget(nombre)
        rubro = QLabel(RUBRO_COMERCIAL.upper())
        rubro.setObjectName("marcaSub")
        textos.addWidget(rubro)
        caja.addWidget(self._textos_marca)
        caja.addStretch()
        return fila

    def _rotulo_seccion(self, texto: str) -> QLabel:
        etiqueta = QLabel(texto)
        etiqueta.setObjectName("navSeccion")
        etiqueta.setContentsMargins(12, 0, 0, 0)
        # Plegada, el rótulo se esconde pero conserva su alto. Así los iconos quedan a la
        # misma altura en los dos estados y al plegar solo se mueve el borde de la barra.
        _conservar_sitio(etiqueta)
        self._secciones.append(etiqueta)
        return etiqueta

    def _boton(self, clave: str, rotulo: str, icono: str, atajo: str) -> _BotonNav:
        boton = _BotonNav(rotulo, icono, atajo, self)
        boton.clicked.connect(lambda _=False, c=clave: self.navegacion_solicitada.emit(c))
        self._botones[clave] = boton
        return boton

    def _ficha_usuario(self) -> QWidget:
        self._ficha = QFrame()
        self._ficha.setObjectName("fichaUsuario")
        self._fila_ficha = QHBoxLayout(self._ficha)
        self._fila_ficha.setContentsMargins(12, 10, 12, 10)
        self._fila_ficha.setSpacing(10)

        self._avatar = QLabel()
        self._avatar.setFixedWidth(20)
        self._avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._fila_ficha.addWidget(self._avatar)

        self._textos_usuario = QWidget()
        self._textos_usuario.setObjectName("transparente")
        textos = QVBoxLayout(self._textos_usuario)
        textos.setContentsMargins(0, 0, 0, 0)
        textos.setSpacing(0)
        self.etiqueta_usuario = QLabel("Sin sesión")
        self.etiqueta_usuario.setObjectName("usuarioNombre")
        textos.addWidget(self.etiqueta_usuario)
        self.etiqueta_rol = QLabel("—")
        self.etiqueta_rol.setObjectName("usuarioRol")
        textos.addWidget(self.etiqueta_rol)
        self._fila_ficha.addWidget(self._textos_usuario, stretch=1)
        self._fila_ficha.addStretch()
        return self._ficha

    # ------------------------------------------------------------------ plegado

    @property
    def esta_plegada(self) -> bool:
        return self._plegada

    def alternar_plegado(self) -> None:
        self.plegar(not self._plegada, animar=True)
        self.plegado_cambiado.emit(self._plegada)

    def plegar(self, plegada: bool, animar: bool = False) -> None:
        """Pasa de columna a tira de iconos, o al revés.

        Solo se anima cuando lo pide el cajero (Ctrl+B o el botón). Al arrancar y al guardar
        la configuración se aplica de golpe: nadie quiere ver el menú recogerse cada vez que
        abre el programa.

        El estado cambia en el acto; lo que tarda es el ancho. Al plegar, los textos se van
        antes de que la barra empiece a estrecharse, porque apretados en una columna que
        encoge se verían partidos a la mitad. Al desplegar vuelven cuando ya hay sitio. Un
        Ctrl+B a medio camino da la vuelta desde donde esté, sin esperar.
        """
        self._plegada = plegada
        destino = estilos.ANCHO_BARRA_LATERAL_PLEGADA if plegada else estilos.ANCHO_BARRA_LATERAL
        self._anim_ancho.stop()

        # El ancho que cuenta es el mínimo, que es el que fija `setFixedWidth`: `width()` aún
        # no está al día si la ventana no se ha mostrado.
        actual = self.minimumWidth()
        if not (animar and movimiento.activo()) or actual == destino:
            self.setFixedWidth(destino)
            self._aplicar_contenido(plegada)
            return

        # En los dos sentidos la barra viaja dibujada como tira: iconos centrados y sin
        # textos. Al desplegar, lo desplegado aparece entero al final, no a trozos.
        self._aplicar_contenido(True)
        # Desaceleración en los dos sentidos: lo pidió el cajero, así que tiene que empezar a
        # moverse en el acto. Una curva que arranca despacio se siente como una tecla lenta.
        self._anim_ancho.setStartValue(actual)
        self._anim_ancho.setEndValue(destino)
        self._anim_ancho.start()

    def _terminar_plegado(self) -> None:
        self._aplicar_contenido(self._plegada)

    def _aplicar_contenido(self, plegada: bool) -> None:
        """Deja textos, márgenes e iconos como corresponden a la barra plegada o no."""
        self._textos_marca.setVisible(not plegada)
        self._logotipo.setFixedWidth(_ANCHO_PLEGADO if plegada else _TAMANO_LOGO)

        self._textos_usuario.setVisible(not plegada)
        self._avatar.setFixedWidth(_ANCHO_PLEGADO - 12 if plegada else 20)
        self._fila_ficha.setContentsMargins(*((6, 10, 6, 10) if plegada else (12, 10, 12, 10)))

        for etiqueta in self._secciones:
            etiqueta.setVisible(not plegada)
        for boton in self._botones.values():
            boton.plegar(plegada)

        self.boton_plegar.setFixedSize(_ANCHO_PLEGADO if plegada else 30, 30)
        self._pintar_boton_plegar()

    def _pintar_boton_plegar(self) -> None:
        nombre = "desplegar" if self._plegada else "plegar"
        self.boton_plegar.setIcon(iconos.icono(nombre, 18, estilos.actual.texto_suave))
        self.boton_plegar.setToolTip(
            "Mostrar el menú   (Ctrl+B)" if self._plegada else "Ocultar el menú   (Ctrl+B)"
        )

    # ------------------------------------------------------------------ estado

    def seleccionar(self, clave: str) -> None:
        """Marca la entrada de la pantalla en la que se está."""
        for nombre, boton in self._botones.items():
            if boton.isCheckable():
                boton.setChecked(nombre == clave)

    def establecer_usuario(self, usuario: Usuario | None, caja: str | None = None) -> None:
        """Pinta quién opera y **en qué caja**.

        El nombre de la caja va siempre a la vista a propósito: es con el que se firman las
        ventas del cierre, y si los dos PC se llamaran igual, el cierre mezclaría sus ventas sin
        ningún aviso. Viéndolo al pie de cada caja, eso se nota el primer día.
        """
        if usuario is None:
            self.etiqueta_usuario.setText("Sin sesión")
            self.etiqueta_rol.setText("Pulse F10 para entrar")
            self._ficha.setToolTip("Sin sesión iniciada")
            return
        rol = "Administrador" if usuario.es_admin else "Cajero"
        # Los usuarios de ejemplo se llaman igual que su rol; repetirlo solo hace ruido.
        detalle = [rol] if usuario.nombre != rol else []
        if caja:
            detalle.append(caja)
        self.etiqueta_usuario.setText(usuario.nombre)
        self.etiqueta_rol.setText(" · ".join(detalle) or "En caja")
        # Plegada no se ve el nombre, así que la ficha lo dice al pasar el ratón por encima.
        self._ficha.setToolTip(" · ".join([usuario.nombre, rol] + ([caja] if caja else [])))

    def repintar(self) -> None:
        """Vuelve a dibujar lo que la hoja de estilos no alcanza: los iconos y la marca."""
        paleta = estilos.actual
        self._logotipo.setPixmap(iconos.logotipo(_TAMANO_LOGO))
        self._avatar.setPixmap(iconos.pixmap("usuario", 20, paleta.texto_suave))
        self._pintar_boton_plegar()
        for boton in self._botones.values():
            boton.repintar()
