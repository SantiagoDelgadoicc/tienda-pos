"""Administración del catálogo: alta, edición y baja de productos.

Reservada al administrador. La comprobación de permisos no vive aquí sino en la capa de
servicios: ocultar un botón no es control de acceso.
"""

from __future__ import annotations


from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QCheckBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..domain.errors import ErrorDominio, ProductoNoEncontrado
from ..domain.models import Producto, Usuario
from ..red.sesion import Sesion
from ..utils.money import formatear_clp, formatear_peso, parsear_clp
from . import dialogos, movimiento, tablas

_COLUMNAS = ("Código de barras", "Producto", "Precio", "Stock")

# Umbral por debajo del cual el stock se muestra en rojo. Es un aviso visual, no una regla
# de negocio: el cliente todavía no ha dicho cuándo considera que le falta un producto.
_STOCK_BAJO = 5


class DialogoProducto(QDialog):
    """Formulario de alta y edición de un producto."""

    def __init__(self, padre: QWidget | None = None, producto: Producto | None = None) -> None:
        super().__init__(padre)
        movimiento.aparecer_al_abrir(self)
        self._producto = producto
        self.setWindowTitle("Editar producto" if producto else "Nuevo producto")
        self.setMinimumWidth(430)

        columna = QVBoxLayout(self)
        columna.setContentsMargins(26, 24, 26, 20)
        columna.setSpacing(8)

        columna.addWidget(QLabel("Código de barras"))
        self.campo_codigo = QLineEdit(producto.codigo_barras if producto else "")
        self.campo_codigo.setPlaceholderText("Escanéelo con el lector o escríbalo")
        columna.addWidget(self.campo_codigo)
        nota_codigo = QLabel("Si no tiene código, como el pan, déjelo vacío: el sistema le pone uno.")
        nota_codigo.setObjectName("subtitulo")
        nota_codigo.setWordWrap(True)
        columna.addWidget(nota_codigo)

        columna.addWidget(QLabel("Nombre del producto"))
        self.campo_nombre = QLineEdit(producto.nombre if producto else "")
        columna.addWidget(self.campo_nombre)

        # Venta por peso (D-037): el precio es el del kilo y en la caja se teclean los gramos.
        self.casilla_peso = QCheckBox("Se vende por peso (pan, pollo, jamón...)")
        self.casilla_peso.setChecked(bool(producto and producto.por_peso))
        self.casilla_peso.toggled.connect(self._rotular)
        columna.addWidget(self.casilla_peso)

        self.rotulo_precio = QLabel("Precio de venta")
        columna.addWidget(self.rotulo_precio)
        self.campo_precio = QLineEdit(str(producto.precio_clp) if producto else "")
        self.campo_precio.setPlaceholderText("Solo el número, por ejemplo 1290")
        columna.addWidget(self.campo_precio)

        self.rotulo_stock = QLabel("Stock")
        columna.addWidget(self.rotulo_stock)
        self.campo_stock = QLineEdit(str(producto.stock) if producto else "0")
        # El mínimo es cero, o el stock negativo que ya tenía (D-009): si no, el validador daría
        # por inválido lo que el propio formulario muestra.
        minimo = min(0, producto.stock) if producto else 0
        self.campo_stock.setValidator(QIntValidator(minimo, 9_999_999, self))
        columna.addWidget(self.campo_stock)
        self._rotular(self.casilla_peso.isChecked())

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

        # Al crear, el foco va al código porque lo normal es escanearlo. Al editar va al
        # precio, porque cambiar precios es el 90% de las ediciones reales.
        (self.campo_precio if producto else self.campo_codigo).setFocus()

    def _rotular(self, por_peso: bool) -> None:
        """Los rótulos dicen en qué unidad va cada número, que es lo fácil de confundir."""
        if por_peso:
            self.rotulo_precio.setText("Precio de un kilo")
            self.rotulo_stock.setText("Stock en gramos  (no impide vender)")
        else:
            self.rotulo_precio.setText("Precio de venta")
            self.rotulo_stock.setText("Stock")

    def _validar(self) -> None:
        """Valida el formato antes de cerrar; las reglas de negocio las revisa el servicio."""
        if not self.campo_nombre.text().strip():
            return self._fallar("Escriba el nombre del producto.")
        try:
            precio = parsear_clp(self.campo_precio.text())
        except ValueError:
            return self._fallar("El precio debe ser un número, por ejemplo 1290.")
        if precio < 0:
            return self._fallar("El precio no puede ser negativo.")
        self.accept()

    def _fallar(self, mensaje: str) -> None:
        self.error.setText(mensaje)
        self.error.show()

    @property
    def datos(self) -> tuple[str, str, int, int | None, bool]:
        """Lo escrito. Al editar, el stock es None si no se tocó: así el servicio conserva el
        de la base, que pudo bajar con las ventas mientras el formulario estaba abierto."""
        texto_stock = self.campo_stock.text().strip()
        if self._producto is not None and texto_stock == str(self._producto.stock):
            stock = None
        else:
            stock = int(texto_stock or 0)
        return (
            self.campo_codigo.text().strip(),
            self.campo_nombre.text().strip(),
            parsear_clp(self.campo_precio.text()),
            stock,
            self.casilla_peso.isChecked(),
        )


class DialogoStock(QDialog):
    """Ajuste rápido del stock de un producto.

    Existe porque contar mercadería y corregir el sistema es lo que más se repite en una
    tienda, y hacerlo por el formulario completo obligaba a pasar por el código de barras, el
    nombre y el precio para tocar un número. Aquí solo está el número, con los saltos que se
    usan de verdad al recibir un pedido.

    No cambia nada más del producto: la vista le pasa al servicio el código, el nombre y el
    precio que ya tenía.
    """

    #: Saltos de los botones rápidos. Van de menor a mayor y en los dos sentidos.
    _SALTOS = (-10, -1, 1, 10)
    #: Los mismos para un producto por peso, en gramos: un kilo y cien gramos (D-037).
    _SALTOS_PESO = (-1000, -100, 100, 1000)

    def __init__(self, producto: Producto, padre: QWidget | None = None) -> None:
        super().__init__(padre)
        movimiento.aparecer_al_abrir(self)
        self._producto = producto
        self.setWindowTitle("Ajustar stock")
        self.setMinimumWidth(420)

        columna = QVBoxLayout(self)
        columna.setContentsMargins(26, 24, 26, 20)
        columna.setSpacing(6)

        titulo = QLabel("Ajustar stock")
        titulo.setObjectName("tituloPantalla")
        columna.addWidget(titulo)

        nombre = QLabel(producto.nombre)
        nombre.setObjectName("subtitulo")
        nombre.setWordWrap(True)
        columna.addWidget(nombre)
        columna.addSpacing(14)

        self._por_peso = producto.por_peso
        saltos = self._SALTOS_PESO if self._por_peso else self._SALTOS
        actual = QLabel(
            f"AHORA HAY {formatear_peso(producto.stock)}" if self._por_peso
            else f"AHORA HAY {producto.stock}"
        )
        actual.setObjectName("etiquetaTotal")
        columna.addWidget(actual)
        columna.addSpacing(6)

        fila = QHBoxLayout()
        fila.setSpacing(8)
        for salto in saltos[:2]:
            fila.addWidget(self._boton_salto(salto))

        self.campo = QLineEdit(str(producto.stock))
        # Como en el formulario: cero, o el negativo que ya tenía. Sin eso, Enter no hace nada
        # sobre un stock negativo, porque Qt no confirma un texto que su validador rechaza.
        self._minimo = min(0, producto.stock)
        self.campo.setValidator(QIntValidator(self._minimo, 9_999_999, self))
        self.campo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.campo.setMinimumWidth(110)
        self.campo.textChanged.connect(self._actualizar_resumen)
        self.campo.returnPressed.connect(self.accept)
        fila.addWidget(self.campo, stretch=1)

        for salto in saltos[2:]:
            fila.addWidget(self._boton_salto(salto))
        columna.addLayout(fila)
        columna.addSpacing(10)

        self.resumen = QLabel()
        self.resumen.setObjectName("subtitulo")
        self.resumen.setAlignment(Qt.AlignmentFlag.AlignCenter)
        columna.addWidget(self.resumen)
        columna.addSpacing(6)

        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        botones.button(QDialogButtonBox.StandardButton.Save).setText("Guardar")
        botones.button(QDialogButtonBox.StandardButton.Save).setObjectName("botonAccion")
        botones.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        columna.addWidget(botones)

        self._actualizar_resumen()
        self.campo.setFocus()
        self.campo.selectAll()

    def _boton_salto(self, salto: int) -> QPushButton:
        boton = QPushButton(f"+{salto}" if salto > 0 else str(salto))
        boton.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        boton.setFixedWidth(64)
        boton.clicked.connect(lambda _=False, s=salto: self._sumar(s))
        return boton

    def _sumar(self, salto: int) -> None:
        # El tope de abajo es cero, o el negativo que ya tenía (D-009): restar nunca lo deja
        # más negativo, y un −1 sobre −3 no puede saltar a cero, que sería sumar tres.
        self.campo.setText(str(max(self._minimo, self.stock + salto)))

    def _actualizar_resumen(self) -> None:
        diferencia = self.stock - self._producto.stock
        if diferencia == 0:
            self.resumen.setText("Sin cambios")
        elif self._por_peso:
            # El número del campo son gramos: el resumen lo dice en kilos para que se lea.
            verbo = "Entran" if diferencia > 0 else "Salen"
            self.resumen.setText(f"{verbo} {formatear_peso(abs(diferencia))}  ·  gramos en el campo")
        else:
            verbo = "Entran" if diferencia > 0 else "Salen"
            if abs(diferencia) == 1:
                verbo = verbo[:-1]  # "Entra 1 unidad", no "Entran 1 unidades"
            unidades = "unidad" if abs(diferencia) == 1 else "unidades"
            self.resumen.setText(f"{verbo} {abs(diferencia)} {unidades}")

    @property
    def stock(self) -> int:
        """Lo escrito, o el stock actual si el campo quedó vacío."""
        texto = self.campo.text().strip()
        return int(texto) if texto else self._producto.stock


class ProductosView(QWidget):
    """Listado y mantenimiento del catálogo."""

    salir_solicitado = Signal()
    #: Cuántos productos hay y cuántos se están mostrando. Lo pinta la cabecera de la
    #: ventana: en la fila de acciones no cabía junto al buscador y a cinco botones.
    resumen_cambiado = Signal(str)

    def __init__(self, sesion: Sesion, padre: QWidget | None = None) -> None:
        super().__init__(padre)
        self._sesion = sesion
        self.usuario: Usuario | None = None
        self._productos: list[Producto] = []

        self._construir()

    def _construir(self) -> None:
        columna = QVBoxLayout(self)
        columna.setContentsMargins(28, 22, 28, 24)
        columna.setSpacing(16)

        fila = QHBoxLayout()
        fila.setSpacing(10)

        self.campo_filtro = QLineEdit()
        self.campo_filtro.setObjectName("campoBusqueda")
        self.campo_filtro.setPlaceholderText("Filtrar por nombre o código")
        # Sin mínimo, los cinco botones de la fila le dejaban un hueco donde no cabía ni el
        # texto de ayuda.
        self.campo_filtro.setMinimumWidth(280)
        self.campo_filtro.setClearButtonEnabled(True)
        self.campo_filtro.textChanged.connect(self._pintar)
        fila.addWidget(self.campo_filtro, stretch=1)

        for texto, destino in (
            ("Nuevo producto", self.crear),
            ("Editar", self.editar),
            ("Stock", self.ajustar_stock),
            ("Pendientes", self.ver_pendientes),
        ):
            boton = QPushButton(texto)
            # Dar de alta es la acción de la pantalla: va rellena y las demás de
            # contorno, que es lo que le da ritmo a una fila de botones iguales.
            if texto == "Nuevo producto":
                boton.setObjectName("botonAccion")
            boton.clicked.connect(destino)
            fila.addWidget(boton)

        self.boton_eliminar = QPushButton("Dar de baja")
        self.boton_eliminar.setObjectName("botonPeligro")
        self.boton_eliminar.clicked.connect(self.dar_de_baja)
        fila.addWidget(self.boton_eliminar)

        columna.addLayout(fila)

        self.tabla = QTableWidget(0, len(_COLUMNAS))
        self.tabla.setHorizontalHeaderLabels(_COLUMNAS)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.setShowGrid(False)
        self.tabla.doubleClicked.connect(self.editar)

        cabecera = self.tabla.horizontalHeader()
        cabecera.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        cabecera.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        cabecera.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        cabecera.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        tablas.alinear_cabeceras(
            self.tabla, (tablas.IZQUIERDA, tablas.IZQUIERDA, tablas.DERECHA, tablas.CENTRO)
        )
        columna.addWidget(self.tabla, stretch=1)

    # ------------------------------------------------------------------ datos

    def recargar(self) -> None:
        self._productos = self._sesion.listar_productos()
        self._pintar()
        self.campo_filtro.setFocus()

    def repintar(self) -> None:
        """Vuelve a pintar la tabla tras un cambio de tema.

        El rojo del stock bajo se fija celda a celda, así que la hoja de estilos no lo
        alcanza y quedaría con el tono del tema anterior.
        """
        self._pintar()

    def _visibles(self) -> list[Producto]:
        texto = self.campo_filtro.text().strip().lower()
        if not texto:
            return self._productos
        return [
            p
            for p in self._productos
            if texto in p.nombre.lower() or texto in p.codigo_barras.lower()
        ]

    def _pintar(self) -> None:
        from PySide6.QtGui import QBrush, QColor

        from . import estilos

        visibles = self._visibles()
        rojo = QBrush(QColor(estilos.actual.error))
        # Vaciando antes de llenar (fase 23): refiltrar o volver a la pantalla con el catálogo
        # de la tienda congelaba la caja minutos. Ver `tablas.rellenar`.
        with tablas.rellenar(self.tabla, len(visibles)):
            for fila, producto in enumerate(visibles):
                self.tabla.setItem(fila, 0, QTableWidgetItem(producto.codigo_barras))
                self.tabla.setItem(fila, 1, QTableWidgetItem(producto.nombre))

                texto_precio = formatear_clp(producto.precio_clp)
                precio = QTableWidgetItem(
                    f"{texto_precio}/kg" if producto.por_peso else texto_precio
                )
                precio.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.tabla.setItem(fila, 2, precio)

                stock = QTableWidgetItem(
                    formatear_peso(producto.stock) if producto.por_peso else str(producto.stock)
                )
                stock.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                # El stock de un producto por peso no impide vender: no se marca como bajo.
                if not producto.por_peso and producto.stock <= _STOCK_BAJO:
                    stock.setForeground(rojo)
                self.tabla.setItem(fila, 3, stock)

        total = len(self._productos)
        mostrados = len(visibles)
        self.resumen_cambiado.emit(
            f"{total} productos en el catálogo"
            if total == mostrados
            else f"{mostrados} de {total} productos, filtrados"
        )

    def _seleccionado(self) -> Producto | None:
        fila = self.tabla.currentRow()
        visibles = self._visibles()
        if fila < 0 or fila >= len(visibles):
            return None
        return visibles[fila]

    # ------------------------------------------------------------------ acciones

    def crear(self) -> None:
        dialogo = DialogoProducto(self)
        if not dialogo.exec():
            return
        codigo, nombre, precio, stock, por_peso = dialogo.datos
        try:
            self._sesion.crear_producto(self.usuario, codigo, nombre, precio, stock, por_peso)
        except ErrorDominio as error:
            dialogos.mostrar_error(self, str(error))
            return
        self.recargar()

    def _al_dia(self, producto: Producto) -> Producto | None:
        """El producto como está ahora en la base, no como se cargó la lista.

        La lista se carga al entrar en la pantalla, y las cajas siguen vendiendo mientras
        tanto: un formulario abierto con esos datos mostraría un stock que ya no es (fase 22).
        """
        try:
            return self._sesion.consultar_por_codigo(
                producto.codigo_barras, registrar_faltante=False
            )
        except ProductoNoEncontrado:
            dialogos.mostrar_error(
                self, f"{producto.nombre} ya no está en el catálogo. Se actualizó la lista."
            )
        except ErrorDominio as error:
            dialogos.mostrar_error(self, str(error))
        self.recargar()
        return None

    def editar(self) -> None:
        producto = self._seleccionado()
        if producto is None:
            dialogos.mostrar_error(self, "Seleccione primero un producto de la lista.")
            return
        producto = self._al_dia(producto)
        if producto is None:
            return

        dialogo = DialogoProducto(self, producto)
        if not dialogo.exec():
            return
        codigo, nombre, precio, stock, por_peso = dialogo.datos
        try:
            self._sesion.actualizar_producto(
                self.usuario, producto.id, codigo, nombre, precio, stock, por_peso
            )
        except ErrorDominio as error:
            dialogos.mostrar_error(self, str(error))
            return
        self.recargar()

    def ajustar_stock(self) -> None:
        """Cambia solo la cantidad del producto seleccionado."""
        producto = self._seleccionado()
        if producto is None:
            dialogos.mostrar_error(self, "Seleccione primero un producto de la lista.")
            return
        producto = self._al_dia(producto)
        if producto is None:
            return

        dialogo = DialogoStock(producto, self)
        if not dialogo.exec() or dialogo.stock == producto.stock:
            return

        try:
            self._sesion.actualizar_producto(
                self.usuario,
                producto.id,
                producto.codigo_barras,
                producto.nombre,
                producto.precio_clp,
                dialogo.stock,
            )
        except ErrorDominio as error:
            dialogos.mostrar_error(self, str(error))
            return

        self.recargar()
        # Recargar deshace la selección, y lo normal al contar mercadería es ajustar varios
        # productos seguidos: devolver la fila donde estaba ahorra buscarla otra vez.
        self.seleccionar_codigo(producto.codigo_barras)

    def seleccionar_codigo(self, codigo: str) -> None:
        """Deja seleccionada la fila de ese código, si sigue a la vista."""
        for fila, producto in enumerate(self._visibles()):
            if producto.codigo_barras == codigo:
                self.tabla.selectRow(fila)
                self.tabla.scrollToItem(self.tabla.item(fila, 0))
                return

    def dar_de_baja(self) -> None:
        producto = self._seleccionado()
        if producto is None:
            dialogos.mostrar_error(self, "Seleccione primero un producto de la lista.")
            return

        if not dialogos.confirmar(
            self,
            "Dar de baja",
            f"{producto.nombre}\n\nDejará de aparecer en las búsquedas y no se podrá "
            "vender.\nLas ventas anteriores no se modifican.\n\n¿Desea darlo de baja?",
            texto_si="Sí, dar de baja",
        ):
            return

        try:
            self._sesion.desactivar_producto(self.usuario, producto.id)
        except ErrorDominio as error:
            dialogos.mostrar_error(self, str(error))
            return
        self.recargar()

    def ver_pendientes(self) -> None:
        """Códigos que se escanearon y no existen en el catálogo."""
        try:
            pendientes = self._sesion.codigos_pendientes(self.usuario)
        except ErrorDominio as error:
            dialogos.mostrar_error(self, str(error))
            return

        if not pendientes:
            dialogos.mostrar_info(
                self,
                "No hay códigos pendientes.\n\nAquí aparecen los productos que se "
                "escanearon en la caja y todavía no están cargados en el catálogo.",
                "Códigos pendientes",
            )
            return

        lineas = "\n".join(
            f"  {p.codigo}      {p.intentos} intento(s)      último: {p.ultima_vez}"
            for p in pendientes
        )
        dialogos.mostrar_info(
            self,
            f"Estos códigos se escanearon en la caja y no están en el catálogo:\n\n{lineas}",
            "Códigos pendientes",
        )
