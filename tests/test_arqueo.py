"""Pruebas de la fase 19: el arqueo de caja (D-036), sin interfaz.

El cliente anota todos los retiros "porque si no le robarían un montón". Lo que más se cuida
aquí es justo eso: que un cajero no pueda anotar un retiro, ni ver cuánto debería haber antes de
contar, ni cobrar con la caja sin abrir —tampoco desde la otra caja, por la red—, y que la cuenta
de lo que debería haber sea exacta.
"""

from __future__ import annotations

import json
import socket
import sqlite3

import pytest

from tienda_pos.db import migrations
from tienda_pos.db.connection import transaccion
from tienda_pos.db.inicio import abrir_base_datos
from tienda_pos.db.migrations import VERSION_ESQUEMA, aplicar_migraciones
from tienda_pos.domain.errors import CajaCerrada, DatosInvalidos, PermisoDenegado
from tienda_pos.domain.models import MedioPago, Producto, Rol, TipoMovimiento
from tienda_pos.red import protocolo
from tienda_pos.red.sesion import SesionLocal
from tienda_pos.repositories import productos as repo_productos
from tienda_pos.repositories import ventas as repo_ventas
from tienda_pos.services import arqueo, auth
from tienda_pos.services import venta as servicio_venta

CAJA = "Caja 1"


@pytest.fixture
def pisco(conexion) -> Producto:
    producto = Producto(codigo_barras="7801234100016", nombre="Pisco 35° 1 L", precio_clp=6990, stock=500)
    with transaccion(conexion):
        repo_productos.crear(conexion, producto)
    return producto


@pytest.fixture
def marta(conexion):
    with transaccion(conexion):
        return auth.crear_usuario(conexion, "Marta", Rol.CAJERO, "5706")


def _vender(conexion, producto, caja=CAJA, medio=MedioPago.EFECTIVO, cantidad=1, **extra):
    carrito = servicio_venta.Carrito()
    carrito.agregar(producto, cantidad)
    return servicio_venta.cerrar_venta(conexion, carrito, caja=caja, medio_pago=medio, **extra)


class TestMigracion:
    def test_una_base_de_la_version_5_gana_el_arqueo_sin_tocar_sus_ventas(self, tmp_path) -> None:
        antigua = sqlite3.connect(tmp_path / "v5.db")
        antigua.row_factory = sqlite3.Row
        for version in range(1, 6):
            migrations._MIGRACIONES[version](antigua)
        antigua.execute("PRAGMA user_version = 5")
        antigua.execute(
            "INSERT INTO venta (folio, fecha_hora, subtotal_clp, descuento_clp, total_clp, caja, "
            "medio_pago) VALUES (8, '2026-09-23 21:00:00', 6990, 0, 6990, 'Caja 1', 'efectivo')"
        )
        antigua.commit()
        antes = dict(antigua.execute("SELECT * FROM venta").fetchone())

        assert aplicar_migraciones(antigua) == VERSION_ESQUEMA
        despues = dict(antigua.execute("SELECT * FROM venta").fetchone())

        # No se abrió con arqueo: no se inventa de qué cajón salió.
        assert despues["turno_id"] is None
        assert {columna: despues[columna] for columna in antes} == antes
        tablas = {f[0] for f in antigua.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"turno_caja", "movimiento_efectivo"} <= tablas
        antigua.close()

    def test_la_base_misma_impide_dos_cajas_abiertas_con_el_mismo_nombre(self, conexion, admin) -> None:
        # Aunque el servicio se equivocara o las dos cajas pidieran abrir a la vez.
        arqueo.abrir_turno(conexion, CAJA, admin, 0)
        with pytest.raises(sqlite3.IntegrityError):
            conexion.execute(
                "INSERT INTO turno_caja (caja, abierto_en, abierto_por, apertura_clp) "
                "VALUES (?, '2026-09-24 10:00:00', ?, 0)",
                (CAJA, admin.id),
            )


class TestAbrir:
    def test_abre_con_el_efectivo_del_cajon(self, conexion, marta) -> None:
        turno = arqueo.abrir_turno(conexion, CAJA, marta, 50_000)
        assert (turno.caja, turno.apertura_clp, turno.abierto_por_nombre) == (CAJA, 50_000, "Marta")
        assert turno.abierto and turno.movimientos == []
        assert arqueo.turno_abierto(conexion, CAJA, marta).id == turno.id

    def test_una_caja_cerrada_no_tiene_turno(self, conexion, marta) -> None:
        assert arqueo.turno_abierto(conexion, CAJA, marta) is None
        assert arqueo.turno_abierto(conexion, None, marta) is None

    def test_no_se_abre_dos_veces_y_dice_quien_la_abrio(self, conexion, marta, admin) -> None:
        arqueo.abrir_turno(conexion, CAJA, marta, 0)
        with pytest.raises(DatosInvalidos, match=r"Caja 1 ya está abierta desde las \d\d:\d\d, por Marta"):
            arqueo.abrir_turno(conexion, CAJA, admin, 0)

    def test_cada_caja_se_abre_por_su_lado(self, conexion, marta) -> None:
        uno = arqueo.abrir_turno(conexion, "Caja 1", marta, 10_000)
        dos = arqueo.abrir_turno(conexion, "Caja 2", marta, 20_000)
        assert uno.id != dos.id
        assert arqueo.turno_abierto(conexion, "Caja 2", marta).apertura_clp == 20_000

    def test_un_reintento_devuelve_la_misma_apertura(self, conexion, marta) -> None:
        # La respuesta se perdió por la red y la caja vuelve a pedirlo con el mismo intento.
        primera = arqueo.abrir_turno(conexion, CAJA, marta, 30_000, intento_id="a1")
        repetida = arqueo.abrir_turno(conexion, CAJA, marta, 30_000, intento_id="a1")
        assert repetida.id == primera.id

    def test_despues_de_cerrar_se_vuelve_a_abrir(self, conexion, marta) -> None:
        # Cambio de turno: la de la mañana cierra, la de la tarde abre.
        primero = arqueo.abrir_turno(conexion, CAJA, marta, 0)
        arqueo.cerrar_turno(conexion, CAJA, marta, primero.id, 0)
        segundo = arqueo.abrir_turno(conexion, CAJA, marta, 5_000)
        assert segundo.id != primero.id and segundo.abierto

    @pytest.mark.parametrize("monto", [-1, 1.5, "1000", True, None, 100_000_000])
    def test_montos_que_no_sirven(self, conexion, marta, monto) -> None:
        with pytest.raises(DatosInvalidos):
            arqueo.abrir_turno(conexion, CAJA, marta, monto)
        assert arqueo.turno_abierto(conexion, CAJA, marta) is None

    def test_cero_si_sirve(self, conexion, marta) -> None:
        assert arqueo.abrir_turno(conexion, CAJA, marta, 0).apertura_clp == 0

    def test_sin_usuario_o_sin_caja_no_se_abre(self, conexion, marta) -> None:
        with pytest.raises(DatosInvalidos, match="Inicie sesión"):
            arqueo.abrir_turno(conexion, CAJA, None, 0)
        with pytest.raises(DatosInvalidos, match="no tiene nombre"):
            arqueo.abrir_turno(conexion, None, marta, 0)


class TestVentasYTurno:
    def test_la_venta_queda_en_el_turno_abierto_de_su_caja(self, conexion, marta, pisco) -> None:
        turno = arqueo.abrir_turno(conexion, CAJA, marta, 0)
        otra = arqueo.abrir_turno(conexion, "Caja 2", marta, 0)
        venta = _vender(conexion, pisco)
        assert venta.turno_id == turno.id != otra.id
        assert repo_ventas.obtener(conexion, venta.id).turno_id == turno.id

    def test_la_sesion_no_cobra_con_la_caja_cerrada_ni_toca_el_stock(self, conexion, marta, pisco) -> None:
        sesion = SesionLocal(conexion, caja=CAJA)
        carrito = servicio_venta.Carrito()
        carrito.agregar(pisco)
        with pytest.raises(CajaCerrada):
            sesion.cerrar_venta(carrito, marta, "v1")
        assert repo_ventas.del_dia(conexion) == []
        assert repo_productos.obtener_por_id(conexion, pisco.id).stock == 500

    def test_con_la_caja_abierta_la_sesion_cobra(self, conexion, marta, pisco) -> None:
        sesion = SesionLocal(conexion, caja=CAJA)
        sesion.abrir_turno(marta, 0)
        carrito = servicio_venta.Carrito()
        carrito.agregar(pisco)
        assert sesion.cerrar_venta(carrito, marta, "v1").turno_id is not None

    def test_el_servicio_a_secas_no_lo_exige(self, conexion, pisco) -> None:
        # Pruebas y herramientas usan el servicio sin sesión: la regla es de la aplicación.
        assert _vender(conexion, pisco).turno_id is None

    def test_una_venta_sin_caja_no_necesita_turno(self, conexion, pisco) -> None:
        assert _vender(conexion, pisco, caja=None, exigir_turno=True).turno_id is None

    def test_un_reintento_de_cobro_tras_cerrar_devuelve_la_venta_original(
        self, conexion, marta, pisco
    ) -> None:
        # El cobro llegó, la respuesta se perdió, y entre medias se cerró la caja. La venta ya
        # ocurrió: se devuelve, en vez de negar que exista.
        turno = arqueo.abrir_turno(conexion, CAJA, marta, 0)
        primera = _vender(conexion, pisco, intento_id="v1", exigir_turno=True)
        arqueo.cerrar_turno(conexion, CAJA, marta, turno.id, 6990)
        repetida = _vender(conexion, pisco, intento_id="v1", exigir_turno=True)
        assert repetida.id == primera.id


class TestMovimientos:
    @pytest.fixture(autouse=True)
    def _caja_abierta(self, conexion, marta):
        self.turno = arqueo.abrir_turno(conexion, CAJA, marta, 100_000)

    def test_un_cajero_no_puede_anotar_un_retiro(self, conexion, marta) -> None:
        with pytest.raises(PermisoDenegado, match="retiro"):
            arqueo.registrar_movimiento(conexion, CAJA, marta, TipoMovimiento.RETIRO, 150_000)
        assert arqueo.turno_abierto(conexion, CAJA, marta).movimientos == []

    def test_el_administrador_si_y_queda_a_su_nombre(self, conexion, admin) -> None:
        retiro = arqueo.registrar_movimiento(
            conexion, CAJA, admin, TipoMovimiento.RETIRO, 150_000, "Para depositar"
        )
        assert (retiro.tipo, retiro.monto_clp, retiro.usuario_nombre) == (
            TipoMovimiento.RETIRO, 150_000, "Administrador",
        )
        assert retiro.turno_id == self.turno.id

    def test_un_pago_a_proveedor_lo_anota_el_cajero_a_su_nombre(self, conexion, marta) -> None:
        pago = arqueo.registrar_movimiento(
            conexion, CAJA, marta, TipoMovimiento.PAGO_PROVEEDOR, 45_000, "  CCU   hielo "
        )
        assert (pago.usuario_nombre, pago.motivo) == ("Marta", "CCU hielo")

    def test_el_pago_a_proveedor_exige_decir_a_quien(self, conexion, marta) -> None:
        with pytest.raises(DatosInvalidos, match="proveedor"):
            arqueo.registrar_movimiento(conexion, CAJA, marta, TipoMovimiento.PAGO_PROVEEDOR, 1000, "  ")

    def test_un_ingreso_de_sencillo(self, conexion, marta) -> None:
        ingreso = arqueo.registrar_movimiento(conexion, CAJA, marta, "ingreso", 20_000)
        assert ingreso.tipo is TipoMovimiento.INGRESO and ingreso.efecto_clp == 20_000

    @pytest.mark.parametrize("monto", [0, -500, 2.5, True, 100_000_000])
    def test_montos_que_no_sirven(self, conexion, admin, monto) -> None:
        with pytest.raises(DatosInvalidos):
            arqueo.registrar_movimiento(conexion, CAJA, admin, TipoMovimiento.RETIRO, monto)

    def test_un_tipo_desconocido(self, conexion, admin) -> None:
        with pytest.raises(DatosInvalidos, match="desconocido"):
            arqueo.registrar_movimiento(conexion, CAJA, admin, "vale", 1000)

    def test_un_motivo_demasiado_largo(self, conexion, admin) -> None:
        with pytest.raises(DatosInvalidos, match="largo"):
            arqueo.registrar_movimiento(conexion, CAJA, admin, TipoMovimiento.RETIRO, 1000, "x" * 121)

    def test_con_la_caja_cerrada_no_se_anota(self, conexion, admin) -> None:
        with pytest.raises(CajaCerrada):
            arqueo.registrar_movimiento(conexion, "Caja 2", admin, TipoMovimiento.RETIRO, 1000)

    def test_un_reintento_no_anota_dos_veces_el_mismo_retiro(self, conexion, admin) -> None:
        primero = arqueo.registrar_movimiento(
            conexion, CAJA, admin, TipoMovimiento.RETIRO, 150_000, intento_id="m1"
        )
        repetido = arqueo.registrar_movimiento(
            conexion, CAJA, admin, TipoMovimiento.RETIRO, 150_000, intento_id="m1"
        )
        assert repetido.id == primero.id
        assert len(arqueo.turno_abierto(conexion, CAJA, admin).movimientos) == 1


class TestCuantoDeberiaHaber:
    def test_la_cuenta_entera(self, conexion, admin, marta, pisco) -> None:
        arqueo.abrir_turno(conexion, CAJA, marta, 200_000)
        _vender(conexion, pisco, cantidad=2)  # 13.980 en efectivo
        _vender(conexion, pisco, medio=MedioPago.DEBITO)  # no pasa por el cajón
        _vender(conexion, pisco, caja="Caja 2")  # es de la otra caja
        anulada = _vender(conexion, pisco, cantidad=3)
        with transaccion(conexion):
            conexion.execute("UPDATE venta SET estado = 'anulada' WHERE id = ?", (anulada.id,))
        arqueo.registrar_movimiento(conexion, CAJA, admin, TipoMovimiento.RETIRO, 150_000)
        arqueo.registrar_movimiento(conexion, CAJA, marta, TipoMovimiento.PAGO_PROVEEDOR, 20_000, "CCU")
        arqueo.registrar_movimiento(conexion, CAJA, marta, TipoMovimiento.INGRESO, 5_000)

        turno = arqueo.turno_abierto(conexion, CAJA, admin)

        assert (turno.ventas_efectivo_clp, turno.ventas_efectivo) == (13_980, 1)
        assert (turno.retiros_clp, turno.pagos_clp, turno.ingresos_clp) == (150_000, 20_000, 5_000)
        assert turno.esperado_clp == 200_000 + 13_980 + 5_000 - 150_000 - 20_000

    def test_al_cerrar_se_guarda_el_esperado_y_la_diferencia(self, conexion, admin, marta, pisco) -> None:
        turno = arqueo.abrir_turno(conexion, CAJA, marta, 10_000)
        _vender(conexion, pisco)
        cerrado = arqueo.cerrar_turno(conexion, CAJA, admin, turno.id, 16_000, "Faltó una moneda")

        assert not cerrado.abierto
        assert (cerrado.esperado_clp, cerrado.contado_clp, cerrado.diferencia_clp) == (16_990, 16_000, -990)
        assert (cerrado.cerrado_por_nombre, cerrado.nota) == ("Administrador", "Faltó una moneda")
        assert arqueo.describir_diferencia(cerrado.diferencia_clp) == "Faltan $990"

    def test_lo_vendido_despues_de_cerrar_no_cambia_el_cierre(self, conexion, admin, marta, pisco) -> None:
        turno = arqueo.abrir_turno(conexion, CAJA, marta, 0)
        arqueo.cerrar_turno(conexion, CAJA, admin, turno.id, 0)
        _vender(conexion, pisco)
        (guardado,) = arqueo.turnos_recientes(conexion, admin)
        assert guardado.esperado_clp == 0 and guardado.diferencia_clp == 0

    @pytest.mark.parametrize(("diferencia", "texto"), [(0, "Cuadra"), (-3000, "Faltan $3.000"), (500, "Sobran $500")])
    def test_describir_diferencia(self, diferencia, texto) -> None:
        assert arqueo.describir_diferencia(diferencia) == texto


class TestConteoACiegas:
    def test_un_cajero_no_ve_cuanto_deberia_haber(self, conexion, marta, pisco) -> None:
        arqueo.abrir_turno(conexion, CAJA, marta, 10_000)
        _vender(conexion, pisco)
        turno = arqueo.turno_abierto(conexion, CAJA, marta)
        assert turno.ventas_efectivo_clp is None and turno.esperado_clp is None
        # Lo que sí ve: con cuánto abrió y lo anotado.
        assert turno.apertura_clp == 10_000

    def test_ni_al_cerrar(self, conexion, marta, pisco) -> None:
        turno = arqueo.abrir_turno(conexion, CAJA, marta, 10_000)
        _vender(conexion, pisco)
        cerrado = arqueo.cerrar_turno(conexion, CAJA, marta, turno.id, 16_990)
        assert cerrado.contado_clp == 16_990
        assert cerrado.esperado_clp is None and cerrado.diferencia_clp is None

    def test_pero_queda_guardado_para_el_administrador(self, conexion, admin, marta, pisco) -> None:
        turno = arqueo.abrir_turno(conexion, CAJA, marta, 10_000)
        _vender(conexion, pisco)
        arqueo.cerrar_turno(conexion, CAJA, marta, turno.id, 16_990)
        (visto,) = arqueo.turnos_recientes(conexion, admin)
        assert (visto.esperado_clp, visto.diferencia_clp, visto.cerrado_por_nombre) == (16_990, 0, "Marta")

    def test_solo_el_administrador_ve_los_cierres_anteriores(self, conexion, marta) -> None:
        with pytest.raises(PermisoDenegado):
            arqueo.turnos_recientes(conexion, marta)


class TestCerrar:
    def test_un_cajero_no_cierra_la_caja_de_otro_equipo(self, conexion, marta) -> None:
        otra = arqueo.abrir_turno(conexion, "Caja 2", marta, 0)
        with pytest.raises(PermisoDenegado):
            arqueo.cerrar_turno(conexion, CAJA, marta, otra.id, 0)
        assert arqueo.turno_abierto(conexion, "Caja 2", marta) is not None

    def test_el_administrador_si_por_si_ese_pc_no_enciende(self, conexion, admin, marta) -> None:
        otra = arqueo.abrir_turno(conexion, "Caja 2", marta, 0)
        assert not arqueo.cerrar_turno(conexion, CAJA, admin, otra.id, 0).abierto

    def test_cerrar_dos_veces_devuelve_el_primer_cierre(self, conexion, admin, marta) -> None:
        turno = arqueo.abrir_turno(conexion, CAJA, marta, 0)
        arqueo.cerrar_turno(conexion, CAJA, admin, turno.id, 1000)
        otra_vez = arqueo.cerrar_turno(conexion, CAJA, admin, turno.id, 99_000)
        assert otra_vez.contado_clp == 1000

    def test_un_turno_que_no_existe(self, conexion, marta) -> None:
        with pytest.raises(DatosInvalidos):
            arqueo.cerrar_turno(conexion, CAJA, marta, 999, 0)

    def test_contado_negativo(self, conexion, marta) -> None:
        turno = arqueo.abrir_turno(conexion, CAJA, marta, 0)
        with pytest.raises(DatosInvalidos):
            arqueo.cerrar_turno(conexion, CAJA, marta, turno.id, -1)
        assert arqueo.turno_abierto(conexion, CAJA, marta) is not None

    def test_la_nota_vacia_queda_sin_nota(self, conexion, admin, marta) -> None:
        turno = arqueo.abrir_turno(conexion, CAJA, marta, 0)
        assert arqueo.cerrar_turno(conexion, CAJA, admin, turno.id, 0, "   ").nota is None


class TestMontoSugerido:
    def test_sin_fijar_no_hay(self, conexion) -> None:
        assert arqueo.monto_sugerido(conexion) is None

    def test_el_administrador_lo_fija_y_lo_quita(self, conexion, admin) -> None:
        arqueo.fijar_monto_sugerido(conexion, admin, 50_000)
        assert arqueo.monto_sugerido(conexion) == 50_000
        arqueo.fijar_monto_sugerido(conexion, admin, None)
        assert arqueo.monto_sugerido(conexion) is None

    def test_un_cajero_no(self, conexion, marta) -> None:
        with pytest.raises(PermisoDenegado):
            arqueo.fijar_monto_sugerido(conexion, marta, 50_000)

    def test_negativo_no(self, conexion, admin) -> None:
        with pytest.raises(DatosInvalidos):
            arqueo.fijar_monto_sugerido(conexion, admin, -1)

    def test_un_valor_raro_en_la_base_no_rompe(self, conexion) -> None:
        with transaccion(conexion):
            conexion.execute("INSERT INTO meta (clave, valor) VALUES (?, 'mucho')", (arqueo.CLAVE_MONTO_SUGERIDO,))
        assert arqueo.monto_sugerido(conexion) is None


class TestProtocolo:
    def test_un_turno_va_y_vuelve(self, conexion, admin, marta, pisco) -> None:
        turno = arqueo.abrir_turno(conexion, CAJA, marta, 10_000)
        _vender(conexion, pisco)
        arqueo.registrar_movimiento(conexion, CAJA, marta, TipoMovimiento.PAGO_PROVEEDOR, 3000, "Hielo Sur")
        arqueo.cerrar_turno(conexion, CAJA, admin, turno.id, 13_990, "ok")
        (original,) = arqueo.turnos_recientes(conexion, admin)

        vuelta = protocolo.a_turno(json.loads(json.dumps(protocolo.de_turno(original))))

        assert vuelta == original
        assert vuelta.esperado_clp == original.esperado_clp == 13_990

    def test_un_tipo_desconocido_no_rompe_la_lectura(self, conexion, admin, marta) -> None:
        arqueo.abrir_turno(conexion, CAJA, marta, 0)
        mov = arqueo.registrar_movimiento(conexion, CAJA, admin, TipoMovimiento.RETIRO, 1000)
        datos = protocolo.de_movimiento(mov)
        datos["tipo"] = "vale"
        leido = protocolo.a_movimiento(datos)
        # Desconocido cuenta como salida: nunca aumenta lo que debería haber.
        assert leido.tipo is None and leido.efecto_clp == -1000


def _puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestPorLaRed:
    @pytest.fixture
    def red(self):
        """Un servidor de verdad, la caja "Principal", y la "Secundaria" conectada a él."""
        from tienda_pos.red.cliente import SesionRemota
        from tienda_pos.red.servidor import ServidorTienda

        conexion = abrir_base_datos(":memory:", con_datos_demo=True, compartida_entre_hilos=True)
        with transaccion(conexion):
            marta = auth.crear_usuario(conexion, "Marta", Rol.CAJERO, "5706")
            jefe = auth.crear_usuario(conexion, "Jefe", Rol.ADMIN, "8342")
        principal = SesionLocal(conexion, caja="Principal")
        puerto = _puerto_libre()
        with ServidorTienda(principal, host="127.0.0.1", puerto=puerto):
            yield SesionRemota("127.0.0.1", puerto, caja="Secundaria"), principal, marta, jefe
        conexion.close()

    @staticmethod
    def _carrito(sesion):
        from tienda_pos.db.seed import codigo_demo

        carrito = servicio_venta.Carrito()
        carrito.agregar(sesion.consultar_por_codigo(codigo_demo(0)))
        return carrito

    def test_la_secundaria_no_cobra_con_su_caja_cerrada(self, red) -> None:
        secundaria, principal, marta, _ = red
        principal.abrir_turno(marta, 0)  # abrir la principal no abre la otra
        with pytest.raises(CajaCerrada):
            secundaria.cerrar_venta(self._carrito(secundaria), marta, "s1")

    def test_abre_la_suya_cobra_y_la_venta_cae_en_su_turno(self, red) -> None:
        secundaria, principal, marta, _ = red
        turno = secundaria.abrir_turno(marta, 20_000, "a1")
        assert turno.caja == "Secundaria"
        venta = secundaria.cerrar_venta(self._carrito(secundaria), marta, "s1")
        assert venta.turno_id == turno.id
        assert principal.turno_abierto(marta) is None

    def test_un_cajero_no_anota_retiros_ni_desde_la_otra_caja(self, red) -> None:
        secundaria, _, marta, jefe = red
        secundaria.abrir_turno(marta, 0)
        with pytest.raises(PermisoDenegado):
            secundaria.registrar_movimiento(marta, TipoMovimiento.RETIRO, 150_000)
        retiro = secundaria.registrar_movimiento(jefe, TipoMovimiento.RETIRO, 150_000, "", "m1")
        again = secundaria.registrar_movimiento(jefe, TipoMovimiento.RETIRO, 150_000, "", "m1")
        assert retiro.id == again.id and retiro.usuario_nombre == "Jefe"

    def test_el_conteo_a_ciegas_tampoco_viaja_por_la_red(self, red) -> None:
        secundaria, _, marta, jefe = red
        turno = secundaria.abrir_turno(marta, 20_000)
        secundaria.cerrar_venta(self._carrito(secundaria), marta, "s1")

        visto_por_marta = secundaria.turno_abierto(marta)
        visto_por_jefe = secundaria.turno_abierto(jefe)
        assert visto_por_marta.esperado_clp is None
        assert visto_por_jefe.esperado_clp > 20_000

        cerrado = secundaria.cerrar_turno(marta, turno.id, 1_000, "Conté mal")
        assert cerrado.esperado_clp is None and cerrado.contado_clp == 1_000
        (del_jefe,) = secundaria.turnos_recientes(jefe)
        assert del_jefe.diferencia_clp < 0 and del_jefe.nota == "Conté mal"

    def test_el_monto_sugerido_es_el_mismo_en_las_dos_cajas(self, red) -> None:
        secundaria, principal, marta, jefe = red
        secundaria.fijar_monto_sugerido(jefe, 40_000)
        assert principal.monto_sugerido() == secundaria.monto_sugerido() == 40_000
        with pytest.raises(PermisoDenegado):
            secundaria.fijar_monto_sugerido(marta, 1)
