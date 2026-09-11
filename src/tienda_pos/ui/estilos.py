"""Paleta y hoja de estilos de la aplicación.

Los colores y tamaños viven en un solo archivo para que cambiar la apariencia no obligue a
tocar la lógica de las pantallas.

Criterio de diseño: una caja se opera de pie, con prisa y a veces con mala luz. Por eso todo
lo importante es grande y de alto contraste, y el color se reserva para tres cosas: el total,
el éxito y el error. Un POS lleno de colores es un POS en el que no se distingue lo urgente.

Hay dos temas. El claro es el de fábrica, porque un mostrador suele estar bien iluminado. El
oscuro existe para locales con poca luz o turnos de noche, donde una pantalla blanca grande
a medio metro de la cara cansa la vista. Ambos usan los mismos tamaños: solo cambian los
colores, de modo que ninguna pantalla se descoloca al cambiar de tema.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..services.preferencias import TEMA_CLARO, TEMA_OSCURO

FUENTE = "Segoe UI, Inter, Roboto, sans-serif"


@dataclass(frozen=True, slots=True)
class Paleta:
    """Los colores de un tema. Cada nombre dice para qué sirve, no de qué color es."""

    nombre: str
    fondo: str
    superficie: str
    superficie_alterna: str
    borde: str
    borde_suave: str
    texto: str
    texto_suave: str
    texto_apagado: str
    primario: str
    primario_oscuro: str
    sobre_primario: str
    exito: str
    exito_fuerte: str
    exito_suave: str
    sobre_exito: str
    error: str
    error_suave: str
    aviso: str
    seleccion: str
    pulsado: str
    barra_desplazamiento: str


CLARO = Paleta(
    nombre=TEMA_CLARO,
    fondo="#EEF1F5",
    superficie="#FFFFFF",
    superficie_alterna="#F3F5F9",
    borde="#D3D9E0",
    borde_suave="#E3E7EC",
    texto="#111827",
    texto_suave="#5B6673",
    texto_apagado="#9AA3AF",
    primario="#1D4ED8",
    primario_oscuro="#1E3A8A",
    sobre_primario="#C7D2FE",
    exito="#15803D",
    exito_fuerte="#166534",
    exito_suave="#DCFCE7",
    sobre_exito="#FFFFFF",
    error="#B91C1C",
    error_suave="#FEE2E2",
    aviso="#B45309",
    seleccion="#DBEAFE",
    pulsado="#E5EAF2",
    barra_desplazamiento="#C4CBD4",
)

# En el tema oscuro el verde y el rojo se aclaran: los tonos del tema claro sobre un fondo
# casi negro no llegan al contraste mínimo, y el total, que es lo que el cajero lee de lejos,
# quedaría ilegible.
OSCURO = Paleta(
    nombre=TEMA_OSCURO,
    fondo="#12161D",
    superficie="#1B212B",
    superficie_alterna="#232B37",
    borde="#333D4B",
    borde_suave="#2A323E",
    texto="#E8ECF2",
    texto_suave="#9BA6B4",
    texto_apagado="#6B7684",
    primario="#60A5FA",
    primario_oscuro="#0F1620",
    sobre_primario="#BFDBFE",
    exito="#4ADE80",
    exito_fuerte="#22C55E",
    exito_suave="#14331F",
    sobre_exito="#08240F",
    error="#F87171",
    error_suave="#3A1717",
    aviso="#FBBF24",
    seleccion="#1E3A5F",
    pulsado="#2C3542",
    barra_desplazamiento="#3E4856",
)

PALETAS = {CLARO.nombre: CLARO, OSCURO.nombre: OSCURO}

#: Paleta en uso. Las pantallas que necesiten un color puntual leen de aquí en lugar de
#: escribir un código de color a mano, que sería el que se olvidaría al cambiar de tema.
actual: Paleta = CLARO


def paleta_de(tema: str) -> Paleta:
    """Devuelve la paleta de un tema, o la clara si el nombre no se reconoce."""
    return PALETAS.get(tema, CLARO)


def hoja_de_estilos(p: Paleta) -> str:
    """Construye la hoja de estilos completa a partir de una paleta."""
    return f"""
QWidget {{
    background-color: {p.fondo};
    color: {p.texto};
    font-family: {FUENTE};
    font-size: 14px;
}}

/* Las etiquetas no pintan fondo: si lo hicieran, cada texto se vería como una caja gris
   sobre las tarjetas y sobre la barra superior. Las que sí llevan fondo (los mensajes
   de éxito y error) lo declaran explícitamente más abajo. */
QLabel {{
    background: transparent;
}}

QLabel#tituloPantalla {{
    font-size: 22px;
    font-weight: 600;
}}

QLabel#subtitulo {{
    color: {p.texto_suave};
    font-size: 13px;
}}

/* Tarjetas que agrupan contenido */
QFrame#tarjeta {{
    background-color: {p.superficie};
    border: 1px solid {p.borde};
    border-radius: 10px;
}}

QFrame#barraSuperior {{
    background-color: {p.primario_oscuro};
    border: none;
}}

QLabel#marca {{
    color: #FFFFFF;
    font-size: 18px;
    font-weight: 600;
}}

QLabel#datosSesion {{
    color: {p.sobre_primario};
    font-size: 13px;
}}

/* La rueda de configuración vive en la barra superior y debe verse sobre ella */
QPushButton#botonConfiguracion {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 2px 8px;
    font-size: 20px;
    color: {p.sobre_primario};
}}
QPushButton#botonConfiguracion:hover {{
    background-color: rgba(255, 255, 255, 0.12);
    border-color: rgba(255, 255, 255, 0.25);
}}

/* El campo de escaneo: lo más importante de la pantalla */
QLineEdit#campoEscaneo {{
    background-color: {p.superficie};
    border: 2px solid {p.primario};
    border-radius: 8px;
    padding: 14px 16px;
    font-size: 26px;
    font-weight: 600;
    letter-spacing: 1px;
}}
QLineEdit#campoEscaneo:focus {{
    border: 3px solid {p.primario};
}}

QLineEdit, QSpinBox, QComboBox {{
    background-color: {p.superficie};
    border: 1px solid {p.borde};
    border-radius: 6px;
    padding: 8px 10px;
    font-size: 14px;
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border: 2px solid {p.primario};
}}
QComboBox QAbstractItemView {{
    background-color: {p.superficie};
    color: {p.texto};
    selection-background-color: {p.seleccion};
    selection-color: {p.texto};
    border: 1px solid {p.borde};
}}

QCheckBox, QRadioButton {{
    background: transparent;
    spacing: 8px;
}}

QPushButton {{
    background-color: {p.superficie};
    border: 1px solid {p.borde};
    border-radius: 8px;
    padding: 10px 16px;
    font-size: 14px;
    font-weight: 600;
}}
QPushButton:hover {{
    border-color: {p.primario};
}}
QPushButton:pressed {{
    background-color: {p.pulsado};
}}
QPushButton:disabled {{
    color: {p.texto_apagado};
    border-color: {p.borde_suave};
}}

QPushButton#botonPrincipal {{
    background-color: {p.exito};
    color: {p.sobre_exito};
    border: none;
    padding: 16px 20px;
    font-size: 18px;
}}
QPushButton#botonPrincipal:hover {{
    background-color: {p.exito_fuerte};
}}
QPushButton#botonPrincipal:disabled {{
    background-color: {p.borde};
    color: {p.texto_apagado};
}}

QPushButton#botonPeligro {{
    color: {p.error};
    border-color: {p.error};
}}
QPushButton#botonPeligro:hover {{
    border-color: {p.error};
    background-color: {p.error_suave};
}}
/* Sin esta regla, el color rojo del selector por id le gana al estado deshabilitado y el
   botón seguiría pareciendo pulsable con el carrito vacío. */
QPushButton#botonPeligro:disabled {{
    color: {p.texto_apagado};
    border-color: {p.borde_suave};
    background-color: {p.superficie};
}}

/* Botones diminutos dentro de la tabla del carrito: copiar el código y ajustar la cantidad.
   Van sin relleno para que la fila no crezca de alto. */
QPushButton#botonCelda {{
    background-color: {p.superficie_alterna};
    border: 1px solid {p.borde};
    border-radius: 6px;
    padding: 0px;
    font-size: 15px;
    font-weight: 700;
    min-width: 26px;
    max-width: 26px;
    min-height: 26px;
    max-height: 26px;
}}
QPushButton#botonCelda:hover {{
    background-color: {p.seleccion};
    border-color: {p.primario};
}}
QPushButton#botonCelda:disabled {{
    color: {p.texto_apagado};
    border-color: {p.borde_suave};
}}

/* Tabla del carrito */
QTableWidget {{
    background-color: {p.superficie};
    border: 1px solid {p.borde};
    border-radius: 8px;
    gridline-color: {p.borde_suave};
    font-size: 15px;
}}
QTableWidget::item {{
    padding: 10px 8px;
}}
QTableWidget::item:selected {{
    background-color: {p.seleccion};
    color: {p.texto};
}}
QHeaderView::section {{
    background-color: {p.superficie_alterna};
    color: {p.texto_suave};
    border: none;
    border-bottom: 1px solid {p.borde};
    padding: 10px 8px;
    font-weight: 600;
    font-size: 13px;
}}

/* Panel de totales */
QLabel#etiquetaTotal {{
    color: {p.texto_suave};
    font-size: 14px;
}}
QLabel#valorSubtotal {{
    font-size: 20px;
    font-weight: 600;
}}
QLabel#valorDescuento {{
    font-size: 18px;
    font-weight: 600;
    color: {p.aviso};
}}
QLabel#valorTotal {{
    font-size: 46px;
    font-weight: 700;
    color: {p.exito};
}}

/* Pantalla de consulta de precio */
QLabel#consultaNombre {{
    font-size: 34px;
    font-weight: 600;
}}
QLabel#consultaPrecio {{
    font-size: 110px;
    font-weight: 700;
    color: {p.exito};
}}
QLabel#consultaDetalle {{
    font-size: 16px;
    color: {p.texto_suave};
}}
QLabel#consultaVacio {{
    font-size: 24px;
    color: {p.texto_suave};
}}

/* Mensajes en línea */
QLabel#mensajeError {{
    background-color: {p.error_suave};
    color: {p.error};
    border-radius: 8px;
    padding: 12px 14px;
    font-size: 15px;
    font-weight: 600;
}}
QLabel#mensajeExito {{
    background-color: {p.exito_suave};
    color: {p.exito};
    border-radius: 8px;
    padding: 12px 14px;
    font-size: 15px;
    font-weight: 600;
}}

/* El código que no se encontró, en grande para poder dictarlo o anotarlo */
QLabel#codigoNoEncontrado {{
    background-color: {p.error_suave};
    color: {p.error};
    border-radius: 8px;
    padding: 14px;
    font-size: 26px;
    font-weight: 700;
    letter-spacing: 2px;
}}

QStatusBar {{
    background-color: {p.superficie};
    border-top: 1px solid {p.borde};
    color: {p.texto_suave};
}}
QStatusBar::item {{
    border: none;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 12px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {p.barra_desplazamiento};
    border-radius: 6px;
    min-height: 30px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QToolTip {{
    background-color: {p.superficie};
    color: {p.texto};
    border: 1px solid {p.borde};
    padding: 6px 8px;
}}
"""


def aplicar(app, tema: str = TEMA_CLARO) -> Paleta:
    """Aplica el tema a la aplicación completa y devuelve la paleta que quedó activa.

    Cambiar la hoja de estilos en caliente basta para que toda la interfaz se repinte: Qt
    vuelve a resolver el estilo de cada widget existente, no solo de los nuevos. Por eso el
    tema se puede cambiar sin reiniciar el programa.
    """
    global actual
    actual = paleta_de(tema)
    app.setStyleSheet(hoja_de_estilos(actual))
    return actual
