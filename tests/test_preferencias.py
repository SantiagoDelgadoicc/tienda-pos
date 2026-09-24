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


class TestTamanoDeTexto:
    """El tamaño de letra que pidió el cliente el 2026-09-23."""

    def test_por_defecto_es_el_normal(self, tmp_path) -> None:
        assert servicio.cargar(tmp_path).tamano_texto == servicio.TAMANO_NORMAL

    def test_se_guarda_y_se_recupera(self, tmp_path) -> None:
        assert servicio.guardar(
            servicio.Preferencias(tamano_texto=servicio.TAMANO_MUY_GRANDE), tmp_path
        )
        assert servicio.cargar(tmp_path).tamano_texto == servicio.TAMANO_MUY_GRANDE

    def test_un_tamano_desconocido_cae_en_el_normal(self, tmp_path) -> None:
        servicio.ruta(tmp_path).write_text(
            json.dumps({"tamano_texto": "gigante"}), encoding="utf-8"
        )
        assert servicio.cargar(tmp_path).tamano_texto == servicio.TAMANO_NORMAL

    def test_un_archivo_de_antes_del_ajuste_abre_con_el_normal(self, tmp_path) -> None:
        # Es el archivo que ya tienen las dos cajas de la tienda: sin la clave nueva.
        servicio.ruta(tmp_path).write_text(
            json.dumps({"tema": servicio.TEMA_OSCURO, "sonido": False}), encoding="utf-8"
        )
        cargadas = servicio.cargar(tmp_path)
        assert cargadas.tamano_texto == servicio.TAMANO_NORMAL
        assert cargadas.tema == servicio.TEMA_OSCURO


class TestEscalaDeLaHoja:
    @pytest.fixture(autouse=True)
    def _qt(self) -> None:
        pytest.importorskip("PySide6", reason="La interfaz requiere PySide6")

    @staticmethod
    def _tamano(hoja: str, selector: str) -> int:
        import re

        inicio = hoja.index(selector)
        bloque = hoja[inicio : hoja.index("}", inicio)]
        return int(re.search(r"font-size:\s*(\d+)px", bloque).group(1))

    def test_sin_escala_la_hoja_no_cambia(self) -> None:
        from tienda_pos.ui import estilos

        assert estilos.hoja_de_estilos(estilos.CLARO) == estilos.hoja_de_estilos(
            estilos.CLARO, 1.0
        )

    def test_crece_lo_que_se_lee_de_lejos(self) -> None:
        from tienda_pos.ui import estilos

        normal = estilos.hoja_de_estilos(estilos.CLARO)
        grande = estilos.hoja_de_estilos(estilos.CLARO, 1.25)
        for selector in ("QTableWidget {", "QLabel#tituloPantalla"):
            assert self._tamano(grande, selector) > self._tamano(normal, selector), selector

    def test_no_crece_lo_que_se_usa_de_cerca(self) -> None:
        # El menú lateral tiene ancho fijo: si su letra creciera, cada rótulo se montaría
        # sobre su atajo. Lo mismo la barra de atajos, que se saldría por la derecha.
        from tienda_pos.ui import estilos

        normal = estilos.hoja_de_estilos(estilos.CLARO)
        grande = estilos.hoja_de_estilos(estilos.CLARO, 1.25)
        for selector in (
            "QLabel#navAtajo",
            "QLabel#navSeccion",
            "QStatusBar {",
            "QHeaderView::section",
            "QLineEdit#campoEscaneo",
        ):
            assert self._tamano(grande, selector) == self._tamano(normal, selector), selector

    def test_los_tamanos_escalados_son_pixeles_enteros(self) -> None:
        # Qt acepta "18.75px" pero lo redondea a su manera, distinta según la plataforma.
        import re

        from tienda_pos.ui import estilos

        for factor in estilos.ESCALA_TEXTO.values():
            hoja = estilos.hoja_de_estilos(estilos.CLARO, factor)
            assert not re.search(r"font-size:\s*\d+\.\d+px", hoja)

    def test_cada_tamano_guardado_tiene_su_escala(self) -> None:
        from tienda_pos.ui import estilos

        assert set(estilos.ESCALA_TEXTO) == set(servicio.TAMANOS_TEXTO)
        assert estilos.ESCALA_TEXTO[servicio.TAMANO_NORMAL] == 1.0
        escalas = [estilos.ESCALA_TEXTO[t] for t in servicio.TAMANOS_TEXTO]
        assert escalas == sorted(escalas)
