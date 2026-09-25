"""Pruebas de la pantalla de efectivo y de la apertura de caja (fase 19, D-036).

La ventana de `conftest.py` está en "Caja 1", abierta con $0. Aquí opera la cajera de verdad
de los datos de ejemplo ("Cajero"), para que lo anotado quede a su nombre.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="La interfaz requiere PySide6")

from tienda_pos.db.seed import codigo_demo  # noqa: E402
from tienda_pos.domain.models import TipoMovimiento  # noqa: E402
from tienda_pos.repositories import ventas as repo_ventas  # noqa: E402
from tienda_pos.services import arqueo, auth  # noqa: E402
from tienda_pos.ui import dialogos, efectivo_view, main_window  # noqa: E402


class _Respuestas:
    """Sustituye al diálogo de montos: devuelve lo que se le diga y recuerda qué preguntó."""

    def __init__(self, *respuestas):
        self.respuestas = list(respuestas)
        self.llamadas: list[tuple[tuple, dict]] = []

    def __call__(self, cls, *args, **kwargs):
        self.llamadas.append((args, kwargs))
        return self.respuestas.pop(0) if self.respuestas else None


@pytest.fixture
def respuestas(monkeypatch):
    def poner(*valores) -> _Respuestas:
        falso = _Respuestas(*valores)
        monkeypatch.setattr(efectivo_view.DialogoMonto, "pedir", classmethod(falso))
        return falso

    return poner


@pytest.fixture
def cajera(ventana, conexion):
    """La ventana operada por la cajera, que no es administradora."""
    usuario = auth.autenticar(conexion, "Cajero", "1111")
    ventana.establecer_usuario(usuario)
    return ventana


@pytest.fixture
def sin_autorizacion(monkeypatch):
    monkeypatch.setattr(main_window.DialogoLogin, "pedir", staticmethod(lambda *a, **k: None))


@pytest.fixture
def avisos(monkeypatch):
    mensajes: list[str] = []
    monkeypatch.setattr(dialogos, "mostrar_info", lambda _p, texto, *a, **k: mensajes.append(texto))
    return mensajes


def _cerrar_la_caja(conexion) -> None:
    admin = auth.autenticar(conexion, "Administrador", "1234")
    turno = arqueo.turno_abierto(conexion, "Caja 1", admin)
    arqueo.cerrar_turno(conexion, "Caja 1", admin, turno.id, 0)


def _textos(tabla, columna: int) -> list[str]:
    return [tabla.item(f, columna).text() for f in range(tabla.rowCount())]


class TestPantalla:
    def test_la_cajera_entra_sin_pin_desde_la_barra(self, cajera, sin_autorizacion) -> None:
        cajera.barra_lateral._botones["efectivo"].click()
        assert cajera.pantallas.currentWidget() is cajera.vista_efectivo
        assert cajera.titulo_pantalla.text() == "Efectivo"
        assert cajera.subtitulo_pantalla.text().startswith("Caja 1  ·  abierta desde las ")

    def test_dice_que_esta_abierta_y_no_ensena_las_cuentas(self, cajera) -> None:
        cajera.mostrar_efectivo()
        vista = cajera.vista_efectivo
        assert vista.etiqueta_estado.text() == "Caja 1 abierta"
        assert not vista.boton_cerrar.isHidden() and vista.boton_abrir.isHidden()
        # Conteo a ciegas: ni la cuenta ni los cierres anteriores.
        assert vista.panel_cuentas.isHidden() and vista.panel_cierres.isHidden()
        assert not vista.aviso_ciego.isHidden()
        assert not vista.boton_ver_cuentas.isHidden()

    def test_ver_las_cuentas_pide_el_pin_y_las_ensena(self, cajera, conexion, monkeypatch) -> None:
        admin = auth.autenticar(conexion, "Administrador", "1234")
        monkeypatch.setattr(main_window.DialogoLogin, "pedir", staticmethod(lambda *a, **k: admin))
        cajera.mostrar_efectivo()
        cajera.vista_efectivo.boton_ver_cuentas.click()
        vista = cajera.vista_efectivo
        assert not vista.panel_cuentas.isHidden() and not vista.panel_cierres.isHidden()
        assert vista.valor_esperado.text() == "$0"
        # Salir y volver lo olvida: la cajera sigue sin verlas.
        cajera.mostrar_venta()
        cajera.mostrar_efectivo()
        assert vista.panel_cuentas.isHidden()

    def test_sin_pin_siguen_ocultas(self, cajera, sin_autorizacion) -> None:
        cajera.mostrar_efectivo()
        cajera.vista_efectivo.boton_ver_cuentas.click()
        assert cajera.vista_efectivo.panel_cuentas.isHidden()

    def test_el_administrador_las_ve_de_entrada(self, como_admin, conexion) -> None:
        como_admin.establecer_usuario(auth.autenticar(conexion, "Administrador", "1234"))
        como_admin.vista_venta.agregar_por_codigo(codigo_demo(0))
        como_admin.vista_venta.cobrar()
        como_admin.mostrar_efectivo()
        vista = como_admin.vista_efectivo
        venta = repo_ventas.del_dia(conexion)[0]
        assert vista.valor_ventas.text() == f"${venta.total_clp:,}".replace(",", ".")
        assert vista.boton_ver_cuentas.isHidden()


class TestAnotar:
    def test_un_pago_a_proveedor_queda_a_nombre_de_la_cajera(self, cajera, respuestas) -> None:
        respuestas((45_000, "CCU"))
        cajera.mostrar_efectivo()
        cajera.vista_efectivo.boton_pago.click()
        tabla = cajera.vista_efectivo.tabla_movimientos
        assert _textos(tabla, 1) == ["Pago proveedor"]
        assert _textos(tabla, 2) == ["−$45.000"]
        assert _textos(tabla, 3) == ["CCU"]
        assert _textos(tabla, 4) == ["Cajero"]

    def test_el_pago_pide_el_proveedor_como_obligatorio(self, cajera, respuestas) -> None:
        falso = respuestas(None)
        cajera.mostrar_efectivo()
        cajera.vista_efectivo.boton_pago.click()
        (_, kwargs), = falso.llamadas
        assert kwargs["texto_obligatorio"] and kwargs["etiqueta_texto"] == "Proveedor"
        assert cajera.vista_efectivo.tabla_movimientos.rowCount() == 0

    def test_la_cajera_sin_pin_no_anota_un_retiro(self, cajera, respuestas, sin_autorizacion) -> None:
        falso = respuestas((150_000, ""))
        cajera.mostrar_efectivo()
        cajera.vista_efectivo.boton_retiro.click()
        assert falso.llamadas == []  # ni siquiera se le pregunta el monto
        assert cajera.vista_efectivo.tabla_movimientos.rowCount() == 0

    def test_con_pin_el_retiro_queda_a_nombre_del_administrador(
        self, cajera, respuestas, conexion, monkeypatch
    ) -> None:
        admin = auth.autenticar(conexion, "Administrador", "1234")
        monkeypatch.setattr(main_window.DialogoLogin, "pedir", staticmethod(lambda *a, **k: admin))
        respuestas((150_000, "Depósito"))
        cajera.mostrar_efectivo()
        cajera.vista_efectivo.boton_retiro.click()
        tabla = cajera.vista_efectivo.tabla_movimientos
        assert _textos(tabla, 1) == ["Retiro"] and _textos(tabla, 4) == ["Administrador"]

    def test_un_ingreso_suma(self, cajera, respuestas) -> None:
        respuestas((20_000, ""))
        cajera.mostrar_efectivo()
        cajera.vista_efectivo.boton_ingreso.click()
        assert _textos(cajera.vista_efectivo.tabla_movimientos, 2) == ["+$20.000"]

    def test_el_mas_reciente_arriba(self, cajera, respuestas) -> None:
        respuestas((1000, "Primero"), (2000, "Segundo"))
        cajera.mostrar_efectivo()
        cajera.vista_efectivo.boton_pago.click()
        cajera.vista_efectivo.boton_pago.click()
        assert _textos(cajera.vista_efectivo.tabla_movimientos, 3) == ["Segundo", "Primero"]

    def test_con_la_caja_cerrada_los_botones_no_se_pueden_usar(self, cajera, conexion) -> None:
        _cerrar_la_caja(conexion)
        cajera.mostrar_efectivo()
        vista = cajera.vista_efectivo
        assert vista.etiqueta_estado.text() == "Caja 1 cerrada"
        assert not any(b.isEnabled() for b in (vista.boton_pago, vista.boton_retiro, vista.boton_ingreso))
        assert not vista.boton_abrir.isHidden() and vista.boton_cerrar.isHidden()


class TestCerrarYAbrir:
    def test_la_cajera_cierra_a_ciegas(self, cajera, respuestas, avisos) -> None:
        respuestas((12_000, "Todo bien"))
        cajera.mostrar_efectivo()
        cajera.vista_efectivo.boton_cerrar.click()
        assert avisos == ["Caja cerrada. Se anotaron $12.000 contados."]
        assert cajera.vista_efectivo.etiqueta_estado.text() == "Caja 1 cerrada"

    def test_el_administrador_ve_el_resultado(self, como_admin, conexion, respuestas, avisos) -> None:
        como_admin.establecer_usuario(auth.autenticar(conexion, "Administrador", "1234"))
        respuestas((500, ""))
        como_admin.mostrar_efectivo()
        como_admin.vista_efectivo.boton_cerrar.click()
        assert "Debería haber: $0" in avisos[0] and "Sobran $500" in avisos[0]
        cierres = como_admin.vista_efectivo.tabla_cierres
        assert _textos(cierres, 4) == ["Sobran $500"]

    def test_cancelar_el_cierre_no_cierra(self, cajera, respuestas) -> None:
        respuestas(None)
        cajera.mostrar_efectivo()
        cajera.vista_efectivo.boton_cerrar.click()
        assert cajera.vista_efectivo.turno is not None

    def test_abrir_desde_la_pantalla_con_el_monto_sugerido(
        self, cajera, respuestas, conexion
    ) -> None:
        _cerrar_la_caja(conexion)
        arqueo.fijar_monto_sugerido(conexion, auth.autenticar(conexion, "Administrador", "1234"), 50_000)
        falso = respuestas((48_500, ""))
        cajera.mostrar_efectivo()
        cajera.vista_efectivo.boton_abrir.click()

        (_, kwargs), = falso.llamadas
        assert kwargs["valor_inicial"] == 50_000
        assert "$50.000" in kwargs["ayuda"]
        # Se guarda lo que se escribió, no lo sugerido.
        assert cajera.vista_efectivo.turno.apertura_clp == 48_500


class TestCobrarConLaCajaCerrada:
    def test_ofrece_abrirla_y_si_no_se_abre_no_cobra(self, cajera, conexion, respuestas) -> None:
        _cerrar_la_caja(conexion)
        falso = respuestas(None)
        cajera.vista_venta.agregar_por_codigo(codigo_demo(0))
        cajera.vista_venta.cobrar()
        assert len(falso.llamadas) == 1
        assert repo_ventas.del_dia(conexion) == []
        # El carrito sigue ahí: el cliente no tiene que volver a pasar nada.
        assert not cajera.vista_venta.carrito.esta_vacio

    def test_si_se_abre_cobra_sin_volver_a_confirmar(
        self, cajera, conexion, respuestas, monkeypatch
    ) -> None:
        _cerrar_la_caja(conexion)
        confirmaciones = []
        monkeypatch.setattr(dialogos, "confirmar", lambda *a, **k: confirmaciones.append(1) or True)
        respuestas((30_000, ""))
        cajera.vista_venta.agregar_por_codigo(codigo_demo(0))
        cajera.vista_venta.cobrar()
        (venta,) = repo_ventas.del_dia(conexion)
        assert venta.turno_id == arqueo.turno_abierto(conexion, "Caja 1", None).id
        assert len(confirmaciones) == 1

    def test_con_la_caja_abierta_no_pregunta_nada(self, cajera, conexion, respuestas) -> None:
        falso = respuestas()
        cajera.vista_venta.agregar_por_codigo(codigo_demo(0))
        cajera.vista_venta.cobrar()
        assert falso.llamadas == [] and len(repo_ventas.del_dia(conexion)) == 1


class TestAlArrancar:
    def test_si_esta_cerrada_propone_abrirla(self, cajera, conexion, respuestas) -> None:
        _cerrar_la_caja(conexion)
        falso = respuestas((10_000, ""))
        cajera.proponer_apertura()
        assert len(falso.llamadas) == 1
        assert arqueo.turno_abierto(conexion, "Caja 1", None).apertura_clp == 10_000

    def test_si_esta_abierta_no_molesta(self, cajera, respuestas) -> None:
        falso = respuestas()
        cajera.proponer_apertura()
        assert falso.llamadas == []

    def test_se_puede_dejar_para_despues(self, cajera, conexion, respuestas) -> None:
        _cerrar_la_caja(conexion)
        respuestas(None)
        cajera.proponer_apertura()
        assert arqueo.turno_abierto(conexion, "Caja 1", None) is None


class TestMontoSugerido:
    def test_el_administrador_lo_cambia(self, como_admin, conexion, respuestas) -> None:
        como_admin.establecer_usuario(auth.autenticar(conexion, "Administrador", "1234"))
        respuestas((60_000, ""))
        como_admin.mostrar_efectivo()
        como_admin.vista_efectivo.boton_sugerido.click()
        assert arqueo.monto_sugerido(conexion) == 60_000
        assert como_admin.vista_efectivo.etiqueta_sugerido.text() == "Apertura sugerida: $60.000"

    def test_la_cajera_no_ve_el_boton(self, cajera) -> None:
        # Va en el panel de los cierres, que solo ve el administrador.
        cajera.mostrar_efectivo()
        assert not cajera.vista_efectivo.boton_sugerido.isVisible()


class TestDialogoMonto:
    @pytest.fixture(autouse=True)
    def _qt(self, app) -> None:
        pass

    def test_valida_antes_de_aceptar(self) -> None:
        dialogo = efectivo_view.DialogoMonto(
            "Pago", "¿Cuánto?", etiqueta_texto="Proveedor", texto_obligatorio=True, puede_ser_cero=False
        )
        for texto, proveedor, error in (
            ("abc", "CCU", "Escriba el monto"),
            ("-5", "CCU", "negativo"),
            ("0", "CCU", "mayor que cero"),
            ("5.000", "  ", "vacío"),
        ):
            dialogo.campo_monto.setText(texto)
            dialogo.campo_texto.setText(proveedor)
            dialogo._validar()
            assert error in dialogo.error.text()
            assert dialogo.result() == 0

        dialogo.campo_monto.setText("$5.000")
        dialogo.campo_texto.setText("CCU")
        dialogo._validar()
        assert (dialogo.monto, dialogo.texto) == (5000, "CCU")
