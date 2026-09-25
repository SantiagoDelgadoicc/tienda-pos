"""Efectivo: abrir la caja, anotar lo que entra y sale del cajón, y cerrarla contando (fase 19).

Lo pidió el cliente el 2026-09-24: anota todos los retiros "porque si no le robarían un montón",
saca plata seguido de cada caja y paga en efectivo a algunos proveedores. La pantalla es para
todos los empleados —cualquiera paga a un proveedor o cierra la caja—, pero con dos límites que
pone el servidor y no esta pantalla (D-036):

- **un retiro exige PIN de administrador**; queda a nombre de quien lo autorizó, que es quien se
  lleva la plata;
- **el conteo es a ciegas**: sin administrador delante no se ve cuánto debería haber, ni la cuenta
  ni la diferencia al cerrar. El dueño lo ve con su PIN ("Ver las cuentas").

Actúa siempre sobre **esta** caja. Los cierres de las dos cajas los ve el administrador abajo.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
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
from ..domain.models import MovimientoEfectivo, TipoMovimiento, TurnoCaja, Usuario
from ..red.sesion import Sesion
from ..services.arqueo import LARGO_MAXIMO_TEXTO, describir_diferencia
from ..utils.money import formatear_clp, parsear_clp
from . import dialogos, estilos, movimiento, tablas

NOMBRE_TIPO = {
    TipoMovimiento.RETIRO: "Retiro",
    TipoMovimiento.PAGO_PROVEEDOR: "Pago a proveedor",
    TipoMovimiento.INGRESO: "Ingreso de sencillo",
}

#: Lo mismo, más corto, para la columna de la tabla: con el nombre largo el detalle no cabía.
NOMBRE_CORTO = {
    TipoMovimiento.RETIRO: "Retiro",
    TipoMovimiento.PAGO_PROVEEDOR: "Pago proveedor",
    TipoMovimiento.INGRESO: "Ingreso",
}

_COLUMNAS_MOVIMIENTOS = ("Hora", "Qué", "Monto", "Detalle", "Quién")
_COLUMNAS_CIERRES = ("Caja", "Turno", "Debería haber", "Contado", "Resultado", "Cerró")

AVISO_A_CIEGAS = (
    "Cuánto debería haber en el cajón lo ve el administrador. Al cerrar, cuente el efectivo y "
    "anote lo que hay."
)


def _nombre_tipo(tipo: TipoMovimiento | None) -> str:
    return NOMBRE_CORTO.get(tipo, "Otro")


def texto_turno(turno: TurnoCaja) -> str:
    """"24/09 09:00–21:30", o con las dos fechas si el turno pasó la medianoche."""
    inicio = turno.abierto_en.strftime("%d/%m %H:%M")
    if turno.cerrado_en is None:
        return f"{inicio}–"
    if turno.cerrado_en.date() == turno.abierto_en.date():
        return f"{inicio}–{turno.cerrado_en:%H:%M}"
    return f"{inicio}–{turno.cerrado_en:%d/%m %H:%M}"


def _monto_con_signo(movimiento: MovimientoEfectivo) -> str:
    efecto = movimiento.efecto_clp
    return f"+{formatear_clp(efecto)}" if efecto > 0 else f"−{formatear_clp(-efecto)}"


def color_diferencia(diferencia: int | None) -> str:
    """Verde si cuadra, rojo si falta. Si sobra, el color corriente: no es un problema de robo,
    pero tampoco "salió bien"."""
    paleta = estilos.actual
    if diferencia is None:
        return paleta.texto_suave
    if diferencia == 0:
        return paleta.exito
    return paleta.error if diferencia < 0 else paleta.texto


# --------------------------------------------------------------------------- diálogo de monto


class DialogoMonto(QDialog):
    """Pide un monto en pesos y, si hace falta, un texto: el proveedor, un motivo, una nota.

    Lo usan las cinco acciones de la pantalla. Valida aquí lo evidente —que sea un número y no
    negativo— para no hacer un viaje al servidor por un dedo que se equivocó; el resto lo valida
    el servicio.
    """

    def __init__(
        self,
        titulo: str,
        pregunta: str,
        padre: QWidget | None = None,
        *,
        ayuda: str = "",
        valor_inicial: int | None = None,
        etiqueta_texto: str | None = None,
        texto_obligatorio: bool = False,
        puede_ser_cero: bool = True,
        texto_aceptar: str = "Aceptar",
    ) -> None:
        super().__init__(padre)
        movimiento.aparecer_al_abrir(self)
        self.setWindowTitle(titulo)
        self.setMinimumWidth(440)
        self._texto_obligatorio = texto_obligatorio
        self._puede_ser_cero = puede_ser_cero
        self.monto: int = 0

        columna = QVBoxLayout(self)
        columna.setContentsMargins(26, 24, 26, 20)
        columna.setSpacing(10)

        encabezado = QLabel(titulo)
        encabezado.setObjectName("tituloPantalla")
        columna.addWidget(encabezado)

        columna.addWidget(QLabel(pregunta))
        self.campo_monto = QLineEdit("" if valor_inicial is None else formatear_clp(valor_inicial))
        self.campo_monto.setPlaceholderText("Por ejemplo: 50.000")
        self.campo_monto.selectAll()
        columna.addWidget(self.campo_monto)

        self.campo_texto: QLineEdit | None = None
        if etiqueta_texto:
            columna.addSpacing(4)
            columna.addWidget(QLabel(etiqueta_texto))
            self.campo_texto = QLineEdit()
            self.campo_texto.setMaxLength(LARGO_MAXIMO_TEXTO)
            columna.addWidget(self.campo_texto)

        if ayuda:
            nota = QLabel(ayuda)
            nota.setObjectName("subtitulo")
            nota.setWordWrap(True)
            columna.addWidget(nota)

        self.error = QLabel()
        self.error.setObjectName("mensajeError")
        self.error.setWordWrap(True)
        self.error.hide()
        columna.addWidget(self.error)

        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botones.button(QDialogButtonBox.StandardButton.Ok).setText(texto_aceptar)
        botones.button(QDialogButtonBox.StandardButton.Ok).setObjectName("botonAccion")
        botones.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        botones.accepted.connect(self._validar)
        botones.rejected.connect(self.reject)
        columna.addWidget(botones)
        self.campo_monto.setFocus()

    @property
    def texto(self) -> str:
        return self.campo_texto.text().strip() if self.campo_texto else ""

    def _fallar(self, mensaje: str, campo: QLineEdit) -> None:
        self.error.setText(mensaje)
        self.error.show()
        campo.setFocus()

    def _validar(self) -> None:
        try:
            monto = parsear_clp(self.campo_monto.text())
        except ValueError:
            self._fallar("Escriba el monto en pesos, por ejemplo 50.000.", self.campo_monto)
            return
        if monto < 0 or (monto == 0 and not self._puede_ser_cero):
            self._fallar(
                "El monto no puede ser negativo."
                if monto < 0
                else "El monto tiene que ser mayor que cero.",
                self.campo_monto,
            )
            return
        if self._texto_obligatorio and self.campo_texto is not None and not self.texto:
            self._fallar("Este dato no puede quedar vacío.", self.campo_texto)
            return
        self.monto = monto
        self.accept()

    @classmethod
    def pedir(cls, *args, **kwargs) -> tuple[int, str] | None:
        """Abre el diálogo y devuelve (monto, texto), o None si se canceló. Las pruebas lo
        sustituyen por una respuesta fija."""
        dialogo = cls(*args, **kwargs)
        if dialogo.exec() != QDialog.DialogCode.Accepted:
            return None
        return dialogo.monto, dialogo.texto


def pedir_apertura(
    sesion: Sesion, usuario: Usuario | None, padre: QWidget | None, *, motivo: str = ""
) -> TurnoCaja | None:
    """Pregunta con cuánto efectivo se abre la caja y la abre. None si se canceló o falló.

    La usan la pantalla de venta —al intentar cobrar con la caja cerrada—, el arranque y esta
    pantalla. Propone el monto que fijó el administrador, pero se guarda lo que se escriba: es
    lo que de verdad hay en el cajón.
    """
    try:
        sugerido = sesion.monto_sugerido()
    except ErrorDominio:
        sugerido = None
    ayuda = "Cuente el efectivo del cajón antes de empezar."
    if sugerido is not None:
        ayuda += f" El administrador indicó que la caja parta con {formatear_clp(sugerido)}."
    respuesta = DialogoMonto.pedir(
        f"Abrir la caja {sesion.caja or ''}".strip(),
        (motivo + "\n\n" if motivo else "") + "¿Cuánto efectivo hay ahora en el cajón?",
        padre,
        ayuda=ayuda,
        valor_inicial=sugerido,
        texto_aceptar="Abrir la caja",
    )
    if respuesta is None:
        return None
    try:
        return sesion.abrir_turno(usuario, respuesta[0], str(uuid.uuid4()))
    except ErrorDominio as error:
        dialogos.mostrar_error(padre, str(error))
        return None


# --------------------------------------------------------------------------- pantalla


class EfectivoView(QWidget):
    """El cajón de esta caja: si está abierta, qué entró y salió, y los cierres anteriores."""

    salir_solicitado = Signal()
    #: Estado de la caja en una línea. Lo pinta la cabecera de la ventana.
    resumen_cambiado = Signal(str)

    def __init__(self, sesion: Sesion, padre: QWidget | None = None) -> None:
        super().__init__(padre)
        self._sesion = sesion
        #: Quien opera la caja. Lo fija la ventana.
        self.usuario: Usuario | None = None
        #: Cómo pedir el PIN de un administrador. Lo fija la ventana, para que se pida igual
        #: que en el resto del programa. Devuelve None si nadie autorizó.
        self.autorizar_admin: Callable[[str], Usuario | None] = lambda _accion: None
        #: El administrador que está mirando las cuentas, si lo hay: el propio usuario si es
        #: administrador, o quien puso su PIN en "Ver las cuentas". Se olvida al salir.
        self._visor: Usuario | None = None
        self._turno: TurnoCaja | None = None
        self._turnos: list[TurnoCaja] = []
        self._construir()

    # ------------------------------------------------------------------ construcción

    def _construir(self) -> None:
        columna = QVBoxLayout(self)
        columna.setContentsMargins(28, 22, 28, 18)
        columna.setSpacing(14)
        columna.addLayout(self._fila_de_estado())
        columna.addLayout(self._fila_de_acciones())

        self.panel_cuentas = self._tarjetas()
        columna.addWidget(self.panel_cuentas)
        self.aviso_ciego = QLabel(AVISO_A_CIEGAS)
        self.aviso_ciego.setObjectName("subtitulo")
        self.aviso_ciego.setWordWrap(True)
        columna.addWidget(self.aviso_ciego)

        # Una tabla sobre la otra, y no lado a lado: los cierres tienen seis columnas y a media
        # pantalla no cabían. La cajera no ve los cierres, y los movimientos ocupan todo.
        cuerpo = QVBoxLayout()
        cuerpo.setSpacing(14)
        self.tabla_movimientos = self._tabla(_COLUMNAS_MOVIMIENTOS, estirar=3)
        tablas.alinear_cabeceras(
            self.tabla_movimientos,
            (tablas.CENTRO, tablas.IZQUIERDA, tablas.DERECHA, tablas.IZQUIERDA, tablas.IZQUIERDA),
        )
        cuerpo.addWidget(
            self._envolver("Salidas y entradas de este turno", self.tabla_movimientos), stretch=1
        )
        self.tabla_cierres = self._tabla(_COLUMNAS_CIERRES, estirar=5)
        tablas.alinear_cabeceras(
            self.tabla_cierres,
            (
                tablas.IZQUIERDA,
                tablas.IZQUIERDA,
                tablas.DERECHA,
                tablas.DERECHA,
                tablas.IZQUIERDA,
                tablas.IZQUIERDA,
            ),
        )
        self.etiqueta_sugerido = QLabel()
        self.etiqueta_sugerido.setObjectName("subtitulo")
        self.boton_sugerido = QPushButton("Cambiar")
        self.boton_sugerido.setObjectName("botonSuave")
        self.boton_sugerido.setToolTip("El monto con que se propone abrir cada caja")
        self.boton_sugerido.clicked.connect(self.cambiar_monto_sugerido)
        self.panel_cierres = self._envolver(
            "Cierres anteriores", self.tabla_cierres, self.etiqueta_sugerido, self.boton_sugerido
        )
        cuerpo.addWidget(self.panel_cierres, stretch=1)
        columna.addLayout(cuerpo, stretch=1)

    def _fila_de_estado(self) -> QHBoxLayout:
        fila = QHBoxLayout()
        fila.setSpacing(10)
        textos = QVBoxLayout()
        textos.setSpacing(2)
        self.etiqueta_estado = QLabel()
        self.etiqueta_estado.setObjectName("tituloTarjeta")
        textos.addWidget(self.etiqueta_estado)
        self.detalle_estado = QLabel()
        self.detalle_estado.setObjectName("subtitulo")
        textos.addWidget(self.detalle_estado)
        fila.addLayout(textos, stretch=1)

        self.boton_ver_cuentas = QPushButton("Ver las cuentas")
        self.boton_ver_cuentas.setToolTip("Con el PIN de un administrador")
        self.boton_ver_cuentas.clicked.connect(self._ver_cuentas)
        fila.addWidget(self.boton_ver_cuentas)

        self.boton_abrir = QPushButton("Abrir la caja")
        self.boton_abrir.setObjectName("botonAccion")
        self.boton_abrir.clicked.connect(self.abrir)
        fila.addWidget(self.boton_abrir)

        self.boton_cerrar = QPushButton("Cerrar la caja")
        self.boton_cerrar.clicked.connect(self.cerrar)
        fila.addWidget(self.boton_cerrar)

        boton_actualizar = QPushButton("Actualizar")
        boton_actualizar.clicked.connect(self.recargar)
        fila.addWidget(boton_actualizar)
        return fila

    def _fila_de_acciones(self) -> QHBoxLayout:
        fila = QHBoxLayout()
        fila.setSpacing(10)
        self.boton_pago = QPushButton("Pago a proveedor")
        self.boton_pago.clicked.connect(lambda: self.anotar(TipoMovimiento.PAGO_PROVEEDOR))
        fila.addWidget(self.boton_pago)
        self.boton_retiro = QPushButton("Retiro")
        self.boton_retiro.setToolTip("Sacar efectivo de la caja. Pide el PIN de un administrador.")
        self.boton_retiro.clicked.connect(lambda: self.anotar(TipoMovimiento.RETIRO))
        fila.addWidget(self.boton_retiro)
        self.boton_ingreso = QPushButton("Ingreso de sencillo")
        self.boton_ingreso.clicked.connect(lambda: self.anotar(TipoMovimiento.INGRESO))
        fila.addWidget(self.boton_ingreso)
        fila.addStretch()
        return fila

    def _tarjetas(self) -> QWidget:
        """La cuenta, como en un cuaderno: cuatro renglones que suman lo que debería haber.

        Una tarjeta con los renglones y otra con el resultado en grande, en vez de cinco tarjetas
        en fila: así se lee como una suma, y a 1080 de ancho con la letra más grande cabe.
        """
        contenedor = QWidget()
        fila = QHBoxLayout(contenedor)
        fila.setContentsMargins(0, 0, 0, 0)
        fila.setSpacing(14)

        cuenta = QFrame()
        cuenta.setObjectName("tarjeta")
        estilos.aplicar_sombra(cuenta)
        rejilla = QGridLayout(cuenta)
        rejilla.setContentsMargins(20, 12, 20, 12)
        rejilla.setHorizontalSpacing(24)
        rejilla.setVerticalSpacing(4)
        renglones = ("Al abrir", "Ventas en efectivo", "Retiros y pagos", "Ingresos")
        valores = []
        for numero, rotulo in enumerate(renglones):
            etiqueta = QLabel(rotulo)
            etiqueta.setObjectName("subtitulo")
            rejilla.addWidget(etiqueta, numero, 0)
            valor = QLabel("—")
            valor.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            rejilla.addWidget(valor, numero, 1)
            valores.append(valor)
        rejilla.setColumnStretch(0, 1)
        self.valor_apertura, self.valor_ventas, self.valor_salidas, self.valor_ingresos = valores
        fila.addWidget(cuenta, stretch=3)

        resultado = QFrame()
        resultado.setObjectName("tarjeta")
        estilos.aplicar_sombra(resultado)
        columna = QVBoxLayout(resultado)
        columna.setContentsMargins(20, 12, 20, 12)
        columna.setSpacing(2)
        etiqueta = QLabel("DEBERÍA HABER")
        etiqueta.setObjectName("etiquetaTotal")
        columna.addWidget(etiqueta)
        self.valor_esperado = QLabel("—")
        self.valor_esperado.setObjectName("valorTotal")
        columna.addWidget(self.valor_esperado)
        columna.addStretch()
        fila.addWidget(resultado, stretch=2)
        return contenedor

    @staticmethod
    def _tabla(columnas: tuple[str, ...], estirar: int) -> QTableWidget:
        tabla = QTableWidget(0, len(columnas))
        tabla.setHorizontalHeaderLabels(columnas)
        tabla.verticalHeader().setVisible(False)
        tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tabla.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        tabla.setShowGrid(False)
        cabecera = tabla.horizontalHeader()
        for indice in range(len(columnas)):
            cabecera.setSectionResizeMode(indice, QHeaderView.ResizeMode.ResizeToContents)
        cabecera.setSectionResizeMode(estirar, QHeaderView.ResizeMode.Stretch)
        return tabla

    @staticmethod
    def _envolver(titulo: str, contenido: QWidget, *acciones: QWidget) -> QWidget:
        contenedor = QWidget()
        columna = QVBoxLayout(contenedor)
        columna.setContentsMargins(0, 0, 0, 0)
        columna.setSpacing(8)
        cabecera = QHBoxLayout()
        etiqueta = QLabel(titulo)
        etiqueta.setObjectName("tituloTarjeta")
        cabecera.addWidget(etiqueta)
        cabecera.addStretch()
        for accion in acciones:
            cabecera.addWidget(accion)
        columna.addLayout(cabecera)
        columna.addWidget(contenido, stretch=1)
        return contenedor

    # ------------------------------------------------------------------ datos

    @property
    def turno(self) -> TurnoCaja | None:
        return self._turno

    def al_entrar(self) -> None:
        """Al abrir la pantalla. Las cuentas se ven solo si quien opera es administrador."""
        self._visor = self.usuario if self.usuario is not None and self.usuario.es_admin else None
        self.recargar()

    def recargar(self) -> None:
        try:
            self._turno = self._sesion.turno_abierto(self._visor or self.usuario)
            self._turnos = self._sesion.turnos_recientes(self._visor) if self._visor else []
            sugerido = self._sesion.monto_sugerido()
        except ErrorDominio as error:
            dialogos.mostrar_error(self, str(error))
            return
        self._pintar(sugerido)

    def repintar(self) -> None:
        """Tras un cambio de tema: los colores de las diferencias van puestos a mano."""
        self._pintar_cuentas()
        self._pintar_cierres()

    # ------------------------------------------------------------------ acciones

    def abrir(self) -> None:
        if pedir_apertura(self._sesion, self.usuario, self) is not None:
            self.recargar()

    def anotar(self, tipo: TipoMovimiento) -> None:
        """Pago a proveedor, retiro o ingreso. El retiro pide el PIN de un administrador, y queda
        a su nombre: es quien se lleva la plata."""
        if self._turno is None:
            dialogos.mostrar_error(self, "La caja está cerrada. Ábrala antes de anotar efectivo.")
            return
        quien = self.usuario
        if tipo is TipoMovimiento.RETIRO:
            quien = self.autorizar_admin("anotar un retiro de efectivo")
            if quien is None:
                return

        textos = {
            TipoMovimiento.PAGO_PROVEEDOR: (
                "¿Cuánto se le pagó?", "Proveedor", True,
                "Queda anotado a su nombre, con el proveedor.",
            ),
            TipoMovimiento.RETIRO: (
                "¿Cuánto efectivo se saca de la caja?", "Motivo (opcional)", False,
                f"Queda anotado a nombre de {quien.nombre if quien else ''}.",
            ),
            TipoMovimiento.INGRESO: (
                "¿Cuánto efectivo se agrega a la caja?", "Motivo (opcional)", False, "",
            ),
        }
        pregunta, etiqueta, obligatorio, ayuda = textos[tipo]
        respuesta = DialogoMonto.pedir(
            NOMBRE_TIPO[tipo],
            pregunta,
            self,
            ayuda=ayuda,
            etiqueta_texto=etiqueta,
            texto_obligatorio=obligatorio,
            puede_ser_cero=False,
            texto_aceptar="Anotar",
        )
        if respuesta is None:
            return
        monto, motivo = respuesta
        try:
            self._sesion.registrar_movimiento(quien, tipo, monto, motivo, str(uuid.uuid4()))
        except ErrorDominio as error:
            dialogos.mostrar_error(self, str(error))
        self.recargar()

    def cerrar(self) -> None:
        """Cierra la caja con lo que se contó. A ciegas: no se enseña cuánto debería haber."""
        turno = self._turno
        if turno is None:
            return
        respuesta = DialogoMonto.pedir(
            f"Cerrar la caja {turno.caja}",
            "Cuente el efectivo del cajón. ¿Cuánto hay?",
            self,
            ayuda=(
                "Una vez cerrada no se puede cambiar. Para seguir vendiendo después, se vuelve a "
                "abrir con lo que quede en el cajón."
            ),
            etiqueta_texto="Nota (opcional)",
            texto_aceptar="Cerrar la caja",
        )
        if respuesta is None:
            return
        contado, nota = respuesta
        try:
            cerrado = self._sesion.cerrar_turno(self.usuario, turno.id, contado, nota or None)
        except ErrorDominio as error:
            dialogos.mostrar_error(self, str(error))
            self.recargar()
            return

        if cerrado.diferencia_clp is None:
            # Quien cerró no es administrador: el resultado no se le enseña (D-036).
            mensaje = f"Caja cerrada. Se anotaron {formatear_clp(contado)} contados."
        else:
            mensaje = (
                f"Caja cerrada.\n\nDebería haber: {formatear_clp(cerrado.esperado_clp)}\n"
                f"Contado: {formatear_clp(contado)}\n\n"
                f"{describir_diferencia(cerrado.diferencia_clp)}."
            )
        dialogos.mostrar_info(self, mensaje, "Cierre de caja")
        self.recargar()

    def _ver_cuentas(self) -> None:
        administrador = self.autorizar_admin("ver las cuentas del efectivo")
        if administrador is not None:
            self._visor = administrador
            self.recargar()

    def cambiar_monto_sugerido(self) -> None:
        administrador = self._visor or self.autorizar_admin("cambiar el monto de apertura")
        if administrador is None:
            return
        try:
            actual = self._sesion.monto_sugerido()
        except ErrorDominio:
            actual = None
        respuesta = DialogoMonto.pedir(
            "Monto de apertura",
            "¿Con cuánto efectivo debería partir cada caja?",
            self,
            ayuda="Se propone al abrir. Quien abre escribe lo que de verdad hay en el cajón.",
            valor_inicial=actual,
            texto_aceptar="Guardar",
        )
        if respuesta is None:
            return
        try:
            self._sesion.fijar_monto_sugerido(administrador, respuesta[0])
        except ErrorDominio as error:
            dialogos.mostrar_error(self, str(error))
        self.recargar()

    # ------------------------------------------------------------------ pintura

    def _pintar(self, sugerido: int | None) -> None:
        turno = self._turno
        abierta = turno is not None
        caja = self._sesion.caja or "Esta caja"
        if abierta:
            self.etiqueta_estado.setText(f"{caja} abierta")
            self.detalle_estado.setText(
                f"Desde las {turno.abierto_en:%H:%M} del {turno.abierto_en:%d/%m}, por "
                f"{turno.abierto_por_nombre or '—'}, con {formatear_clp(turno.apertura_clp)}."
            )
            self.resumen_cambiado.emit(f"{caja}  ·  abierta desde las {turno.abierto_en:%H:%M}")
        else:
            self.etiqueta_estado.setText(f"{caja} cerrada")
            self.detalle_estado.setText("Para cobrar, ábrala con el efectivo que hay en el cajón.")
            self.resumen_cambiado.emit(f"{caja}  ·  cerrada")

        self.boton_abrir.setVisible(not abierta)
        self.boton_cerrar.setVisible(abierta)
        for boton in (self.boton_pago, self.boton_retiro, self.boton_ingreso):
            boton.setEnabled(abierta)

        con_cuentas = self._visor is not None
        self.boton_ver_cuentas.setVisible(not con_cuentas)
        self.panel_cuentas.setVisible(con_cuentas and abierta)
        self.aviso_ciego.setVisible(not con_cuentas and abierta)
        self.panel_cierres.setVisible(con_cuentas)
        self.etiqueta_sugerido.setText(
            f"Apertura sugerida: {formatear_clp(sugerido)}"
            if sugerido is not None
            else "Sin monto de apertura sugerido"
        )

        self._pintar_cuentas()
        self._pintar_movimientos()
        self._pintar_cierres()

    def _pintar_cuentas(self) -> None:
        turno = self._turno
        if turno is None or turno.esperado_clp is None:
            for valor in (
                self.valor_apertura,
                self.valor_ventas,
                self.valor_salidas,
                self.valor_ingresos,
                self.valor_esperado,
            ):
                valor.setText("—")
            return
        self.valor_apertura.setText(formatear_clp(turno.apertura_clp))
        self.valor_ventas.setText(formatear_clp(turno.ventas_efectivo_clp or 0))
        self.valor_salidas.setText(f"−{formatear_clp(turno.retiros_clp + turno.pagos_clp)}")
        self.valor_ingresos.setText(f"+{formatear_clp(turno.ingresos_clp)}")
        self.valor_esperado.setText(formatear_clp(turno.esperado_clp))
        # En el color del texto y no en el verde del total de venta: lo que debería haber no es
        # algo que "salió bien". Negativo es imposible en un cajón, y se marca: alguna salida se
        # anotó mal.
        paleta = estilos.actual
        color = paleta.error if turno.esperado_clp < 0 else paleta.texto
        self.valor_esperado.setStyleSheet(f"color: {color};")

    def _pintar_movimientos(self) -> None:
        movimientos = list(reversed(self._turno.movimientos)) if self._turno else []
        tabla = self.tabla_movimientos
        tabla.setRowCount(len(movimientos))
        for fila, mov in enumerate(movimientos):
            celdas = (
                (mov.fecha_hora.strftime("%H:%M"), tablas.CENTRO),
                (_nombre_tipo(mov.tipo), tablas.IZQUIERDA),
                (_monto_con_signo(mov), tablas.DERECHA),
                (mov.motivo or "—", tablas.IZQUIERDA),
                (mov.usuario_nombre or "—", tablas.IZQUIERDA),
            )
            for columna, (texto, alineacion) in enumerate(celdas):
                celda = QTableWidgetItem(texto)
                celda.setTextAlignment(alineacion | Qt.AlignmentFlag.AlignVCenter)
                if columna == 3:
                    celda.setToolTip(texto)
                tabla.setItem(fila, columna, celda)

    def _pintar_cierres(self) -> None:
        tabla = self.tabla_cierres
        tabla.setRowCount(len(self._turnos))
        for fila, turno in enumerate(self._turnos):
            if turno.abierto:
                resultado, esperado, contado = "Abierta", "—", "—"
            else:
                resultado = describir_diferencia(turno.diferencia_clp) if turno.diferencia_clp is not None else "—"
                esperado = formatear_clp(turno.esperado_clp) if turno.esperado_clp is not None else "—"
                contado = formatear_clp(turno.contado_clp) if turno.contado_clp is not None else "—"
            celdas = (
                (turno.caja, tablas.IZQUIERDA),
                (texto_turno(turno), tablas.IZQUIERDA),
                (esperado, tablas.DERECHA),
                (contado, tablas.DERECHA),
                (resultado, tablas.IZQUIERDA),
                (turno.cerrado_por_nombre or "—", tablas.IZQUIERDA),
            )
            for columna, (texto, alineacion) in enumerate(celdas):
                celda = QTableWidgetItem(texto)
                celda.setTextAlignment(alineacion | Qt.AlignmentFlag.AlignVCenter)
                if columna == 4 and not turno.abierto:
                    celda.setForeground(QBrush(QColor(color_diferencia(turno.diferencia_clp))))
                    if turno.nota:
                        celda.setToolTip(f"Nota: {turno.nota}")
                tabla.setItem(fila, columna, celda)
