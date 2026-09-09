"""Genera capturas de pantalla de la aplicación sin intervención manual.

Sirve para dos cosas: ilustrar el manual de usuario y revisar el aspecto de la interfaz sin
tener que abrirla y encuadrar a mano cada pantalla.

Se ejecuta con una base de datos en memoria y datos de ejemplo, de modo que no toca los datos
reales. Con QT_QPA_PLATFORM=offscreen funciona incluso sin escritorio disponible.

    python tools/capturas.py [carpeta_destino]
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

# Debe fijarse antes de importar Qt.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from tienda_pos.db.inicio import abrir_base_datos  # noqa: E402
from tienda_pos.db.seed import codigo_demo  # noqa: E402
from tienda_pos.domain.models import Rol, Usuario  # noqa: E402
from tienda_pos.ui import estilos  # noqa: E402
from tienda_pos.ui.main_window import VentanaPrincipal  # noqa: E402

ANCHO, ALTO = 1280, 800


def _guardar(ventana: VentanaPrincipal, destino: Path, nombre: str) -> Path:
    QApplication.processEvents()
    ruta = destino / f"{nombre}.png"
    ventana.grab().save(str(ruta))
    print(f"  {ruta.relative_to(RAIZ)}")
    return ruta


def generar(destino: Path) -> list[Path]:
    destino.mkdir(parents=True, exist_ok=True)

    app = QApplication.instance() or QApplication(sys.argv)
    estilos.aplicar(app)

    conexion = abrir_base_datos(":memory:", con_datos_demo=True)
    ventana = VentanaPrincipal(conexion)
    ventana.resize(ANCHO, ALTO)
    ventana.establecer_usuario(Usuario(id=1, nombre="Ana Pérez", rol=Rol.CAJERO))
    ventana.show()

    generadas = []
    print("Generando capturas:")

    # 1. Pantalla de venta vacía, tal como la ve el cajero al abrir.
    ventana.mostrar_venta()
    generadas.append(_guardar(ventana, destino, "01-venta-vacia"))

    # 2. Venta con varios productos escaneados.
    for indice in (0, 0, 10, 19, 35, 52):
        ventana.vista_venta.agregar_por_codigo(codigo_demo(indice))
    generadas.append(_guardar(ventana, destino, "02-venta-con-carrito"))

    # 3. Consulta de precio con un producto encontrado.
    ventana.mostrar_consulta()
    ventana.vista_consulta.consultar(codigo_demo(35))
    generadas.append(_guardar(ventana, destino, "03-consulta-precio"))

    # 4. Consulta de un código que no existe en el catálogo.
    ventana.vista_consulta.consultar("7790000000017")
    generadas.append(_guardar(ventana, destino, "04-consulta-no-encontrado"))

    conexion.close()
    return generadas


if __name__ == "__main__":
    carpeta = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "docs" / "img"
    generar(carpeta)
