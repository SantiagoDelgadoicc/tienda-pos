"""Pruebas de la interfaz.

Se ejecutan sin ventana visible gracias a la plataforma "offscreen" de Qt, de modo que
funcionan igual en un equipo de desarrollo que en un servidor de integración continua.

No comprueban la estética, que se revisa con `tools/capturas.py`. Comprueban lo que se puede
romper sin que nadie lo note: que la tabla refleje el carrito, que los totales cuadren, que
el foco vuelva al campo de escaneo y que un código inexistente no rompa la pantalla.
"""

from __future__ import annotations

import os

import pytest

# Debe fijarse antes de importar Qt.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6", reason="La interfaz requiere PySide6")

from tienda_pos.db.seed import codigo_demo  # noqa: E402
from tienda_pos.repositories import codigos as repo_codigos  # noqa: E402
from tienda_pos.repositories import ventas as repo_ventas  # noqa: E402
from tienda_pos.ui import dialogos, venta_view  # noqa: E402
from tienda_pos.ui.main_window import VentanaPrincipal  # noqa: E402

# Códigos del catálogo de ejemplo usados en las pruebas.
COLA = codigo_demo(0)
LECHE = codigo_demo(10)
INEXISTENTE = "7790000000017"


class TestPantallaDeVenta:
    def test_arranca_vacia_y_con_el_foco_puesto(self, ventana) -> None:
        vista = ventana.vista_venta
        assert vista.tabla.rowCount() == 0
        assert vista.valor_total.text() == "$0"
        assert vista.campo_codigo.hasFocus()

    def test_escanear_agrega_una_fila_y_actualiza_el_total(self, ventana) -> None:
        vista = ventana.vista_venta
        vista.agregar_por_codigo(COLA)

        assert vista.tabla.rowCount() == 1
        assert vista.tabla.item(0, venta_view.COL_CODIGO).text() == COLA
        assert vista.valor_total.text() == "$2.290"
        assert vista.etiqueta_articulos.text() == "1 artículos"

    def test_escanear_dos_veces_agrupa_en_una_sola_fila(self, ventana) -> None:
        vista = ventana.vista_venta
        vista.agregar_por_codigo(COLA)
        vista.agregar_por_codigo(COLA)

        assert vista.tabla.rowCount() == 1
        assert vista.tabla.item(0, venta_view.COL_CANTIDAD).text() == "2"
        assert vista.valor_total.text() == "$4.580"

    def test_el_foco_vuelve_al_campo_tras_escanear(self, ventana) -> None:
        # Si el foco se perdiera, el siguiente disparo de la pistola se perdería con él.
        vista = ventana.vista_venta
        vista.agregar_por_codigo(COLA)
        assert vista.campo_codigo.hasFocus()

    def test_los_botones_se_habilitan_solo_con_productos(self, ventana) -> None:
        vista = ventana.vista_venta
        assert not vista.boton_cobrar.isEnabled()
        vista.agregar_por_codigo(COLA)
        assert vista.boton_cobrar.isEnabled()

    def test_escribir_en_el_campo_y_pulsar_enter(self, ventana) -> None:
        vista = ventana.vista_venta
        vista.campo_codigo.setText(LECHE)
        vista.campo_codigo.returnPressed.emit()

        assert vista.tabla.rowCount() == 1
        assert vista.campo_codigo.text() == ""

    def test_enter_con_el_campo_vacio_no_hace_nada(self, ventana) -> None:
        vista = ventana.vista_venta
        vista.campo_codigo.returnPressed.emit()
        assert vista.tabla.rowCount() == 0

    def test_un_codigo_invalido_avisa_sin_romper_la_pantalla(self, ventana) -> None:
        vista = ventana.vista_venta
        vista.agregar_por_codigo("codigo/invalido")

        assert vista.tabla.rowCount() == 0
        assert vista.mensaje.isVisible()

    def test_un_codigo_inexistente_queda_registrado(self, ventana, conexion, monkeypatch) -> None:
        # El diálogo de "no encontrado" se responde solo, como si el usuario pulsara Continuar.
        monkeypatch.setattr(
            ventana.vista_venta, "_codigo_no_encontrado", lambda codigo: None
        )
        ventana.vista_venta.agregar_por_codigo(INEXISTENTE)

        pendientes = repo_codigos.listar_pendientes(conexion)
        assert [p.codigo for p in pendientes] == [INEXISTENTE]


class TestQuitarYCancelar:
    def test_quitar_baja_una_unidad_antes_de_borrar_la_linea(self, ventana) -> None:
        vista = ventana.vista_venta
        vista.agregar_por_codigo(COLA)
        vista.agregar_por_codigo(COLA)

        vista.quitar_linea_seleccionada()
        assert vista.tabla.item(0, venta_view.COL_CANTIDAD).text() == "1"

        vista.quitar_linea_seleccionada()
        assert vista.tabla.rowCount() == 0

    def test_cancelar_vacia_el_carrito(self, ventana) -> None:
        vista = ventana.vista_venta
        vista.agregar_por_codigo(COLA)
        vista.agregar_por_codigo(LECHE)

        vista.cancelar_venta()  # el diálogo de confirmación responde que sí
        assert vista.tabla.rowCount() == 0
        assert vista.valor_total.text() == "$0"


class TestCantidadesYTeclado:
    """Las acciones sobre el carrito que no exigen soltar el lector."""

    def _pulsar(self, vista, tecla, modificador=None) -> None:
        from PySide6.QtCore import QEvent, Qt
        from PySide6.QtGui import QKeyEvent

        modificador = modificador or Qt.KeyboardModifier.NoModifier
        evento = QKeyEvent(QEvent.Type.KeyPress, tecla, modificador)
        vista.eventFilter(vista.campo_codigo, evento)

    def test_el_boton_mas_suma_una_unidad(self, ventana) -> None:
        vista = ventana.vista_venta
        vista.agregar_por_codigo(COLA)
        vista.aumentar_cantidad()

        assert vista.tabla.item(0, venta_view.COL_CANTIDAD).text() == "2"
        assert vista.valor_total.text() == "$4.580"

    def test_el_boton_menos_resta_y_despues_borra(self, ventana) -> None:
        vista = ventana.vista_venta
        vista.agregar_por_codigo(COLA)
        vista.aumentar_cantidad()

        vista.disminuir_cantidad()
        assert vista.tabla.item(0, venta_view.COL_CANTIDAD).text() == "1"
        vista.disminuir_cantidad()
        assert vista.tabla.rowCount() == 0

    def test_la_flecha_derecha_suma_una_unidad(self, ventana) -> None:
        from PySide6.QtCore import Qt

        vista = ventana.vista_venta
        vista.agregar_por_codigo(COLA)
        self._pulsar(vista, Qt.Key.Key_Right)

        assert vista.tabla.item(0, venta_view.COL_CANTIDAD).text() == "2"

    def test_la_flecha_izquierda_resta_una_unidad(self, ventana) -> None:
        from PySide6.QtCore import Qt

        vista = ventana.vista_venta
        vista.agregar_por_codigo(COLA)
        vista.aumentar_cantidad()
        self._pulsar(vista, Qt.Key.Key_Left)

        assert vista.tabla.item(0, venta_view.COL_CANTIDAD).text() == "1"

    def test_las_flechas_no_tocan_el_carrito_si_hay_un_codigo_a_medio_escribir(
        self, ventana
    ) -> None:
        # Con texto en el campo, las flechas son del campo: sirven para corregir el código.
        from PySide6.QtCore import Qt

        vista = ventana.vista_venta
        vista.agregar_por_codigo(COLA)
        vista.campo_codigo.setText("78012")
        self._pulsar(vista, Qt.Key.Key_Right)

        assert vista.tabla.item(0, venta_view.COL_CANTIDAD).text() == "1"

    def test_arriba_y_abajo_mueven_la_seleccion(self, ventana) -> None:
        from PySide6.QtCore import Qt

        vista = ventana.vista_venta
        vista.agregar_por_codigo(COLA)
        vista.agregar_por_codigo(LECHE)  # queda seleccionada la segunda fila

        self._pulsar(vista, Qt.Key.Key_Up)
        assert vista.tabla.currentRow() == 0
        self._pulsar(vista, Qt.Key.Key_Down)
        assert vista.tabla.currentRow() == 1

    def test_la_seleccion_no_se_sale_de_la_tabla(self, ventana) -> None:
        from PySide6.QtCore import Qt

        vista = ventana.vista_venta
        vista.agregar_por_codigo(COLA)
        for _ in range(3):
            self._pulsar(vista, Qt.Key.Key_Up)
        assert vista.tabla.currentRow() == 0

    def test_el_teclado_con_el_carrito_vacio_no_rompe_nada(self, ventana) -> None:
        # Y tampoco regaña: pulsar una flecha sin carrito no es un error del cajero.
        from PySide6.QtCore import Qt

        vista = ventana.vista_venta
        for tecla in (Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Left, Qt.Key.Key_Right):
            self._pulsar(vista, tecla)

        assert vista.tabla.rowCount() == 0
        assert not vista.mensaje.isVisible()

    def test_no_se_pasa_del_tope_por_linea(self, ventana) -> None:
        from tienda_pos.services import venta as servicio_venta

        vista = ventana.vista_venta
        vista.agregar_por_codigo(COLA)
        vista.carrito.cambiar_cantidad(COLA, servicio_venta.CANTIDAD_MAX_POR_LINEA)
        vista._refrescar()
        vista.aumentar_cantidad()

        assert vista.carrito.lineas[0].cantidad == servicio_venta.CANTIDAD_MAX_POR_LINEA

    def test_copiar_deja_el_codigo_en_el_portapapeles(self, ventana) -> None:
        from PySide6.QtGui import QGuiApplication

        vista = ventana.vista_venta
        vista.agregar_por_codigo(COLA)
        vista.copiar_codigo_seleccionado()

        assert QGuiApplication.clipboard().text() == COLA

    def test_copiar_sin_seleccion_avisa_y_no_falla(self, ventana) -> None:
        vista = ventana.vista_venta
        vista.copiar_codigo_seleccionado()
        assert vista.mensaje.isVisible()

    def test_cada_fila_trae_sus_celdas_de_accion(self, ventana) -> None:
        vista = ventana.vista_venta
        vista.agregar_por_codigo(COLA)

        assert vista.tabla.item(0, venta_view.COL_COPIAR).text() == venta_view._COPIAR
        assert vista.tabla.item(0, venta_view.COL_MENOS).text() == venta_view._MENOS
        assert vista.tabla.item(0, venta_view.COL_MAS).text() == venta_view._MAS

    def test_pulsar_la_celda_de_mas_suma_una_unidad(self, ventana) -> None:
        vista = ventana.vista_venta
        vista.agregar_por_codigo(COLA)
        vista.tabla.cellClicked.emit(0, venta_view.COL_MAS)

        assert vista.tabla.item(0, venta_view.COL_CANTIDAD).text() == "2"

    def test_pulsar_la_celda_de_menos_resta_una_unidad(self, ventana) -> None:
        vista = ventana.vista_venta
        vista.agregar_por_codigo(COLA)
        vista.aumentar_cantidad()
        vista.tabla.cellClicked.emit(0, venta_view.COL_MENOS)

        assert vista.tabla.item(0, venta_view.COL_CANTIDAD).text() == "1"

    def test_pulsar_la_celda_de_copiar_copia_el_codigo(self, ventana) -> None:
        from PySide6.QtGui import QGuiApplication

        vista = ventana.vista_venta
        vista.agregar_por_codigo(LECHE)
        vista.tabla.cellClicked.emit(0, venta_view.COL_COPIAR)

        assert QGuiApplication.clipboard().text() == LECHE

    def test_pulsar_una_celda_normal_no_cambia_el_carrito(self, ventana) -> None:
        vista = ventana.vista_venta
        vista.agregar_por_codigo(COLA)
        vista.tabla.cellClicked.emit(0, venta_view.COL_NOMBRE)

        assert vista.tabla.item(0, venta_view.COL_CANTIDAD).text() == "1"

    def test_al_llegar_al_tope_la_celda_de_mas_se_apaga(self, ventana) -> None:
        from tienda_pos.services import venta as servicio_venta

        vista = ventana.vista_venta
        vista.agregar_por_codigo(COLA)
        vista.carrito.cambiar_cantidad(COLA, servicio_venta.CANTIDAD_MAX_POR_LINEA)
        vista._refrescar()

        assert vista.tabla.item(0, venta_view.COL_MAS).text() == ""


class TestCobrar:
    def test_cobrar_registra_la_venta_y_limpia_la_pantalla(self, ventana, conexion) -> None:
        vista = ventana.vista_venta
        vista.agregar_por_codigo(COLA)
        vista.agregar_por_codigo(LECHE)
        vista.cobrar()

        assert vista.tabla.rowCount() == 0
        assert vista.valor_total.text() == "$0"

        resumen = repo_ventas.resumen_del_dia(conexion)
        assert resumen["cantidad_ventas"] == 1
        assert resumen["total_clp"] == 2290 + 1290

    def test_cobrar_sin_productos_no_registra_nada(self, ventana, conexion) -> None:
        ventana.vista_venta.cobrar()
        assert repo_ventas.resumen_del_dia(conexion)["cantidad_ventas"] == 0


class TestConsultaDePrecio:
    def test_muestra_nombre_y_precio(self, ventana) -> None:
        ventana.mostrar_consulta()
        ventana.vista_consulta.consultar(COLA)

        assert ventana.vista_consulta.etiqueta_nombre.text() == "Bebida Cola 1.5 L"
        assert ventana.vista_consulta.etiqueta_precio.text() == "$2.290"

    def test_un_codigo_inexistente_se_explica_sin_precio(self, ventana) -> None:
        ventana.mostrar_consulta()
        ventana.vista_consulta.consultar(INEXISTENTE)

        assert ventana.vista_consulta.etiqueta_nombre.text() == "Producto no encontrado"
        assert ventana.vista_consulta.etiqueta_precio.text() == INEXISTENTE

    def test_limpiar_vuelve_al_estado_de_espera(self, ventana) -> None:
        ventana.mostrar_consulta()
        ventana.vista_consulta.consultar(COLA)
        ventana.vista_consulta.limpiar()

        assert ventana.vista_consulta.etiqueta_espera.isVisible()
        assert not ventana.vista_consulta.etiqueta_nombre.isVisible()

    def test_la_consulta_no_toca_el_carrito(self, ventana) -> None:
        # Consultar un precio no debe vender nada: es el error más fácil de cometer aquí.
        ventana.vista_venta.agregar_por_codigo(COLA)
        ventana.mostrar_consulta()
        ventana.vista_consulta.consultar(LECHE)

        assert ventana.vista_venta.tabla.rowCount() == 1


class TestNavegacion:
    def test_f2_alterna_entre_venta_y_consulta(self, ventana) -> None:
        assert ventana.pantallas.currentWidget() is ventana.vista_venta

        ventana.alternar_consulta()
        assert ventana.pantallas.currentWidget() is ventana.vista_consulta

        ventana.alternar_consulta()
        assert ventana.pantallas.currentWidget() is ventana.vista_venta

    def test_volver_a_la_venta_devuelve_el_foco_al_campo(self, ventana) -> None:
        ventana.mostrar_consulta()
        ventana.mostrar_venta()
        assert ventana.vista_venta.campo_codigo.hasFocus()

    def test_los_atajos_no_actuan_fuera_de_la_pantalla_de_venta(self, ventana, conexion) -> None:
        ventana.vista_venta.agregar_por_codigo(COLA)
        ventana.mostrar_consulta()
        ventana._cobrar()  # F12 estando en consulta: no debe cobrar

        assert repo_ventas.resumen_del_dia(conexion)["cantidad_ventas"] == 0

    def test_la_barra_superior_muestra_al_usuario(self, ventana) -> None:
        assert "Ana Pérez" in ventana.etiqueta_sesion.text()
        assert "Cajero" in ventana.etiqueta_sesion.text()
