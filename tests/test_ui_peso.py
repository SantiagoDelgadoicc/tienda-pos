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

    def test_el_pan_sin_codigo_se_elige_por_nombre(self, ventana, pesos) -> None:
        # Desde la fase 25, en el campo del nombre, al lado del código: "batido" y Enter.
        respuestas, _ = pesos
        respuestas.append(500)
        vista = ventana.vista_venta
        vista.buscar_por_nombre()
        vista.campo_nombre.setText("batido")
        vista.campo_nombre.returnPressed.emit()
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

    def test_los_gramos_escriben_el_monto(self, ventana) -> None:
        dialogo = dialogos.DialogoPeso("Jamón pierna", 7990, ventana)
        dialogo.campo.setText("350")
        assert dialogo.campo_pesos.text() == "2.797"
        assert dialogo.nota.isHidden()

    def test_al_reabrir_trae_el_monto_de_la_linea(self, ventana) -> None:
        dialogo = dialogos.DialogoPeso("Jamón pierna", 7990, ventana, gramos_iniciales=350)
        assert dialogo.campo_pesos.text() == "2.797"

    def test_el_monto_dice_cuantos_gramos_son(self, ventana) -> None:
        """Fase 27: "deme $2.000 de marraqueta"."""
        dialogo = dialogos.DialogoPeso("Pan marraqueta", 2990, ventana)
        dialogo.campo_pesos.setText("2.000")
        assert dialogo.campo.text() == "669"
        assert dialogo.vista.text() == "669 g  ·  $2.000"
        assert dialogo.nota.isHidden()
        assert dialogo.campo_pesos.text() == "2.000"  # no se reescribe lo que tecleó
        dialogo._confirmar()
        assert dialogo.gramos == 669

    def test_si_el_kilo_no_da_justo_dice_lo_que_se_cobra(self, ventana) -> None:
        dialogo = dialogos.DialogoPeso("Jamón pierna", 7990, ventana)
        dialogo.campo_pesos.setText("$2000")
        assert dialogo.vista.text() == "250 g  ·  $1.998"
        assert not dialogo.nota.isHidden()
        assert dialogo.nota.text() == "Lo más cercano a $2.000: se cobran $1.998."
        dialogo._confirmar()
        assert dialogo.gramos == 250

    def test_volver_a_los_gramos_olvida_el_monto(self, ventana) -> None:
        dialogo = dialogos.DialogoPeso("Jamón pierna", 7990, ventana)
        dialogo.campo_pesos.setText("2000")
        dialogo.campo.setText("300")
        assert dialogo.campo_pesos.text() == "2.397"
        assert dialogo.nota.isHidden()

    def test_un_monto_que_no_es_monto(self, ventana) -> None:
        dialogo = dialogos.DialogoPeso("Pan marraqueta", 2990, ventana)
        for texto in ("dos mil", "-500"):
            dialogo.campo_pesos.setText(texto)
            assert not dialogo._aceptar.isEnabled()
            assert "2.000" in dialogo.error.text()
            assert dialogo.campo.text() == ""
        dialogo.campo_pesos.setText("")
        assert not dialogo._aceptar.isEnabled()
        assert dialogo.error.isHidden()

    def test_un_monto_de_mas_de_50_kilos(self, ventana) -> None:
        dialogo = dialogos.DialogoPeso("Pan marraqueta", 2990, ventana)
        dialogo.campo_pesos.setText("1.000.000")
        assert not dialogo._aceptar.isEnabled()
        assert "50 kg" in dialogo.error.text()
        dialogo._confirmar()
        assert dialogo.gramos is None

    def test_a_cero_pesos_el_kilo_no_se_puede_pedir_por_monto(self, ventana) -> None:
        assert not dialogos.DialogoPeso("Pan", 0, ventana).campo_pesos.isEnabled()

    def test_con_teclas_de_verdad(self, ventana) -> None:
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest

        dialogo = dialogos.DialogoPeso("Pan marraqueta", 2990, ventana)
        dialogo.show()
        dialogo.campo_pesos.setFocus()
        QTest.keyClicks(dialogo.campo_pesos, "2000")
        assert dialogo.campo.text() == "669"
        QTest.keyClick(dialogo.campo_pesos, Qt.Key.Key_Return)
        assert dialogo.gramos == 669
        dialogo.deleteLater()

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
