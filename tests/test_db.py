"""Pruebas de la base de datos: esquema, migraciones, transacciones y datos de ejemplo."""

from __future__ import annotations

import sqlite3

import pytest

from tienda_pos.db.connection import conectar, escribir_meta, leer_meta, transaccion
from tienda_pos.db.inicio import abrir_base_datos
from tienda_pos.db.migrations import VERSION_ESQUEMA, aplicar_migraciones
from tienda_pos.db.seed import cargar_datos_demo, catalogo_demo
from tienda_pos.repositories import productos as repo_productos
from tienda_pos.utils.codigo_barras import es_ean13


class TestEsquema:
    def test_crea_todas_las_tablas(self, conexion) -> None:
        tablas = {
            f["name"]
            for f in conexion.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        assert {"producto", "usuario", "venta", "venta_linea", "codigo_no_encontrado", "meta"} <= tablas

    def test_deja_la_base_en_la_ultima_version(self, conexion) -> None:
        assert conexion.execute("PRAGMA user_version").fetchone()[0] == VERSION_ESQUEMA

    def test_aplicar_migraciones_dos_veces_no_rompe_nada(self, conexion) -> None:
        assert aplicar_migraciones(conexion) == VERSION_ESQUEMA
        assert aplicar_migraciones(conexion) == VERSION_ESQUEMA

    def test_se_niega_a_abrir_una_base_mas_nueva(self, conexion) -> None:
        # Preferimos no abrirla antes que corromper los datos del cliente.
        conexion.execute(f"PRAGMA user_version = {VERSION_ESQUEMA + 1}")
        with pytest.raises(RuntimeError, match="más nueva"):
            aplicar_migraciones(conexion)

    def test_una_base_de_la_version_1_se_actualiza_sin_perder_datos(self, tmp_path) -> None:
        """El caso real: el cliente ya tiene ventas cobradas cuando llega la versión nueva."""
        import sqlite3 as sqlite

        from tienda_pos.db import migrations

        ruta = tmp_path / "vieja.db"
        antigua = sqlite.connect(ruta)
        antigua.row_factory = sqlite.Row
        # Se construye tal como quedaba una base de la versión 1: el esquema inicial y nada
        # más. No se reutiliza el esquema actual, que ya trae la migración aplicada.
        migrations._crear_esquema_inicial(antigua)
        antigua.execute("PRAGMA user_version = 1")
        antigua.execute(
            "INSERT INTO venta (folio, fecha_hora, subtotal_clp, descuento_clp, total_clp) "
            "VALUES (1, '2026-01-01 10:00:00', 1000, 0, 1000)"
        )
        antigua.execute(
            "INSERT INTO venta_linea (venta_id, codigo_barras, nombre, precio_unit_clp, "
            "cantidad, subtotal_clp) VALUES (1, '123', 'Antiguo', 1000, 1, 1000)"
        )
        antigua.commit()

        assert aplicar_migraciones(antigua) == VERSION_ESQUEMA

        fila = antigua.execute("SELECT * FROM venta_linea").fetchone()
        assert fila["nombre"] == "Antiguo"
        assert fila["subtotal_clp"] == 1000
        # Las ventas ya registradas no llevaban descuento por línea, y 0 es exactamente lo
        # que ocurrió en ellas.
        assert fila["descuento_clp"] == 0
        antigua.close()

    def test_las_claves_foraneas_estan_activas(self, conexion) -> None:
        assert conexion.execute("PRAGMA foreign_keys").fetchone()[0] == 1

    def test_no_admite_un_precio_negativo(self, conexion) -> None:
        with pytest.raises(sqlite3.IntegrityError):
            conexion.execute(
                "INSERT INTO producto (codigo_barras, nombre, precio_clp) VALUES (?, ?, ?)",
                ("123", "Imposible", -100),
            )

    def test_no_admite_una_linea_sin_venta(self, conexion) -> None:
        with pytest.raises(sqlite3.IntegrityError):
            conexion.execute(
                "INSERT INTO venta_linea (venta_id, codigo_barras, nombre, precio_unit_clp, "
                "cantidad, subtotal_clp) VALUES (999, '123', 'X', 100, 1, 100)"
            )


class TestTransacciones:
    def test_confirma_los_cambios_al_terminar_bien(self, conexion) -> None:
        with transaccion(conexion):
            escribir_meta(conexion, "prueba", "valor")
        assert leer_meta(conexion, "prueba") == "valor"

    def test_revierte_todo_si_algo_falla(self, conexion) -> None:
        with pytest.raises(RuntimeError):
            with transaccion(conexion):
                escribir_meta(conexion, "prueba", "valor")
                raise RuntimeError("algo se rompió")
        assert leer_meta(conexion, "prueba") is None

    def test_meta_devuelve_el_valor_por_defecto(self, conexion) -> None:
        assert leer_meta(conexion, "inexistente", "por_defecto") == "por_defecto"


class TestDatosDemo:
    def test_todos_los_codigos_son_ean13_validos(self) -> None:
        # Si no lo fueran, una pistola real no los leería en la demostración. La excepción es
        # el pan, que no trae etiqueta: lleva un código interno y se vende por nombre (D-037).
        etiquetados = [p for p in catalogo_demo() if p.codigo_barras != "2000001"]
        assert all(es_ean13(p.codigo_barras) for p in etiquetados)
        assert len(etiquetados) == len(catalogo_demo()) - 1

    def test_no_hay_codigos_repetidos(self) -> None:
        codigos = [p.codigo_barras for p in catalogo_demo()]
        assert len(codigos) == len(set(codigos))

    def test_todos_tienen_precio_y_nombre(self) -> None:
        assert all(p.precio_clp > 0 and p.nombre.strip() for p in catalogo_demo())

    def test_carga_el_catalogo_en_una_base_vacia(self, conexion) -> None:
        with transaccion(conexion):
            insertados = cargar_datos_demo(conexion)
        assert insertados == len(catalogo_demo())
        assert repo_productos.contar(conexion) == insertados

    def test_cargar_dos_veces_no_duplica(self, conexion) -> None:
        with transaccion(conexion):
            cargar_datos_demo(conexion)
        total = repo_productos.contar(conexion)

        with transaccion(conexion):
            assert cargar_datos_demo(conexion) == 0
        assert repo_productos.contar(conexion) == total

    def test_crea_los_usuarios_por_defecto(self, conexion) -> None:
        with transaccion(conexion):
            cargar_datos_demo(conexion)
        nombres = {f["nombre"] for f in conexion.execute("SELECT nombre FROM usuario")}
        assert nombres == {"Administrador", "Cajero"}


class TestApertura:
    def test_abre_una_base_en_archivo_y_persiste(self, tmp_path) -> None:
        ruta = tmp_path / "sub" / "tienda.db"
        conexion = abrir_base_datos(ruta, con_datos_demo=False)
        with transaccion(conexion):
            escribir_meta(conexion, "clave", "valor")
        conexion.close()

        assert ruta.exists()
        otra = conectar(ruta)
        assert leer_meta(otra, "clave") == "valor"
        otra.close()

    def test_abre_con_datos_demo(self, tmp_path) -> None:
        conexion = abrir_base_datos(tmp_path / "tienda.db", con_datos_demo=True)
        assert repo_productos.contar(conexion) > 0
        conexion.close()
