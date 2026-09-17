"""Genera capturas de pantalla de la aplicación sin intervención manual.

Sirve para dos cosas: ilustrar el manual de usuario y revisar el aspecto de la interfaz sin
tener que abrirla y encuadrar a mano cada pantalla.

Se ejecuta con una base de datos en memoria y datos de ejemplo, de modo que no toca los datos
reales.

    python tools/capturas.py [carpeta_destino]

Nota: en Windows conviene ejecutarlo con la plataforma nativa, porque la plataforma
"offscreen" de Qt no carga las fuentes del sistema y el texto sale como cajas vacías:

    QT_QPA_PLATFORM=windows python tools/capturas.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

# Debe fijarse antes de importar Qt.
os.environ.setdefault("QT_QPA_PLATFORM", "windows" if os.name == "nt" else "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from tienda_pos.db.inicio import abrir_base_datos  # noqa: E402
from tienda_pos.db.seed import codigo_demo  # noqa: E402
from tienda_pos.domain.models import Rol, Usuario  # noqa: E402
from tienda_pos.red.sesion import SesionLocal  # noqa: E402
from tienda_pos.services import preferencias as servicio_preferencias  # noqa: E402
from tienda_pos.ui import estilos  # noqa: E402
from tienda_pos.ui.login_dialog import DialogoLogin  # noqa: E402
from tienda_pos.ui.main_window import VentanaPrincipal  # noqa: E402

ANCHO, ALTO = 1280, 800

CAJERA = Usuario(id=2, nombre="Ana Pérez", rol=Rol.CAJERO)


def _guardar(widget, destino: Path, nombre: str) -> Path:
    QApplication.processEvents()
    ruta = destino / f"{nombre}.png"
    widget.grab().save(str(ruta))
    print(f"  {ruta.relative_to(RAIZ)}")
    return ruta


def _silenciar_dialogos() -> None:
    """Responde automáticamente a los diálogos modales.

    Sin esto, la primera venta que se cobra abre una confirmación y el proceso se queda
    esperando un clic que nadie va a dar.
    """
    from tienda_pos.ui import dialogos

    dialogos.confirmar = lambda *args, **kwargs: True
    dialogos.mostrar_info = lambda *args, **kwargs: None
    dialogos.mostrar_error = lambda *args, **kwargs: None


def generar(destino: Path) -> list[Path]:
    destino.mkdir(parents=True, exist_ok=True)
    _silenciar_dialogos()

    app = QApplication.instance() or QApplication(sys.argv)
    estilos.aplicar(app, servicio_preferencias.TEMA_CLARO)

    conexion = abrir_base_datos(":memory:", con_datos_demo=True)
    # Las pantallas hablan con una Sesion, no con la conexion: es lo que permite que la
    # misma interfaz funcione contra la base local o contra el servidor de la otra caja.
    sesion = SesionLocal(conexion)
    ventana = VentanaPrincipal(sesion)
    # Las capturas no deben depender de los ajustes que tenga guardados quien las genera.
    ventana.aplicar_preferencias(servicio_preferencias.Preferencias())
    ventana.resize(ANCHO, ALTO)
    ventana.establecer_usuario(CAJERA)
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

    # 5. Diálogo de acceso.
    dialogo = DialogoLogin(sesion)
    dialogo.show()
    generadas.append(_guardar(dialogo, destino, "05-acceso"))
    dialogo.close()

    # A partir de aquí se necesita un administrador de verdad.
    administrador = sesion.autenticar("Administrador", "1234")
    ventana.establecer_usuario(administrador)

    # 6. Administración del catálogo.
    ventana.mostrar_productos()
    generadas.append(_guardar(ventana, destino, "06-productos"))

    # 7. Ventas del día, con un par de ventas ya registradas.
    ventana.mostrar_venta()
    for compra in ((0, 10, 19), (35, 35, 52, 44)):
        for indice in compra:
            ventana.vista_venta.agregar_por_codigo(codigo_demo(indice))
        ventana.vista_venta.cobrar()
    ventana.mostrar_reportes()
    generadas.append(_guardar(ventana, destino, "07-ventas-del-dia"))

    # 8. Descuento aplicado a un solo producto: la columna "Desc." solo aparece aquí.
    ventana.mostrar_venta()
    ventana.vista_venta.carrito.vaciar()
    for indice in (0, 10, 19, 35):
        ventana.vista_venta.agregar_por_codigo(codigo_demo(indice))
    ventana.vista_venta.carrito.aplicar_descuento_linea_porcentaje(codigo_demo(10), 20)
    ventana.vista_venta._refrescar()
    generadas.append(_guardar(ventana, destino, "08-descuento-por-producto"))

    # 9. La misma pantalla en tema oscuro, para poder compararlas de un vistazo.
    ventana.aplicar_tema(servicio_preferencias.TEMA_OSCURO)
    generadas.append(_guardar(ventana, destino, "09-tema-oscuro"))
    ventana.aplicar_tema(servicio_preferencias.TEMA_CLARO)

    # 10. La barra lateral plegada a tira de iconos.
    ventana.mostrar_venta()
    for indice in (0, 10, 19):
        ventana.vista_venta.agregar_por_codigo(codigo_demo(indice))
    ventana.barra_lateral.plegar(True)
    generadas.append(_guardar(ventana, destino, "11-barra-plegada"))
    ventana.barra_lateral.plegar(False)

    # 11. La rueda de configuración.
    from tienda_pos.ui.configuracion_dialog import DialogoConfiguracion

    configuracion = DialogoConfiguracion(servicio_preferencias.Preferencias(), ventana)
    configuracion.show()
    generadas.append(_guardar(configuracion, destino, "10-configuracion"))
    configuracion.close()

    conexion.close()
    return generadas


if __name__ == "__main__":
    carpeta = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "docs" / "img"
    generar(carpeta)
