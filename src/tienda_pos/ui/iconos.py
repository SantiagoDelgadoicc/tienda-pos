"""Iconos de línea dibujados con QPainter.

No hay biblioteca de iconos ni archivos de imagen, y es a propósito: un puñado de trazos
geométricos pesa nada, se colorea con la paleta del tema —cosa que un PNG no hace— y no
añade nada que empaquetar en el ejecutable.

Todos se dibujan sobre una rejilla de 24×24 y se escalan al tamaño pedido, con trazo de
1,7 px y remates redondos, que es el estilo de icono que pide `docs/DESIGN.md`.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

from ..config import directorio_recursos

#: Lado de la rejilla sobre la que están dibujados todos los iconos.
_REJILLA = 24.0
_GROSOR = 1.7

#: El rojo del logotipo. Vive aquí y no en la paleta porque la marca no cambia con el
#: tema: el círculo es rojo tanto de día como de noche.
ROJO_MARCA = "#BE1E2D"

#: Centinela para distinguir "todavía no he mirado" de "miré y no hay archivo".
_SIN_BUSCAR = object()
_RUTA_LOGOTIPO: "Path | None | object" = _SIN_BUSCAR


def _trazo(pintor: QPainter, color: QColor, grosor: float = _GROSOR) -> None:
    pluma = QPen(color, grosor)
    pluma.setCapStyle(Qt.PenCapStyle.RoundCap)
    pluma.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    pintor.setPen(pluma)
    pintor.setBrush(Qt.BrushStyle.NoBrush)


def _escanear(pintor: QPainter, color: QColor) -> None:
    """Código de barras entre las cuatro esquinas del visor del lector."""
    _trazo(pintor, color)
    for x1, y1, x2, y2, x3, y3 in (
        (4, 8, 4, 4, 8, 4),
        (16, 4, 20, 4, 20, 8),
        (20, 16, 20, 20, 16, 20),
        (8, 20, 4, 20, 4, 16),
    ):
        esquina = QPainterPath(QPointF(x1, y1))
        esquina.lineTo(x2, y2)
        esquina.lineTo(x3, y3)
        pintor.drawPath(esquina)

    _trazo(pintor, color, 1.5)
    for x in (8.5, 11.5, 15.5):
        pintor.drawLine(QPointF(x, 8.5), QPointF(x, 15.5))
    _trazo(pintor, color, 2.6)
    pintor.drawLine(QPointF(13.5, 8.5), QPointF(13.5, 15.5))


def _etiqueta(pintor: QPainter, color: QColor) -> None:
    """Etiqueta de precio: el rombo con su ojal."""
    _trazo(pintor, color)
    pintor.save()
    pintor.translate(12, 12)
    pintor.rotate(45)
    cuerpo = QPainterPath()
    cuerpo.addRoundedRect(QRectF(-7.5, -7.5, 15, 15), 3, 3)
    pintor.drawPath(cuerpo)
    pintor.restore()
    pintor.drawEllipse(QPointF(9.2, 9.2), 1.3, 1.3)


def _catalogo(pintor: QPainter, color: QColor) -> None:
    """Cuatro celdas: la rejilla del catálogo."""
    _trazo(pintor, color)
    for x, y in ((4, 4), (13.5, 4), (4, 13.5), (13.5, 13.5)):
        celda = QPainterPath()
        celda.addRoundedRect(QRectF(x, y, 6.5, 6.5), 2, 2)
        pintor.drawPath(celda)


def _informe(pintor: QPainter, color: QColor) -> None:
    """Tres barras de distinta altura."""
    _trazo(pintor, color, 2.6)
    for x, alto in ((6.5, 5.5), (12, 10), (17.5, 14)):
        pintor.drawLine(QPointF(x, 19), QPointF(x, 19 - alto))


def _ajustes(pintor: QPainter, color: QColor) -> None:
    """Dos correderas: el icono de configuración sin recurrir a un engranaje."""
    _trazo(pintor, color)
    pintor.drawLine(QPointF(4, 9), QPointF(20, 9))
    pintor.drawLine(QPointF(4, 15), QPointF(20, 15))
    pintor.setBrush(QColor(color))
    pintor.drawEllipse(QPointF(9, 9), 2.2, 2.2)
    pintor.drawEllipse(QPointF(15, 15), 2.2, 2.2)


def _salir(pintor: QPainter, color: QColor) -> None:
    """Puerta abierta con la flecha saliendo."""
    _trazo(pintor, color)
    puerta = QPainterPath(QPointF(13, 4.5))
    puerta.lineTo(5.5, 4.5)
    puerta.lineTo(5.5, 19.5)
    puerta.lineTo(13, 19.5)
    pintor.drawPath(puerta)
    pintor.drawLine(QPointF(11.5, 12), QPointF(20, 12))
    flecha = QPainterPath(QPointF(17.2, 9))
    flecha.lineTo(20.2, 12)
    flecha.lineTo(17.2, 15)
    pintor.drawPath(flecha)


def _usuario(pintor: QPainter, color: QColor) -> None:
    _trazo(pintor, color)
    pintor.drawEllipse(QPointF(12, 9), 3.6, 3.6)
    hombros = QPainterPath(QPointF(5.2, 19.8))
    hombros.cubicTo(6.2, 15.2, 17.8, 15.2, 18.8, 19.8)
    pintor.drawPath(hombros)


def _reloj(pintor: QPainter, color: QColor) -> None:
    _trazo(pintor, color)
    pintor.drawEllipse(QPointF(12, 12), 8, 8)
    pintor.drawLine(QPointF(12, 7.5), QPointF(12, 12))
    pintor.drawLine(QPointF(12, 12), QPointF(15.5, 13.8))


def _buscar(pintor: QPainter, color: QColor) -> None:
    _trazo(pintor, color)
    pintor.drawEllipse(QPointF(10.8, 10.8), 6, 6)
    pintor.drawLine(QPointF(15.3, 15.3), QPointF(20, 20))


def _plegar(pintor: QPainter, color: QColor) -> None:
    """Doble ángulo hacia la izquierda: plegar la barra lateral."""
    _trazo(pintor, color)
    for desplazamiento in (0, 5.5):
        angulo = QPainterPath(QPointF(14.5 - desplazamiento, 7))
        angulo.lineTo(9.5 - desplazamiento, 12)
        angulo.lineTo(14.5 - desplazamiento, 17)
        pintor.drawPath(angulo)


def _desplegar(pintor: QPainter, color: QColor) -> None:
    """El mismo, hacia la derecha: devolver la barra lateral a su sitio."""
    _trazo(pintor, color)
    for desplazamiento in (0, 5.5):
        angulo = QPainterPath(QPointF(9.5 + desplazamiento, 7))
        angulo.lineTo(14.5 + desplazamiento, 12)
        angulo.lineTo(9.5 + desplazamiento, 17)
        pintor.drawPath(angulo)


def _caja(pintor: QPainter, color: QColor) -> None:
    """Cajas apiladas: el stock de un producto."""
    _trazo(pintor, color)
    cuerpo = QPainterPath()
    cuerpo.addRoundedRect(QRectF(3.5, 8.5, 17, 11), 2, 2)
    pintor.drawPath(cuerpo)
    pintor.drawLine(QPointF(3.5, 12.5), QPointF(20.5, 12.5))
    pintor.drawLine(QPointF(12, 8.5), QPointF(12, 19.5))
    tapa = QPainterPath(QPointF(6.5, 8.5))
    tapa.lineTo(8.5, 4.5)
    tapa.lineTo(15.5, 4.5)
    tapa.lineTo(17.5, 8.5)
    pintor.drawPath(tapa)


def _enlace(pintor: QPainter, color: QColor) -> None:
    """Dos nodos unidos: el estado de la conexión entre las dos cajas."""
    _trazo(pintor, color)
    pintor.drawLine(QPointF(8.5, 12), QPointF(15.5, 12))
    pintor.setBrush(QColor(color))
    pintor.drawEllipse(QPointF(6, 12), 2.4, 2.4)
    pintor.drawEllipse(QPointF(18, 12), 2.4, 2.4)


_DIBUJOS = {
    "escanear": _escanear,
    "etiqueta": _etiqueta,
    "catalogo": _catalogo,
    "informe": _informe,
    "ajustes": _ajustes,
    "salir": _salir,
    "usuario": _usuario,
    "reloj": _reloj,
    "buscar": _buscar,
    "enlace": _enlace,
    "plegar": _plegar,
    "desplegar": _desplegar,
    "caja": _caja,
}

NOMBRES = tuple(_DIBUJOS)


def pixmap(nombre: str, tamano: int, color: str, escala: float = 2.0) -> QPixmap:
    """Dibuja un icono y lo devuelve como mapa de píxeles.

    Se pinta al doble de resolución y se marca con esa proporción para que no salga borroso
    en una pantalla con escalado de Windows, que es lo normal en un portátil moderno.
    """
    lado = int(tamano * escala)
    lienzo = QPixmap(lado, lado)
    lienzo.fill(Qt.GlobalColor.transparent)
    lienzo.setDevicePixelRatio(escala)

    pintor = QPainter(lienzo)
    pintor.setRenderHint(QPainter.RenderHint.Antialiasing)
    pintor.scale(tamano / _REJILLA, tamano / _REJILLA)
    _DIBUJOS[nombre](pintor, QColor(color))
    pintor.end()
    return lienzo


def icono(nombre: str, tamano: int, color: str) -> QIcon:
    """El mismo dibujo, envuelto en un QIcon para ponérselo a un botón."""
    return QIcon(pixmap(nombre, tamano, color))


def logotipo(tamano: int, escala: float = 2.0) -> QPixmap:
    """La marca del negocio, al tamaño pedido.

    Si existe `assets/logo.png` se usa ese archivo, que es el logotipo de verdad. Si no, se
    dibuja la marca —el círculo rojo con su tallo— que es la parte del logotipo que
    sobrevive a 24 píxeles; el lettering a ese tamaño sería una mancha de todas formas.
    """
    archivo = _archivo_de_logotipo()
    if archivo is not None:
        original = QPixmap(str(archivo))
        if not original.isNull():
            lado = int(tamano * escala)
            reducido = original.scaled(
                lado,
                lado,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            reducido.setDevicePixelRatio(escala)
            return reducido
    return marca_dibujada(tamano, escala)


def _archivo_de_logotipo() -> "Path | None":
    """Busca el logotipo junto al programa. El resultado se recuerda: esto se llama en cada
    repintado y mirar el disco cada vez no tiene sentido."""
    global _RUTA_LOGOTIPO
    if _RUTA_LOGOTIPO is _SIN_BUSCAR:
        _RUTA_LOGOTIPO = None
        try:
            for nombre in ("logo.png", "logo.jpg", "logo.jpeg"):
                candidato = directorio_recursos() / nombre
                if candidato.exists():
                    _RUTA_LOGOTIPO = candidato
                    break
        except OSError:
            _RUTA_LOGOTIPO = None
    return _RUTA_LOGOTIPO


def marca_dibujada(tamano: int, escala: float = 2.0) -> QPixmap:
    """El círculo rojo de «Punto y Fama», con el tallo que le sale por arriba."""
    lado = int(tamano * escala)
    lienzo = QPixmap(lado, lado)
    lienzo.fill(Qt.GlobalColor.transparent)
    lienzo.setDevicePixelRatio(escala)

    pintor = QPainter(lienzo)
    pintor.setRenderHint(QPainter.RenderHint.Antialiasing)
    pintor.scale(tamano / _REJILLA, tamano / _REJILLA)

    rojo = QColor(ROJO_MARCA)

    # El tallo va primero: el círculo lo tapa donde nacen, que es como está en el logotipo.
    pluma = QPen(rojo, 2.1)
    pluma.setCapStyle(Qt.PenCapStyle.RoundCap)
    pintor.setPen(pluma)
    pintor.setBrush(Qt.BrushStyle.NoBrush)
    tallo = QPainterPath(QPointF(12.5, 8.0))
    tallo.cubicTo(17.0, 2.6, 21.8, 6.0, 21.2, 14.5)
    pintor.drawPath(tallo)

    pintor.setPen(Qt.PenStyle.NoPen)
    pintor.setBrush(rojo)
    pintor.drawEllipse(QPointF(10.0, 14.0), 8.6, 8.6)
    pintor.end()
    return lienzo
