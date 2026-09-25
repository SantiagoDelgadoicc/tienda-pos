"""Pruebas de la venta por peso en la pantalla (D-037).

El cajero escanea el jamón o busca el pan por nombre, teclea los gramos y ve el precio. Se
comprueba que la ventana del peso aparezca solo para productos por peso, que cancelarla no
agregue nada, que la línea diga el peso y el precio del kilo, y que se cobre bien.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6", reason="La interfaz requiere PySide6")

from tienda_pos.db.seed import catalogo_demo, codigo_demo  # noqa: E402
from tienda_pos.repositories import ventas as repo_ventas  # noqa: E402
from tienda_pos.ui import dialogos, venta_view  # noqa: E402

COLA = codigo_demo(0)
JAMON = next(p.codigo_barras for p in catalogo_demo() if p.nombre == "Jamón pierna")
PAN = "2000001"


@pytest.fixture
def pesos(ventana, monkeypatch):
    """Contesta la ventana del peso con los gramos de la lista, y anota qué se preguntó."""
    respuestas: list[int | None] = []
    preguntas: list[tuple] = []

    def pedir(nombre, precio_kilo, gramos_iniciales=None):
        preguntas.append((nombre, precio_kilo, gramos_iniciales))
        return respuestas.pop(0)

    monkeypatch.setattr(ventana.vista_venta, "pedir_gramos", pedir)
    return respuestas, preguntas


class TestAgregar:
    def test_escanear_un_producto_por_peso_pide_los_gramos(self, ventana, pesos) -> None:
        respuestas, preguntas = pesos
        respuestas.append(350)
        vista = ventana.vista_venta
        vista.agregar_por_codigo(JAMON)

        assert preguntas == [("Jamón pierna", 7990, None)]
        assert vista.tabla.item(0, venta_view.COL_CANTIDAD).text() == "350 g"
        assert vista.tabla.item(0, venta_view.COL_PRECIO).text() == "$7.990/kg"
        assert vista.tabla.item(0, venta_view.COL_SUBTOTAL).text() == "$2.797"
        assert vista.valor_total.text() == "$2.797"

    def test_un_producto_por_unidad_no_pregunta_nada(self, ventana, pesos) -> None:
        _, preguntas = pesos
        ventana.vista_venta.agregar_por_codigo(COLA)
        assert preguntas == []

    def test_cancelar_el_peso_no_agrega_nada(self, ventana, pesos) -> None:
        respuestas, _ = pesos
        respuestas.append(None)
        vista = ventana.vista_venta
        vista.agregar_por_codigo(JAMON)
        assert vista.carrito.esta_vacio
        assert vista.campo_codigo.hasFocus()

    def test_el_pan_sin_codigo_se_elige_por_nombre(self, ventana, pesos, monkeypatch) -> None:
        from tienda_pos.ui import buscador

        respuestas, _ = pesos
        respuestas.append(500)
        monkeypatch.setattr(
            dialogos.DialogoTexto, "exec", lambda self: (self.campo.setText("batido"), True)[1]
        )
        monkeypatch.setattr(
            buscador.DialogoResultados, "elegir", lambda self: self._resultados[0]
        )
        vista = ventana.vista_venta
        vista.buscar_por_nombre()
        linea = vista.carrito.lineas[0]
        assert (linea.codigo_barras, linea.gramos, linea.total_clp) == (PAN, 500, 1245)


class TestCorregir:
    def test_la_flecha_derecha_vuelve_a_pesar(self, ventana, pesos) -> None:
        respuestas, preguntas = pesos
        respuestas.extend([350, 1000])
        vista = ventana.vista_venta
        vista.agregar_por_codigo(JAMON)
        vista.aumentar_cantidad(JAMON)
        assert preguntas[-1] == ("Jamón pierna", 7990, 350)
        assert vista.tabla.item(0, venta_view.COL_CANTIDAD).text() == "1 kg"
        assert vista.valor_total.text() == "$7.990"

    def test_la_flecha_izquierda_quita_la_linea_entera(self, ventana, pesos) -> None:
        respuestas, _ = pesos
        respuestas.append(350)
        vista = ventana.vista_venta
        vista.agregar_por_codigo(COLA)
        vista.agregar_por_codigo(JAMON)
        vista.disminuir_cantidad(JAMON)
        assert [linea.codigo_barras for linea in vista.carrito.lineas] == [COLA]

    def test_escanear_otra_vez_suma_los_gramos(self, ventana, pesos) -> None:
        respuestas, _ = pesos
        respuestas.extend([300, 200])
        vista = ventana.vista_venta
        vista.agregar_por_codigo(JAMON)
        vista.agregar_por_codigo(JAMON)
        assert vista.tabla.rowCount() == 1
        assert vista.tabla.item(0, venta_view.COL_CANTIDAD).text() == "500 g"


class TestCobrar:
    def test_se_cobra_con_su_peso(self, ventana, conexion, pesos) -> None:
        respuestas, _ = pesos
        respuestas.append(750)
        vista = ventana.vista_venta
        vista.agregar_por_codigo(COLA)
        vista.agregar_por_codigo(JAMON)
        vista.cobrar()

        assert vista.carrito.esta_vacio
        venta = repo_ventas.del_dia(conexion)[-1]
        lineas = repo_ventas.lineas_de(conexion, venta.id)
        assert [linea.gramos for linea in lineas] == [None, 750]
        assert venta.total_clp == 2290 + 5993


class TestDialogoPeso:
    def test_ensena_el_precio_mientras_se_teclea(self, ventana) -> None:
        dialogo = dialogos.DialogoPeso("Jamón pierna", 7990, ventana)
        assert not dialogo._aceptar.isEnabled()
        dialogo.campo.setText("350")
        assert dialogo.vista.text() == "350 g  ·  $2.797"
        assert dialogo._aceptar.isEnabled()
        dialogo._confirmar()
        assert dialogo.gramos == 350

    def test_no_acepta_un_peso_imposible(self, ventana) -> None:
        dialogo = dialogos.DialogoPeso("Jamón pierna", 7990, ventana)
        dialogo.campo.setText("350000")
        assert not dialogo._aceptar.isEnabled()
        assert "50 kg" in dialogo.error.text()
        dialogo.campo.setText("0")
        assert not dialogo._aceptar.isEnabled()
        dialogo._confirmar()
        assert dialogo.gramos is None

    def test_el_descuento_de_una_linea_por_peso_dice_los_gramos(self, ventana, pesos) -> None:
        """Fase 22: decía "(1 unidad)", que en 350 g de jamón no significa nada."""
        respuestas, _ = pesos
        respuestas.append(350)
        vista = ventana.vista_venta
        vista.agregar_por_codigo(JAMON)
        dialogo = dialogos.DialogoDescuento(
            vista.carrito.base_descontable_clp, ventana, linea=vista.carrito.linea_de(JAMON)
        )
        assert dialogo.opcion_producto.text() == "Solo a Jamón pierna  (350 g)"
