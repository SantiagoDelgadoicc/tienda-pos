"""Pruebas de las utilidades de dinero y de códigos de barras."""

from __future__ import annotations

import pytest

from tienda_pos.utils import codigo_barras as cb
from tienda_pos.utils.money import formatear_clp, parsear_clp, porcentaje_de


class TestFormatoDinero:
    @pytest.mark.parametrize(
        "monto, esperado",
        [
            (0, "$0"),
            (990, "$990"),
            (1290, "$1.290"),
            (1234567, "$1.234.567"),
            (-1200, "-$1.200"),
        ],
    )
    def test_formatea_con_separador_de_miles(self, monto: int, esperado: str) -> None:
        assert formatear_clp(monto) == esperado

    def test_puede_omitir_el_simbolo(self) -> None:
        assert formatear_clp(1290, con_simbolo=False) == "1.290"


class TestParseoDinero:
    @pytest.mark.parametrize(
        "texto, esperado",
        [
            ("1290", 1290),
            ("1.290", 1290),
            ("$1.290", 1290),
            ("  $ 1.290  ", 1290),
            ("-500", -500),
        ],
    )
    def test_acepta_lo_que_escribe_una_persona(self, texto: str, esperado: int) -> None:
        assert parsear_clp(texto) == esperado

    @pytest.mark.parametrize("texto", ["", "   ", "abc", "12,5", "1.2.a"])
    def test_rechaza_lo_que_no_es_un_monto(self, texto: str) -> None:
        with pytest.raises(ValueError):
            parsear_clp(texto)


class TestPorcentaje:
    def test_calcula_el_porcentaje(self) -> None:
        assert porcentaje_de(10000, 10) == 1000

    def test_redondea_la_mitad_hacia_arriba(self) -> None:
        # El 10% de 1005 es 100,5. Una persona espera 101, no 100.
        assert porcentaje_de(1005, 10) == 101

    def test_porcentaje_cero_no_descuenta_nada(self) -> None:
        assert porcentaje_de(9990, 0) == 0

    def test_porcentaje_cien_descuenta_todo(self) -> None:
        assert porcentaje_de(9990, 100) == 9990


class TestCodigoDeBarras:
    def test_calcula_el_digito_verificador(self) -> None:
        # Caso conocido de la especificación EAN-13.
        assert cb.digito_verificador_ean13("400638133393") == 1

    def test_genera_codigos_validos(self) -> None:
        codigo = cb.generar_ean13("780123400000")
        assert len(codigo) == 13
        assert cb.es_ean13(codigo)

    def test_detecta_un_digito_verificador_incorrecto(self) -> None:
        valido = cb.generar_ean13("780123400000")
        alterado = valido[:12] + str((int(valido[12]) + 1) % 10)
        assert not cb.es_ean13(alterado)

    def test_normaliza_lo_que_llega_del_lector(self) -> None:
        assert cb.normalizar("  7801 234-000019 \r\n") == "7801234000019"

    @pytest.mark.parametrize("codigo", ["7801234000019", "ABC123", "12", "producto1"])
    def test_acepta_codigos_estandar_e_internos(self, codigo: str) -> None:
        # Muchas tiendas usan códigos internos cortos para sus productos propios: rechazarlos
        # por no ser EAN-13 dejaría fuera media bodega.
        assert cb.es_valido(codigo)

    @pytest.mark.parametrize("codigo", ["", "   ", "cod/igo", "a" * 40])
    def test_rechaza_codigos_imposibles(self, codigo: str) -> None:
        assert not cb.es_valido(codigo)
