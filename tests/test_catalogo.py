"""Pruebas del catálogo: la consulta código -> precio, que es el corazón del sistema."""

from __future__ import annotations

import sqlite3

import pytest

from tienda_pos.domain.errors import (
    CodigoInvalido,
    DatosInvalidos,
    PermisoDenegado,
    ProductoDuplicado,
    ProductoNoEncontrado,
)
from tienda_pos.domain.models import Producto, Usuario
from tienda_pos.repositories import codigos as repo_codigos
from tienda_pos.services import catalogo


class TestConsultaPorCodigo:
    def test_encuentra_el_producto_y_su_precio(self, conexion, productos) -> None:
        producto = catalogo.consultar_por_codigo(conexion, "7801234000019")
        assert producto.nombre == "Leche Entera 1 L"
        assert producto.precio_clp == 1290

    def test_limpia_el_codigo_antes_de_buscar(self, conexion, productos) -> None:
        # La pistola puede enviar un salto de línea final, y una persona puede escribir
        # espacios sin darse cuenta.
        producto = catalogo.consultar_por_codigo(conexion, "  7801234000019\r\n")
        assert producto.precio_clp == 1290

    def test_codigo_inexistente_da_un_error_claro(self, conexion, productos) -> None:
        with pytest.raises(ProductoNoEncontrado) as error:
            catalogo.consultar_por_codigo(conexion, "9999999999999")
        assert "9999999999999" in str(error.value)

    def test_codigo_vacio_o_con_basura_se_rechaza(self, conexion, productos) -> None:
        for codigo in ("", "   ", "cod/igo"):
            with pytest.raises(CodigoInvalido):
                catalogo.consultar_por_codigo(conexion, codigo)

    def test_un_producto_desactivado_deja_de_encontrarse(self, conexion, productos, admin) -> None:
        producto = catalogo.consultar_por_codigo(conexion, "7801234000019")
        catalogo.desactivar_producto(conexion, admin, producto.id)
        with pytest.raises(ProductoNoEncontrado):
            catalogo.consultar_por_codigo(conexion, "7801234000019")


class TestRegistroDeCodigosNoEncontrados:
    def test_anota_el_codigo_que_no_existe(self, conexion, productos) -> None:
        with pytest.raises(ProductoNoEncontrado):
            catalogo.consultar_por_codigo(conexion, "1111111111116")

        pendientes = repo_codigos.listar_pendientes(conexion)
        assert [p.codigo for p in pendientes] == ["1111111111116"]
        assert pendientes[0].intentos == 1

    def test_cuenta_los_intentos_repetidos(self, conexion, productos) -> None:
        for _ in range(3):
            with pytest.raises(ProductoNoEncontrado):
                catalogo.consultar_por_codigo(conexion, "1111111111116")

        pendientes = repo_codigos.listar_pendientes(conexion)
        assert pendientes[0].intentos == 3

    def test_dar_de_alta_el_producto_resuelve_el_pendiente(self, conexion, admin) -> None:
        with pytest.raises(ProductoNoEncontrado):
            catalogo.consultar_por_codigo(conexion, "1111111111116")

        catalogo.crear_producto(conexion, admin, "1111111111116", "Producto nuevo", 990, 5)

        assert repo_codigos.listar_pendientes(conexion) == []

    def test_puede_no_registrar_cuando_no_corresponde(self, conexion, productos) -> None:
        # En la pantalla de administración, buscar un código que no existe es trabajo normal.
        with pytest.raises(ProductoNoEncontrado):
            catalogo.consultar_por_codigo(conexion, "1111111111116", registrar_faltante=False)
        assert repo_codigos.listar_pendientes(conexion) == []


class TestBusquedaPorNombre:
    def test_encuentra_por_texto_parcial(self, conexion, productos) -> None:
        resultados = catalogo.buscar_por_nombre(conexion, "leche")
        assert len(resultados) == 1
        assert resultados[0].nombre == "Leche Entera 1 L"

    def test_no_distingue_mayusculas(self, conexion, productos) -> None:
        assert len(catalogo.buscar_por_nombre(conexion, "LECHE")) == 1

    def test_con_menos_de_dos_letras_no_devuelve_medio_catalogo(self, conexion, productos) -> None:
        assert catalogo.buscar_por_nombre(conexion, "a") == []

    def test_un_nombre_con_comillas_no_rompe_la_consulta(self, conexion, productos) -> None:
        # Defensa contra inyección: el patrón viaja como parámetro, nunca concatenado.
        assert catalogo.buscar_por_nombre(conexion, "'; DROP TABLE producto; --") == []
        assert conexion.execute("SELECT COUNT(*) FROM producto").fetchone()[0] == 3


class TestAdministracionDeProductos:
    def test_el_admin_puede_crear(self, conexion, admin) -> None:
        producto = catalogo.crear_producto(conexion, admin, "7801234000040", "Café 170 g", 5490, 8)
        assert producto.id is not None
        assert catalogo.consultar_por_codigo(conexion, "7801234000040").precio_clp == 5490

    def test_el_cajero_no_puede_crear(self, conexion, cajero) -> None:
        with pytest.raises(PermisoDenegado):
            catalogo.crear_producto(conexion, cajero, "7801234000040", "Café", 5490, 8)

    def test_sin_sesion_tampoco_se_puede_crear(self, conexion) -> None:
        with pytest.raises(PermisoDenegado):
            catalogo.crear_producto(conexion, None, "7801234000040", "Café", 5490, 8)

    def test_no_se_admiten_dos_productos_con_el_mismo_codigo(self, conexion, productos, admin) -> None:
        with pytest.raises(ProductoDuplicado):
            catalogo.crear_producto(conexion, admin, "7801234000019", "Otra leche", 1500, 3)

    @pytest.mark.parametrize(
        "codigo, nombre, precio, stock",
        [
            ("", "Producto", 1000, 1),
            ("7801234000040", "", 1000, 1),
            ("7801234000040", "   ", 1000, 1),
            ("7801234000040", "Producto", -1, 1),
            ("7801234000040", "Producto", 1000, -5),
        ],
    )
    def test_rechaza_datos_invalidos(self, conexion, admin, codigo, nombre, precio, stock) -> None:
        with pytest.raises(DatosInvalidos):
            catalogo.crear_producto(conexion, admin, codigo, nombre, precio, stock)

    def test_actualizar_cambia_el_precio(self, conexion, productos, admin) -> None:
        producto = catalogo.consultar_por_codigo(conexion, "7801234000019")
        catalogo.actualizar_producto(
            conexion, admin, producto.id, producto.codigo_barras, producto.nombre, 1490, 20
        )
        assert catalogo.consultar_por_codigo(conexion, "7801234000019").precio_clp == 1490

    def test_no_se_puede_actualizar_algo_que_no_existe(self, conexion, admin) -> None:
        with pytest.raises(DatosInvalidos):
            catalogo.actualizar_producto(conexion, admin, 9999, "7801234000040", "X", 100, 1)
