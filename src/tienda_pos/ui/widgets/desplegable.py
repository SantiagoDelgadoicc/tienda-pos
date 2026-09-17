"""Desplegable con el chevrón dibujado a mano.

Existe por un detalle de Qt que no tiene arreglo desde la hoja de estilos. Qt pinta el botón
del desplegable como un subcontrol con marco propio, cuadrado, que asoma por encima del radio
de cápsula del campo y lo rompe. Cualquier regla sobre `QComboBox::drop-down` lo apaga, pero
se lleva por delante también la flecha: Qt solo la dibuja mientras el subcontrol conserva su
estilo nativo, de modo que o se queda el marco cuadrado o se queda sin flecha.

La salida es apagar el subcontrol entero en la hoja de estilos y pintar aquí el chevrón, que
además así sale con el color del tema en vez de con el negro del estilo nativo.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QComboBox, QWidget

from .. import estilos

#: Medidas del chevrón, en píxeles.
_ANCHO = 10
_ALTO = 5
_GROSOR = 1.6
#: Distancia entre la punta derecha del chevrón y el borde del campo. Coincide con el relleno
#: que la hoja de estilos reserva a la derecha, para que el texto nunca pase por debajo.
_MARGEN_DERECHO = 18


class Desplegable(QComboBox):
    """`QComboBox` que dibuja su propia flecha."""

    def __init__(self, padre: QWidget | None = None) -> None:
        super().__init__(padre)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, evento) -> None:  # noqa: N802 - lo nombra Qt
        super().paintEvent(evento)

        paleta = estilos.actual
        color = QColor(paleta.texto_suave if self.isEnabled() else paleta.texto_apagado)
        lapiz = QPen(color, _GROSOR)
        lapiz.setCapStyle(Qt.PenCapStyle.RoundCap)
        lapiz.setJoinStyle(Qt.PenJoinStyle.RoundJoin)

        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.RenderHint.Antialiasing)
        pintor.setPen(lapiz)

        derecha = self.width() - _MARGEN_DERECHO
        izquierda = derecha - _ANCHO
        centro = self.height() / 2

        camino = QPainterPath()
        camino.moveTo(izquierda, centro - _ALTO / 2)
        camino.lineTo((izquierda + derecha) / 2, centro + _ALTO / 2)
        camino.lineTo(derecha, centro - _ALTO / 2)
        pintor.drawPath(camino)
        pintor.end()
