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
from . import movimiento


def mostrar_error(padre: QWidget | None, mensaje: str, titulo: str = "No se pudo continuar") -> None:
    """Error previsible: el usuario hizo algo que no corresponde."""
    caja = QMessageBox(padre)
    caja.setIcon(QMessageBox.Icon.Warning)
    caja.setWindowTitle(titulo)
    caja.setText(mensaje)
    caja.setStandardButtons(QMessageBox.StandardButton.Ok)
    caja.button(QMessageBox.StandardButton.Ok).setText("Entendido")
    movimiento.aparecer_al_abrir(caja)
    caja.exec()


def mostrar_info(padre: QWidget | None, mensaje: str, titulo: str = NOMBRE_COMERCIAL) -> None:
    caja = QMessageBox(padre)
    caja.setIcon(QMessageBox.Icon.Information)
    caja.setWindowTitle(titulo)
    caja.setText(mensaje)
    caja.setStandardButtons(QMessageBox.StandardButton.Ok)
    caja.button(QMessageBox.StandardButton.Ok).setText("Aceptar")
    movimiento.aparecer_al_abrir(caja)
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
    movimiento.aparecer_al_abrir(caja)
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
        movimiento.aparecer_al_abrir(self)
        self.setWindowTitle("Producto no encontrado")
        self.setMinimumWidth(460)
        self.buscar_por_nombre = False

        disposicion = QVBoxLayout(self)
        disposicion.setContentsMargins(24, 24, 24, 20)
        disposicion.setSpacing(14)

        titulo = QLabel("Este producto no está en el catálogo")
        titulo.setObjectName("tituloPantalla")
        disposicion.addWidget(titulo)

        etiqueta_codigo = QLabel(codigo)
        # El color sale de la hoja de estilos y no de aquí: si se escribiera a mano, el
        # tema oscuro seguiría pintando este recuadro con los colores del claro.
        etiqueta_codigo.setObjectName("codigoNoEncontrado")
        etiqueta_codigo.setAlignment(Qt.AlignmentFlag.AlignCenter)
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
        boton_cerrar.setObjectName("botonAccion")
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
        movimiento.aparecer_al_abrir(self)
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
        caja.button(QDialogButtonBox.StandardButton.Ok).setObjectName("botonAccion")
        caja.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        caja.accepted.connect(self.accept)
        caja.rejected.connect(self.reject)
        disposicion.addWidget(caja)

    @property
    def texto(self) -> str:
        return self.campo.text().strip()


#: Ámbitos posibles de un descuento.
AMBITO_VENTA = "venta"
AMBITO_PRODUCTO = "producto"


class DialogoDescuento(QDialog):
    """Pide un descuento por monto fijo o por porcentaje, y sobre qué se aplica.

    Se ofrecen las dos formas de calcularlo porque en una tienda pequena conviven: "te dejo
    en cinco mil" (monto) y "te hago el diez por ciento" (porcentaje). Obligar a convertir
    mentalmente una en la otra delante del cliente es pedir errores.

    Y se ofrecen los dos ámbitos por el mismo motivo: el descuento del pan del día anterior
    es del pan, no de la compra entera, y aplicarlo al total daría el importe correcto hoy
    pero una venta imposible de explicar mañana.

    Tras cerrar se consultan `ambito`, `quitar`, `es_porcentaje` y `valor`.
    """

    def __init__(
        self,
        subtotal_clp: int,
        padre: QWidget | None = None,
        linea=None,
    ) -> None:
        from PySide6.QtWidgets import QLineEdit, QRadioButton

        super().__init__(padre)
        movimiento.aparecer_al_abrir(self)
        self.setWindowTitle("Descuento")
        self.setMinimumWidth(430)
        self._subtotal = subtotal_clp
        self._linea = linea
        self.quitar = False

        columna = QVBoxLayout(self)
        columna.setContentsMargins(26, 24, 26, 20)
        columna.setSpacing(10)

        titulo = QLabel("Aplicar descuento")
        titulo.setObjectName("tituloPantalla")
        columna.addWidget(titulo)

        # ------------------------------------------------------------ ámbito
        self.opcion_venta = QRadioButton("A toda la venta")
        self.opcion_venta.setChecked(True)
        columna.addWidget(self.opcion_venta)

        self.opcion_producto = QRadioButton(self._texto_opcion_producto())
        # Sin línea seleccionada no hay producto al que aplicar nada. Se deja visible y
        # deshabilitada, y no oculta, para que se vea que la opción existe.
        self.opcion_producto.setEnabled(linea is not None)
        columna.addWidget(self.opcion_producto)

        self.opcion_venta.toggled.connect(self._actualizar_base)
        columna.addSpacing(4)

        self.etiqueta_base = QLabel()
        self.etiqueta_base.setObjectName("subtitulo")
        columna.addWidget(self.etiqueta_base)

        # ------------------------------------------------------------ forma de cálculo
        self.opcion_monto = QRadioButton("Descontar un monto en pesos")
        self.opcion_monto.setChecked(True)
        self.opcion_porcentaje = QRadioButton("Descontar un porcentaje")
        columna.addWidget(self.opcion_monto)
        columna.addWidget(self.opcion_porcentaje)

        self.campo = QLineEdit()
        self.campo.setPlaceholderText("Por ejemplo: 500")
        self.campo.returnPressed.connect(self._validar)
        columna.addWidget(self.campo)

        self.error = QLabel()
        self.error.setObjectName("mensajeError")
        self.error.setWordWrap(True)
        self.error.hide()
        columna.addWidget(self.error)

        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botones.button(QDialogButtonBox.StandardButton.Ok).setText("Aplicar")
        botones.button(QDialogButtonBox.StandardButton.Ok).setObjectName("botonAccion")
        botones.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        quitar = botones.addButton("Quitar descuento", QDialogButtonBox.ButtonRole.ResetRole)
        quitar.setToolTip("Quita el descuento del ámbito seleccionado arriba.")
        quitar.clicked.connect(self._quitar)
        botones.accepted.connect(self._validar)
        botones.rejected.connect(self.reject)
        columna.addWidget(botones)

        self._actualizar_base()
        self.campo.setFocus()

    # ------------------------------------------------------------------ ayuda interna

    def _texto_opcion_producto(self) -> str:
        if self._linea is None:
            return "Solo a un producto  (seleccione antes una línea del carrito)"
        if self._linea.gramos is not None:
            # Por peso (D-037): su "1 unidad" no significa nada; lo que se descuenta son gramos.
            from ..utils.money import formatear_peso

            return f"Solo a {self._linea.nombre}  ({formatear_peso(self._linea.gramos)})"
        unidades = "unidad" if self._linea.cantidad == 1 else "unidades"
        return f"Solo a {self._linea.nombre}  ({self._linea.cantidad} {unidades})"

    def _actualizar_base(self) -> None:
        """Mantiene a la vista el importe sobre el que se calculará el descuento."""
        from ..utils.money import formatear_clp

        if self.ambito == AMBITO_PRODUCTO:
            self.etiqueta_base.setText(
                f"Importe de la línea: {formatear_clp(self.base_clp)}"
            )
        else:
            self.etiqueta_base.setText(
                f"Subtotal de la venta: {formatear_clp(self.base_clp)}"
            )
        self.error.hide()

    def _quitar(self) -> None:
        self.quitar = True
        self.accept()

    def _validar(self) -> None:
        from ..utils.money import parsear_clp

        texto = self.campo.text().strip().replace("%", "")
        if not texto:
            self.error.setText("Escriba el descuento.")
            self.error.show()
            return

        if self.opcion_porcentaje.isChecked():
            try:
                valor = float(texto.replace(",", "."))
            except ValueError:
                self.error.setText("El porcentaje debe ser un numero, por ejemplo 10.")
                self.error.show()
                return
            if not 0 <= valor <= 100:
                self.error.setText("El porcentaje debe estar entre 0 y 100.")
                self.error.show()
                return
        else:
            try:
                valor = parsear_clp(texto)
            except ValueError:
                self.error.setText("El monto debe ser un numero, por ejemplo 500.")
                self.error.show()
                return
            if valor < 0:
                self.error.setText("El descuento no puede ser negativo.")
                self.error.show()
                return
            if valor > self.base_clp:
                self.error.setText(
                    "El descuento no puede superar el importe de esa línea."
                    if self.ambito == AMBITO_PRODUCTO
                    else "El descuento no puede superar el total de la venta."
                )
                self.error.show()
                return

        self._valor = valor
        self.accept()

    # ------------------------------------------------------------------ resultado

    @property
    def ambito(self) -> str:
        return AMBITO_PRODUCTO if self.opcion_producto.isChecked() else AMBITO_VENTA

    @property
    def base_clp(self) -> int:
        """Importe contra el que se valida el monto, según el ámbito elegido."""
        if self.ambito == AMBITO_PRODUCTO and self._linea is not None:
            return self._linea.subtotal_clp
        return self._subtotal

    @property
    def es_porcentaje(self) -> bool:
        return self.opcion_porcentaje.isChecked()

    @property
    def valor(self) -> float:
        return getattr(self, "_valor", 0)


class DialogoPeso(QDialog):
    """Pide los gramos de un producto por peso (D-037) y enseña el precio mientras se teclean.

    Se ve el precio antes de aceptar porque es lo que el cajero le dice al cliente: "son 350
    gramos, $2.797". Solo admite gramos enteros, que es como marca la balanza, y avisa del tope
    en lugar de aceptar un cero de más. Tras cerrar con Aceptar, `gramos` tiene el peso.
    """

    def __init__(
        self,
        nombre: str,
        precio_kilo_clp: int,
        padre: QWidget | None = None,
        gramos_iniciales: int | None = None,
    ) -> None:
        from PySide6.QtGui import QIntValidator
        from PySide6.QtWidgets import QLineEdit

        from ..config import GRAMOS_MAX_POR_LINEA
        from ..utils.money import formatear_clp, formatear_peso, precio_por_gramos

        super().__init__(padre)
        movimiento.aparecer_al_abrir(self)
        self.setWindowTitle("Peso del producto")
        self.setMinimumWidth(400)
        self._precio_kilo = precio_kilo_clp
        self._tope = GRAMOS_MAX_POR_LINEA
        self._formatear_clp = formatear_clp
        self._formatear_peso = formatear_peso
        self._precio_por_gramos = precio_por_gramos
        self.gramos: int | None = None

        disposicion = QVBoxLayout(self)
        disposicion.setContentsMargins(24, 24, 24, 20)
        disposicion.setSpacing(10)

        titulo = QLabel(nombre)
        titulo.setObjectName("tituloPantalla")
        titulo.setWordWrap(True)
        disposicion.addWidget(titulo)
        precio = QLabel(f"{formatear_clp(precio_kilo_clp)} el kilo")
        precio.setObjectName("subtitulo")
        disposicion.addWidget(precio)

        disposicion.addWidget(QLabel("Peso en gramos"))
        self.campo = QLineEdit("" if gramos_iniciales is None else str(gramos_iniciales))
        self.campo.setValidator(QIntValidator(0, 10 * GRAMOS_MAX_POR_LINEA, self))
        self.campo.setPlaceholderText("Por ejemplo: 350")
        self.campo.selectAll()
        self.campo.textChanged.connect(self._actualizar)
        disposicion.addWidget(self.campo)

        self.vista = QLabel()
        self.vista.setObjectName("valorSubtotal")
        disposicion.addWidget(self.vista)
        self.error = QLabel()
        self.error.setObjectName("mensajeError")
        self.error.setWordWrap(True)
        self.error.hide()  # su estilo lleva fondo: vacío se vería como un recuadro sin motivo
        disposicion.addWidget(self.error)

        caja = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._aceptar = caja.button(QDialogButtonBox.StandardButton.Ok)
        self._aceptar.setText("Agregar" if gramos_iniciales is None else "Cambiar")
        self._aceptar.setObjectName("botonAccion")
        caja.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        caja.accepted.connect(self._confirmar)
        caja.rejected.connect(self.reject)
        disposicion.addWidget(caja)
        self._actualizar()

    def _leer(self) -> int | None:
        texto = self.campo.text().strip()
        return int(texto) if texto.isdigit() else None

    def _actualizar(self) -> None:
        gramos = self._leer()
        self.error.clear()
        self.error.hide()
        if gramos is None or gramos <= 0:
            self.vista.setText(" ")
            self._aceptar.setEnabled(False)
            return
        if gramos > self._tope:
            self.vista.setText(" ")
            self.error.setText(f"El máximo es {self._tope // 1000} kg. Revise el peso.")
            self.error.show()
            self._aceptar.setEnabled(False)
            return
        precio = self._precio_por_gramos(self._precio_kilo, gramos)
        self.vista.setText(f"{self._formatear_peso(gramos)}  ·  {self._formatear_clp(precio)}")
        self._aceptar.setEnabled(True)

    def _confirmar(self) -> None:
        gramos = self._leer()
        if gramos is None or not 0 < gramos <= self._tope:
            return
        self.gramos = gramos
        self.accept()

    def pedir(self) -> int | None:
        """Abre el diálogo y devuelve los gramos, o None si se canceló."""
        return self.gramos if self.exec() else None
