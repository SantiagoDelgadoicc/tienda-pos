"""Pruebas de las pantallas reservadas al administrador y del descuento.

Se apoyan en las fixtures `ventana` y `como_admin` de conftest.py, que dejan la aplicación
lista y silencian los diálogos modales.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="La interfaz requiere PySide6")

from tienda_pos.db.seed import catalogo_demo, codigo_demo  # noqa: E402
from tienda_pos.domain.errors import ProductoNoEncontrado  # noqa: E402
from tienda_pos.repositories import ventas as repo_ventas  # noqa: E402
from tienda_pos.services import catalogo  # noqa: E402
from tienda_pos.ui import dialogos, main_window, productos_view  # noqa: E402

COLA = codigo_demo(0)
LECHE = codigo_demo(10)


class _DialogoFalso:
    """Sustituto de un diálogo modal que siempre acepta con datos prefijados."""

    def __init__(self, **atributos):
        # El ámbito por defecto es la venta entera, que es como llega el diálogo real.
        self._atributos = {"ambito": dialogos.AMBITO_VENTA, **atributos}

    def __call__(self, *args, **kwargs):
        for clave, valor in self._atributos.items():
            setattr(self, clave, valor)
        return self

    def exec(self) -> bool:
        return True


class TestDescuento:
    def _aplicar(
        self,
        ventana,
        monkeypatch,
        *,
        porcentaje=False,
        valor=0,
        quitar=False,
        ambito=None,
    ):
        monkeypatch.setattr(
            dialogos,
            "DialogoDescuento",
            _DialogoFalso(
                quitar=quitar,
                es_porcentaje=porcentaje,
                valor=valor,
                ambito=ambito or dialogos.AMBITO_VENTA,
            ),
        )
        ventana.vista_venta.aplicar_descuento()

    def test_descuento_por_monto(self, ventana, monkeypatch) -> None:
        ventana.vista_venta.agregar_por_codigo(COLA)  # 2.290
        self._aplicar(ventana, monkeypatch, valor=290)

        assert ventana.vista_venta.valor_total.text() == "$2.000"
        assert ventana.vista_venta.fila_descuento.isVisible()

    def test_descuento_por_porcentaje(self, ventana, monkeypatch) -> None:
        ventana.vista_venta.agregar_por_codigo(COLA)  # 2.290
        self._aplicar(ventana, monkeypatch, porcentaje=True, valor=10)

        assert ventana.vista_venta.valor_descuento.text() == "-$229"
        assert ventana.vista_venta.valor_total.text() == "$2.061"

    def test_quitar_el_descuento(self, ventana, monkeypatch) -> None:
        ventana.vista_venta.agregar_por_codigo(COLA)
        self._aplicar(ventana, monkeypatch, valor=290)
        self._aplicar(ventana, monkeypatch, quitar=True)

        assert ventana.vista_venta.valor_total.text() == "$2.290"
        assert not ventana.vista_venta.fila_descuento.isVisible()

    def test_el_descuento_queda_registrado_en_la_venta(
        self, ventana, monkeypatch, conexion
    ) -> None:
        ventana.vista_venta.agregar_por_codigo(COLA)
        self._aplicar(ventana, monkeypatch, valor=290)
        ventana.vista_venta.cobrar()

        venta = repo_ventas.del_dia(conexion)[0]
        assert venta.descuento_clp == 290
        assert venta.total_clp == 2000

    def test_descuento_sobre_un_solo_producto(self, ventana, monkeypatch) -> None:
        vista = ventana.vista_venta
        vista.agregar_por_codigo(COLA)  # 2.290, queda seleccionada
        vista.agregar_por_codigo(LECHE)
        vista._seleccionar(COLA)
        self._aplicar(
            ventana, monkeypatch, valor=290, ambito=dialogos.AMBITO_PRODUCTO
        )

        linea = vista.carrito.linea_de(COLA)
        assert linea.descuento_clp == 290
        assert vista.carrito.linea_de(LECHE).descuento_clp == 0
        assert vista.valor_descuento.text() == "-$290"

    def test_el_descuento_del_producto_aparece_en_su_fila(self, ventana, monkeypatch) -> None:
        from tienda_pos.ui import venta_view

        vista = ventana.vista_venta
        vista.agregar_por_codigo(COLA)
        self._aplicar(
            ventana, monkeypatch, porcentaje=True, valor=10, ambito=dialogos.AMBITO_PRODUCTO
        )

        assert not vista.tabla.isColumnHidden(venta_view.COL_DESCUENTO)
        assert vista.tabla.item(0, venta_view.COL_DESCUENTO).text() == "-$229"
        assert vista.tabla.item(0, venta_view.COL_SUBTOTAL).text() == "$2.061"

    def test_quitar_el_descuento_de_un_producto(self, ventana, monkeypatch) -> None:
        from tienda_pos.ui import venta_view

        vista = ventana.vista_venta
        vista.agregar_por_codigo(COLA)
        self._aplicar(ventana, monkeypatch, valor=290, ambito=dialogos.AMBITO_PRODUCTO)
        self._aplicar(ventana, monkeypatch, quitar=True, ambito=dialogos.AMBITO_PRODUCTO)

        assert vista.valor_total.text() == "$2.290"
        assert vista.tabla.isColumnHidden(venta_view.COL_DESCUENTO)

    def test_el_descuento_del_producto_queda_registrado_en_la_venta(
        self, ventana, monkeypatch, conexion
    ) -> None:
        vista = ventana.vista_venta
        vista.agregar_por_codigo(COLA)
        self._aplicar(ventana, monkeypatch, valor=290, ambito=dialogos.AMBITO_PRODUCTO)
        vista.cobrar()

        venta = repo_ventas.obtener(conexion, repo_ventas.del_dia(conexion)[0].id)
        assert venta.lineas[0].descuento_clp == 290
        assert venta.descuento_clp == 290
        assert venta.total_clp == 2000

    def test_sin_linea_seleccionada_el_descuento_va_a_la_venta(
        self, ventana, monkeypatch
    ) -> None:
        # El diálogo no deja elegir "producto" sin selección; si aun así llegara, el
        # descuento debe recaer sobre la venta y nunca perderse en silencio.
        vista = ventana.vista_venta
        vista.agregar_por_codigo(COLA)
        vista.tabla.clearSelection()
        vista.tabla.setCurrentCell(-1, -1)
        self._aplicar(ventana, monkeypatch, valor=290, ambito=dialogos.AMBITO_PRODUCTO)

        assert vista.valor_total.text() == "$2.000"
        assert vista.carrito.descuento_venta_clp == 290

    def test_no_se_descuenta_sobre_un_carrito_vacio(self, ventana, monkeypatch) -> None:
        self._aplicar(ventana, monkeypatch, valor=500)
        assert ventana.vista_venta.valor_total.text() == "$0"


class TestAccesoDeAdministrador:
    def test_un_cajero_que_cancela_no_entra(self, ventana, monkeypatch) -> None:
        monkeypatch.setattr(
            main_window.DialogoLogin, "pedir", staticmethod(lambda *a, **k: None)
        )
        ventana.mostrar_productos()
        assert ventana.pantallas.currentWidget() is ventana.vista_venta

    def test_con_autorizacion_de_administrador_si_entra(self, como_admin) -> None:
        como_admin.mostrar_productos()
        assert como_admin.pantallas.currentWidget() is como_admin.vista_productos
        assert como_admin.vista_productos.usuario.es_admin

    def test_autorizar_no_cambia_al_cajero_que_opera(self, como_admin) -> None:
        # El encargado autoriza una acción puntual; la caja sigue siendo del cajero.
        como_admin.mostrar_productos()
        assert como_admin.usuario.nombre == "Ana Pérez"

    def test_a_un_administrador_no_le_piden_nada(self, ventana, conexion) -> None:
        from tienda_pos.services import auth

        ventana.establecer_usuario(auth.autenticar(conexion, "Administrador", "1234"))
        # Si pidiera PIN, el diálogo real bloquearía la prueba para siempre.
        ventana.mostrar_reportes()
        assert ventana.pantallas.currentWidget() is ventana.vista_reportes


class TestPantallaDeProductos:
    @pytest.fixture
    def vista(self, como_admin):
        como_admin.mostrar_productos()
        return como_admin.vista_productos

    def test_lista_todo_el_catalogo(self, vista) -> None:
        assert vista.tabla.rowCount() == len(catalogo_demo())

    def test_el_filtro_reduce_la_lista(self, vista) -> None:
        vista.campo_filtro.setText("leche")
        assert 0 < vista.tabla.rowCount() < 10
        # El filtro no distingue mayúsculas, así que "Crema de leche" también es correcto.
        nombres = [vista.tabla.item(f, 1).text().lower() for f in range(vista.tabla.rowCount())]
        assert all("leche" in nombre for nombre in nombres)

    def test_el_filtro_tambien_busca_por_codigo(self, vista) -> None:
        vista.campo_filtro.setText(COLA)
        assert vista.tabla.rowCount() == 1

    def test_crear_un_producto(self, vista, conexion, monkeypatch) -> None:
        monkeypatch.setattr(
            productos_view,
            "DialogoProducto",
            _DialogoFalso(datos=("7790000000024", "Producto de prueba", 1990, 7)),
        )
        antes = vista.tabla.rowCount()
        vista.crear()

        assert vista.tabla.rowCount() == antes + 1
        assert catalogo.consultar_por_codigo(conexion, "7790000000024").precio_clp == 1990

    def test_editar_cambia_el_precio(self, vista, conexion, monkeypatch) -> None:
        vista.campo_filtro.setText(COLA)
        vista.tabla.selectRow(0)
        monkeypatch.setattr(
            productos_view,
            "DialogoProducto",
            _DialogoFalso(datos=(COLA, "Bebida Cola 1.5 L", 2490, 48)),
        )
        vista.editar()

        assert catalogo.consultar_por_codigo(conexion, COLA).precio_clp == 2490

    def test_dar_de_baja_lo_saca_del_catalogo(self, vista, conexion) -> None:
        vista.campo_filtro.setText(COLA)
        vista.tabla.selectRow(0)
        vista.dar_de_baja()  # la confirmación responde que sí

        with pytest.raises(ProductoNoEncontrado):
            catalogo.consultar_por_codigo(conexion, COLA)

    def test_editar_sin_seleccion_avisa_y_no_rompe(self, vista) -> None:
        vista.tabla.clearSelection()
        vista.tabla.setCurrentCell(-1, -1)
        vista.editar()  # mostrar_error está silenciado; lo que se prueba es que no reviente

    def test_los_codigos_pendientes_se_pueden_consultar(self, vista, conexion) -> None:
        from tienda_pos.repositories import codigos as repo_codigos

        with pytest.raises(ProductoNoEncontrado):
            catalogo.consultar_por_codigo(conexion, "7790000000017")

        vista.ver_pendientes()  # el diálogo informativo está silenciado
        assert len(repo_codigos.listar_pendientes(conexion)) == 1


class TestPantallaDeReportes:
    def test_sin_ventas_muestra_ceros(self, como_admin) -> None:
        como_admin.mostrar_reportes()
        vista = como_admin.vista_reportes

        assert vista.valor_total.text() == "$0"
        assert vista.valor_ventas.text() == "0"
        assert vista.tabla_ventas.rowCount() == 0

    def test_refleja_las_ventas_del_dia(self, como_admin) -> None:
        como_admin.vista_venta.agregar_por_codigo(COLA)
        como_admin.vista_venta.agregar_por_codigo(LECHE)
        como_admin.vista_venta.cobrar()

        como_admin.mostrar_reportes()
        vista = como_admin.vista_reportes
        assert vista.valor_ventas.text() == "1"
        assert vista.valor_articulos.text() == "2"
        assert vista.valor_total.text() == "$3.580"
        assert vista.tabla_ventas.rowCount() == 1

    def test_muestra_el_detalle_de_la_venta_seleccionada(self, como_admin) -> None:
        como_admin.vista_venta.agregar_por_codigo(COLA)
        como_admin.vista_venta.agregar_por_codigo(LECHE)
        como_admin.vista_venta.cobrar()

        como_admin.mostrar_reportes()
        vista = como_admin.vista_reportes
        assert vista.tabla_detalle.rowCount() == 2
        assert "Venta N° 1" in vista.titulo_detalle.text()


class TestCambioDeUsuario:
    def test_cambiar_de_usuario_vacia_el_carrito(self, como_admin) -> None:
        como_admin.vista_venta.agregar_por_codigo(COLA)
        como_admin.cambiar_usuario()  # la confirmación responde que sí

        assert como_admin.vista_venta.tabla.rowCount() == 0
        assert como_admin.usuario.nombre == "Administrador"

    def test_si_se_cancela_el_acceso_no_cambia_nada(self, ventana, monkeypatch) -> None:
        monkeypatch.setattr(
            main_window.DialogoLogin, "pedir", staticmethod(lambda *a, **k: None)
        )
        ventana.cambiar_usuario()

        assert ventana.usuario.nombre == "Ana Pérez"


class TestAjusteDeStock:
    """El camino corto para corregir cantidades: contar mercadería es lo que más se repite."""

    def _dialogo(self, como_admin, codigo):
        from tienda_pos.ui.productos_view import DialogoStock

        como_admin.mostrar_productos()
        vista = como_admin.vista_productos
        vista.seleccionar_codigo(codigo)
        return vista, DialogoStock(vista._seleccionado(), vista)

    def test_guardar_una_cantidad_nueva_la_deja_en_el_catalogo(self, como_admin, monkeypatch) -> None:
        from tienda_pos.ui import productos_view

        como_admin.mostrar_productos()
        vista = como_admin.vista_productos
        vista.seleccionar_codigo(COLA)
        antes = vista._seleccionado().stock

        monkeypatch.setattr(
            productos_view, "DialogoStock", _dialogo_falso(antes + 7)
        )
        vista.ajustar_stock()

        vista.recargar()
        vista.seleccionar_codigo(COLA)
        assert vista._seleccionado().stock == antes + 7

    def test_sin_seleccion_avisa_y_no_toca_nada(self, como_admin, monkeypatch) -> None:
        from tienda_pos.ui import productos_view

        como_admin.mostrar_productos()
        vista = como_admin.vista_productos
        vista.tabla.clearSelection()
        vista.tabla.setCurrentCell(-1, -1)

        # Si el diálogo llegara a abrirse, esto haría fallar la prueba en lugar de dejarlo
        # pasar en silencio.
        monkeypatch.setattr(productos_view, "DialogoStock", _no_debe_abrirse)
        vista.ajustar_stock()

    def test_los_saltos_rapidos_no_bajan_de_cero(self, como_admin) -> None:
        vista, dialogo = self._dialogo(como_admin, COLA)
        dialogo.campo.setText("3")
        dialogo._sumar(-10)
        assert dialogo.stock == 0

    def test_el_campo_vacio_vale_la_cantidad_actual(self, como_admin) -> None:
        vista, dialogo = self._dialogo(como_admin, COLA)
        actual = vista._seleccionado().stock
        dialogo.campo.clear()
        assert dialogo.stock == actual

    def test_el_resumen_dice_cuanto_entra_y_cuanto_sale(self, como_admin) -> None:
        vista, dialogo = self._dialogo(como_admin, COLA)
        actual = vista._seleccionado().stock

        dialogo.campo.setText(str(actual))
        assert dialogo.resumen.text() == "Sin cambios"
        dialogo.campo.setText(str(actual + 4))
        assert "Entran 4" in dialogo.resumen.text()
        dialogo.campo.setText(str(max(0, actual - 2)))
        assert "Salen 2" in dialogo.resumen.text()

    def test_guardar_la_misma_cantidad_no_llama_al_servicio(self, como_admin, monkeypatch) -> None:
        from tienda_pos.ui import productos_view

        como_admin.mostrar_productos()
        vista = como_admin.vista_productos
        vista.seleccionar_codigo(COLA)
        igual = vista._seleccionado().stock

        def _no_debe_guardar(*args, **kwargs):
            raise AssertionError("No debía tocarse el producto")

        monkeypatch.setattr(productos_view, "DialogoStock", _dialogo_falso(igual))
        monkeypatch.setattr(vista._sesion, "actualizar_producto", _no_debe_guardar)
        vista.ajustar_stock()


def _dialogo_falso(stock_elegido: int):
    """Sustituye al diálogo por uno que acepta y devuelve la cantidad indicada."""

    class _Falso:
        def __init__(self, producto, padre=None) -> None:
            self.stock = stock_elegido

        def exec(self) -> int:
            return 1

    return _Falso


def _no_debe_abrirse(*args, **kwargs):
    raise AssertionError("No debía abrirse el diálogo sin un producto seleccionado")
