"""Genera el icono de la aplicación.

Se dibuja con Qt y se empaqueta como .ico para que Windows lo use en el ejecutable, en la
barra de tareas y en el acceso directo. Un programa sin icono propio parece un experimento;
uno con icono parece un producto, y en una demostración eso pesa.

El .ico se construye a mano incrustando PNG, que es lo que Windows admite desde Vista. Se
evita así añadir Pillow como dependencia solo para esto.

    python tools/icono.py
"""

from __future__ import annotations

import os
import struct
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

# La plataforma "offscreen" de Qt no carga las fuentes del sistema, asi que en Windows se
# usa la nativa.
os.environ.setdefault("QT_QPA_PLATFORM", "windows" if os.name == "nt" else "offscreen")

from PySide6.QtCore import QBuffer, QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

TAMANOS = (16, 32, 48, 64, 128, 256)

#: El rojo del logotipo. No se lee de la paleta de la interfaz porque la marca no cambia con
#: el tema: el círculo es rojo tanto de día como de noche.
# El rojo exacto de la marca. El icono del ejecutable es un objeto de marca que se ve a 32 px
# sobre el escritorio, no texto que haya que leer, así que aquí no se aplica el ajuste de
# contraste que sí lleva el acento de la interfaz (ver `ui/estilos.py`).
_ROJO = "#E30119"
_FONDO = "#FFFFFF"


def _logotipo_del_cliente() -> "QImage | None":
    """El archivo de logotipo, si lo hay.

    Mientras no exista, el icono se dibuja. En cuanto alguien deje `assets/logo.png`, esta
    herramienta lo usa sin tocar nada más.
    """
    for nombre in ("logo.png", "logo.jpg", "logo.jpeg"):
        archivo = RAIZ / "assets" / nombre
        if archivo.exists():
            imagen = QImage(str(archivo))
            if not imagen.isNull():
                return imagen
    return None


def dibujar(lado: int, logotipo: "QImage | None" = None) -> QImage:
    """Un icono cuadrado con la marca centrada sobre fondo blanco.

    El fondo es blanco y no transparente a propósito: el logotipo es rojo sobre blanco, y
    sobre una barra de tareas oscura el rojo solo se sostiene si lleva su papel debajo.
    """
    imagen = QImage(lado, lado, QImage.Format.Format_ARGB32)
    imagen.fill(Qt.GlobalColor.transparent)

    pintor = QPainter(imagen)
    pintor.setRenderHint(QPainter.RenderHint.Antialiasing)
    pintor.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

    pintor.setBrush(QColor(_FONDO))
    pintor.setPen(Qt.PenStyle.NoPen)
    radio = lado * 0.22
    pintor.drawRoundedRect(QRectF(0, 0, lado, lado), radio, radio)

    if logotipo is not None:
        margen = lado * 0.10
        util = lado - 2 * margen
        reducido = logotipo.scaled(
            int(util),
            int(util),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        pintor.drawImage(
            QRectF(
                (lado - reducido.width()) / 2,
                (lado - reducido.height()) / 2,
                reducido.width(),
                reducido.height(),
            ),
            reducido,
        )
        pintor.end()
        return imagen

    # Sin archivo, se dibuja la marca: el círculo rojo con su tallo. Es la parte del
    # logotipo que sobrevive a 16 píxeles; el lettering a ese tamaño sería una mancha.
    unidad = lado / 24.0
    pintor.scale(unidad, unidad)

    pluma = QPen(QColor(_ROJO), 2.1)
    pluma.setCapStyle(Qt.PenCapStyle.RoundCap)
    pintor.setPen(pluma)
    pintor.setBrush(Qt.BrushStyle.NoBrush)
    tallo = QPainterPath(QPointF(12.7, 8.4))
    tallo.cubicTo(16.8, 3.4, 21.0, 6.6, 20.4, 14.2)
    pintor.drawPath(tallo)

    pintor.setPen(Qt.PenStyle.NoPen)
    pintor.setBrush(QColor(_ROJO))
    pintor.drawEllipse(QPointF(10.4, 14.4), 7.6, 7.6)

    pintor.end()
    return imagen


def _a_png(imagen: QImage) -> bytes:
    # QBuffer sin argumentos usa su propio almacenamiento interno. Pasarle un QByteArray
    # recién creado deja un puntero a un objeto temporal y el proceso termina en un segfault.
    buffer = QBuffer()
    buffer.open(QBuffer.OpenModeFlag.WriteOnly)
    imagen.save(buffer, "PNG")
    buffer.close()
    return bytes(buffer.data())


def construir_ico(destino: Path) -> Path:
    """Escribe un .ico con todos los tamaños, cada uno incrustado como PNG."""
    logotipo = _logotipo_del_cliente()
    imagenes = [_a_png(dibujar(lado, logotipo)) for lado in TAMANOS]

    cabecera = struct.pack("<HHH", 0, 1, len(TAMANOS))
    desplazamiento = len(cabecera) + 16 * len(TAMANOS)

    entradas = b""
    for lado, datos in zip(TAMANOS, imagenes):
        # En el formato ICO, 256 se codifica como 0.
        medida = 0 if lado >= 256 else lado
        entradas += struct.pack(
            "<BBBBHHII", medida, medida, 0, 0, 1, 32, len(datos), desplazamiento
        )
        desplazamiento += len(datos)

    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(cabecera + entradas + b"".join(imagenes))
    return destino


if __name__ == "__main__":
    app = QApplication.instance() or QApplication(sys.argv)
    ico = construir_ico(RAIZ / "assets" / "punto_y_fama.ico")
    png = RAIZ / "assets" / "punto_y_fama.png"
    dibujar(256, _logotipo_del_cliente()).save(str(png))
    origen = "assets/logo.png" if _logotipo_del_cliente() is not None else "la marca dibujada"
    print(f"Icono generado desde {origen}: {ico.relative_to(RAIZ)} y {png.relative_to(RAIZ)}")
