"""Ventana principal: barra lateral, cabecera, pantallas y atajos de teclado.

La ventana es solo el armazón. A la izquierda la navegación, arriba una cabecera que dice en
qué pantalla se está, y en medio la pantalla propiamente dicha. Las pantallas no pintan su
propio título: se lo pone la cabecera, y por eso todas empiezan a la misma altura y el
programa se ve como un sistema y no como cuatro ventanas distintas pegadas.
"""

from __future__ import annotations

import weakref


from PySide6.QtCore import QDateTime, Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
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
from ..domain.errors import ErrorDominio
from ..domain.models import Usuario
from ..red.sesion import Sesion
from ..services import preferencias as servicio_preferencias
from ..services.preferencias import Preferencias
from ..utils import sonido
from . import dialogos, estilos, iconos, movimiento
from .barra_lateral import BarraLateral
from .cierre_view import CierreView
from .configuracion_dialog import DialogoConfiguracion
from .consulta_view import ConsultaView
from .efectivo_view import EfectivoView, pedir_apertura
from .login_dialog import DialogoLogin
from .productos_view import ProductosView
from .usuarios_view import UsuariosView
from .reportes_view import ReportesView
from .venta_view import VentaView

#: Qué dice la cabecera en cada pantalla. La clave es la misma que usa la barra lateral.
_CABECERAS = {
    "venta": ("Venta", "Escanee los productos y cobre cuando termine."),
    "consulta": ("Consulta de precio", "Para mirar un precio sin abrir una venta."),
    "efectivo": ("Efectivo", "Abrir la caja, lo que entra y sale del cajón, y el cierre."),
    "productos": ("Productos", "El catálogo completo de la tienda."),
    "reportes": ("Ventas del día", "Lo que se vendió hoy, venta por venta."),
    "cierre": ("Ventas por caja", "El cierre diario: lo vendido en una caja, por medio de pago y por empleado."),
    "usuarios": ("Usuarios", "Un usuario por empleado, cada uno con su PIN."),
}

_AYUDA = """<b>Atajos de teclado</b><br><br>
<table cellpadding="4">
<tr><td><b>Enter</b></td><td>Agregar el producto escaneado al carrito</td></tr>
<tr><td><b>F2</b></td><td>Consulta de precio a pantalla completa</td></tr>
<tr><td><b>F3</b></td><td>Ir a la búsqueda por nombre, al lado del código</td></tr>
<tr><td><b>F4</b></td><td>Aplicar un descuento a la venta</td></tr>
<tr><td><b>F5</b></td><td>Quitar una unidad de la línea seleccionada</td></tr>
<tr><td><b>↑ ↓</b></td><td>Moverse entre las líneas del carrito</td></tr>
<tr><td><b>→</b> o <b>+</b></td><td>Agregar una unidad a la línea seleccionada</td></tr>
<tr><td><b>←</b> o <b>−</b></td><td>Quitar una unidad de la línea seleccionada</td></tr>
<tr><td><b>Ctrl+C</b></td><td>Copiar el código de la línea seleccionada</td></tr>
<tr><td><b>F6</b></td><td>Cancelar la venta en curso</td></tr>
<tr><td><b>F11</b></td><td>Cambiar el medio de pago: efectivo, débito, crédito</td></tr>
<tr><td><b>F12</b></td><td>Cobrar y registrar la venta</td></tr>
<tr><td><b>F7</b></td><td>Administrar productos</td></tr>
<tr><td><b>F8</b></td><td>Ventas del día <i>(administrador)</i></td></tr>
<tr><td><b>F9</b></td><td>Configuración</td></tr>
<tr><td><b>F10</b></td><td>Cambiar de usuario</td></tr>
<tr><td><b>Esc</b></td><td>Volver a la pantalla de venta</td></tr>
<tr><td><b>Ctrl+B</b></td><td>Ocultar o mostrar el menú lateral</td></tr>
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
        self._tema_aplicado = self.preferencias.tema
        self._letra_aplicada = self.preferencias.tamano_texto

        self.setWindowTitle(f"{NOMBRE_COMERCIAL} · Caja {VERSION}")
        self.resize(1280, 800)
        self.setMinimumSize(1080, 680)

        self._construir()
        self._registrar_atajos()
        self.aplicar_preferencias(self.preferencias)
        self.mostrar_venta()

    # ------------------------------------------------------------------ construcción

    def _construir(self) -> None:
        central = QWidget()
        fila = QHBoxLayout(central)
        fila.setContentsMargins(0, 0, 0, 0)
        fila.setSpacing(0)

        self.barra_lateral = BarraLateral()
        self.barra_lateral.navegacion_solicitada.connect(self._navegar)
        self.barra_lateral.plegado_cambiado.connect(self._recordar_plegado)
        fila.addWidget(self.barra_lateral)
        #: Las pruebas y la configuración llegan a la rueda por aquí.
        self.boton_configuracion = self.barra_lateral.boton_configuracion

        fila.addWidget(self._zona_de_contenido(), stretch=1)
        self.setCentralWidget(central)

        barra = QStatusBar()
        barra.showMessage(
            "F1 ayuda   ·   F2 consulta   ·   F3 buscar   ·   F4 descuento   ·   F5 quitar"
            "   ·   F6 cancelar   ·   F7 productos   ·   F8 ventas del día"
            "   ·   F9 configuración   ·   F10 cambiar usuario   ·   F11 pago   ·   F12 cobrar"
            "   ·   Ctrl+B menú"
        )
        self.setStatusBar(barra)

    def _zona_de_contenido(self) -> QWidget:
        contenido = QWidget()
        contenido.setObjectName("transparente")
        columna = QVBoxLayout(contenido)
        columna.setContentsMargins(0, 0, 0, 0)
        columna.setSpacing(0)
        columna.addWidget(self._cabecera())

        self.pantallas = QStackedWidget()
        self.vista_venta = VentaView(self._sesion)
        self.vista_consulta = ConsultaView(self._sesion)
        self.vista_productos = ProductosView(self._sesion)
        self.vista_reportes = ReportesView(self._sesion)
        self.vista_cierre = CierreView(self._sesion)
        self.vista_usuarios = UsuariosView(self._sesion)
        self.vista_efectivo = EfectivoView(self._sesion)
        # Por una referencia débil: si la vista guardara el método de la ventana, habría un ciclo
        # y la ventana no se liberaría al cerrarse. Las ventanas que quedaban vivas hacían que
        # cada cambio de tema tardara más que el anterior.
        asegurar_admin = weakref.WeakMethod(self._asegurar_admin)
        self.vista_efectivo.autorizar_admin = lambda accion: (
            metodo(accion) if (metodo := asegurar_admin()) is not None else None
        )
        for vista in (
            self.vista_venta,
            self.vista_consulta,
            self.vista_efectivo,
            self.vista_productos,
            self.vista_reportes,
            self.vista_cierre,
            self.vista_usuarios,
        ):
            self.pantallas.addWidget(vista)
        columna.addWidget(self.pantallas, stretch=1)

        self.vista_venta.consulta_solicitada.connect(self.mostrar_consulta)
        self.vista_consulta.salir_solicitado.connect(self.mostrar_venta)
        self.vista_productos.salir_solicitado.connect(self.mostrar_venta)
        self.vista_productos.resumen_cambiado.connect(self._resumen_de_productos)
        self.vista_reportes.salir_solicitado.connect(self.mostrar_venta)
        self.vista_reportes.cierre_solicitado.connect(self.mostrar_cierre)
        self.vista_cierre.salir_solicitado.connect(self.mostrar_venta)
        self.vista_cierre.resumen_cambiado.connect(self._resumen_de_cierre)
        self.vista_usuarios.salir_solicitado.connect(self.mostrar_venta)
        self.vista_usuarios.resumen_cambiado.connect(self._resumen_de_usuarios)
        self.vista_efectivo.salir_solicitado.connect(self.mostrar_venta)
        self.vista_efectivo.resumen_cambiado.connect(self._resumen_de_efectivo)
        return contenido

    def _cabecera(self) -> QWidget:
        cabecera = QFrame()
        cabecera.setObjectName("cabecera")
        cabecera.setFixedHeight(88)

        fila = QHBoxLayout(cabecera)
        fila.setContentsMargins(28, 0, 28, 0)
        fila.setSpacing(16)

        # El bloque de título va en un widget propio y centrado: dentro de un layout suelto,
        # Qt le reparte todo el alto de la cabecera y el subtítulo se despega del título.
        bloque = QWidget()
        bloque.setObjectName("transparente")
        textos = QVBoxLayout(bloque)
        textos.setContentsMargins(0, 0, 0, 0)
        textos.setSpacing(3)
        self.titulo_pantalla = QLabel()
        self.titulo_pantalla.setObjectName("tituloPantalla")
        textos.addWidget(self.titulo_pantalla)
        self.subtitulo_pantalla = QLabel()
        self.subtitulo_pantalla.setObjectName("subtitulo")
        textos.addWidget(self.subtitulo_pantalla)
        fila.addWidget(bloque, stretch=1, alignment=Qt.AlignmentFlag.AlignVCenter)

        # El reloj no es decorativo: en una caja se necesita saber la hora sin soltar nada.
        self._icono_reloj = QLabel()
        fila.addWidget(self._icono_reloj, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.etiqueta_sesion = QLabel()
        self.etiqueta_sesion.setObjectName("datosSesion")
        fila.addWidget(self.etiqueta_sesion, alignment=Qt.AlignmentFlag.AlignVCenter)

        self._reloj = QTimer(self)
        self._reloj.timeout.connect(self._actualizar_reloj)
        self._reloj.start(1000)
        self._actualizar_reloj()
        return cabecera

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
        # F11 recorre efectivo, débito y crédito (fase 17): la tecla libre más cerca de F12.
        self._atajo(QKeySequence(Qt.Key.Key_F11), self._medio_pago)
        self._atajo(QKeySequence(Qt.Key.Key_F12), self._cobrar)
        self._atajo(QKeySequence(Qt.Key.Key_Escape), self.mostrar_venta)
        self._atajo(QKeySequence("Ctrl+B"), self.barra_lateral.alternar_plegado)

    def _atajo(self, secuencia: QKeySequence, destino) -> None:
        atajo = QShortcut(secuencia, self)
        atajo.setContext(Qt.ShortcutContext.ApplicationShortcut)
        atajo.activated.connect(destino)

    # ------------------------------------------------------------------ navegación

    def _navegar(self, clave: str) -> None:
        """Atiende a la barra lateral. Cada entrada hace lo mismo que su tecla."""
        destinos = {
            "venta": self.mostrar_venta,
            "consulta": self.mostrar_consulta,
            "efectivo": self.mostrar_efectivo,
            "productos": self.mostrar_productos,
            "reportes": self.mostrar_reportes,
            "cierre": self.mostrar_cierre,
            "usuarios": self.mostrar_usuarios,
            "configuracion": self.abrir_configuracion,
            "usuario": self.cambiar_usuario,
        }
        destinos[clave]()

    def _resumen_de_productos(self, texto: str) -> None:
        """Refleja en la cabecera cuántos productos hay, mientras se esté mirando esa
        pantalla. Filtrar el catálogo cambia el subtítulo en vivo."""
        if self.pantallas.currentWidget() is self.vista_productos:
            self.subtitulo_pantalla.setText(texto)

    def _resumen_de_usuarios(self, texto: str) -> None:
        if self.pantallas.currentWidget() is self.vista_usuarios:
            self.subtitulo_pantalla.setText(texto)

    def _resumen_de_efectivo(self, texto: str) -> None:
        if self.pantallas.currentWidget() is self.vista_efectivo:
            self.subtitulo_pantalla.setText(texto)

    def _resumen_de_cierre(self, texto: str) -> None:
        """Qué caja y qué día se está mirando. Cambia al elegir otro de los dos."""
        if self.pantallas.currentWidget() is self.vista_cierre:
            self.subtitulo_pantalla.setText(texto)

    def _ir_a(self, clave: str, vista: QWidget) -> None:
        """Deja la ventana entera —pantalla, cabecera y barra— coherente con un solo sitio."""
        self.pantallas.setCurrentWidget(vista)
        titulo, subtitulo = _CABECERAS[clave]
        self.titulo_pantalla.setText(titulo)
        self.subtitulo_pantalla.setText(subtitulo)
        self.barra_lateral.seleccionar(clave)

    def mostrar_venta(self) -> None:
        self._ir_a("venta", self.vista_venta)
        self.vista_venta.enfocar_escaneo()

    def mostrar_consulta(self) -> None:
        self.vista_consulta.limpiar()
        self._ir_a("consulta", self.vista_consulta)
        self.vista_consulta.enfocar_escaneo()

    def alternar_consulta(self) -> None:
        """F2 entra a la consulta y F2 de nuevo vuelve: una sola tecla para ir y volver."""
        if self.pantallas.currentWidget() is self.vista_consulta:
            self.mostrar_venta()
        else:
            self.mostrar_consulta()

    def mostrar_productos(self) -> None:
        """Catálogo. Para cualquier empleado, sin PIN de administrador (D-038)."""
        if self.usuario is None:
            return
        self.vista_productos.usuario = self.usuario
        # Primero se cambia de pantalla y después se recarga: al recargar, la vista anuncia
        # cuántos productos hay y la cabecera solo lo recoge si ya está mostrándola.
        self._ir_a("productos", self.vista_productos)
        self.vista_productos.recargar()

    def mostrar_reportes(self) -> None:
        if self._asegurar_admin("ver las ventas del día") is None:
            return
        self._ir_a("reportes", self.vista_reportes)
        self.vista_reportes.recargar()

    def mostrar_efectivo(self) -> None:
        """El cajón de esta caja (fase 19). Para cualquier empleado: las cuentas y el retiro
        piden el PIN de un administrador dentro de la propia pantalla."""
        self.vista_efectivo.usuario = self.usuario
        self._ir_a("efectivo", self.vista_efectivo)
        self.vista_efectivo.al_entrar()

    def proponer_apertura(self) -> None:
        """Al arrancar: si la caja está cerrada, ofrece abrirla antes de la primera venta.

        Se puede dejar para después —se vuelve a pedir al cobrar—, pero así el cajón se cuenta
        con calma y no con un cliente esperando.
        """
        if self.usuario is None:
            return
        try:
            abierta = self._sesion.turno_abierto(self.usuario) is not None
        except ErrorDominio:
            return
        if not abierta:
            pedir_apertura(
                self._sesion, self.usuario, self, motivo="La caja está cerrada. Para cobrar hay que abrirla."
            )
        self._devolver_foco()

    def mostrar_cierre(self) -> None:
        """Cierre diario por caja (fase 18). Reservado al administrador, como las ventas del
        día: quién más debería verlo es la pregunta H4, sin responder."""
        if self._asegurar_admin("ver el cierre de caja") is None:
            return
        self._ir_a("cierre", self.vista_cierre)
        self.vista_cierre.al_entrar()

    def mostrar_usuarios(self) -> None:
        """Usuarios de la tienda. Si quien opera no es administrador, se le pide el PIN de uno."""
        administrador = self._asegurar_admin("administrar los usuarios")
        if administrador is None:
            return
        self.vista_usuarios.usuario = administrador
        self._ir_a("usuarios", self.vista_usuarios)
        self.vista_usuarios.recargar()

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
        self.vista_venta._empezar_venta_nueva()
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

    def _medio_pago(self) -> None:
        if self._en_venta():
            self.vista_venta.alternar_medio_pago()

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
            self.preferencias,
            self,
            al_previsualizar_tema=self.aplicar_tema,
            al_previsualizar_letra=self.aplicar_tamano_texto,
        )
        if elegidas is not None:
            self.aplicar_preferencias(elegidas)
        self._devolver_foco()

    def aplicar_preferencias(self, preferencias: Preferencias) -> None:
        """Deja la aplicación en el estado que describen las preferencias."""
        self.preferencias = preferencias
        self._aplicar_apariencia(preferencias.tema, preferencias.tamano_texto)
        sonido.habilitado = preferencias.sonido
        movimiento.habilitado = preferencias.animaciones
        self.barra_lateral.plegar(preferencias.barra_lateral_plegada)
        self.vista_venta.preferencias = preferencias
        if self.statusBar() is not None:
            self.statusBar().setVisible(preferencias.mostrar_atajos)

    def _recordar_plegado(self, plegada: bool) -> None:
        """Guarda el plegado en cuanto cambia.

        No espera a que alguien abra la rueda de configuración y pulse Guardar: se cambia
        con una tecla, y una tecla que hay que volver a pulsar en cada arranque no sirve de
        nada. Si el archivo no se puede escribir, la barra queda plegada igual y el fallo se
        anota en el registro; no es motivo para interrumpir una venta.
        """
        self.preferencias.barra_lateral_plegada = plegada
        servicio_preferencias.guardar(self.preferencias)

    def aplicar_tema(self, tema: str) -> None:
        """Repinta toda la aplicación con el tema indicado, sin tocar el tamaño de letra."""
        self._aplicar_apariencia(tema, self._letra_aplicada)

    def aplicar_tamano_texto(self, tamano: str) -> None:
        """Repinta toda la aplicación con el tamaño de letra indicado, sin tocar el tema."""
        self._aplicar_apariencia(self._tema_aplicado, tamano)

    def _aplicar_apariencia(self, tema: str, tamano_texto: str) -> None:
        """Repinta toda la aplicación con un tema y un tamaño de letra, sin reiniciar.

        Los dos van juntos porque viven en la misma hoja de estilos: aplicar solo el tema
        devolvería la letra al tamaño de fábrica, y al revés. Por eso la ventana recuerda lo
        que está aplicado, que durante la previsualización del diálogo de configuración no
        coincide con lo guardado en `self.preferencias`.

        Se aplica sobre la QApplication y no sobre esta ventana porque los diálogos son
        ventanas aparte: si el estilo viviera aquí, seguirían saliendo con el tema anterior.
        """
        self._tema_aplicado = tema
        self._letra_aplicada = tamano_texto
        app = QApplication.instance()
        if app is not None:
            estilos.aplicar(app, tema, tamano_texto)
        # Lo que la hoja de estilos no alcanza: los iconos, que son mapas de píxeles ya
        # pintados, y los colores que las pantallas fijan celda a celda.
        self.barra_lateral.repintar()
        self._actualizar_reloj()
        self.vista_venta.repintar()
        self.vista_productos.repintar()
        self.vista_usuarios.repintar()
        self.vista_reportes.repintar()
        self.vista_cierre.repintar()
        self.vista_efectivo.repintar()

    # ------------------------------------------------------------------ sesión

    def establecer_usuario(self, usuario: Usuario | None) -> None:
        self.usuario = usuario
        self.vista_venta.usuario = usuario
        self.vista_efectivo.usuario = usuario
        # Si se cambia de usuario con Productos a la vista, lo que se cree después es del nuevo.
        self.vista_productos.usuario = usuario
        self.barra_lateral.establecer_usuario(usuario, self._sesion.caja)

    def _actualizar_reloj(self) -> None:
        self._icono_reloj.setPixmap(iconos.pixmap("reloj", 16, estilos.actual.texto_apagado))
        self.etiqueta_sesion.setText(
            QDateTime.currentDateTime().toString("dd/MM/yyyy   HH:mm:ss")
        )
