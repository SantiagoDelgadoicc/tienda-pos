"""Pruebas de la venta por peso (D-037), sin interfaz.

El cliente vende pan, pollo y jamón: fija el precio del kilo y en la caja se teclean los gramos.
Lo que más se cuida es no romper nada de lo que ya se vendía por unidad, que el precio sea exacto
al peso, que el stock de un producto por peso nunca impida vender, y que por la red las dos
cajas cobren lo mismo.
"""

from __future__ import annotations

import socket
import sqlite3

import pytest

from tienda_pos import config
from tienda_pos.db import migrations
from tienda_pos.db.connection import transaccion
from tienda_pos.db.inicio import abrir_base_datos
from tienda_pos.db.migrations import VERSION_ESQUEMA, aplicar_migraciones
from tienda_pos.domain.errors import DatosInvalidos, StockInsuficiente
from tienda_pos.domain.models import MedioPago, Producto, Rol
from tienda_pos.red.sesion import SesionLocal
from tienda_pos.repositories import productos as repo_productos
from tienda_pos.repositories import ventas as repo_ventas
from tienda_pos.services import auth, catalogo, reportes
from tienda_pos.services import venta as servicio_venta
from tienda_pos.utils.money import formatear_peso, precio_por_gramos

CAJA = "Caja 1"


@pytest.fixture
def jamon(conexion) -> Producto:
    producto = Producto(
        codigo_barras="2000010", nombre="Jamón pierna", precio_clp=7990, stock=2000, por_peso=True
    )
    with transaccion(conexion):
        repo_productos.crear(conexion, producto)
    return producto


@pytest.fixture
def leche(conexion) -> Producto:
    producto = Producto(codigo_barras="7801234000019", nombre="Leche 1 L", precio_clp=1290, stock=10)
    with transaccion(conexion):
        repo_productos.crear(conexion, producto)
    return producto


def _cobrar(conexion, carrito):
    return servicio_venta.cerrar_venta(
        conexion, carrito, caja=CAJA, medio_pago=MedioPago.EFECTIVO
    )


class TestPrecio:
    @pytest.mark.parametrize(
        ("kilo", "gramos", "precio"),
        [
            (7990, 1000, 7990),
            (7990, 500, 3995),
            (7990, 350, 2797),  # 2.796,5 se redondea hacia arriba
            (7990, 1, 8),  # 7,99
            (2490, 250, 623),  # 622,5
            (1000, 1234, 1234),
            (0, 800, 0),
        ],
    )
    def test_al_peso_mas_cercano(self, kilo, gramos, precio) -> None:
        assert precio_por_gramos(kilo, gramos) == precio

    @pytest.mark.parametrize(
        ("gramos", "texto"),
        [(350, "350 g"), (999, "999 g"), (1000, "1 kg"), (1250, "1,25 kg"), (2005, "2,005 kg")],
    )
    def test_el_peso_se_lee_como_en_la_caja(self, gramos, texto) -> None:
        assert formatear_peso(gramos) == texto


class TestCarrito:
    def test_la_linea_cobra_el_peso_y_cuenta_un_articulo(self, jamon) -> None:
        carrito = servicio_venta.Carrito()
        linea = carrito.agregar(jamon, gramos=350)
        assert linea.por_peso and linea.gramos == 350 and linea.cantidad == 1
        assert carrito.total_clp == 2797
        assert carrito.cantidad_articulos == 1

    def test_pesar_dos_veces_suma_los_gramos(self, jamon) -> None:
        carrito = servicio_venta.Carrito()
        carrito.agregar(jamon, gramos=300)
        carrito.agregar(jamon, gramos=200)
        assert len(carrito.lineas) == 1
        assert carrito.lineas[0].gramos == 500 and carrito.total_clp == 3995

    def test_se_mezcla_con_productos_por_unidad(self, jamon, leche) -> None:
        carrito = servicio_venta.Carrito()
        carrito.agregar(leche, 2)
        carrito.agregar(jamon, gramos=250)
        assert carrito.total_clp == 2 * 1290 + 1998  # 1.997,5

    def test_un_producto_por_peso_exige_los_gramos(self, jamon) -> None:
        with pytest.raises(DatosInvalidos, match="por peso"):
            servicio_venta.Carrito().agregar(jamon)

    def test_uno_por_unidad_no_acepta_gramos(self, leche) -> None:
        with pytest.raises(DatosInvalidos, match="por unidad"):
            servicio_venta.Carrito().agregar(leche, gramos=300)

    @pytest.mark.parametrize("gramos", [0, -5, config.GRAMOS_MAX_POR_LINEA + 1, 2.5, True])
    def test_rechaza_pesos_imposibles(self, jamon, gramos) -> None:
        with pytest.raises(DatosInvalidos):
            servicio_venta.Carrito().agregar(jamon, gramos=gramos)

    def test_sumar_pesos_tampoco_pasa_del_tope(self, jamon) -> None:
        carrito = servicio_venta.Carrito()
        carrito.agregar(jamon, gramos=config.GRAMOS_MAX_POR_LINEA)
        with pytest.raises(DatosInvalidos):
            carrito.agregar(jamon, gramos=1)
        assert carrito.lineas[0].gramos == config.GRAMOS_MAX_POR_LINEA

    def test_cambiar_el_peso(self, jamon) -> None:
        carrito = servicio_venta.Carrito()
        carrito.agregar(jamon, gramos=350)
        carrito.cambiar_gramos(jamon.codigo_barras, 1000)
        assert carrito.total_clp == 7990
        carrito.cambiar_gramos(jamon.codigo_barras, 0)
        assert carrito.esta_vacio

    def test_la_cantidad_de_una_linea_por_peso_solo_se_puede_quitar(self, jamon) -> None:
        carrito = servicio_venta.Carrito()
        carrito.agregar(jamon, gramos=350)
        with pytest.raises(DatosInvalidos, match="cambie el peso"):
            carrito.cambiar_cantidad(jamon.codigo_barras, 2)
        carrito.cambiar_cantidad(jamon.codigo_barras, 0)
        assert carrito.esta_vacio

    def test_cambiar_gramos_a_uno_por_unidad_se_niega(self, leche) -> None:
        carrito = servicio_venta.Carrito()
        carrito.agregar(leche)
        with pytest.raises(DatosInvalidos):
            carrito.cambiar_gramos(leche.codigo_barras, 300)

    def test_descuentos_sobre_una_linea_por_peso(self, jamon) -> None:
        carrito = servicio_venta.Carrito()
        carrito.agregar(jamon, gramos=1000)
        carrito.aplicar_descuento_linea_porcentaje(jamon.codigo_barras, 10)
        assert carrito.total_clp == 7191
        carrito.cambiar_gramos(jamon.codigo_barras, 500)  # el 10 % sigue siendo el 10 %
        assert carrito.total_clp == 3995 - 400

    def test_viaja_por_la_red_con_sus_gramos(self, jamon, leche) -> None:
        carrito = servicio_venta.Carrito()
        carrito.agregar(jamon, gramos=350)
        carrito.agregar(leche)
        copia = servicio_venta.Carrito.desde_dict(carrito.a_dict())
        assert copia.total_clp == carrito.total_clp
        assert {linea.nombre: linea.gramos for linea in copia.lineas} == {
            "Jamón pierna": 350,
            "Leche 1 L": None,
        }


class TestCobro:
    @pytest.fixture(autouse=True)
    def _caja_abierta(self, conexion):
        from tienda_pos.services import arqueo

        with transaccion(conexion):
            jefe = auth.crear_usuario(conexion, "Jefe", Rol.ADMIN, "8342")
        arqueo.abrir_turno(conexion, CAJA, jefe, 0)

    def test_la_venta_guarda_los_gramos_y_el_precio_del_kilo(self, conexion, jamon) -> None:
        carrito = servicio_venta.Carrito()
        carrito.agregar(jamon, gramos=350)
        venta = _cobrar(conexion, carrito)
        linea = repo_ventas.lineas_de(conexion, venta.id)[0]
        assert (linea.gramos, linea.precio_unit_clp, linea.cantidad, linea.subtotal_clp) == (
            350,
            7990,
            1,
            2797,
        )
        assert venta.total_clp == 2797

    def test_el_stock_baja_en_gramos(self, conexion, jamon) -> None:
        carrito = servicio_venta.Carrito()
        carrito.agregar(jamon, gramos=350)
        _cobrar(conexion, carrito)
        assert repo_productos.obtener_por_id(conexion, jamon.id).stock == 2000 - 350

    def test_el_stock_no_impide_vender_ni_queda_negativo(self, conexion, jamon) -> None:
        # Nadie pesa el pan al recibirlo: un stock en cero no puede frenar la caja.
        carrito = servicio_venta.Carrito()
        carrito.agregar(jamon, gramos=5000)
        _cobrar(conexion, carrito)
        assert repo_productos.obtener_por_id(conexion, jamon.id).stock == 0

    def test_con_stock_estricto_los_de_unidad_lo_exigen(self, conexion, leche, monkeypatch) -> None:
        monkeypatch.setattr(config, "PERMITIR_STOCK_NEGATIVO", False)
        carrito = servicio_venta.Carrito()
        carrito.agregar(leche, 11)
        with pytest.raises(StockInsuficiente):
            _cobrar(conexion, carrito)

    def test_si_el_producto_cambio_a_peso_se_avisa(self, conexion, leche, jamon) -> None:
        # La otra caja armó el carrito con la leche por unidad y el dueño la pasó a peso.
        carrito = servicio_venta.Carrito()
        carrito.agregar(leche)
        with transaccion(conexion):
            leche.por_peso = True
            repo_productos.actualizar(conexion, leche)
        with pytest.raises(DatosInvalidos, match="cambió"):
            _cobrar(conexion, carrito)

    def test_los_informes_cuentan_la_linea_por_peso_como_un_articulo(
        self, conexion, jamon, leche
    ) -> None:
        carrito = servicio_venta.Carrito()
        carrito.agregar(jamon, gramos=750)
        carrito.agregar(leche, 2)
        _cobrar(conexion, carrito)
        resumen = reportes.resumen_del_dia(conexion)
        assert resumen["articulos"] == 3
        assert resumen["total_clp"] == 5993 + 2580
        cierre = reportes.cierre_de_caja(conexion, None, CAJA)
        assert cierre.articulos == 3 and cierre.total_clp == 5993 + 2580
        assert [linea.gramos for linea in cierre.ventas[0].lineas] == [750, None]


class TestMigracion:
    def test_una_base_de_la_version_6_pasa_a_7_sin_tocar_lo_anterior(self, tmp_path) -> None:
        antigua = sqlite3.connect(tmp_path / "v6.db")
        antigua.row_factory = sqlite3.Row
        for version in range(1, 7):
            migrations._MIGRACIONES[version](antigua)
        antigua.execute("PRAGMA user_version = 6")
        antigua.execute(
            "INSERT INTO producto (codigo_barras, nombre, precio_clp, stock) "
            "VALUES ('7801', 'Bebida', 1990, 12)"
        )
        antigua.execute(
            "INSERT INTO venta (folio, fecha_hora, subtotal_clp, descuento_clp, total_clp) "
            "VALUES (1, '2026-09-20 10:00:00', 1990, 0, 1990)"
        )
        antigua.execute(
            "INSERT INTO venta_linea (venta_id, producto_id, codigo_barras, nombre, "
            "precio_unit_clp, cantidad, subtotal_clp) VALUES (1, 1, '7801', 'Bebida', 1990, 1, 1990)"
        )
        antigua.commit()

        assert aplicar_migraciones(antigua) == VERSION_ESQUEMA
        producto = repo_productos.obtener_por_codigo(antigua, "7801")
        assert producto.por_peso is False and producto.stock == 12
        linea = repo_ventas.lineas_de(antigua, 1)[0]
        assert linea.gramos is None and linea.subtotal_clp == 1990
        assert antigua.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def _puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestPorLaRed:
    @pytest.fixture
    def red(self):
        """Un servidor de verdad y la caja secundaria conectada a él."""
        from tienda_pos.red.cliente import SesionRemota
        from tienda_pos.red.servidor import ServidorTienda
        from tienda_pos.services import arqueo

        conexion = abrir_base_datos(":memory:", con_datos_demo=False, compartida_entre_hilos=True)
        with transaccion(conexion):
            jefe = auth.crear_usuario(conexion, "Jefe", Rol.ADMIN, "8342")
        arqueo.abrir_turno(conexion, "Secundaria", jefe, 0)
        principal = SesionLocal(conexion, caja="Principal")
        puerto = _puerto_libre()
        with ServidorTienda(principal, host="127.0.0.1", puerto=puerto):
            yield SesionRemota("127.0.0.1", puerto, caja="Secundaria"), conexion, jefe
        conexion.close()

    def test_la_secundaria_crea_pesa_y_cobra(self, red) -> None:
        secundaria, conexion, jefe = red
        pan = secundaria.crear_producto(jefe, "", "Pan batido", 2490, 0, por_peso=True)
        assert pan.por_peso and pan.codigo_barras == "2000001"

        encontrado = secundaria.buscar_por_nombre("batido")[0]
        assert encontrado.por_peso
        carrito = servicio_venta.Carrito()
        carrito.agregar(encontrado, gramos=750)
        venta = secundaria.cerrar_venta(carrito, jefe, "p1")

        assert venta.total_clp == 1868  # 1.867,5
        guardada = repo_ventas.lineas_de(conexion, venta.id)[0]
        assert guardada.gramos == 750 and guardada.subtotal_clp == 1868

    def test_la_secundaria_cambia_un_producto_a_peso(self, red) -> None:
        secundaria, conexion, jefe = red
        pollo = secundaria.crear_producto(jefe, "7801234999999", "Pollo entero", 3990, 0)
        assert not pollo.por_peso
        secundaria.actualizar_producto(
            jefe, pollo.id, pollo.codigo_barras, pollo.nombre, 3990, 0, por_peso=True
        )
        assert catalogo.consultar_por_codigo(conexion, "7801234999999").por_peso
