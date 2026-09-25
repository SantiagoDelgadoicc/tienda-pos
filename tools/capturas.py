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
from tienda_pos.ui import estilos, movimiento  # noqa: E402
from tienda_pos.ui.login_dialog import DialogoLogin  # noqa: E402
from tienda_pos.ui.main_window import VentanaPrincipal  # noqa: E402

ANCHO, ALTO = 1280, 800

CAJERA = Usuario(id=2, nombre="Ana Pérez", rol=Rol.CAJERO)


def _guardar(widget, destino: Path, nombre: str) -> Path:
    QApplication.processEvents()
    ruta = destino / f"{nombre}.png"
    widget.grab().save(str(ruta))
    # Relativa al proyecto cuando cae dentro; la carpeta de destino puede estar en cualquier sitio.
    print(f"  {ruta.relative_to(RAIZ) if ruta.is_relative_to(RAIZ) else ruta}")
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
    # Las capturas enseñan cada pantalla en reposo. Con el movimiento encendido saldrían a
    # medio fundido: el aviso transparente y la última línea del carrito todavía en verde.
    movimiento.suprimir()
    estilos.aplicar(app, servicio_preferencias.TEMA_CLARO)

    conexion = abrir_base_datos(":memory:", con_datos_demo=True)
    # Las pantallas hablan con una Sesion, no con la conexion: es lo que permite que la
    # misma interfaz funcione contra la base local o contra el servidor de la otra caja.
    # Con nombre de caja, como toda caja de verdad (D-033): el cierre la muestra.
    sesion = SesionLocal(conexion, caja="Caja 1")
    # Las dos cajas abiertas desde el principio: desde la fase 19 no se cobra con la caja
    # cerrada, y el diálogo de apertura se quedaría esperando un clic (D-036).
    encargado = sesion.autenticar("Administrador", "1234")
    sesion.abrir_turno(encargado, 50_000, "captura-apertura-1")
    sesion.abrir_turno(encargado, 30_000, "captura-apertura-2", caja="Caja 2")
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

    # 12. Usuarios por empleado (fase 15), con uno dado de baja para que se vea cómo queda.
    from tienda_pos.domain.models import Rol
    from tienda_pos.ui.usuarios_view import DialogoPin

    for nombre in ("Marta Rojas", "Pedro Soto", "Luis Araya"):
        usuario, _ = sesion.alta_usuario(administrador, nombre, Rol.CAJERO)
        if nombre == "Luis Araya":
            sesion.desactivar_usuario(administrador, usuario.id)
    ventana.mostrar_usuarios()
    ventana.vista_usuarios.casilla_bajas.setChecked(True)
    generadas.append(_guardar(ventana, destino, "12-usuarios"))

    # 13. El PIN recién generado. Se fija a mano: con uno al azar, la captura cambiaría en
    # cada ejecución y ensuciaría el historial del repositorio.
    marta = next(u for u in sesion.listar_para_administrar(administrador) if u.nombre == "Marta Rojas")
    pin = DialogoPin("Usuario creado", marta, "5706", ventana)
    pin.show()
    generadas.append(_guardar(pin, destino, "13-pin-generado"))
    pin.close()

    # 14. Cierre de caja (fase 18): dos empleados en la misma caja, los tres medios, y otra
    # caja que también vendió, para que se vea el desplegable. La primera venta, abierta.
    from tienda_pos.domain.models import MedioPago
    from tienda_pos.services.venta import Carrito

    empleados = {u.nombre: u for u in sesion.listar_para_administrar(administrador)}
    ventas_del_cierre = (
        ("Marta Rojas", MedioPago.DEBITO, (35, 52, 44), "Caja 1"),
        ("Pedro Soto", MedioPago.EFECTIVO, (0, 0, 19), "Caja 1"),
        ("Marta Rojas", MedioPago.CREDITO, (10, 12), "Caja 1"),
        ("Pedro Soto", MedioPago.DEBITO, (3,), "Caja 2"),
    )
    for numero, (nombre, medio, indices, caja) in enumerate(ventas_del_cierre):
        carrito = Carrito()
        for indice in indices:
            carrito.agregar(sesion.consultar_por_codigo(codigo_demo(indice)))
        sesion.cerrar_venta(
            carrito, empleados[nombre], f"captura-{numero}", medio_pago=medio, caja=caja
        )
    ventana.mostrar_cierre()
    ventana.vista_cierre.arbol_ventas.topLevelItem(0).setExpanded(True)
    generadas.append(_guardar(ventana, destino, "14-cierre"))

    # 15. Efectivo (fase 19), como lo ve el administrador: un pago a proveedor, un retiro y un
    # ingreso en la caja 1, y la caja 2 ya cerrada con una diferencia, abajo.
    from tienda_pos.domain.models import TipoMovimiento

    marta_rojas = empleados["Marta Rojas"]
    sesion.registrar_movimiento(marta_rojas, TipoMovimiento.PAGO_PROVEEDOR, 18_500, "Hielo Sur", "c-m1")
    sesion.registrar_movimiento(administrador, TipoMovimiento.RETIRO, 60_000, "Depósito", "c-m2")
    sesion.registrar_movimiento(marta_rojas, TipoMovimiento.INGRESO, 10_000, "Sencillo", "c-m3")
    caja_2 = sesion.turno_abierto(administrador, caja="Caja 2")
    sesion.cerrar_turno(empleados["Pedro Soto"], caja_2.id, 33_000, "Revisar", caja="Caja 2")
    ventana.mostrar_efectivo()
    generadas.append(_guardar(ventana, destino, "15-efectivo"))

    # 16 y 17. Venta por peso (D-037): el jamón escaneado, el pan buscado por nombre, y la
    # ventana del peso con el precio a la vista.
    from tienda_pos.db.seed import catalogo_demo
    from tienda_pos.ui.dialogos import DialogoPeso

    jamon = next(p.codigo_barras for p in catalogo_demo() if p.nombre == "Jamón pierna")
    ventana.mostrar_venta()
    ventana.vista_venta.carrito.vaciar()
    pesos = iter([350, 640])
    ventana.vista_venta.pedir_gramos = lambda *a, **k: next(pesos)
    for codigo in (codigo_demo(0), jamon, "2000001"):
        ventana.vista_venta.agregar_por_codigo(codigo)
    generadas.append(_guardar(ventana, destino, "16-venta-por-peso"))
    peso = DialogoPeso("Pan batido", 2490, ventana)
    peso.campo.setText("640")
    peso.show()
    generadas.append(_guardar(peso, destino, "17-peso"))
    peso.close()

    # 18. El formulario de un producto por peso sin código, como el pan.
    from tienda_pos.ui.productos_view import DialogoProducto

    formulario = DialogoProducto(ventana)
    formulario.campo_nombre.setText("Pan amasado")
    formulario.casilla_peso.setChecked(True)
    formulario.campo_precio.setText("2790")
    formulario.show()
    generadas.append(_guardar(formulario, destino, "18-producto-por-peso"))
    formulario.close()

    conexion.close()
    return generadas


if __name__ == "__main__":
    carpeta = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "docs" / "img"
    generar(carpeta)
