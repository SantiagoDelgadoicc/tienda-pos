"""Pruebas de las preferencias y de los temas.

Lo que importa aquí no es que se guarde un JSON, sino que un archivo ausente, roto o escrito
por una versión distinta nunca impida abrir la caja.
"""

from __future__ import annotations

import json

import pytest

from tienda_pos.services import preferencias as servicio


class TestArchivoDePreferencias:
    def test_sin_archivo_devuelve_las_de_fabrica(self, tmp_path) -> None:
        cargadas = servicio.cargar(tmp_path)
        assert cargadas.tema == servicio.TEMA_CLARO
        assert cargadas.sonido is True
        assert cargadas.confirmar_cobro is True

    def test_guardar_y_volver_a_cargar(self, tmp_path) -> None:
        elegidas = servicio.Preferencias(
            tema=servicio.TEMA_OSCURO, sonido=False, confirmar_cobro=False
        )
        assert servicio.guardar(elegidas, tmp_path)

        cargadas = servicio.cargar(tmp_path)
        assert cargadas.tema == servicio.TEMA_OSCURO
        assert cargadas.sonido is False
        assert cargadas.confirmar_cobro is False

    def test_un_archivo_roto_no_impide_arrancar(self, tmp_path) -> None:
        servicio.ruta(tmp_path).write_text("{esto no es json", encoding="utf-8")
        assert servicio.cargar(tmp_path).tema == servicio.TEMA_CLARO

    def test_un_archivo_que_no_es_un_objeto_no_impide_arrancar(self, tmp_path) -> None:
        servicio.ruta(tmp_path).write_text("[1, 2, 3]", encoding="utf-8")
        assert servicio.cargar(tmp_path).tema == servicio.TEMA_CLARO

    def test_un_tema_desconocido_cae_en_el_claro(self, tmp_path) -> None:
        servicio.ruta(tmp_path).write_text(
            json.dumps({"tema": "fucsia"}), encoding="utf-8"
        )
        assert servicio.cargar(tmp_path).tema == servicio.TEMA_CLARO

    def test_las_claves_desconocidas_se_ignoran(self, tmp_path) -> None:
        # Es lo que pasaría al volver a una versión anterior tras probar una más nueva.
        servicio.ruta(tmp_path).write_text(
            json.dumps({"tema": servicio.TEMA_OSCURO, "inventado": 42}), encoding="utf-8"
        )
        assert servicio.cargar(tmp_path).tema == servicio.TEMA_OSCURO

    def test_se_crea_la_carpeta_si_no_existe(self, tmp_path) -> None:
        destino = tmp_path / "sin" / "crear"
        assert servicio.guardar(servicio.Preferencias(), destino)
        assert servicio.ruta(destino).exists()


class TestTemas:
    def test_los_dos_temas_definen_todos_los_colores(self) -> None:
        pytest.importorskip("PySide6", reason="La interfaz requiere PySide6")
        from tienda_pos.ui import estilos

        for tema in servicio.TEMAS:
            paleta = estilos.paleta_de(tema)
            hoja = estilos.hoja_de_estilos(paleta)
            # Un campo sin rellenar saldría como "None" en medio de la hoja de estilos y Qt
            # lo ignoraría en silencio, dejando ese elemento sin color.
            assert "None" not in hoja
            assert hoja.count("#") > 20

    def test_un_tema_desconocido_no_rompe_la_hoja(self) -> None:
        pytest.importorskip("PySide6", reason="La interfaz requiere PySide6")
        from tienda_pos.ui import estilos

        assert estilos.paleta_de("fucsia") is estilos.CLARO
