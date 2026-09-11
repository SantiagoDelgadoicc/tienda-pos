"""Pruebas del carrito y del cierre de venta."""

from __future__ import annotations

import sqlite3
from datetime import date

import pytest

from tienda_pos.domain.errors import (
    CarritoVacio,
    DatosInvalidos,
    DescuentoInvalido,
    StockInsuficiente,
)
from tienda_pos.repositories import productos as repo_productos
from tienda_pos.repositories import ventas as repo_ventas
from tienda_pos.services import venta as servicio_venta
from tienda_pos.services.venta import Carrito


class TestCarrito:
    def test_empieza_vacio(self) -> None:
        carrito = Carrito()
        assert carrito.esta_vacio
        assert carrito.total_clp == 0

    def test_agrega_un_producto(self, productos) -> None:
        carrito = Carrito()
        carrito.agregar(productos["leche"])
        assert carrito.cantidad_articulos == 1
        assert carrito.total_clp == 1290

    def test_escanear_dos_veces_agrupa_en_una_linea(self, productos) -> None:
        carrito = Carrito()
        carrito.agregar(productos["leche"])
        carrito.agregar(productos["leche"])
        assert len(carrito.lineas) == 1
        assert carrito.lineas[0].cantidad == 2
        assert carrito.total_clp == 2580

    def test_suma_productos_distintos(self, productos) -> None:
        carrito = Carrito()
        carrito.agregar(productos["leche"])
        carrito.agregar(productos["pan"])
        assert len(carrito.lineas) == 2
        assert carrito.total_clp == 1290 + 2190

    def test_cambiar_cantidad_a_cero_elimina_la_linea(self, productos) -> None:
        carrito = Carrito()
        carrito.agregar(productos["leche"], 3)
        carrito.cambiar_cantidad("7801234000019", 0)
        assert carrito.esta_vacio

    def test_quitar_una_linea(self, productos) -> None:
        carrito = Carrito()
        carrito.agregar(productos["leche"])
        carrito.agregar(productos["pan"])
        carrito.quitar("7801234000019")
        assert len(carrito.lineas) == 1

    def test_quitar_algo_que_no_esta_avisa(self, productos) -> None:
        carrito = Carrito()
        with pytest.raises(DatosInvalidos):
            carrito.quitar("7801234000019")

    def test_rechaza_cantidades_no_positivas(self, productos) -> None:
        carrito = Carrito()
        with pytest.raises(DatosInvalidos):
            carrito.agregar(productos["leche"], 0)
        with pytest.raises(DatosInvalidos):
            carrito.agregar(productos["leche"], -2)

    def test_tope_de_unidades_por_linea(self, productos) -> None:
        # Protege del caso real de que la pistola se quede leyendo el mismo código.
        carrito = Carrito()
        carrito.agregar(productos["leche"], servicio_venta.CANTIDAD_MAX_POR_LINEA)
        with pytest.raises(DatosInvalidos):
            carrito.agregar(productos["leche"])

    def test_vaciar_deja_el_carrito_como_nuevo(self, productos) -> None:
        carrito = Carrito()
        carrito.agregar(productos["leche"], 2)
        carrito.aplicar_descuento_monto(500)
        carrito.vaciar()
        assert carrito.esta_vacio
        assert carrito.descuento_clp == 0


class TestDescuentos:
    def test_descuento_por_monto(self, productos) -> None:
        carrito = Carrito()
        carrito.agregar(productos["leche"], 2)  # 2580
        carrito.aplicar_descuento_monto(580)
        assert carrito.total_clp == 2000

    def test_descuento_por_porcentaje(self, productos) -> None:
        carrito = Carrito()
        carrito.agregar(productos["leche"], 2)  # 2580
        carrito.aplicar_descuento_porcentaje(10)
        assert carrito.descuento_clp == 258
        assert carrito.total_clp == 2322

    def test_el_porcentaje_se_recalcula_al_cambiar_el_carrito(self, productos) -> None:
        # Si se pactó un 10%, debe seguir siendo un 10% aunque se añadan productos.
        carrito = Carrito()
        carrito.agregar(productos["leche"])  # 1290
        carrito.aplicar_descuento_porcentaje(10)
        assert carrito.descuento_clp == 129
        carrito.agregar(productos["leche"])  # 2580
        assert carrito.descuento_clp == 258

    def test_no_se_admite_descuento_negativo(self, productos) -> None:
        carrito = Carrito()
        carrito.agregar(productos["leche"])
        with pytest.raises(DescuentoInvalido):
            carrito.aplicar_descuento_monto(-100)

    def test_no_se_admite_descuento_mayor_que_el_total(self, productos) -> None:
        carrito = Carrito()
        carrito.agregar(productos["leche"])  # 1290
        with pytest.raises(DescuentoInvalido):
            carrito.aplicar_descuento_monto(2000)

    @pytest.mark.parametrize("porcentaje", [-1, 101])
    def test_porcentaje_fuera_de_rango(self, productos, porcentaje) -> None:
        carrito = Carrito()
        carrito.agregar(productos["leche"])
        with pytest.raises(DescuentoInvalido):
            carrito.aplicar_descuento_porcentaje(porcentaje)

    def test_el_total_nunca_queda_negativo(self, productos) -> None:
        # Se descuenta 2.000 sobre 2.580 y luego se quita una unidad: el total baja a 1.290,
        # menor que el descuento. Debe quedar en 0, jamás en un número negativo.
        carrito = Carrito()
        carrito.agregar(productos["leche"], 2)
        carrito.aplicar_descuento_monto(2000)
        carrito.cambiar_cantidad("7801234000019", 1)
        assert carrito.total_clp == 0
        assert carrito.descuento_clp == 1290


class TestDescuentosPorProducto:
    """El descuento que se aplica a una línea y no a la venta entera."""

    LECHE = "7801234000019"
    PAN = "7801234000026"

    def test_descuento_por_monto_en_una_linea(self, productos) -> None:
        carrito = Carrito()
        carrito.agregar(productos["leche"], 2)  # 2580
        carrito.agregar(productos["pan"])  # 2190
        carrito.aplicar_descuento_linea_monto(self.LECHE, 580)

        assert carrito.subtotal_clp == 4770
        assert carrito.descuento_clp == 580
        assert carrito.total_clp == 4190

    def test_descuento_por_porcentaje_en_una_linea(self, productos) -> None:
        carrito = Carrito()
        carrito.agregar(productos["leche"], 2)  # 2580
        carrito.aplicar_descuento_linea_porcentaje(self.LECHE, 10)

        assert carrito.lineas[0].descuento_clp == 258
        assert carrito.lineas[0].total_clp == 2322
        assert carrito.total_clp == 2322

    def test_el_porcentaje_de_la_linea_sigue_a_la_cantidad(self, productos) -> None:
        carrito = Carrito()
        carrito.agregar(productos["leche"])  # 1290
        carrito.aplicar_descuento_linea_porcentaje(self.LECHE, 50)
        assert carrito.descuento_clp == 645

        carrito.agregar(productos["leche"])  # 2580
        assert carrito.descuento_clp == 1290

    def test_los_dos_descuentos_conviven(self, productos) -> None:
        # 10% del pan (219) y luego 1.000 sobre el resto de la venta.
        carrito = Carrito()
        carrito.agregar(productos["leche"])  # 1290
        carrito.agregar(productos["pan"])  # 2190
        carrito.aplicar_descuento_linea_porcentaje(self.PAN, 10)
        carrito.aplicar_descuento_monto(1000)

        assert carrito.descuento_lineas_clp == 219
        assert carrito.descuento_venta_clp == 1000
        assert carrito.descuento_clp == 1219
        assert carrito.total_clp == 3480 - 1219

    def test_el_descuento_de_venta_no_puede_pasarse_de_la_base_ya_rebajada(
        self, productos
    ) -> None:
        # Regalado el producto entero, no queda nada sobre lo que seguir descontando.
        carrito = Carrito()
        carrito.agregar(productos["leche"])  # 1290
        carrito.aplicar_descuento_linea_porcentaje(self.LECHE, 100)
        with pytest.raises(DescuentoInvalido):
            carrito.aplicar_descuento_monto(100)
        assert carrito.total_clp == 0

    def test_el_descuento_de_linea_no_puede_superar_la_linea(self, productos) -> None:
        carrito = Carrito()
        carrito.agregar(productos["leche"])  # 1290
        with pytest.raises(DescuentoInvalido):
            carrito.aplicar_descuento_linea_monto(self.LECHE, 1500)

    @pytest.mark.parametrize("porcentaje", [-1, 101])
    def test_porcentaje_de_linea_fuera_de_rango(self, productos, porcentaje) -> None:
        carrito = Carrito()
        carrito.agregar(productos["leche"])
        with pytest.raises(DescuentoInvalido):
            carrito.aplicar_descuento_linea_porcentaje(self.LECHE, porcentaje)

    def test_no_se_descuenta_un_producto_que_no_esta_en_el_carrito(self, productos) -> None:
        carrito = Carrito()
        carrito.agregar(productos["leche"])
        with pytest.raises(DatosInvalidos):
            carrito.aplicar_descuento_linea_monto(self.PAN, 100)

    def test_quitar_la_linea_se_lleva_su_descuento(self, productos) -> None:
        carrito = Carrito()
        carrito.agregar(productos["leche"])
        carrito.agregar(productos["pan"])
        carrito.aplicar_descuento_linea_monto(self.LECHE, 500)
        carrito.quitar(self.LECHE)

        assert carrito.descuento_clp == 0
        assert carrito.total_clp == 2190

    def test_quitar_el_descuento_de_una_linea(self, productos) -> None:
        carrito = Carrito()
        carrito.agregar(productos["leche"])
        carrito.aplicar_descuento_linea_monto(self.LECHE, 500)
        carrito.quitar_descuento_linea(self.LECHE)
        assert carrito.total_clp == 1290

    def test_el_descuento_de_linea_baja_con_la_cantidad(self, productos) -> None:
        # Descuento fijo de 1.000 sobre dos leches; al quedar una, no puede superar su
        # propio importe.
        carrito = Carrito()
        carrito.agregar(productos["leche"], 2)  # 2580
        carrito.aplicar_descuento_linea_monto(self.LECHE, 1000)
        carrito.cambiar_cantidad(self.LECHE, 1)  # 1290
        assert carrito.descuento_clp == 1000
        assert carrito.total_clp == 290

    def test_la_venta_guarda_el_descuento_de_cada_linea(
        self, conexion, productos, cajero
    ) -> None:
        carrito = Carrito()
        carrito.agregar(productos["leche"], 2)  # 2580
        carrito.agregar(productos["pan"])  # 2190
        carrito.aplicar_descuento_linea_monto(self.LECHE, 580)

        venta = servicio_venta.cerrar_venta(conexion, carrito, cajero)
        guardada = repo_ventas.obtener(conexion, venta.id)

        por_codigo = {linea.codigo_barras: linea for linea in guardada.lineas}
        assert por_codigo[self.LECHE].descuento_clp == 580
        assert por_codigo[self.LECHE].subtotal_clp == 2580  # el bruto no se toca
        assert por_codigo[self.PAN].descuento_clp == 0
        assert guardada.descuento_clp == 580
        assert guardada.total_clp == 4190


class TestCierreDeVenta:
    def test_registra_la_venta_con_sus_lineas(self, conexion, productos, cajero) -> None:
        carrito = Carrito()
        carrito.agregar(productos["leche"], 2)
        carrito.agregar(productos["pan"])

        venta = servicio_venta.cerrar_venta(conexion, carrito, cajero)

        assert venta.id is not None
        assert venta.folio == 1
        assert venta.total_clp == 2580 + 2190
        guardada = repo_ventas.obtener(conexion, venta.id)
        assert len(guardada.lineas) == 2
        assert guardada.usuario_nombre == "Cajero"

    def test_descuenta_el_stock(self, conexion, productos, cajero) -> None:
        carrito = Carrito()
        carrito.agregar(productos["leche"], 3)
        servicio_venta.cerrar_venta(conexion, carrito, cajero)

        assert repo_productos.obtener_por_codigo(conexion, "7801234000019").stock == 7

    def test_los_folios_son_correlativos(self, conexion, productos, cajero) -> None:
        for esperado in (1, 2, 3):
            carrito = Carrito()
            carrito.agregar(productos["leche"])
            assert servicio_venta.cerrar_venta(conexion, carrito, cajero).folio == esperado

    def test_no_se_puede_cerrar_un_carrito_vacio(self, conexion, cajero) -> None:
        with pytest.raises(CarritoVacio):
            servicio_venta.cerrar_venta(conexion, Carrito(), cajero)

    def test_se_rechaza_si_no_alcanza_el_stock(self, conexion, productos, cajero) -> None:
        carrito = Carrito()
        carrito.agregar(productos["agua"], 5)  # solo hay 1

        with pytest.raises(StockInsuficiente) as error:
            servicio_venta.cerrar_venta(conexion, carrito, cajero)
        assert "Agua Mineral" in str(error.value)

    def test_un_rechazo_por_stock_no_deja_rastro(self, conexion, productos, cajero) -> None:
        carrito = Carrito()
        carrito.agregar(productos["leche"])
        carrito.agregar(productos["agua"], 5)

        with pytest.raises(StockInsuficiente):
            servicio_venta.cerrar_venta(conexion, carrito, cajero)

        # Ni venta registrada, ni stock tocado del producto que sí alcanzaba.
        assert conexion.execute("SELECT COUNT(*) FROM venta").fetchone()[0] == 0
        assert repo_productos.obtener_por_codigo(conexion, "7801234000019").stock == 10

    def test_un_fallo_a_mitad_del_cierre_revierte_todo(
        self, conexion, productos, cajero, monkeypatch
    ) -> None:
        """El caso que de verdad importa: la venta ya se insertó y algo falla después.

        Se simula un fallo al descontar el stock del segundo producto. Si la transacción
        funciona, no debe quedar ni la venta, ni sus líneas, ni el stock del primero.
        """
        carrito = Carrito()
        carrito.agregar(productos["leche"], 2)
        carrito.agregar(productos["pan"])

        original = servicio_venta.repo_productos.descontar_stock
        llamadas = {"n": 0}

        def descontar_con_fallo(conexion_, producto_id, cantidad):
            llamadas["n"] += 1
            if llamadas["n"] == 2:
                raise sqlite3.OperationalError("fallo de disco simulado")
            return original(conexion_, producto_id, cantidad)

        monkeypatch.setattr(servicio_venta.repo_productos, "descontar_stock", descontar_con_fallo)

        with pytest.raises(sqlite3.OperationalError):
            servicio_venta.cerrar_venta(conexion, carrito, cajero)

        assert conexion.execute("SELECT COUNT(*) FROM venta").fetchone()[0] == 0
        assert conexion.execute("SELECT COUNT(*) FROM venta_linea").fetchone()[0] == 0
        assert repo_productos.obtener_por_codigo(conexion, "7801234000019").stock == 10
        assert repo_productos.obtener_por_codigo(conexion, "7801234000026").stock == 5

    def test_guarda_el_precio_del_momento_de_la_venta(
        self, conexion, productos, cajero, admin
    ) -> None:
        """Cambiar un precio hoy no debe reescribir el valor de las ventas de ayer."""
        from tienda_pos.services import catalogo

        carrito = Carrito()
        carrito.agregar(productos["leche"])
        venta = servicio_venta.cerrar_venta(conexion, carrito, cajero)

        producto = productos["leche"]
        catalogo.actualizar_producto(
            conexion, admin, producto.id, producto.codigo_barras, producto.nombre, 9990, 50
        )

        guardada = repo_ventas.obtener(conexion, venta.id)
        assert guardada.lineas[0].precio_unit_clp == 1290
        assert guardada.total_clp == 1290


class TestResumenDelDia:
    def test_suma_las_ventas_de_hoy(self, conexion, productos, cajero) -> None:
        for _ in range(2):
            carrito = Carrito()
            carrito.agregar(productos["leche"], 2)
            servicio_venta.cerrar_venta(conexion, carrito, cajero)

        resumen = repo_ventas.resumen_del_dia(conexion, date.today())
        assert resumen["cantidad_ventas"] == 2
        assert resumen["total_clp"] == 5160
        assert resumen["articulos"] == 4

    def test_un_dia_sin_ventas_devuelve_ceros(self, conexion) -> None:
        resumen = repo_ventas.resumen_del_dia(conexion, date(2020, 1, 1))
        assert resumen == {"cantidad_ventas": 0, "total_clp": 0, "articulos": 0}
