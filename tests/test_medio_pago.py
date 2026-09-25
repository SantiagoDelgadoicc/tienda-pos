"""Pruebas de la fase 17: con qué pagó el cliente.

El cliente pidió ver en el cierre "ventas en efectivo y ventas en débito y crédito", separados.
Lo marca el cajero al cobrar. Lo que más se cuida aquí: que nunca se invente el dato —las
ventas de antes quedan sin registrar, no en efectivo— y que un valor raro no tumbe el cierre.
"""

from __future__ import annotations

import socket
import sqlite3

import pytest

from tienda_pos.db import migrations
from tienda_pos.db.connection import transaccion
from tienda_pos.db.inicio import abrir_base_datos
from tienda_pos.db.migrations import VERSION_ESQUEMA, aplicar_migraciones
from tienda_pos.domain.errors import DatosInvalidos
from tienda_pos.domain.models import MedioPago, Rol
from tienda_pos.red import protocolo
from tienda_pos.repositories import ventas as repo_ventas
from tienda_pos.services import auth
from tienda_pos.services import venta as servicio_venta

from .conftest import abrir_cajas


def _carrito(producto):
    carrito = servicio_venta.Carrito()
    carrito.agregar(producto)
    return carrito


class TestMigracion:
    def test_una_base_de_la_version_4_gana_el_medio_sin_rellenarlo(self, tmp_path) -> None:
        antigua = sqlite3.connect(tmp_path / "v4.db")
        antigua.row_factory = sqlite3.Row
        for paso in (
            migrations._crear_esquema_inicial,
            migrations._descuento_por_linea,
            migrations._intento_de_cobro,
            migrations._caja_de_la_venta,
        ):
            paso(antigua)
        antigua.execute("PRAGMA user_version = 4")
        antigua.execute(
            "INSERT INTO venta (folio, fecha_hora, subtotal_clp, descuento_clp, total_clp, caja) "
            "VALUES (3, '2026-09-22 20:00:00', 2290, 0, 2290, 'Caja 1')"
        )
        antigua.commit()
        antes = dict(antigua.execute("SELECT * FROM venta").fetchone())

        assert aplicar_migraciones(antigua) == VERSION_ESQUEMA
        despues = dict(antigua.execute("SELECT * FROM venta").fetchone())

        # "No registrado", no "efectivo": no se sabe, y no se inventa.
        assert despues["medio_pago"] is None
        assert {columna: despues[columna] for columna in antes} == antes
        antigua.close()


class TestServicio:
    @pytest.mark.parametrize("medio", list(MedioPago))
    def test_se_guarda_cada_medio(self, conexion, productos, medio) -> None:
        venta = servicio_venta.cerrar_venta(conexion, _carrito(productos["leche"]), medio_pago=medio)
        assert repo_ventas.obtener(conexion, venta.id).medio_pago is medio

    def test_por_defecto_es_efectivo(self, conexion, productos) -> None:
        venta = servicio_venta.cerrar_venta(conexion, _carrito(productos["leche"]))
        assert venta.medio_pago is MedioPago.EFECTIVO

    def test_se_acepta_el_texto_que_llega_por_la_red(self, conexion, productos) -> None:
        venta = servicio_venta.cerrar_venta(conexion, _carrito(productos["leche"]), medio_pago="credito")
        assert venta.medio_pago is MedioPago.CREDITO

    @pytest.mark.parametrize("raro", ["cheque", "Débito", "", "DEBITO"])
    def test_un_medio_desconocido_se_rechaza_y_no_se_cobra(self, conexion, productos, raro) -> None:
        stock_antes = productos["leche"].stock
        with pytest.raises(DatosInvalidos, match="Medio de pago desconocido"):
            servicio_venta.cerrar_venta(conexion, _carrito(productos["leche"]), medio_pago=raro)
        assert repo_ventas.del_dia(conexion) == []
        fila = conexion.execute(
            "SELECT stock FROM producto WHERE id = ?", (productos["leche"].id,)
        ).fetchone()
        assert fila["stock"] == stock_antes

    def test_none_deja_el_medio_sin_registrar(self, conexion, productos) -> None:
        venta = servicio_venta.cerrar_venta(conexion, _carrito(productos["leche"]), medio_pago=None)
        assert repo_ventas.obtener(conexion, venta.id).medio_pago is None

    def test_un_reintento_con_otro_medio_devuelve_la_venta_original(self, conexion, productos) -> None:
        # El cobro llegó, la respuesta se perdió, y el cajero cambió a débito antes de reintentar.
        # La venta ya ocurrió en efectivo: gana la guardada, y no se cobra dos veces.
        primera = servicio_venta.cerrar_venta(
            conexion, _carrito(productos["leche"]), intento_id="i1", medio_pago=MedioPago.EFECTIVO
        )
        repetida = servicio_venta.cerrar_venta(
            conexion, _carrito(productos["leche"]), intento_id="i1", medio_pago=MedioPago.DEBITO
        )
        assert repetida.id == primera.id
        assert repetida.medio_pago is MedioPago.EFECTIVO
        assert len(repo_ventas.del_dia(conexion)) == 1


class TestLecturaTolerante:
    def test_un_valor_desconocido_en_la_base_no_tumba_las_ventas_del_dia(self, conexion, productos) -> None:
        # La columna no tiene CHECK: un valor raro es posible, escrito a mano o por una versión
        # más nueva. Se lee como no registrado en lugar de romper el cierre.
        venta = servicio_venta.cerrar_venta(conexion, _carrito(productos["leche"]))
        conexion.execute("UPDATE venta SET medio_pago = 'transferencia' WHERE id = ?", (venta.id,))
        ventas = repo_ventas.del_dia(conexion)
        assert [v.medio_pago for v in ventas] == [None]

    @pytest.mark.parametrize(("valor", "leido"), [
        ("efectivo", MedioPago.EFECTIVO), ("debito", MedioPago.DEBITO),
        (None, None), ("", None), ("transferencia", None), (7, None),
    ])
    def test_leer(self, valor, leido) -> None:
        assert MedioPago.leer(valor) is leido


class TestProtocolo:
    def test_el_medio_va_y_vuelve(self, conexion, productos) -> None:
        venta = servicio_venta.cerrar_venta(
            conexion, _carrito(productos["leche"]), medio_pago=MedioPago.DEBITO
        )
        assert protocolo.a_venta(protocolo.de_venta(venta)).medio_pago is MedioPago.DEBITO

    def test_un_mensaje_sin_medio_no_rompe(self, conexion, productos) -> None:
        datos = protocolo.de_venta(servicio_venta.cerrar_venta(conexion, _carrito(productos["leche"])))
        del datos["medio_pago"]
        assert protocolo.a_venta(datos).medio_pago is None


def _puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestPorLaRed:
    @pytest.fixture
    def secundaria(self):
        from tienda_pos.red.cliente import SesionRemota
        from tienda_pos.red.servidor import ServidorTienda
        from tienda_pos.red.sesion import SesionLocal

        conexion = abrir_base_datos(":memory:", con_datos_demo=True, compartida_entre_hilos=True)
        with transaccion(conexion):
            cajera = auth.crear_usuario(conexion, "Marta", Rol.CAJERO, "5706")
        abrir_cajas(conexion, cajera, "Secundaria")
        puerto = _puerto_libre()
        with ServidorTienda(SesionLocal(conexion, caja="Principal"), host="127.0.0.1", puerto=puerto):
            yield SesionRemota("127.0.0.1", puerto, caja="Secundaria"), cajera, conexion
        conexion.close()

    @staticmethod
    def _carrito_demo(sesion):
        from tienda_pos.db.seed import codigo_demo

        carrito = servicio_venta.Carrito()
        carrito.agregar(sesion.consultar_por_codigo(codigo_demo(0)))
        return carrito

    def test_el_medio_de_la_secundaria_llega_al_servidor(self, secundaria) -> None:
        remota, cajera, conexion = secundaria
        venta = remota.cerrar_venta(
            self._carrito_demo(remota), cajera, "r1", medio_pago=MedioPago.CREDITO
        )
        guardada = repo_ventas.obtener(conexion, venta.id)
        assert guardada.medio_pago is MedioPago.CREDITO
        assert guardada.caja == "Secundaria"

    def test_una_peticion_sin_medio_queda_sin_registrar(self, secundaria) -> None:
        remota, cajera, conexion = secundaria
        venta = remota.cerrar_venta(self._carrito_demo(remota), cajera, "r2", medio_pago=None)
        assert repo_ventas.obtener(conexion, venta.id).medio_pago is None


class TestPantallaDeCobro:
    @pytest.fixture(autouse=True)
    def _qt(self, app) -> None:
        pytest.importorskip("PySide6", reason="La interfaz requiere PySide6")

    @staticmethod
    def _cobrar(ventana, *codigos: int) -> None:
        from tienda_pos.db.seed import codigo_demo

        for indice in codigos:
            ventana.vista_venta.agregar_por_codigo(codigo_demo(indice))
        ventana.vista_venta.cobrar()

    def test_empieza_en_efectivo(self, ventana) -> None:
        assert ventana.vista_venta.medio_pago is MedioPago.EFECTIVO
        assert ventana.vista_venta._botones_medio[MedioPago.EFECTIVO].isChecked()

    def test_f11_recorre_los_tres_y_vuelve(self, ventana) -> None:
        vistos = []
        for _ in range(4):
            ventana._medio_pago()
            vistos.append(ventana.vista_venta.medio_pago)
        assert vistos == [MedioPago.DEBITO, MedioPago.CREDITO, MedioPago.EFECTIVO, MedioPago.DEBITO]

    def test_f11_no_hace_nada_fuera_de_la_venta(self, ventana) -> None:
        ventana.mostrar_consulta()
        ventana._medio_pago()
        assert ventana.vista_venta.medio_pago is MedioPago.EFECTIVO

    def test_pulsar_un_medio_lo_elige_y_devuelve_el_foco_al_escaneo(self, ventana) -> None:
        ventana.vista_venta._botones_medio[MedioPago.CREDITO].click()
        assert ventana.vista_venta.medio_pago is MedioPago.CREDITO
        assert ventana.vista_venta.campo_codigo.hasFocus()

    def test_los_botones_no_le_quitan_el_foco_a_la_pistola(self, ventana) -> None:
        from PySide6.QtCore import Qt

        for boton in ventana.vista_venta._botones_medio.values():
            assert boton.focusPolicy() == Qt.FocusPolicy.NoFocus

    def test_cobrar_con_debito_lo_guarda_y_vuelve_a_efectivo(self, ventana, conexion) -> None:
        ventana.vista_venta.elegir_medio_pago(MedioPago.DEBITO)
        self._cobrar(ventana, 0)
        assert [v.medio_pago for v in repo_ventas.del_dia(conexion)] == [MedioPago.DEBITO]
        # Un selector pegajoso cobraría mal la primera venta de la mañana siguiente.
        assert ventana.vista_venta.medio_pago is MedioPago.EFECTIVO

    def test_el_aviso_dice_el_medio(self, ventana, monkeypatch) -> None:
        avisos = []
        monkeypatch.setattr(ventana.vista_venta, "_avisar", lambda texto, exito: avisos.append(texto))
        ventana.vista_venta.elegir_medio_pago(MedioPago.CREDITO)
        self._cobrar(ventana, 0)
        assert avisos[-1].endswith("· Crédito.")

    def test_la_confirmacion_dice_el_medio(self, ventana, monkeypatch) -> None:
        from tienda_pos.services.preferencias import Preferencias
        from tienda_pos.ui import dialogos

        textos = []
        monkeypatch.setattr(dialogos, "confirmar", lambda _p, _t, texto, **k: textos.append(texto) or True)
        ventana.vista_venta.preferencias = Preferencias(confirmar_cobro=True)
        ventana.vista_venta.elegir_medio_pago(MedioPago.DEBITO)
        self._cobrar(ventana, 0)
        assert "Pago: Débito" in textos[0]

    def test_cancelar_la_venta_vuelve_a_efectivo(self, ventana) -> None:
        from tienda_pos.db.seed import codigo_demo

        ventana.vista_venta.agregar_por_codigo(codigo_demo(0))
        ventana.vista_venta.elegir_medio_pago(MedioPago.CREDITO)
        ventana.vista_venta.cancelar_venta()
        assert ventana.vista_venta.medio_pago is MedioPago.EFECTIVO

    def test_un_cobro_fallido_conserva_el_medio_elegido(self, ventana, monkeypatch) -> None:
        # Si falla, el cajero reintenta: el medio no puede cambiar por su cuenta en medio.
        from tienda_pos.domain.errors import ErrorDominio

        def falla(*a, **k):
            raise ErrorDominio("La red se cayó")

        monkeypatch.setattr(ventana.vista_venta._sesion, "cerrar_venta", falla)
        ventana.vista_venta.elegir_medio_pago(MedioPago.DEBITO)
        self._cobrar(ventana, 0)
        assert ventana.vista_venta.medio_pago is MedioPago.DEBITO


class TestVentasDelDia:
    @pytest.fixture(autouse=True)
    def _qt(self, app) -> None:
        pytest.importorskip("PySide6", reason="La interfaz requiere PySide6")

    def test_la_columna_medio_con_color_y_sin_registrar(self, como_admin, conexion, productos) -> None:
        from tienda_pos.ui import estilos
        from tienda_pos.ui.reportes_view import _COL_MEDIO

        servicio_venta.cerrar_venta(conexion, _carrito(productos["leche"]), medio_pago=MedioPago.DEBITO)
        servicio_venta.cerrar_venta(conexion, _carrito(productos["leche"]), medio_pago=None)
        como_admin.mostrar_reportes()
        tabla = como_admin.vista_reportes.tabla_ventas

        textos = {tabla.item(f, _COL_MEDIO).text() for f in range(tabla.rowCount())}
        assert textos == {"Débito", "Sin registrar"}
        fila_debito = next(f for f in range(tabla.rowCount()) if tabla.item(f, _COL_MEDIO).text() == "Débito")
        color = tabla.item(fila_debito, _COL_MEDIO).foreground().color().name().upper()
        assert color == estilos.actual.debito.upper()

    def test_cada_medio_tiene_el_mismo_color_en_todas_partes(self, app) -> None:
        from tienda_pos.ui import estilos

        assert estilos.color_medio(MedioPago.DEBITO) == estilos.actual.debito
        assert estilos.color_medio(MedioPago.CREDITO) == estilos.actual.credito
        assert estilos.color_medio(MedioPago.EFECTIVO) == estilos.actual.texto
        assert estilos.color_medio(None) == estilos.actual.texto
