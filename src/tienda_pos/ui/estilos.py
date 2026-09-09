"""Paleta y hoja de estilos de la aplicación.

Los colores y tamaños viven en un solo archivo para que cambiar la apariencia no obligue a
tocar la lógica de las pantallas.

Criterio de diseño: una caja se opera de pie, con prisa y a veces con mala luz. Por eso todo
lo importante es grande y de alto contraste, y el color se reserva para tres cosas: el total,
el éxito y el error. Un POS lleno de colores es un POS en el que no se distingue lo urgente.
"""

from __future__ import annotations

# --------------------------------------------------------------------------- paleta

FONDO = "#EEF1F5"
SUPERFICIE = "#FFFFFF"
BORDE = "#D3D9E0"
TEXTO = "#111827"
TEXTO_SUAVE = "#5B6673"

PRIMARIO = "#1D4ED8"
PRIMARIO_OSCURO = "#1E3A8A"
EXITO = "#15803D"
EXITO_SUAVE = "#DCFCE7"
ERROR = "#B91C1C"
ERROR_SUAVE = "#FEE2E2"
AVISO = "#B45309"

FUENTE = "Segoe UI, Inter, Roboto, sans-serif"


HOJA_DE_ESTILOS = f"""
QWidget {{
    background-color: {FONDO};
    color: {TEXTO};
    font-family: {FUENTE};
    font-size: 14px;
}}

/* Las etiquetas no pintan fondo: si lo hicieran, cada texto se vería como una caja gris
   sobre las tarjetas blancas y sobre la barra azul. Las que sí llevan fondo (los mensajes
   de éxito y error) lo declaran explícitamente más abajo. */
QLabel {{
    background: transparent;
}}

QLabel#tituloPantalla {{
    font-size: 22px;
    font-weight: 600;
}}

QLabel#subtitulo {{
    color: {TEXTO_SUAVE};
    font-size: 13px;
}}

/* Tarjetas blancas que agrupan contenido */
QFrame#tarjeta {{
    background-color: {SUPERFICIE};
    border: 1px solid {BORDE};
    border-radius: 10px;
}}

QFrame#barraSuperior {{
    background-color: {PRIMARIO_OSCURO};
    border: none;
}}

QLabel#marca {{
    color: #FFFFFF;
    font-size: 18px;
    font-weight: 600;
}}

QLabel#datosSesion {{
    color: #C7D2FE;
    font-size: 13px;
}}

/* El campo de escaneo: lo más importante de la pantalla */
QLineEdit#campoEscaneo {{
    background-color: {SUPERFICIE};
    border: 2px solid {PRIMARIO};
    border-radius: 8px;
    padding: 14px 16px;
    font-size: 26px;
    font-weight: 600;
    letter-spacing: 1px;
}}
QLineEdit#campoEscaneo:focus {{
    border: 3px solid {PRIMARIO};
}}

QLineEdit, QSpinBox, QComboBox {{
    background-color: {SUPERFICIE};
    border: 1px solid {BORDE};
    border-radius: 6px;
    padding: 8px 10px;
    font-size: 14px;
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border: 2px solid {PRIMARIO};
}}

QPushButton {{
    background-color: {SUPERFICIE};
    border: 1px solid {BORDE};
    border-radius: 8px;
    padding: 10px 16px;
    font-size: 14px;
    font-weight: 600;
}}
QPushButton:hover {{
    border-color: {PRIMARIO};
}}
QPushButton:pressed {{
    background-color: #E5EAF2;
}}
QPushButton:disabled {{
    color: #9AA3AF;
    border-color: #E3E7EC;
}}

QPushButton#botonPrincipal {{
    background-color: {EXITO};
    color: #FFFFFF;
    border: none;
    padding: 16px 20px;
    font-size: 18px;
}}
QPushButton#botonPrincipal:hover {{
    background-color: #166534;
}}
QPushButton#botonPrincipal:disabled {{
    background-color: #A7BDAF;
    color: #EEF2EE;
}}

QPushButton#botonPeligro {{
    color: {ERROR};
    border-color: #F0C2C2;
}}
QPushButton#botonPeligro:hover {{
    border-color: {ERROR};
}}
/* Sin esta regla, el color rojo del selector por id le gana al estado deshabilitado y el
   botón seguiría pareciendo pulsable con el carrito vacío. */
QPushButton#botonPeligro:disabled {{
    color: #9AA3AF;
    border-color: #E3E7EC;
}}

/* Tabla del carrito */
QTableWidget {{
    background-color: {SUPERFICIE};
    border: 1px solid {BORDE};
    border-radius: 8px;
    gridline-color: #EDF0F4;
    font-size: 15px;
}}
QTableWidget::item {{
    padding: 10px 8px;
}}
QTableWidget::item:selected {{
    background-color: #DBEAFE;
    color: {TEXTO};
}}
QHeaderView::section {{
    background-color: #F3F5F9;
    color: {TEXTO_SUAVE};
    border: none;
    border-bottom: 1px solid {BORDE};
    padding: 10px 8px;
    font-weight: 600;
    font-size: 13px;
}}

/* Panel de totales */
QLabel#etiquetaTotal {{
    color: {TEXTO_SUAVE};
    font-size: 14px;
}}
QLabel#valorSubtotal {{
    font-size: 20px;
    font-weight: 600;
}}
QLabel#valorDescuento {{
    font-size: 18px;
    font-weight: 600;
    color: {AVISO};
}}
QLabel#valorTotal {{
    font-size: 46px;
    font-weight: 700;
    color: {EXITO};
}}

/* Pantalla de consulta de precio */
QLabel#consultaNombre {{
    font-size: 34px;
    font-weight: 600;
}}
QLabel#consultaPrecio {{
    font-size: 110px;
    font-weight: 700;
    color: {EXITO};
}}
QLabel#consultaDetalle {{
    font-size: 16px;
    color: {TEXTO_SUAVE};
}}
QLabel#consultaVacio {{
    font-size: 24px;
    color: {TEXTO_SUAVE};
}}

/* Mensajes en línea */
QLabel#mensajeError {{
    background-color: {ERROR_SUAVE};
    color: {ERROR};
    border-radius: 8px;
    padding: 12px 14px;
    font-size: 15px;
    font-weight: 600;
}}
QLabel#mensajeExito {{
    background-color: {EXITO_SUAVE};
    color: {EXITO};
    border-radius: 8px;
    padding: 12px 14px;
    font-size: 15px;
    font-weight: 600;
}}

QStatusBar {{
    background-color: {SUPERFICIE};
    border-top: 1px solid {BORDE};
    color: {TEXTO_SUAVE};
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
    background: #C4CBD4;
    border-radius: 6px;
    min-height: 30px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
"""


def aplicar(app) -> None:
    """Aplica la hoja de estilos a la aplicación completa."""
    app.setStyleSheet(HOJA_DE_ESTILOS)
