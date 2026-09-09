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

# La plataforma "offscreen" de Qt no carga las fuentes del sistema y el simbolo de precio
# saldria vacio, asi que en Windows se usa la nativa.
os.environ.setdefault("QT_QPA_PLATFORM", "windows" if os.name == "nt" else "offscreen")

from PySide6.QtCore import QBuffer, QRectF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QFont, QImage, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

TAMANOS = (16, 32, 48, 64, 128, 256)

_FONDO = "#1E3A8A"
_BARRA = "#FFFFFF"
_ACENTO = "#22C55E"

# Anchos relativos de las barras del código, para que parezca un código de barras real y no
# una reja uniforme.
_PATRON = (3, 1, 2, 1, 1, 3, 1, 2, 1, 1, 2, 3)


def dibujar(lado: int) -> QImage:
    imagen = QImage(lado, lado, QImage.Format.Format_ARGB32)
    imagen.fill(Qt.GlobalColor.transparent)

    pintor = QPainter(imagen)
    pintor.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Fondo redondeado.
    pintor.setBrush(QColor(_FONDO))
    pintor.setPen(Qt.PenStyle.NoPen)
    radio = lado * 0.22
    pintor.drawRoundedRect(QRectF(0, 0, lado, lado), radio, radio)

    # Código de barras centrado en la mitad superior.
    margen = lado * 0.18
    arriba = lado * 0.22
    alto_barras = lado * 0.40
    ancho_util = lado - 2 * margen
    unidades = sum(_PATRON) + len(_PATRON)  # barras más un espacio entre cada una
    unidad = ancho_util / unidades

    pintor.setBrush(QColor(_BARRA))
    x = margen
    for ancho in _PATRON:
        pintor.drawRect(QRectF(x, arriba, unidad * ancho, alto_barras))
        x += unidad * (ancho + 1)

    # Símbolo de precio bajo el código. En los tamaños diminutos el texto se convierte en una
    # mancha ilegible, así que se sustituye por una barra de color.
    if lado >= 32:
        pintor.setPen(QColor(_ACENTO))
        fuente = QFont("Segoe UI", int(lado * 0.30), QFont.Weight.Bold)
        pintor.setFont(fuente)
        pintor.drawText(
            QRectF(0, lado * 0.60, lado, lado * 0.32),
            Qt.AlignmentFlag.AlignCenter,
            "$",
        )
    else:
        pintor.setBrush(QColor(_ACENTO))
        pintor.setPen(Qt.PenStyle.NoPen)
        pintor.drawRect(QRectF(margen, lado * 0.70, ancho_util, lado * 0.12))

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
    imagenes = [_a_png(dibujar(lado)) for lado in TAMANOS]

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
    ico = construir_ico(RAIZ / "assets" / "tienda_pos.ico")
    png = RAIZ / "assets" / "tienda_pos.png"
    dibujar(256).save(str(png))
    print(f"Icono generado: {ico.relative_to(RAIZ)} y {png.relative_to(RAIZ)}")
