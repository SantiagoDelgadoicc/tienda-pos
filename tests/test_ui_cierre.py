"""Pruebas de la pantalla de cierre de caja (fase 18, D-035).

Se apoyan en las fixtures `ventana` y `como_admin` de conftest.py. La sesión de esas fixtures
no tiene nombre de caja; aquí se le pone "Caja 1", que es lo que tiene toda caja de verdad
(D-033: sale de `red.json` o del nombre del PC, nunca queda vacío).
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

pytest.importorskip("PySide6", reason="La interfaz requiere PySide6")

from PySide6.QtCore import QDate  # noqa: E402

from tienda_pos.db.connection import transaccion  # noqa: E402
from tienda_pos.db.seed import codigo_demo  # noqa: E402
from tienda_pos.domain.errors import ErrorDominio  # noqa: E402
from tienda_pos.domain.models import MedioPago, Rol  # noqa: E402
from tienda_pos.services import auth, reportes  # noqa: E402
from tienda_pos.services import venta as servicio_venta  # noqa: E402
from tienda_pos.ui import cierre_view, dialogos, estilos, main_window  # noqa: E402
from tienda_pos.utils.money import formatear_clp  # noqa: E402


@pytest.fixture
def caja_1(como_admin, monkeypatch):
    """La ventana, autorizada como administrador y en una caja que se llama "Caja 1"."""
    monkeypatch.setattr(como_admin._sesion, "_caja", "Caja 1")
    return como_admin


@pytest.fixture
def vender(conexion):
    """Cobra una venta de productos del catálogo demo, en la caja y con el medio que se diga."""
    from tienda_pos.red.sesion import SesionLocal

    sesion = SesionLocal(conexion)
    cajero = auth.autenticar(conexion, "Cajero", "1111")

    def _vender(
        *indices: int,
        caja: str | None = "Caja 1",
        medio: MedioPago | None = MedioPago.EFECTIVO,
        usuario=cajero,
    ):
        carrito = servicio_venta.Carrito()
        for indice in indices or (0,):
            carrito.agregar(sesion.consultar_por_codigo(codigo_demo(indice)))
        return servicio_venta.cerrar_venta(conexion, carrito, usuario, caja=caja, medio_pago=medio)

    return _vender


def _textos_de_ventas(vista) -> list[str]:
    arbol = vista.arbol_ventas
    return [arbol.topLevelItem(i).text(0) for i in range(arbol.topLevelItemCount())]


class TestAcceso:
    def test_un_cajero_sin_autorizacion_no_entra(self, ventana, monkeypatch) -> None:
        monkeypatch.setattr(main_window.DialogoLogin, "pedir", staticmethod(lambda *a, **k: None))
        ventana.mostrar_cierre()
        assert ventana.pantallas.currentWidget() is ventana.vista_venta

    def test_con_autorizacion_entra_y_la_ventana_lo_dice(self, caja_1, vender) -> None:
        vender(0)
        caja_1.mostrar_cierre()

        assert caja_1.pantallas.currentWidget() is caja_1.vista_cierre
        assert caja_1.titulo_pantalla.text() == "Ventas por caja"
        assert caja_1.barra_lateral._botones["cierre"].isChecked()
        # La cabecera dice qué caja y qué día se está mirando.
        subtitulo = caja_1.subtitulo_pantalla.text()
        assert subtitulo.startswith("Caja 1  ·  ")
        assert cierre_view.fecha_larga(reportes.dia_comercial()) in subtitulo
        assert "1 venta  ·  " in subtitulo

    def test_se_llega_desde_la_barra_lateral(self, caja_1) -> None:
        caja_1.barra_lateral._botones["cierre"].click()
        assert caja_1.pantallas.currentWidget() is caja_1.vista_cierre

    def test_se_llega_desde_las_ventas_del_dia(self, caja_1) -> None:
        # Es donde el dueño lo va a buscar.
        caja_1.mostrar_reportes()
        caja_1.vista_reportes.boton_cierre.click()
        assert caja_1.pantallas.currentWidget() is caja_1.vista_cierre

    def test_esc_vuelve_a_la_venta(self, caja_1) -> None:
        caja_1.mostrar_cierre()
        caja_1.mostrar_venta()
        assert caja_1.pantallas.currentWidget() is caja_1.vista_venta
        assert not caja_1.barra_lateral._botones["cierre"].isChecked()


class TestSelectorDeCaja:
    def test_con_una_sola_caja_no_aparece(self, caja_1, vender) -> None:
        vender(0)
        caja_1.mostrar_cierre()
        vista = caja_1.vista_cierre
        assert vista.selector_caja.isHidden()
        assert vista.etiqueta_caja.isHidden()

    def test_un_dia_sin_ventas_tampoco(self, caja_1) -> None:
        caja_1.mostrar_cierre()
        assert caja_1.vista_cierre.selector_caja.isHidden()

    def test_con_dos_cajas_aparece_y_empieza_en_la_propia(self, caja_1, vender) -> None:
        vender(0, caja="Caja 1")
        vender(1, caja="Caja 2")
        caja_1.mostrar_cierre()
        selector = caja_1.vista_cierre.selector_caja

        assert not selector.isHidden()
        assert [selector.itemText(i) for i in range(selector.count())] == ["Caja 1", "Caja 2"]
        assert selector.currentText() == "Caja 1"

    def test_si_solo_vendio_la_otra_aparece_la_propia_en_cero(self, caja_1, vender) -> None:
        # Un día sin ventas en esta caja dice "$0" en vez de saltar sola a la otra.
        vender(0, caja="Caja 2")
        caja_1.mostrar_cierre()
        vista = caja_1.vista_cierre

        assert vista.selector_caja.currentText() == "Caja 1"
        assert vista.selector_caja.count() == 2
        assert vista.valor_total.text() == "$0"

    def test_elegir_otra_caja_recarga_todo(self, caja_1, vender) -> None:
        vender(0, caja="Caja 1")
        otra = vender(1, 2, caja="Caja 2", medio=MedioPago.DEBITO)
        caja_1.mostrar_cierre()
        vista = caja_1.vista_cierre

        vista.selector_caja.activated.emit(1)

        assert vista.valor_total.text() == formatear_clp(otra.total_clp)
        assert _textos_de_ventas(vista) == [f"N° {otra.folio}  ·  {otra.fecha_hora:%H:%M}"]
        assert caja_1.subtitulo_pantalla.text().startswith("Caja 2  ·  ")
        assert vista.selector_caja.currentText() == "Caja 2"

    def test_las_ventas_sin_caja_tienen_su_nombre(self, caja_1, vender) -> None:
        vender(0, caja=None)
        vender(1, caja="Caja 1")
        caja_1.mostrar_cierre()
        selector = caja_1.vista_cierre.selector_caja
        assert [selector.itemText(i) for i in range(selector.count())] == [
            "Caja 1",
            cierre_view.SIN_CAJA,
        ]

    def test_al_volver_a_entrar_se_mira_la_propia_y_hoy(self, caja_1, vender) -> None:
        vender(0, caja="Caja 1")
        vender(1, caja="Caja 2")
        caja_1.mostrar_cierre()
        vista = caja_1.vista_cierre
        vista.selector_caja.activated.emit(1)
        vista.selector_dia.setDate(vista.selector_dia.date().addDays(-3))

        caja_1.mostrar_venta()
        caja_1.mostrar_cierre()

        assert vista.selector_caja.currentText() == "Caja 1"
        assert vista.dia == reportes.dia_comercial()


class TestTarjetas:
    def test_total_y_cada_medio(self, caja_1, vender) -> None:
        efectivo = vender(0, 1, medio=MedioPago.EFECTIVO)
        debito = [vender(2, medio=MedioPago.DEBITO), vender(3, medio=MedioPago.DEBITO)]
        credito = vender(4, medio=MedioPago.CREDITO)
        caja_1.mostrar_cierre()
        vista = caja_1.vista_cierre
        medios = vista._tarjetas_medio

        total = efectivo.total_clp + sum(v.total_clp for v in debito) + credito.total_clp
        assert vista.valor_total.text() == formatear_clp(total)
        assert vista.detalle_total.text().startswith("4 ventas · ")
        assert medios[MedioPago.EFECTIVO][0].text() == formatear_clp(efectivo.total_clp)
        assert medios[MedioPago.DEBITO][0].text() == formatear_clp(sum(v.total_clp for v in debito))
        assert medios[MedioPago.DEBITO][1].text() == "2 ventas"
        assert medios[MedioPago.CREDITO][1].text() == "1 venta"

    def test_los_tres_medios_se_ven_aunque_esten_en_cero(self, caja_1) -> None:
        caja_1.mostrar_cierre()
        for medio in MedioPago:
            valor, _, tarjeta = caja_1.vista_cierre._tarjetas_medio[medio]
            assert not tarjeta.isHidden()
            assert valor.text() == "$0"

    def test_sin_registrar_solo_si_hay_ventas_asi(self, caja_1, vender) -> None:
        vender(0)
        caja_1.mostrar_cierre()
        tarjeta = caja_1.vista_cierre._tarjetas_medio[None][2]
        assert tarjeta.isHidden()

        antigua = vender(1, medio=None)
        caja_1.vista_cierre.recargar()
        valor, detalle, tarjeta = caja_1.vista_cierre._tarjetas_medio[None]
        assert not tarjeta.isHidden()
        assert (valor.text(), detalle.text()) == (formatear_clp(antigua.total_clp), "1 venta")

    def test_cada_medio_con_su_color(self, caja_1) -> None:
        # El mismo que en el cobro y en las ventas del día (D-034).
        caja_1.mostrar_cierre()
        for medio in MedioPago:
            valor = caja_1.vista_cierre._tarjetas_medio[medio][0]
            assert estilos.color_medio(medio) in valor.styleSheet()

    def test_el_color_sigue_al_tema(self, caja_1, vender) -> None:
        from tienda_pos.services.preferencias import TEMA_CLARO, TEMA_OSCURO

        vender(0, medio=MedioPago.DEBITO)
        caja_1.mostrar_cierre()
        vista = caja_1.vista_cierre
        claro = estilos.actual.debito
        try:
            caja_1.aplicar_tema(TEMA_OSCURO)
            oscuro = estilos.actual.debito
            assert oscuro != claro
            assert oscuro in vista._tarjetas_medio[MedioPago.DEBITO][0].styleSheet()
            medio = vista.arbol_ventas.topLevelItem(0).foreground(3).color().name().upper()
            assert medio == oscuro.upper()
        finally:
            caja_1.aplicar_tema(TEMA_CLARO)


class TestVentas:
    def test_plegadas_al_abrir_con_sus_productos_dentro(self, caja_1, vender) -> None:
        venta = vender(0, 10, 10)
        caja_1.mostrar_cierre()
        fila = caja_1.vista_cierre.arbol_ventas.topLevelItem(0)

        assert not fila.isExpanded()
        assert fila.text(1) == "3"
        assert fila.text(2) == "Cajero"
        assert fila.text(4) == formatear_clp(venta.total_clp)
        productos = [(fila.child(i).text(0), fila.child(i).text(1)) for i in range(fila.childCount())]
        assert productos == [(linea.nombre, str(linea.cantidad)) for linea in venta.lineas]

    def test_el_boton_las_despliega_y_las_vuelve_a_plegar(self, caja_1, vender) -> None:
        vender(0)
        vender(1)
        caja_1.mostrar_cierre()
        vista = caja_1.vista_cierre
        filas = vista._filas_de_venta()

        vista.boton_desplegar.click()
        assert all(f.isExpanded() for f in filas)
        assert vista.boton_desplegar.text() == "Ocultar productos"

        vista.boton_desplegar.click()
        assert not any(f.isExpanded() for f in filas)
        assert vista.boton_desplegar.text() == "Ver productos"

    def test_abrirlas_una_a_una_tambien_cambia_el_boton(self, caja_1, vender) -> None:
        vender(0)
        vender(1)
        caja_1.mostrar_cierre()
        vista = caja_1.vista_cierre
        for fila in vista._filas_de_venta():
            fila.setExpanded(True)
        assert vista.boton_desplegar.text() == "Ocultar productos"

    def test_cambiar_el_tema_no_pliega_lo_abierto(self, caja_1, vender) -> None:
        from tienda_pos.services.preferencias import TEMA_CLARO, TEMA_OSCURO

        vender(0)
        vender(1)
        caja_1.mostrar_cierre()
        vista = caja_1.vista_cierre
        vista.arbol_ventas.topLevelItem(1).setExpanded(True)
        try:
            caja_1.aplicar_tema(TEMA_OSCURO)
        finally:
            caja_1.aplicar_tema(TEMA_CLARO)
        assert [f.isExpanded() for f in vista._filas_de_venta()] == [False, True]

    def test_un_dia_sin_ventas_lo_dice(self, caja_1) -> None:
        caja_1.mostrar_cierre()
        vista = caja_1.vista_cierre

        assert _textos_de_ventas(vista) == ["Esta caja no tiene ventas ese día."]
        assert not vista.boton_desplegar.isEnabled()
        assert vista.valor_total.text() == "$0"
        assert vista.tabla_empleados.rowCount() == 0
        assert "0 ventas" in caja_1.subtitulo_pantalla.text()

    def test_las_anuladas_no_salen(self, caja_1, vender, conexion) -> None:
        anulada = vender(0)
        with transaccion(conexion):
            conexion.execute("UPDATE venta SET estado = 'anulada' WHERE id = ?", (anulada.id,))
        caja_1.mostrar_cierre()
        assert _textos_de_ventas(caja_1.vista_cierre) == ["Esta caja no tiene ventas ese día."]


class TestDia:
    def test_no_se_puede_elegir_un_dia_futuro(self, caja_1) -> None:
        caja_1.mostrar_cierre()
        hoy = reportes.dia_comercial()
        assert caja_1.vista_cierre.selector_dia.maximumDate().toPython() == hoy

    def test_elegir_otro_dia_recarga(self, caja_1, vender, conexion) -> None:
        ayer = reportes.dia_comercial() - timedelta(days=1)
        de_ayer = vender(0, 1)
        with transaccion(conexion):
            conexion.execute(
                "UPDATE venta SET fecha_hora = ? WHERE id = ?",
                (f"{ayer.isoformat()} 21:15:00", de_ayer.id),
            )
        caja_1.mostrar_cierre()
        vista = caja_1.vista_cierre
        assert vista.valor_total.text() == "$0"

        vista.selector_dia.setDate(QDate(ayer.year, ayer.month, ayer.day))

        assert vista.dia == ayer
        assert vista.valor_total.text() == formatear_clp(de_ayer.total_clp)
        assert _textos_de_ventas(vista) == [f"N° {de_ayer.folio}  ·  21:15"]
        assert cierre_view.fecha_larga(ayer) in caja_1.subtitulo_pantalla.text()

    def test_hoy_es_el_dia_de_la_tienda_y_no_el_del_calendario(
        self, caja_1, monkeypatch
    ) -> None:
        # Con la hora de corte de la pregunta H10, a la una de la madrugada sigue siendo ayer.
        ayer = date.today() - timedelta(days=1)
        monkeypatch.setattr(cierre_view.reportes, "dia_comercial", lambda: ayer)
        caja_1.mostrar_cierre()
        assert caja_1.vista_cierre.dia == ayer

    @pytest.mark.parametrize(
        ("dia", "texto"),
        [
            (date(2026, 9, 24), "jueves 24 de septiembre"),
            (date(2026, 9, 27), "domingo 27 de septiembre"),
            (date(2027, 1, 1), "viernes 1 de enero"),
        ],
    )
    def test_fecha_larga_en_castellano(self, dia, texto) -> None:
        # A mano y no con la configuración regional: en un Windows en inglés diría "Thursday".
        assert cierre_view.fecha_larga(dia) == texto


class TestEmpleados:
    def test_dos_empleados_en_la_misma_caja(self, caja_1, vender, conexion) -> None:
        with transaccion(conexion):
            marta = auth.crear_usuario(conexion, "Marta", Rol.CAJERO, "5706")
        de_marta = [vender(0, usuario=marta), vender(1, 2, usuario=marta)]
        del_cajero = vender(3)
        caja_1.mostrar_cierre()
        tabla = caja_1.vista_cierre.tabla_empleados

        filas = {
            tabla.item(f, 0).text(): (tabla.item(f, 1).text(), tabla.item(f, 3).text())
            for f in range(tabla.rowCount())
        }
        assert filas == {
            "Marta": ("2", formatear_clp(sum(v.total_clp for v in de_marta))),
            "Cajero": ("1", formatear_clp(del_cajero.total_clp)),
        }

    def test_las_ventas_sin_usuario_se_nombran(self, caja_1, vender) -> None:
        vender(0, usuario=None)
        caja_1.mostrar_cierre()
        tabla = caja_1.vista_cierre.tabla_empleados
        assert tabla.item(0, 0).text() == cierre_view.SIN_USUARIO
        assert caja_1.vista_cierre.arbol_ventas.topLevelItem(0).text(2) == "Sin usuario"


class TestErrores:
    def test_si_no_carga_lo_dice_y_no_deja_cifras_viejas(self, caja_1, vender, monkeypatch) -> None:
        vender(0)
        caja_1.mostrar_cierre()
        vista = caja_1.vista_cierre
        assert vista.valor_total.text() != "—"

        errores = []
        monkeypatch.setattr(dialogos, "mostrar_error", lambda _p, texto, *a, **k: errores.append(texto))

        def sin_servidor(*_a, **_k):
            raise ErrorDominio("No hay conexión con la caja principal.")

        monkeypatch.setattr(vista._sesion, "cierre_de_caja", sin_servidor)
        vista.recargar()

        assert errores == ["No hay conexión con la caja principal."]
        assert vista.valor_total.text() == "—"
        assert all(valor.text() == "—" for valor, _, _ in vista._tarjetas_medio.values())
        assert vista.tabla_empleados.rowCount() == 0
        assert _textos_de_ventas(vista) == ["No se pudo cargar el cierre. Pruebe con Actualizar."]
        assert not vista.boton_desplegar.isEnabled()
        # Un cambio de tema después no resucita lo de antes.
        vista.repintar()
        assert vista.valor_total.text() == "—"


class TestVentasDelDia:
    def test_usa_el_dia_de_la_tienda(self, como_admin, vender, conexion, monkeypatch) -> None:
        # Antes usaba la fecha del calendario; con la hora de corte distinta de cero, las ventas
        # del día y el cierre dirían cosas distintas pasada la medianoche.
        from tienda_pos.ui import reportes_view

        ayer = reportes.dia_comercial() - timedelta(days=1)
        venta = vender(0)
        with transaccion(conexion):
            conexion.execute(
                "UPDATE venta SET fecha_hora = ? WHERE id = ?", (f"{ayer.isoformat()} 23:40:00", venta.id)
            )
        monkeypatch.setattr(reportes_view.reportes, "dia_comercial", lambda: ayer)

        como_admin.mostrar_reportes()

        assert como_admin.vista_reportes.tabla_ventas.rowCount() == 1
        assert como_admin.vista_reportes.valor_total.text() == formatear_clp(venta.total_clp)
