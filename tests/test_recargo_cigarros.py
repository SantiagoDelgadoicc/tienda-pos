"""Pruebas de la fase 26: el recargo de los cigarros pagados con tarjeta (D-040).

Lo pidió el cliente el 2026-10-10: con débito o crédito, $500 más por cada cajetilla, y que el
dueño pueda cambiar el monto. Se prueba de abajo arriba: el ajuste, el carrito, el cobro —donde
el servidor manda—, la migración de la base de la tienda, la red entre cajas y las pantallas.
"""

from __future__ import annotations

import socket
import sqlite3

import pytest

from tienda_pos.db.connection import transaccion
from tienda_pos.db.inicio import abrir_base_datos
from tienda_pos.domain.errors import DatosInvalidos, PermisoDenegado
from tienda_pos.domain.models import MedioPago, Producto, Rol
from tienda_pos.repositories import productos as repo_productos
from tienda_pos.repositories import ventas as repo_ventas
from tienda_pos.services import auth, catalogo
from tienda_pos.services import venta as servicio_venta
from tienda_pos.services.venta import Carrito

from .conftest import abrir_cajas

RUBIOS = "7802000000017"
MENTA = "7802000000024"
LECHE = "7801234000019"


@pytest.fixture
def tienda(conexion, admin, cajero):
    """Dos cajetillas y una leche, con la caja abierta."""
    with transaccion(conexion):
        for producto in (
            Producto(codigo_barras=RUBIOS, nombre="Rubios 20", precio_clp=5200, stock=40, es_cigarro=True),
            Producto(codigo_barras=MENTA, nombre="Mentolados 20", precio_clp=5400, stock=40, es_cigarro=True),
            Producto(codigo_barras=LECHE, nombre="Leche 1 L", precio_clp=1290, stock=40),
        ):
            repo_productos.crear(conexion, producto)
    abrir_cajas(conexion, admin, "Caja 1")
    return conexion


def _carrito(conexion, *pares, recargo: int | None = None) -> Carrito:
    carrito = Carrito()
    for codigo, cantidad in pares:
        carrito.agregar(catalogo.consultar_por_codigo(conexion, codigo), cantidad)
    carrito.recargo_unitario_clp = recargo
    return carrito


# --------------------------------------------------------------------------- el ajuste


class TestElRecargo:
    def test_por_defecto_son_500(self, conexion) -> None:
        assert catalogo.recargo_cigarro(conexion) == 500

    def test_el_administrador_lo_cambia(self, conexion, admin) -> None:
        catalogo.fijar_recargo_cigarro(conexion, admin, 700)
        assert catalogo.recargo_cigarro(conexion) == 700

    def test_con_cero_no_hay_recargo(self, conexion, admin) -> None:
        catalogo.fijar_recargo_cigarro(conexion, admin, 0)
        assert catalogo.recargo_cigarro(conexion) == 0

    def test_un_cajero_no_lo_cambia(self, conexion, cajero) -> None:
        with pytest.raises(PermisoDenegado):
            catalogo.fijar_recargo_cigarro(conexion, cajero, 0)
        assert catalogo.recargo_cigarro(conexion) == 500

    @pytest.mark.parametrize("monto", [-1, 10_001, 500.5, "500", True])
    def test_rechaza_montos_que_no_sirven(self, conexion, admin, monto) -> None:
        with pytest.raises(DatosInvalidos):
            catalogo.fijar_recargo_cigarro(conexion, admin, monto)

    def test_un_valor_ilegible_en_la_base_vuelve_al_de_siempre(self, conexion) -> None:
        from tienda_pos.db.connection import escribir_meta

        with transaccion(conexion):
            escribir_meta(conexion, catalogo.CLAVE_RECARGO_CIGARRO, "quinientos")
        assert catalogo.recargo_cigarro(conexion) == 500


class TestProductoCigarro:
    def test_se_crea_y_se_lee_marcado(self, conexion, cajero) -> None:
        # Lo crea un cajero: Productos es de todos (D-038).
        catalogo.crear_producto(conexion, cajero, RUBIOS, "Rubios 20", 5200, 10, es_cigarro=True)
        assert catalogo.consultar_por_codigo(conexion, RUBIOS).es_cigarro

    def test_un_cigarro_no_se_vende_por_peso(self, conexion, cajero) -> None:
        with pytest.raises(DatosInvalidos, match="por unidad"):
            catalogo.crear_producto(conexion, cajero, "", "Tabaco suelto", 100, 0, por_peso=True, es_cigarro=True)

    def test_editar_sin_decir_nada_lo_deja_como_estaba(self, tienda, cajero) -> None:
        rubios = catalogo.consultar_por_codigo(tienda, RUBIOS)
        catalogo.actualizar_producto(tienda, cajero, rubios.id, RUBIOS, "Rubios 20", 5500, None)
        assert catalogo.consultar_por_codigo(tienda, RUBIOS).es_cigarro

    def test_se_marca_y_se_desmarca(self, tienda, cajero) -> None:
        leche = catalogo.consultar_por_codigo(tienda, LECHE)
        catalogo.actualizar_producto(tienda, cajero, leche.id, LECHE, "Leche 1 L", 1290, None, es_cigarro=True)
        assert catalogo.consultar_por_codigo(tienda, LECHE).es_cigarro
        catalogo.actualizar_producto(tienda, cajero, leche.id, LECHE, "Leche 1 L", 1290, None, es_cigarro=False)
        assert not catalogo.consultar_por_codigo(tienda, LECHE).es_cigarro

    def test_pasar_un_cigarro_a_peso_se_rechaza(self, tienda, cajero) -> None:
        rubios = catalogo.consultar_por_codigo(tienda, RUBIOS)
        with pytest.raises(DatosInvalidos):
            catalogo.actualizar_producto(tienda, cajero, rubios.id, RUBIOS, "Rubios", 5200, None, por_peso=True)


# --------------------------------------------------------------------------- el carrito


class TestCarrito:
    def test_cuenta_cajetillas_y_no_otros_productos(self, tienda) -> None:
        carrito = _carrito(tienda, (RUBIOS, 2), (MENTA, 1), (LECHE, 3), recargo=500)
        assert carrito.cajetillas == 3

    @pytest.mark.parametrize(
        "medio, recargo", [(MedioPago.EFECTIVO, 0), (MedioPago.DEBITO, 1500), (MedioPago.CREDITO, 1500), (None, 0)]
    )
    def test_solo_con_tarjeta(self, tienda, medio, recargo) -> None:
        carrito = _carrito(tienda, (RUBIOS, 2), (MENTA, 1), recargo=500)
        assert carrito.recargo_clp(medio) == recargo
        assert carrito.total_con(medio) == carrito.total_clp + recargo

    def test_sin_saber_el_recargo_no_lo_inventa(self, tienda) -> None:
        assert _carrito(tienda, (RUBIOS, 2)).recargo_clp(MedioPago.DEBITO) == 0

    def test_los_descuentos_no_tocan_el_recargo(self, tienda) -> None:
        carrito = _carrito(tienda, (RUBIOS, 2), recargo=500)
        carrito.aplicar_descuento_porcentaje(10)
        assert carrito.recargo_clp(MedioPago.DEBITO) == 1000
        assert carrito.total_con(MedioPago.DEBITO) == 10_400 - 1040 + 1000

    def test_viaja_por_la_red_con_el_carrito(self, tienda) -> None:
        carrito = _carrito(tienda, (RUBIOS, 2), (LECHE, 1), recargo=700)
        copia = Carrito.desde_dict(carrito.a_dict())
        assert copia.cajetillas == 2 and copia.recargo_unitario_clp == 700


# --------------------------------------------------------------------------- el cobro


class TestCobro:
    def _cobrar(self, conexion, carrito, medio, **k):
        return servicio_venta.cerrar_venta(conexion, carrito, caja="Caja 1", medio_pago=medio, **k)

    def test_con_debito_suma_500_por_cajetilla(self, tienda) -> None:
        carrito = _carrito(tienda, (RUBIOS, 2), (LECHE, 1), recargo=500)
        venta = self._cobrar(tienda, carrito, MedioPago.DEBITO)
        assert venta.recargo_clp == 1000
        assert venta.total_clp == 2 * 5200 + 1290 + 1000
        guardada = repo_ventas.obtener(tienda, venta.id)
        assert (guardada.recargo_clp, guardada.total_clp) == (1000, venta.total_clp)

    def test_en_efectivo_no_hay_recargo(self, tienda) -> None:
        venta = self._cobrar(tienda, _carrito(tienda, (RUBIOS, 2), recargo=500), MedioPago.EFECTIVO)
        assert (venta.recargo_clp, venta.total_clp) == (0, 10_400)

    def test_sin_cigarros_no_hay_recargo(self, tienda) -> None:
        venta = self._cobrar(tienda, _carrito(tienda, (LECHE, 2), recargo=500), MedioPago.CREDITO)
        assert venta.recargo_clp == 0

    def test_el_servidor_usa_el_vigente_si_la_caja_no_lo_sabe(self, tienda, admin) -> None:
        catalogo.fijar_recargo_cigarro(tienda, admin, 600)
        venta = self._cobrar(tienda, _carrito(tienda, (RUBIOS, 1)), MedioPago.DEBITO)
        assert venta.recargo_clp == 600

    def test_si_cambio_mientras_tanto_no_cobra(self, tienda, admin) -> None:
        # La caja mostró $500 por cajetilla; el dueño lo subió a $700 desde la otra caja.
        carrito = _carrito(tienda, (RUBIOS, 2), recargo=500)
        catalogo.fijar_recargo_cigarro(tienda, admin, 700)
        with pytest.raises(DatosInvalidos, match=r"cambió a \$700"):
            self._cobrar(tienda, carrito, MedioPago.DEBITO)
        assert repo_ventas.del_dia(tienda) == []
        assert catalogo.consultar_por_codigo(tienda, RUBIOS).stock == 40

    def test_en_efectivo_da_igual_que_haya_cambiado(self, tienda, admin) -> None:
        carrito = _carrito(tienda, (RUBIOS, 2), recargo=500)
        catalogo.fijar_recargo_cigarro(tienda, admin, 700)
        assert self._cobrar(tienda, carrito, MedioPago.EFECTIVO).recargo_clp == 0

    def test_si_lo_desmarcaron_mientras_tanto_no_cobra(self, tienda, cajero) -> None:
        carrito = _carrito(tienda, (RUBIOS, 1), recargo=500)
        rubios = catalogo.consultar_por_codigo(tienda, RUBIOS)
        catalogo.actualizar_producto(tienda, cajero, rubios.id, RUBIOS, "Rubios 20", 5200, None, es_cigarro=False)
        with pytest.raises(DatosInvalidos, match="Quítelo del carrito"):
            self._cobrar(tienda, carrito, MedioPago.EFECTIVO)

    def test_el_cierre_lo_cuenta_en_la_tarjeta(self, tienda) -> None:
        from tienda_pos.services import reportes

        self._cobrar(tienda, _carrito(tienda, (RUBIOS, 1), recargo=500), MedioPago.DEBITO)
        self._cobrar(tienda, _carrito(tienda, (RUBIOS, 1), recargo=500), MedioPago.EFECTIVO)
        cierre = reportes.cierre_de_caja(tienda, None, "Caja 1")
        assert cierre.total_clp == 5700 + 5200
        assert sum(v.recargo_clp for v in cierre.ventas) == 500

    def test_el_arqueo_no_lo_ve(self, tienda, admin) -> None:
        # El recargo es de la tarjeta: al cajón no entra.
        from tienda_pos.services import arqueo

        self._cobrar(tienda, _carrito(tienda, (RUBIOS, 1), recargo=500), MedioPago.DEBITO)
        self._cobrar(tienda, _carrito(tienda, (LECHE, 1), recargo=500), MedioPago.EFECTIVO)
        turno = arqueo.turno_abierto(tienda, "Caja 1", admin)
        assert turno.ventas_efectivo_clp == 1290
        assert turno.esperado_clp == turno.apertura_clp + 1290


# --------------------------------------------------------------------------- la base de la tienda


class TestMigracion:
    def test_una_base_de_la_version_7_pasa_a_la_8_sin_tocar_lo_que_habia(self) -> None:
        from tienda_pos.db.migrations import _MIGRACIONES, VERSION_ESQUEMA, aplicar_migraciones

        antigua = sqlite3.connect(":memory:")
        antigua.row_factory = sqlite3.Row
        antigua.execute("PRAGMA foreign_keys = ON")
        for version in range(1, 8):
            _MIGRACIONES[version](antigua)
        antigua.execute("PRAGMA user_version = 7")
        antigua.execute(
            "INSERT INTO producto (codigo_barras, nombre, precio_clp, stock) VALUES ('7801', 'Rubios', 5200, 3)"
        )
        antigua.execute(
            "INSERT INTO venta (folio, fecha_hora, subtotal_clp, descuento_clp, total_clp) "
            "VALUES (1, '2026-10-09 10:00:00', 5200, 0, 5200)"
        )
        antigua.commit()

        assert aplicar_migraciones(antigua) == VERSION_ESQUEMA == 8
        producto = repo_productos.obtener_por_codigo(antigua, "7801")
        assert (producto.es_cigarro, producto.stock, producto.precio_clp) == (False, 3, 5200)
        (venta,) = antigua.execute("SELECT * FROM venta").fetchall()
        assert (venta["recargo_clp"], venta["total_clp"]) == (0, 5200)


# --------------------------------------------------------------------------- dos cajas


def _puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestPorLaRed:
    @pytest.fixture
    def red(self):
        from tienda_pos.red.cliente import SesionRemota
        from tienda_pos.red.servidor import ServidorTienda
        from tienda_pos.red.sesion import SesionLocal

        conexion = abrir_base_datos(":memory:", con_datos_demo=False, compartida_entre_hilos=True)
        with transaccion(conexion):
            admin = auth.crear_usuario(conexion, "Dueño", Rol.ADMIN, "907315")
            cajera = auth.crear_usuario(conexion, "Marta", Rol.CAJERO, "481526")
        abrir_cajas(conexion, admin, "Caja 1", "Caja 2")
        local = SesionLocal(conexion, caja="Caja 1")
        puerto = _puerto_libre()
        with ServidorTienda(local, host="127.0.0.1", puerto=puerto):
            yield SesionRemota("127.0.0.1", puerto, caja="Caja 2"), local, admin, cajera
        conexion.close()

    def test_la_secundaria_crea_un_cigarro_y_cobra_con_recargo(self, red) -> None:
        remota, local, _, cajera = red
        rubios = remota.crear_producto(cajera, RUBIOS, "Rubios 20", 5200, 10, es_cigarro=True)
        assert rubios.es_cigarro and local.consultar_por_codigo(RUBIOS).es_cigarro

        carrito = Carrito()
        carrito.agregar(remota.consultar_por_codigo(RUBIOS), 3)
        carrito.recargo_unitario_clp = remota.recargo_cigarro()
        venta = remota.cerrar_venta(carrito, cajera, "r1", medio_pago=MedioPago.CREDITO)
        assert (venta.recargo_clp, venta.total_clp, venta.caja) == (1500, 3 * 5200 + 1500, "Caja 2")

    def test_el_recargo_se_cambia_desde_la_secundaria_y_vale_en_las_dos(self, red) -> None:
        remota, local, admin, cajera = red
        with pytest.raises(PermisoDenegado):
            remota.fijar_recargo_cigarro(cajera, 900)
        remota.fijar_recargo_cigarro(admin, 900)
        assert local.recargo_cigarro() == remota.recargo_cigarro() == 900

    def test_el_aviso_de_recargo_cambiado_cruza_la_red(self, red) -> None:
        remota, local, admin, cajera = red
        remota.crear_producto(cajera, RUBIOS, "Rubios 20", 5200, 10, es_cigarro=True)
        carrito = Carrito()
        carrito.agregar(remota.consultar_por_codigo(RUBIOS), 1)
        carrito.recargo_unitario_clp = 500
        local.fijar_recargo_cigarro(admin, 800)
        with pytest.raises(DatosInvalidos, match=r"\$800"):
            remota.cerrar_venta(carrito, cajera, "r2", medio_pago=MedioPago.DEBITO)

    def test_editar_desde_una_caja_vieja_no_borra_la_marca(self, red) -> None:
        # Una petición sin `es_cigarro` —como la de una caja que no sabe de cigarros— lo deja.
        remota, local, _, cajera = red
        rubios = remota.crear_producto(cajera, RUBIOS, "Rubios 20", 5200, 10, es_cigarro=True)
        remota.actualizar_producto(cajera, rubios.id, RUBIOS, "Rubios 20", 5300, None)
        assert local.consultar_por_codigo(RUBIOS).es_cigarro


# --------------------------------------------------------------------------- pantallas

pytest.importorskip("PySide6", reason="La interfaz requiere PySide6")


def _cigarro_demo() -> Producto:
    from tienda_pos.db.seed import catalogo_demo

    return next(p for p in catalogo_demo() if p.es_cigarro)


class TestPantallaDeVenta:
    def test_el_total_sube_al_marcar_tarjeta_y_dice_por_que(self, ventana) -> None:
        vista = ventana.vista_venta
        cigarro = _cigarro_demo()
        vista.agregar_por_codigo(cigarro.codigo_barras)
        vista.aumentar_cantidad(cigarro.codigo_barras)
        assert vista.valor_total.text() == "$10.400" and vista.fila_recargo.isHidden()

        vista.elegir_medio_pago(MedioPago.DEBITO)
        assert vista.valor_total.text() == "$11.400"
        assert not vista.fila_recargo.isHidden()
        assert vista.valor_recargo.text() == "+$1.000"
        assert "2 × $500" in vista.etiqueta_recargo.text()

        vista.elegir_medio_pago(MedioPago.EFECTIVO)
        assert vista.valor_total.text() == "$10.400" and vista.fila_recargo.isHidden()

    def test_cobrar_con_tarjeta_guarda_el_recargo_sin_avisos_raros(self, ventana, conexion, monkeypatch) -> None:
        # El aviso de "venta registrada en el intento anterior" compara totales: con el recargo
        # tiene que reconocer la venta como la de la pantalla.
        errores = []
        monkeypatch.setattr(dialogos_mod(), "mostrar_error", lambda *a, **k: errores.append(a))
        vista = ventana.vista_venta
        vista.agregar_por_codigo(_cigarro_demo().codigo_barras)
        vista.elegir_medio_pago(MedioPago.CREDITO)
        vista.cobrar()
        (venta,) = repo_ventas.del_dia(conexion)
        assert (venta.recargo_clp, venta.total_clp) == (500, 5700)
        assert errores == []

    def test_si_el_recargo_cambio_no_cobra_y_muestra_el_total_nuevo(self, ventana, conexion, monkeypatch) -> None:
        errores = []
        monkeypatch.setattr(dialogos_mod(), "mostrar_error", lambda _p, texto, *a, **k: errores.append(texto))
        vista = ventana.vista_venta
        vista.agregar_por_codigo(_cigarro_demo().codigo_barras)
        vista.elegir_medio_pago(MedioPago.DEBITO)
        assert vista.valor_total.text() == "$5.700"
        catalogo.fijar_recargo_cigarro(conexion, auth.autenticar(conexion, "Administrador", "1234"), 800)
        vista.cobrar()
        assert repo_ventas.del_dia(conexion) == []
        assert "$800" in errores[0]
        assert vista.valor_total.text() == "$6.000"
        vista.cobrar()
        assert repo_ventas.del_dia(conexion)[0].total_clp == 6000

    def test_la_confirmacion_dice_el_recargo(self, ventana, monkeypatch) -> None:
        from tienda_pos.services.preferencias import Preferencias

        textos = []
        monkeypatch.setattr(dialogos_mod(), "confirmar", lambda _p, _t, texto, **k: textos.append(texto) or True)
        vista = ventana.vista_venta
        vista.preferencias = Preferencias(confirmar_cobro=True)
        vista.agregar_por_codigo(_cigarro_demo().codigo_barras)
        vista.elegir_medio_pago(MedioPago.DEBITO)
        vista.cobrar()
        assert "Total a cobrar: $5.700" in textos[0] and "recargo de cigarros: $500" in textos[0]


def dialogos_mod():
    from tienda_pos.ui import dialogos

    return dialogos


class TestPantallaDeProductos:
    def test_la_casilla_se_apaga_con_peso(self, ventana) -> None:
        from tienda_pos.ui.productos_view import DialogoProducto

        dialogo = DialogoProducto(ventana)
        dialogo.casilla_cigarro.setChecked(True)
        dialogo.casilla_peso.setChecked(True)
        assert not dialogo.casilla_cigarro.isChecked() and not dialogo.casilla_cigarro.isEnabled()
        dialogo.casilla_peso.setChecked(False)
        assert dialogo.casilla_cigarro.isEnabled()
        dialogo.deleteLater()

    def test_al_editar_trae_la_marca(self, ventana) -> None:
        from tienda_pos.ui.productos_view import DialogoProducto

        dialogo = DialogoProducto(ventana, _cigarro_demo())
        assert dialogo.es_cigarro
        dialogo.deleteLater()

    def test_filtrar_cigarro_los_muestra_y_la_lista_los_marca(self, ventana) -> None:
        ventana.mostrar_productos()
        vista = ventana.vista_productos
        vista.campo_filtro.setText("cigarro")
        nombres = [vista.tabla.item(f, 1).text() for f in range(vista.tabla.rowCount())]
        assert nombres and all(n.endswith("· cigarro") for n in nombres)

    def test_la_barra_dice_el_recargo(self, ventana) -> None:
        ventana.mostrar_productos()
        assert "$500 más por cajetilla" in ventana.vista_productos.etiqueta_recargo.text()

    def test_cambiarlo_pide_el_pin_y_si_no_lo_ponen_no_cambia(self, ventana, conexion, monkeypatch) -> None:
        from tienda_pos.ui import main_window

        monkeypatch.setattr(main_window.DialogoLogin, "pedir", staticmethod(lambda *a, **k: None))
        ventana.mostrar_productos()
        ventana.vista_productos.cambiar_recargo()
        assert catalogo.recargo_cigarro(conexion) == 500

    def test_con_el_pin_cambia_y_la_venta_se_entera(self, como_admin, conexion, monkeypatch) -> None:
        from tienda_pos.ui import efectivo_view

        monkeypatch.setattr(efectivo_view.DialogoMonto, "pedir", classmethod(lambda cls, *a, **k: (700, "")))
        como_admin.mostrar_productos()
        como_admin.vista_productos.cambiar_recargo()
        assert catalogo.recargo_cigarro(conexion) == 700
        assert "$700" in como_admin.vista_productos.etiqueta_recargo.text()

        como_admin.mostrar_venta()
        vista = como_admin.vista_venta
        vista.agregar_por_codigo(_cigarro_demo().codigo_barras)
        vista.elegir_medio_pago(MedioPago.DEBITO)
        assert vista.valor_recargo.text() == "+$700"
