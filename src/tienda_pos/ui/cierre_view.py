"""Cierre diario de una caja (fase 18).

**BORRADOR, SIN CONECTAR (2026-09-24).** La fase 18 se cortó aquí a pedido de Santiago. Esta
pantalla no está en la barra lateral ni en la ventana, y no tiene pruebas: se escribió y se
comprobó que importa, nada más. Lo que falta está en `docs/PLAN.md`, fase 18.

Lo que pidió el cliente: por caja, cuánto se vendió y con qué se pagó —efectivo, débito y
crédito por separado—, qué empleado vendió cuánto, y la lista de ventas con los productos de
cada una. Reservada al administrador, como las ventas del día (pregunta H4 pendiente).

**Es un informe que se calcula al pedirlo, no un registro.** No cierra nada ni bloquea la caja:
se puede mirar a media tarde y volver a mirar después. Lo dice al pie, para que nadie crea que
ha "cerrado" algo. El dinero del cajón —fondo inicial, conteo, diferencia— es la fase 19, y va
detrás de un interruptor porque el cliente no contestó claro si lo quiere.
"""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDateEdit,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..domain.errors import ErrorDominio
from ..domain.models import CierreCaja, MedioPago
from ..red.sesion import Sesion
from ..services import reportes
from ..utils.money import formatear_clp
from . import dialogos, estilos, tablas
from .venta_view import NOMBRE_MEDIO
from .widgets.desplegable import Desplegable

_DIAS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
_MESES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)

#: Columnas del árbol de ventas. Las mismas sirven para la venta y para cada una de sus líneas:
#: qué, cuántos, quién, cómo pagó y cuánto. Una línea deja en blanco lo que no le toca.
_COLUMNAS_VENTAS = ("Venta / producto", "Cant.", "Atendió", "Medio", "Total")
_COLUMNAS_EMPLEADOS = ("Empleado", "Ventas", "Artículos", "Total")

SIN_CAJA = "Sin caja registrada"
SIN_USUARIO = "Sin usuario (antes de la actualización)"


def fecha_larga(dia: date) -> str:
    """'martes 24 de septiembre'. A mano y no con la configuración regional de Windows, que en
    un equipo en inglés diría 'Tuesday'."""
    return f"{_DIAS[dia.weekday()]} {dia.day} de {_MESES[dia.month - 1]}"


def nombre_caja(caja: str | None) -> str:
    return caja if caja is not None else SIN_CAJA


class CierreView(QWidget):
    """El cierre del día de una caja, con sus ventas desplegables."""

    salir_solicitado = Signal()
    #: Caja, día y cuántas ventas. Lo pinta la cabecera de la ventana.
    resumen_cambiado = Signal(str)

    def __init__(self, sesion: Sesion, padre: QWidget | None = None) -> None:
        super().__init__(padre)
        self._sesion = sesion
        self._cierre: CierreCaja | None = None
        #: La caja que se está mirando. Empieza siendo la de este equipo.
        self._caja: str | None = sesion.caja
        self._construir()

    # ------------------------------------------------------------------ construcción

    def _construir(self) -> None:
        columna = QVBoxLayout(self)
        columna.setContentsMargins(28, 22, 28, 18)
        columna.setSpacing(16)
        columna.addLayout(self._fila_de_filtros())
        columna.addLayout(self._tarjetas())

        cuerpo = QHBoxLayout()
        cuerpo.setSpacing(16)
        cuerpo.addWidget(self._panel_ventas(), stretch=3)
        cuerpo.addWidget(self._panel_empleados(), stretch=2)
        columna.addLayout(cuerpo, stretch=1)

        pie = QLabel(
            "Este informe se calcula al pedirlo. No cierra nada ni bloquea la caja: puede "
            "consultarse las veces que haga falta."
        )
        pie.setObjectName("subtitulo")
        pie.setWordWrap(True)
        columna.addWidget(pie)

    def _fila_de_filtros(self) -> QHBoxLayout:
        fila = QHBoxLayout()
        fila.setSpacing(10)

        fila.addWidget(QLabel("Día"))
        self.selector_dia = QDateEdit()
        self.selector_dia.setCalendarPopup(True)
        self.selector_dia.setDisplayFormat("dd/MM/yyyy")
        self.selector_dia.setMinimumWidth(150)
        # Se puede mirar un día anterior: con la pregunta de la medianoche sin responder (H10),
        # quien cierra a la una de la madrugada querrá ver el de "ayer".
        self.selector_dia.dateChanged.connect(lambda _fecha: self.recargar())
        fila.addWidget(self.selector_dia)

        fila.addSpacing(14)
        self.etiqueta_caja = QLabel("Caja")
        fila.addWidget(self.etiqueta_caja)
        self.selector_caja = Desplegable()
        self.selector_caja.setMinimumWidth(200)
        self.selector_caja.activated.connect(self._elegir_caja)
        fila.addWidget(self.selector_caja)

        fila.addStretch()

        self.boton_desplegar = QPushButton("Ver los productos de todas")
        self.boton_desplegar.clicked.connect(self._alternar_despliegue)
        fila.addWidget(self.boton_desplegar)

        boton_actualizar = QPushButton("Actualizar")
        boton_actualizar.clicked.connect(self.recargar)
        fila.addWidget(boton_actualizar)
        return fila

    def _tarjetas(self) -> QHBoxLayout:
        fila = QHBoxLayout()
        fila.setSpacing(16)
        self.valor_total, self.detalle_total, tarjeta = self._tarjeta("Total vendido", "valorTotal")
        fila.addWidget(tarjeta, stretch=4)

        #: Una tarjeta por medio, con su color (D-034): lo que el cliente pidió ver primero.
        self._tarjetas_medio: dict[MedioPago | None, tuple[QLabel, QLabel, QFrame]] = {}
        for medio in (*MedioPago, None):
            titulo = NOMBRE_MEDIO[medio] if medio else "Sin registrar"
            valor, detalle, tarjeta = self._tarjeta(titulo, "valorSubtotal")
            self._tarjetas_medio[medio] = (valor, detalle, tarjeta)
            fila.addWidget(tarjeta, stretch=3)
        return fila

    @staticmethod
    def _tarjeta(titulo: str, estilo_valor: str) -> tuple[QLabel, QLabel, QFrame]:
        tarjeta = QFrame()
        tarjeta.setObjectName("tarjeta")
        estilos.aplicar_sombra(tarjeta)
        columna = QVBoxLayout(tarjeta)
        columna.setContentsMargins(20, 14, 20, 14)
        columna.setSpacing(2)

        etiqueta = QLabel(titulo.upper())
        etiqueta.setObjectName("etiquetaTotal")
        columna.addWidget(etiqueta)
        valor = QLabel("—")
        valor.setObjectName(estilo_valor)
        columna.addWidget(valor)
        detalle = QLabel("")
        detalle.setObjectName("subtitulo")
        columna.addWidget(detalle)
        return valor, detalle, tarjeta

    def _panel_ventas(self) -> QWidget:
        self.arbol_ventas = QTreeWidget()
        self.arbol_ventas.setColumnCount(len(_COLUMNAS_VENTAS))
        self.arbol_ventas.setHeaderLabels(_COLUMNAS_VENTAS)
        self.arbol_ventas.setRootIsDecorated(True)
        self.arbol_ventas.setUniformRowHeights(True)
        self.arbol_ventas.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.arbol_ventas.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        cabecera = self.arbol_ventas.header()
        cabecera.setStretchLastSection(False)
        cabecera.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for columna in range(1, len(_COLUMNAS_VENTAS)):
            cabecera.setSectionResizeMode(columna, QHeaderView.ResizeMode.ResizeToContents)
        return self._envolver("Ventas de la caja", self.arbol_ventas)

    def _panel_empleados(self) -> QWidget:
        self.tabla_empleados = QTableWidget(0, len(_COLUMNAS_EMPLEADOS))
        self.tabla_empleados.setHorizontalHeaderLabels(_COLUMNAS_EMPLEADOS)
        self.tabla_empleados.verticalHeader().setVisible(False)
        self.tabla_empleados.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla_empleados.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.tabla_empleados.setShowGrid(False)
        cabecera = self.tabla_empleados.horizontalHeader()
        cabecera.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for columna in range(1, len(_COLUMNAS_EMPLEADOS)):
            cabecera.setSectionResizeMode(columna, QHeaderView.ResizeMode.ResizeToContents)
        tablas.alinear_cabeceras(
            self.tabla_empleados,
            (tablas.IZQUIERDA, tablas.CENTRO, tablas.CENTRO, tablas.DERECHA),
        )
        return self._envolver("Por empleado", self.tabla_empleados)

    @staticmethod
    def _envolver(titulo: str, contenido: QWidget) -> QWidget:
        contenedor = QWidget()
        columna = QVBoxLayout(contenedor)
        columna.setContentsMargins(0, 0, 0, 0)
        columna.setSpacing(8)
        etiqueta = QLabel(titulo)
        etiqueta.setObjectName("tituloTarjeta")
        columna.addWidget(etiqueta)
        columna.addWidget(contenido, stretch=1)
        return contenedor

    # ------------------------------------------------------------------ datos

    def al_entrar(self) -> None:
        """Al abrir la pantalla: el día de hoy y la caja de este equipo."""
        self._caja = self._sesion.caja
        self.selector_dia.blockSignals(True)
        hoy = reportes.dia_comercial()
        self.selector_dia.setMaximumDate(QDate(hoy.year, hoy.month, hoy.day))
        self.selector_dia.setDate(QDate(hoy.year, hoy.month, hoy.day))
        self.selector_dia.blockSignals(False)
        self.recargar()

    @property
    def dia(self) -> date:
        return self.selector_dia.date().toPython()

    def recargar(self) -> None:
        try:
            self._cierre = self._sesion.cierre_de_caja(self.dia, self._caja)
        except ErrorDominio as error:
            dialogos.mostrar_error(self, str(error))
            return
        self._pintar()

    def repintar(self) -> None:
        """Tras un cambio de tema: los colores de los medios van puestos a mano."""
        if self._cierre is not None:
            self._pintar()

    def _elegir_caja(self, indice: int) -> None:
        self._caja = self.selector_caja.itemData(indice)
        self.recargar()

    def _alternar_despliegue(self) -> None:
        todas_abiertas = all(
            self.arbol_ventas.topLevelItem(i).isExpanded()
            for i in range(self.arbol_ventas.topLevelItemCount())
        )
        if todas_abiertas:
            self.arbol_ventas.collapseAll()
        else:
            self.arbol_ventas.expandAll()
        self._actualizar_boton_despliegue()

    def _actualizar_boton_despliegue(self) -> None:
        cuantas = self.arbol_ventas.topLevelItemCount()
        abiertas = cuantas and all(
            self.arbol_ventas.topLevelItem(i).isExpanded() for i in range(cuantas)
        )
        self.boton_desplegar.setText(
            "Ocultar los productos" if abiertas else "Ver los productos de todas"
        )
        self.boton_desplegar.setEnabled(bool(self._cierre and self._cierre.ventas))

    # ------------------------------------------------------------------ pintura

    def _pintar(self) -> None:
        cierre = self._cierre
        assert cierre is not None
        self._pintar_selector_de_caja(cierre)
        self._pintar_tarjetas(cierre)
        self._pintar_ventas(cierre)
        self._pintar_empleados(cierre)

        cantidad = cierre.cantidad_ventas
        ventas = "1 venta" if cantidad == 1 else f"{cantidad} ventas"
        self.resumen_cambiado.emit(
            f"{nombre_caja(cierre.caja)}  ·  {fecha_larga(cierre.dia)}  ·  {ventas}"
            f"  ·  {cierre.articulos} artículos"
        )

    def _pintar_selector_de_caja(self, cierre: CierreCaja) -> None:
        """El desplegable solo aparece si ese día vendió más de una caja.

        La caja que se mira entra en la lista aunque no haya vendido, para que un día sin ventas
        diga "Caja 1: $0" en vez de saltar sola a la otra.
        """
        opciones = list(cierre.cajas_del_dia)
        if cierre.caja not in opciones:
            opciones.insert(0, cierre.caja)
        self.selector_caja.blockSignals(True)
        self.selector_caja.clear()
        for caja in opciones:
            self.selector_caja.addItem(nombre_caja(caja), caja)
        self.selector_caja.setCurrentIndex(opciones.index(cierre.caja))
        self.selector_caja.blockSignals(False)
        varias = len(opciones) > 1
        self.selector_caja.setVisible(varias)
        self.etiqueta_caja.setVisible(varias)

    def _pintar_tarjetas(self, cierre: CierreCaja) -> None:
        self.valor_total.setText(formatear_clp(cierre.total_clp))
        self.detalle_total.setText(
            f"{cierre.cantidad_ventas} ventas · {cierre.articulos} artículos"
        )
        por_medio = {fila.medio_pago: fila for fila in cierre.por_medio}
        for medio, (valor, detalle, tarjeta) in self._tarjetas_medio.items():
            fila = por_medio.get(medio)
            # "Sin registrar" solo existe si hay ventas de antes de registrar el medio.
            tarjeta.setVisible(fila is not None)
            if fila is None:
                continue
            valor.setText(formatear_clp(fila.total_clp))
            valor.setStyleSheet(f"color: {estilos.color_medio(medio)};")
            detalle.setText("1 venta" if fila.ventas == 1 else f"{fila.ventas} ventas")

    def _pintar_ventas(self, cierre: CierreCaja) -> None:
        self.arbol_ventas.clear()
        suave = QBrush(QColor(estilos.actual.texto_suave))
        if not cierre.ventas:
            vacio = QTreeWidgetItem(["Esta caja no tiene ventas ese día."])
            vacio.setForeground(0, suave)
            vacio.setFlags(Qt.ItemFlag.NoItemFlags)
            self.arbol_ventas.addTopLevelItem(vacio)
            vacio.setFirstColumnSpanned(True)
            self._actualizar_boton_despliegue()
            return

        negrita = QFont(self.arbol_ventas.font())
        negrita.setBold(True)
        for venta in cierre.ventas:
            medio = NOMBRE_MEDIO[venta.medio_pago] if venta.medio_pago else "Sin registrar"
            fila = QTreeWidgetItem(
                [
                    f"N° {venta.folio}  ·  {venta.fecha_hora.strftime('%H:%M')}",
                    str(venta.cantidad_articulos),
                    venta.usuario_nombre or "Sin usuario",
                    medio,
                    formatear_clp(venta.total_clp),
                ]
            )
            fila.setTextAlignment(1, Qt.AlignmentFlag.AlignCenter)
            fila.setTextAlignment(4, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            # El total en negrita: con las líneas desplegadas en medio, la columna de las ventas
            # se sigue leyendo en vertical.
            fila.setFont(4, negrita)
            fila.setForeground(3, QBrush(QColor(estilos.color_medio(venta.medio_pago))))
            for linea in venta.lineas:
                hija = QTreeWidgetItem(
                    [linea.nombre, str(linea.cantidad), "", "", formatear_clp(linea.subtotal_clp)]
                )
                hija.setTextAlignment(1, Qt.AlignmentFlag.AlignCenter)
                hija.setTextAlignment(
                    4, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )
                for columna in range(len(_COLUMNAS_VENTAS)):
                    hija.setForeground(columna, suave)
                fila.addChild(hija)
            self.arbol_ventas.addTopLevelItem(fila)
        # Todas plegadas al abrir: doscientas ventas desplegadas no las lee nadie.
        self.arbol_ventas.collapseAll()
        self._actualizar_boton_despliegue()

    def _pintar_empleados(self, cierre: CierreCaja) -> None:
        filas = cierre.por_empleado
        self.tabla_empleados.setRowCount(len(filas))
        for indice, fila in enumerate(filas):
            celdas = (
                (fila.nombre or SIN_USUARIO, Qt.AlignmentFlag.AlignLeft),
                (str(fila.ventas), Qt.AlignmentFlag.AlignCenter),
                (str(fila.articulos), Qt.AlignmentFlag.AlignCenter),
                (formatear_clp(fila.total_clp), Qt.AlignmentFlag.AlignRight),
            )
            for columna, (texto, alineacion) in enumerate(celdas):
                celda = QTableWidgetItem(texto)
                celda.setTextAlignment(alineacion | Qt.AlignmentFlag.AlignVCenter)
                self.tabla_empleados.setItem(indice, columna, celda)
