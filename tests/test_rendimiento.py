"""Pruebas de rendimiento.

Comprueban el criterio de aceptación del plan: la búsqueda por código de barras debe
responder muy por debajo de 50 ms incluso con un catálogo mucho mayor que el que se le
supone al cliente.

Los umbrales son deliberadamente holgados: una prueba de rendimiento que falla porque el
equipo estaba ocupado no mide nada, solo genera ruido y acaba desactivada.
"""

from __future__ import annotations

import time

import pytest

from tienda_pos.db.connection import transaccion
from tienda_pos.domain.models import Producto
from tienda_pos.repositories import productos as repo_productos
from tienda_pos.services import catalogo
from tienda_pos.utils.codigo_barras import generar_ean13

CANTIDAD = 5000
LIMITE_MS = 50


@pytest.fixture
def catalogo_grande(conexion):
    """Un catálogo de 5.000 productos: unas cien veces el de un almacén de barrio."""
    with transaccion(conexion):
        for indice in range(CANTIDAD):
            repo_productos.crear(
                conexion,
                Producto(
                    codigo_barras=generar_ean13(f"779{indice:09d}"),
                    nombre=f"Producto de prueba {indice:05d}",
                    precio_clp=1000 + indice,
                    stock=10,
                ),
            )
    return conexion


def _medir_ms(funcion, repeticiones: int = 50) -> float:
    """Tiempo medio de una operación, en milisegundos."""
    inicio = time.perf_counter()
    for _ in range(repeticiones):
        funcion()
    return (time.perf_counter() - inicio) * 1000 / repeticiones


class TestRendimiento:
    def test_la_busqueda_por_codigo_es_inmediata(self, catalogo_grande) -> None:
        codigo = generar_ean13(f"779{CANTIDAD - 1:09d}")  # el último, el peor caso sin índice

        medio = _medir_ms(lambda: catalogo.consultar_por_codigo(catalogo_grande, codigo))
        assert medio < LIMITE_MS, f"La búsqueda tardó {medio:.1f} ms de media"

    def test_la_busqueda_por_nombre_tambien_responde(self, catalogo_grande) -> None:
        medio = _medir_ms(
            lambda: catalogo.buscar_por_nombre(catalogo_grande, "prueba 04999"), repeticiones=10
        )
        assert medio < LIMITE_MS * 4, f"La búsqueda por nombre tardó {medio:.1f} ms de media"

    def test_el_indice_de_codigo_de_barras_existe_y_se_usa(self, catalogo_grande) -> None:
        # Sin índice, la consulta recorrería la tabla entera y el tiempo crecería con el
        # catálogo. Se comprueba el plan de ejecución, que no depende de lo ocupado que esté
        # el equipo.
        filas = catalogo_grande.execute(
            "EXPLAIN QUERY PLAN SELECT * FROM producto WHERE codigo_barras = ? AND activo = 1",
            ("x",),
        ).fetchall()
        plan = " ".join(str(valor) for fila in filas for valor in fila)

        # SQLite dice "SEARCH ... USING INDEX" cuando usa uno, y "SCAN" cuando recorre la
        # tabla entera. Lo que no puede aparecer aquí es SCAN.
        assert "INDEX" in plan, plan
        assert "SCAN" not in plan, plan
