"""Paleta, sombras y hoja de estilos de la aplicación.

Los colores y tamaños viven en un solo archivo para que cambiar la apariencia no obligue a
tocar la lógica de las pantallas.

**Sistema visual.** La interfaz sigue `docs/DESIGN.md`: lienzo de piedra cálida, tarjetas
blancas planas, filete de 1 px como recurso estructural principal, controles en forma de
cápsula y sombras muy suaves. La tipografía es Inter.

**Dos colores, dos significados, y ninguno más.** Un punto de venta se opera de pie, con
prisa y mirando al cliente en vez de a la pantalla, así que el color no puede ser decoración:
tiene que decir algo desde el rabillo del ojo.

- **Rojo** — el del logotipo. Marca dónde estoy y dónde está el foco, y también lo que
  cancela o borra. Va siempre en lavado, en filete o en texto: **nunca relleno**, y por eso
  no se confunde el menú con un botón de borrar.
- **Verde** — lo que salió bien y lo que confirma: el producto agregado, el total, cobrar,
  guardar, entrar. Es el único color que se usa relleno.

`DESIGN.md` pide un acento cian único y prohíbe expresamente añadir verde. Se desoye a
conciencia: un cajero necesita distinguir "lo agregué" de "no existe" sin leer, y el rojo es
el de la marca del negocio. Lo que sí se respeta es la disciplina: dos colores, una regla de
uso para cada uno, y nada de color decorativo. Ver D-026 y D-027.

Hay dos temas. El claro es el de fábrica. El oscuro no viene en el documento y se deriva
oscureciendo la pila de piedra y aclarando los dos colores, que sobre un fondo casi negro no
llegarían al contraste mínimo. Los tamaños, los radios y el interletrado son idénticos en los
dos, de modo que ninguna pantalla se descoloca al cambiar de tema.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..services.preferencias import TEMA_CLARO, TEMA_OSCURO

#: Inter es la fuente del sistema. En un Windows sin ella la pila cae en Segoe UI, que es el
#: sustituto razonable: neutra, de trazo uniforme y presente en todas las instalaciones.
FUENTE = 'Inter, "Inter Tight", "Segoe UI Variable Text", "Segoe UI", Roboto, sans-serif'

# Radios. Cada uno tiene su sitio y no se usan valores intermedios.
RADIO_TARJETA = 16       # tarjetas de contenido
RADIO_ANIDADO = 12       # lo que va dentro de una tarjeta
RADIO_CAMPO = 12         # campos de texto grandes
RADIO_PEQUENO = 8        # detalles

# Cápsulas. Qt no admite el truco de poner un radio enorme y dejar que lo recorte: con
# `border-radius: 999px` dibuja el control **cuadrado**, sin redondear nada. Hay que darle un
# radio de verdad, y además por debajo de la mitad del alto del control, porque en cuanto lo
# supera vuelve a rendirse. De ahí que haya un valor por cada altura.
RADIO_PILDORA = 20       # botón normal, unos 42 px de alto
RADIO_PILDORA_ALTA = 26  # el botón de cobrar, 56 px
RADIO_PILDORA_BAJA = 14  # fichas y etiquetas cápsula, unos 32 px

#: Anchura de la barra lateral, desplegada y plegada. Plegada cabe justo el icono centrado
#: con su zona de pulsación; más estrecha, apuntar con el ratón se vuelve incómodo.
ANCHO_BARRA_LATERAL = 232
ANCHO_BARRA_LATERAL_PLEGADA = 72


@dataclass(frozen=True, slots=True)
class Paleta:
    """Los colores de un tema. Cada nombre dice para qué sirve, no de qué color es."""

    nombre: str
    fondo: str                 # lienzo de la zona de contenido
    superficie: str            # papel: tarjetas, barra lateral, campos
    superficie_alterna: str    # tinte suave: cabeceras de tabla, hover, filas
    borde: str                 # el filete de 1 px que estructura todo
    borde_suave: str           # separadores internos y rejilla de tablas
    borde_fuerte: str          # borde de un campo de texto
    texto: str                 # tinta
    texto_suave: str           # texto secundario y etiquetas
    texto_apagado: str         # deshabilitado
    acento: str                # rojo de marca: navegación y foco
    acento_fuerte: str         # el mismo rojo legible sobre fondo claro
    acento_suave: str          # lavado rojo de fondo
    exito: str                 # verde: lo que salió bien y lo que confirma
    exito_fuerte: str          # el verde bajo el cursor
    exito_suave: str           # lavado verde de fondo
    sobre_exito: str           # texto sobre el verde relleno
    error: str                 # rojo de lo destructivo y de lo que falló
    error_suave: str           # lavado rojo de fondo para el error
    seleccion: str             # fila seleccionada
    pulsado: str               # control mientras se pulsa
    barra_desplazamiento: str
    sombra: tuple[int, int, int, int]  # r, g, b, alfa de la sombra de las tarjetas


CLARO = Paleta(
    nombre=TEMA_CLARO,
    # Un escalón por debajo del #FAFAF9 del documento. Con aquel, el papel blanco de las
    # tarjetas y el lienzo quedaban a un punto de distancia y los recuadros no se separaban:
    # la tarjeta solo se veía por su filete. Este sigue leyéndose como papel cálido y no como
    # pantalla gris, que es lo que el sistema pide.
    fondo="#F1EFEC",
    superficie="#FFFFFF",
    superficie_alterna="#F4F2F1",
    borde="#E4E1DF",
    borde_suave="#EFECEA",
    borde_fuerte="#D2CECB",
    texto="#0C0A09",
    # Más oscuro que el gris del documento: sobre papel blanco, el #78716C original se leía
    # bien en una web y se perdía en un mostrador con luz de tubo.
    texto_suave="#57534E",
    texto_apagado="#8C847E",
    acento="#BE1E2D",
    acento_fuerte="#9E1824",
    acento_suave="#FCECEE",
    exito="#15803D",
    exito_fuerte="#126A33",
    exito_suave="#E7F5EC",
    sobre_exito="#FFFFFF",
    error="#BE1E2D",
    error_suave="#FCECEE",
    seleccion="#F2EFED",
    pulsado="#EBE8E5",
    barra_desplazamiento="#CFCBC7",
    sombra=(28, 25, 23, 22),
)

# La piedra se oscurece sin perder el tinte cálido: un gris neutro al lado del tema claro
# parecería otro programa. Los dos colores se aclaran porque sus tonos del tema claro sobre
# un fondo casi negro no llegan al contraste mínimo, y el total es justo lo que el cajero lee
# de lejos.
OSCURO = Paleta(
    nombre=TEMA_OSCURO,
    fondo="#121110",
    superficie="#1C1A19",
    superficie_alterna="#262322",
    borde="#332F2D",
    borde_suave="#292625",
    borde_fuerte="#413C39",
    texto="#FAFAF9",
    texto_suave="#B5AFA9",
    texto_apagado="#857D77",
    acento="#F0757F",
    acento_fuerte="#F8A6AC",
    acento_suave="#2E1618",
    exito="#4ADE80",
    exito_fuerte="#6EE7A0",
    exito_suave="#15291D",
    sobre_exito="#062211",
    error="#F0757F",
    error_suave="#2E1618",
    seleccion="#292625",
    pulsado="#332F2D",
    barra_desplazamiento="#413C39",
    sombra=(0, 0, 0, 110),
)

PALETAS = {CLARO.nombre: CLARO, OSCURO.nombre: OSCURO}

#: Paleta en uso. Las pantallas que necesiten un color puntual leen de aquí en lugar de
#: escribir un código de color a mano, que sería el que se olvidaría al cambiar de tema.
actual: Paleta = CLARO


def paleta_de(tema: str) -> Paleta:
    """Devuelve la paleta de un tema, o la clara si el nombre no se reconoce."""
    return PALETAS.get(tema, CLARO)


def aplicar_sombra(widget, difuminado: int = 18, desplazamiento: int = 4) -> None:
    """Pone a una tarjeta la sombra suave del sistema.

    Qt no entiende `box-shadow` en una hoja de estilos, así que la única forma de tener una
    es un efecto gráfico. Se reserva a las tarjetas de contenido —son pocas y no se
    redibujan en cada escaneo—, porque un efecto sobre una tabla que se repinta entera sale
    caro y se nota en una caja.
    """
    from PySide6.QtGui import QColor
    from PySide6.QtWidgets import QGraphicsDropShadowEffect

    r, g, b, alfa = actual.sombra
    efecto = QGraphicsDropShadowEffect(widget)
    efecto.setBlurRadius(difuminado)
    efecto.setXOffset(0)
    efecto.setYOffset(desplazamiento)
    efecto.setColor(QColor(r, g, b, alfa))
    widget.setGraphicsEffect(efecto)


def hoja_de_estilos(p: Paleta) -> str:
    """Construye la hoja de estilos completa a partir de una paleta.

    Los tamaños, los radios y el interletrado son los mismos en los dos temas: solo se
    interpolan colores.
    """
    return f"""
QWidget {{
    background-color: {p.fondo};
    color: {p.texto};
    font-family: {FUENTE};
    font-size: 15px;
}}

/* Las etiquetas no pintan fondo: si lo hicieran, cada texto se vería como una caja gris
   sobre las tarjetas. Las que sí llevan fondo lo declaran explícitamente más abajo. */
QLabel {{
    background: transparent;
}}

QDialog {{
    background-color: {p.superficie};
}}
/* La caja de botones y los contenedores que solo agrupan widgets son QWidget sueltos: sin
   esto pintarían el lienzo dentro de una tarjeta, como un recuadro gris. */
QDialogButtonBox, QWidget#transparente {{
    background: transparent;
}}

/* ------------------------------------------------------------------ barra lateral */

QFrame#barraLateral {{
    background-color: {p.superficie};
    border: none;
    border-right: 1px solid {p.borde};
}}

QLabel#marca {{
    color: {p.texto};
    font-size: 17px;
    font-weight: 700;
    letter-spacing: -0.3px;
}}
QLabel#marcaSub {{
    color: {p.texto_suave};
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.6px;
}}

/* Rótulo de un grupo del menú. Diminuto y espaciado: ordena sin pedir atención. */
QLabel#navSeccion {{
    color: {p.texto_apagado};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1.1px;
}}

QPushButton#navBoton {{
    background: transparent;
    border: none;
    border-radius: {RADIO_ANIDADO}px;
    padding: 10px 12px;
    text-align: left;
}}
QPushButton#navBoton:hover {{
    background-color: {p.superficie_alterna};
}}
QPushButton#navBoton:checked {{
    background-color: {p.acento_suave};
}}

QLabel#navAtajo {{
    color: {p.texto_apagado};
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.3px;
}}

/* Ficha del usuario, al pie de la barra lateral. */
QFrame#fichaUsuario {{
    background-color: {p.superficie_alterna};
    border: 1px solid {p.borde};
    border-radius: {RADIO_ANIDADO}px;
}}
QLabel#usuarioNombre {{
    color: {p.texto};
    font-size: 14px;
    font-weight: 700;
}}
QLabel#usuarioRol {{
    color: {p.texto_suave};
    font-size: 12px;
}}

/* Botón de plegar y desplegar, arriba del todo. */
QPushButton#botonPlegar {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: {RADIO_PEQUENO}px;
    padding: 5px;
}}
QPushButton#botonPlegar:hover {{
    background-color: {p.superficie_alterna};
    border-color: {p.borde};
}}

/* ------------------------------------------------------------------ cabecera */

QFrame#cabecera {{
    background-color: {p.fondo};
    border: none;
    border-bottom: 1px solid {p.borde};
}}

QLabel#tituloPantalla {{
    font-size: 28px;
    font-weight: 600;
    letter-spacing: -0.75px;
}}
QLabel#subtitulo {{
    color: {p.texto_suave};
    font-size: 14px;
}}
QLabel#datosSesion {{
    color: {p.texto_suave};
    font-size: 14px;
    font-weight: 500;
}}

/* Fichas cápsula. La neutra informa; la verde y la roja marcan estado. */
QLabel#ficha {{
    background-color: {p.superficie};
    color: {p.texto_suave};
    border: 1px solid {p.borde};
    border-radius: {RADIO_PILDORA_BAJA}px;
    padding: 6px 14px;
    font-size: 13px;
    font-weight: 600;
}}
QLabel#fichaExito {{
    background-color: {p.exito_suave};
    color: {p.exito};
    border: 1px solid transparent;
    border-radius: {RADIO_PILDORA_BAJA}px;
    padding: 6px 14px;
    font-size: 13px;
    font-weight: 700;
}}
QLabel#fichaError {{
    background-color: {p.error_suave};
    color: {p.error};
    border: 1px solid transparent;
    border-radius: {RADIO_PILDORA_BAJA}px;
    padding: 6px 14px;
    font-size: 13px;
    font-weight: 700;
}}

/* ------------------------------------------------------------------ tarjetas */

QFrame#tarjeta {{
    background-color: {p.superficie};
    border: 1px solid {p.borde};
    border-radius: {RADIO_TARJETA}px;
}}

QLabel#tituloTarjeta {{
    color: {p.texto};
    font-size: 16px;
    font-weight: 700;
    letter-spacing: -0.2px;
}}
QLabel#notaTarjeta {{
    color: {p.texto_suave};
    font-size: 13px;
}}

QFrame#separador {{
    background-color: {p.borde};
    border: none;
}}

/* ------------------------------------------------------------------ campos */

/* El campo de escaneo es el centro del programa. En reposo se distingue por su filete, y al
   recibir el foco se le enciende el anillo rojo de la marca: saber si el disparo de la
   pistola va a caer aquí no puede ser un detalle sutil. */
QLineEdit#campoEscaneo {{
    background-color: {p.superficie};
    border: 1px solid {p.borde_fuerte};
    border-radius: {RADIO_CAMPO}px;
    padding: 16px 20px;
    font-size: 30px;
    font-weight: 700;
    letter-spacing: -0.5px;
    color: {p.texto};
}}
QLineEdit#campoEscaneo:focus {{
    border: 2px solid {p.acento};
    padding: 15px 19px;
}}

QLineEdit, QSpinBox {{
    background-color: {p.superficie};
    border: 1px solid {p.borde_fuerte};
    border-radius: {RADIO_PEQUENO}px;
    padding: 9px 13px;
    font-size: 15px;
    color: {p.texto};
}}
QLineEdit:focus, QSpinBox:focus {{
    border: 1px solid {p.acento};
}}
QLineEdit:disabled, QSpinBox:disabled {{
    color: {p.texto_apagado};
    background-color: {p.superficie_alterna};
}}

/* Campo de búsqueda: mismo control, forma de cápsula, para que se lea como un buscador y no
   como un formulario. */
QLineEdit#campoBusqueda {{
    border-radius: 19px;
    padding: 9px 18px;
}}

QComboBox {{
    background-color: {p.superficie};
    border: 1px solid {p.borde_fuerte};
    border-radius: {RADIO_PEQUENO}px;
    padding: 9px 13px;
    padding-right: 34px;
    font-size: 15px;
    color: {p.texto};
}}
QComboBox:focus {{
    border: 1px solid {p.acento};
}}
/* El subcontrol nativo se apaga entero: su marco cuadrado rompe el radio del campo. La
   flecha la pinta `ui/widgets/desplegable.py`; ver allí por qué no puede quedarse. */
QComboBox::drop-down {{
    background: transparent;
    border: none;
    width: 34px;
}}
QComboBox QAbstractItemView {{
    background-color: {p.superficie};
    color: {p.texto};
    selection-background-color: {p.acento_suave};
    selection-color: {p.acento_fuerte};
    border: 1px solid {p.borde};
    border-radius: {RADIO_PEQUENO}px;
    padding: 4px;
}}

QCheckBox, QRadioButton {{
    background: transparent;
    spacing: 10px;
    color: {p.texto};
    font-size: 15px;
}}

/* ------------------------------------------------------------------ botones */

/* Botón de contorno: el filete define la forma sin añadir peso. Es el botón por defecto
   porque funciona igual dentro de una tarjeta blanca que sobre el lienzo. */
QPushButton {{
    background-color: {p.superficie};
    color: {p.texto};
    border: 1px solid {p.borde_fuerte};
    border-radius: {RADIO_PILDORA}px;
    padding: 10px 18px;
    font-size: 15px;
    font-weight: 600;
}}
QPushButton:hover {{
    background-color: {p.superficie_alterna};
    border-color: {p.texto_apagado};
}}
QPushButton:pressed {{
    background-color: {p.pulsado};
}}
QPushButton:disabled {{
    background-color: {p.superficie};
    color: {p.texto_apagado};
    border-color: {p.borde};
}}

/* Cobrar. Verde, grande y el único relleno de la pantalla de venta. */
QPushButton#botonPrincipal {{
    background-color: {p.exito};
    color: {p.sobre_exito};
    border: 1px solid {p.exito};
    border-radius: {RADIO_PILDORA_ALTA}px;
    padding: 16px 20px;
    font-size: 18px;
    font-weight: 700;
    letter-spacing: -0.2px;
}}
QPushButton#botonPrincipal:hover {{
    background-color: {p.exito_fuerte};
    border-color: {p.exito_fuerte};
}}
QPushButton#botonPrincipal:pressed {{
    background-color: {p.exito_fuerte};
}}
QPushButton#botonPrincipal:disabled {{
    background-color: {p.superficie_alterna};
    color: {p.texto_apagado};
    border-color: {p.borde};
}}

/* El botón que confirma un diálogo o abre un alta. Verde, como cobrar: los dos dicen
   "adelante", y nunca están en la misma pantalla. */
QPushButton#botonAccion {{
    background-color: {p.exito};
    color: {p.sobre_exito};
    border: 1px solid {p.exito};
    font-weight: 700;
}}
QPushButton#botonAccion:hover {{
    background-color: {p.exito_fuerte};
    border-color: {p.exito_fuerte};
}}
QPushButton#botonAccion:pressed {{
    background-color: {p.exito_fuerte};
}}
QPushButton#botonAccion:disabled {{
    background-color: {p.superficie_alterna};
    color: {p.texto_apagado};
    border-color: {p.borde};
}}

/* Lo destructivo lleva el rojo en el texto y en el filete, nunca de relleno. */
QPushButton#botonPeligro {{
    color: {p.error};
    border-color: {p.borde_fuerte};
}}
QPushButton#botonPeligro:hover {{
    background-color: {p.error_suave};
    border-color: {p.error};
}}
/* Sin esta regla, el color rojo del selector por id le gana al estado deshabilitado y el
   botón seguiría pareciendo pulsable con el carrito vacío. */
QPushButton#botonPeligro:disabled {{
    color: {p.texto_apagado};
    border-color: {p.borde};
    background-color: {p.superficie};
}}

/* Botón sin marco, para acciones de servicio dentro de una cabecera. */
QPushButton#botonSuave {{
    background: transparent;
    border: 1px solid transparent;
    color: {p.texto_suave};
    padding: 9px 14px;
}}
QPushButton#botonSuave:hover {{
    background-color: {p.superficie_alterna};
    color: {p.texto};
}}

QPushButton#botonConfiguracion {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: {RADIO_ANIDADO}px;
    padding: 8px;
    color: {p.texto_suave};
}}
QPushButton#botonConfiguracion:hover {{
    background-color: {p.superficie_alterna};
    color: {p.texto};
}}

/* ------------------------------------------------------------------ tablas */

QTableWidget {{
    background-color: {p.superficie};
    alternate-background-color: {p.superficie};
    border: 1px solid {p.borde};
    border-radius: {RADIO_ANIDADO}px;
    gridline-color: {p.borde_suave};
    font-size: 15px;
    outline: none;
}}
/* Dentro de una tarjeta la tabla no lleva marco propio: el marco ya lo pone la tarjeta. */
QTableWidget#tablaLimpia {{
    border: none;
    border-radius: 0px;
    background: transparent;
    alternate-background-color: transparent;
}}
QTableWidget::item {{
    padding: 12px 6px;
    border-bottom: 1px solid {p.borde_suave};
}}
QTableWidget::item:selected {{
    background-color: {p.seleccion};
    color: {p.texto};
}}
QHeaderView {{
    background: transparent;
}}
QHeaderView::section {{
    background-color: transparent;
    color: {p.texto_suave};
    border: none;
    border-bottom: 1px solid {p.borde};
    padding: 10px 6px;
    font-weight: 700;
    font-size: 12px;
    letter-spacing: 0.8px;
}}
QTableCornerButton::section {{
    background: transparent;
    border: none;
}}

/* ------------------------------------------------------------------ totales */

QLabel#etiquetaTotal {{
    color: {p.texto_suave};
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.8px;
}}
/* El rótulo del total, en tinta: es el único de la columna que se lee de verdad, y en gris
   claro quedaba por debajo de la cifra que anuncia. */
QLabel#etiquetaTotalFuerte {{
    color: {p.texto};
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.8px;
}}
QLabel#valorSubtotal {{
    font-size: 22px;
    font-weight: 600;
    letter-spacing: -0.3px;
}}
QLabel#valorDescuento {{
    font-size: 19px;
    font-weight: 600;
    color: {p.texto_suave};
}}
/* El total: verde, enorme y con el interletrado apretado. Es lo que el cajero lee de lejos
   y lo que el cliente busca en la pantalla. */
QLabel#valorTotal {{
    font-size: 48px;
    font-weight: 700;
    letter-spacing: -1.7px;
    color: {p.exito};
}}

/* ------------------------------------------------------------------ consulta */

QLabel#consultaNombre {{
    font-size: 36px;
    font-weight: 600;
    letter-spacing: -0.9px;
}}
QLabel#consultaPrecio {{
    font-size: 110px;
    font-weight: 700;
    letter-spacing: -4.4px;
    color: {p.exito};
}}
QLabel#consultaDetalle {{
    font-size: 16px;
    color: {p.texto_suave};
}}
QLabel#consultaVacio {{
    font-size: 22px;
    font-weight: 500;
    letter-spacing: -0.4px;
    color: {p.texto_apagado};
}}

/* ------------------------------------------------------------------ mensajes */

QLabel#mensajeExito {{
    background-color: {p.exito_suave};
    color: {p.exito};
    border: 1px solid transparent;
    border-radius: {RADIO_ANIDADO}px;
    padding: 14px 18px;
    font-size: 15px;
    font-weight: 700;
}}
QLabel#mensajeError {{
    background-color: {p.error_suave};
    color: {p.error};
    border: 1px solid transparent;
    border-radius: {RADIO_ANIDADO}px;
    padding: 14px 18px;
    font-size: 15px;
    font-weight: 700;
}}

/* El código que no se encontró, en grande para poder dictarlo o anotarlo. */
QLabel#codigoNoEncontrado {{
    background-color: {p.error_suave};
    color: {p.error};
    border-radius: {RADIO_ANIDADO}px;
    padding: 14px;
    font-size: 26px;
    font-weight: 700;
    letter-spacing: 1.3px;
}}

/* ------------------------------------------------------------------ resto */

QStatusBar {{
    background-color: {p.superficie};
    border-top: 1px solid {p.borde};
    color: {p.texto_apagado};
    font-size: 12px;
    font-weight: 500;
    letter-spacing: 0.4px;
}}
QStatusBar::item {{
    border: none;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {p.barra_desplazamiento};
    border-radius: 5px;
    min-height: 32px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: {p.barra_desplazamiento};
    border-radius: 5px;
    min-width: 32px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

QToolTip {{
    background-color: {p.texto};
    color: {p.superficie};
    border: none;
    border-radius: {RADIO_PEQUENO}px;
    padding: 7px 11px;
    font-size: 13px;
}}
"""


def aplicar(app, tema: str = TEMA_CLARO) -> Paleta:
    """Aplica el tema a la aplicación completa y devuelve la paleta que quedó activa.

    Cambiar la hoja de estilos en caliente basta para que toda la interfaz se repinte: Qt
    vuelve a resolver el estilo de cada widget existente, no solo de los nuevos. Por eso el
    tema se puede cambiar sin reiniciar el programa. Lo que no alcanza son los iconos y los
    colores fijados celda a celda, que cada pantalla vuelve a pintar en su `repintar()`.
    """
    global actual
    actual = paleta_de(tema)
    app.setStyleSheet(hoja_de_estilos(actual))
    return actual
