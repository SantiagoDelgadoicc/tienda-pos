"""Pruebas de la rueda de configuración y del cambio de tema en caliente."""

from __future__ import annotations

import os

import pytest

# Debe fijarse antes de importar Qt.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6", reason="La interfaz requiere PySide6")

from tienda_pos.services import preferencias as servicio  # noqa: E402
from tienda_pos.ui import estilos  # noqa: E402
from tienda_pos.ui.configuracion_dialog import DialogoConfiguracion  # noqa: E402
from tienda_pos.utils import sonido  # noqa: E402


@pytest.fixture(autouse=True)
def _restaurar_estado(app):
    """Devuelve el tema y el sonido a su estado inicial pase lo que pase en la prueba."""
    tema_inicial = estilos.actual.nombre
    sonaba = sonido.habilitado
    yield
    estilos.aplicar(app, tema_inicial)
    sonido.habilitado = sonaba


class TestVentanaConLaConfiguracion:
    def test_la_ventana_trae_la_rueda(self, ventana) -> None:
        assert ventana.boton_configuracion.isVisible()

    def test_aplicar_el_tema_oscuro_repinta_la_aplicacion(self, ventana) -> None:
        ventana.aplicar_tema(servicio.TEMA_OSCURO)
        assert estilos.actual is estilos.OSCURO
        # El fondo oscuro tiene que estar realmente en la hoja aplicada, no solo elegido.
        from PySide6.QtWidgets import QApplication

        assert estilos.OSCURO.fondo in QApplication.instance().styleSheet()

    def test_las_preferencias_llegan_a_la_pantalla_de_venta(self, ventana) -> None:
        elegidas = servicio.Preferencias(
            tema=servicio.TEMA_OSCURO, sonido=False, confirmar_cobro=False
        )
        ventana.aplicar_preferencias(elegidas)

        assert ventana.vista_venta.preferencias.confirmar_cobro is False
        assert sonido.habilitado is False

    def test_ocultar_la_barra_de_atajos(self, ventana) -> None:
        ventana.aplicar_preferencias(servicio.Preferencias(mostrar_atajos=False))
        assert not ventana.statusBar().isVisible()
        ventana.aplicar_preferencias(servicio.Preferencias(mostrar_atajos=True))
        assert ventana.statusBar().isVisible()

    def test_sin_confirmacion_la_venta_se_cierra_directa(self, ventana, conexion) -> None:
        from tienda_pos.db.seed import codigo_demo
        from tienda_pos.repositories import ventas as repo_ventas
        from tienda_pos.ui import dialogos

        # Si la confirmación se pidiera, esta función haría fallar la prueba en lugar de
        # dejar pasar la venta.
        def _no_debe_preguntar(*args, **kwargs):
            raise AssertionError("No debía pedirse confirmación")

        ventana.aplicar_preferencias(servicio.Preferencias(confirmar_cobro=False))
        vista = ventana.vista_venta
        vista.agregar_por_codigo(codigo_demo(0))

        original = dialogos.confirmar
        dialogos.confirmar = _no_debe_preguntar
        try:
            vista.cobrar()
        finally:
            dialogos.confirmar = original

        assert repo_ventas.resumen_del_dia(conexion)["cantidad_ventas"] == 1


class TestDialogoDeConfiguracion:
    def test_devuelve_lo_elegido(self, ventana) -> None:
        dialogo = DialogoConfiguracion(servicio.Preferencias(), ventana)
        dialogo.combo_tema.setCurrentIndex(dialogo.combo_tema.findData(servicio.TEMA_OSCURO))
        dialogo.casilla_sonido.setChecked(False)

        elegidas = dialogo.preferencias
        assert elegidas.tema == servicio.TEMA_OSCURO
        assert elegidas.sonido is False

    def test_el_tema_se_previsualiza_al_elegirlo(self, ventana) -> None:
        vistos: list[str] = []
        dialogo = DialogoConfiguracion(
            servicio.Preferencias(), ventana, al_previsualizar_tema=vistos.append
        )
        dialogo.combo_tema.setCurrentIndex(dialogo.combo_tema.findData(servicio.TEMA_OSCURO))
        assert vistos == [servicio.TEMA_OSCURO]

    def test_cancelar_deshace_la_previsualizacion(self, ventana) -> None:
        vistos: list[str] = []
        dialogo = DialogoConfiguracion(
            servicio.Preferencias(), ventana, al_previsualizar_tema=vistos.append
        )
        dialogo.combo_tema.setCurrentIndex(dialogo.combo_tema.findData(servicio.TEMA_OSCURO))
        dialogo.reject()

        assert vistos == [servicio.TEMA_OSCURO, servicio.TEMA_CLARO]

    def test_guardar_deja_el_archivo_en_la_carpeta_de_datos(self, ventana, tmp_path) -> None:
        # La fixture `ventana` ya apunta TIENDA_POS_HOME a una carpeta temporal.
        from tienda_pos import config

        dialogo = DialogoConfiguracion(servicio.Preferencias(), ventana)
        dialogo.combo_tema.setCurrentIndex(dialogo.combo_tema.findData(servicio.TEMA_OSCURO))
        assert servicio.guardar(dialogo.preferencias)

        assert servicio.ruta().exists()
        assert servicio.ruta().parent == config.directorio_datos()
        assert servicio.cargar().tema == servicio.TEMA_OSCURO


class TestTotalTrasCambiarDeTema:
    def test_el_total_recupera_el_verde_del_tema(self, ventana) -> None:
        # El total lleva su tamaño y su color en un estilo propio de la etiqueta, no en la
        # hoja de la aplicación, así que un cambio de tema no lo alcanza solo.
        from tienda_pos.db.seed import codigo_demo

        vista = ventana.vista_venta
        vista.agregar_por_codigo(codigo_demo(0))

        ventana.aplicar_tema(servicio.TEMA_OSCURO)
        assert estilos.OSCURO.exito.lower() in vista.valor_total.styleSheet().lower()

        ventana.aplicar_tema(servicio.TEMA_CLARO)
        assert estilos.CLARO.exito.lower() in vista.valor_total.styleSheet().lower()


class TestBarraLateral:
    """Plegarla es un ajuste del equipo, así que tiene que sobrevivir al cierre."""

    def test_plegar_esconde_los_rotulos_y_estrecha_la_barra(self, ventana) -> None:
        from tienda_pos.ui import estilos

        barra = ventana.barra_lateral
        assert barra.width() == estilos.ANCHO_BARRA_LATERAL

        barra.alternar_plegado()
        assert barra.esta_plegada
        assert barra.width() == estilos.ANCHO_BARRA_LATERAL_PLEGADA

        barra.alternar_plegado()
        assert not barra.esta_plegada
        assert barra.width() == estilos.ANCHO_BARRA_LATERAL

    def test_el_plegado_se_guarda_en_el_disco(self, ventana) -> None:
        ventana.barra_lateral.alternar_plegado()
        assert servicio.cargar().barra_lateral_plegada is True

        ventana.barra_lateral.alternar_plegado()
        assert servicio.cargar().barra_lateral_plegada is False

    def test_aplicar_preferencias_pliega_la_barra(self, ventana) -> None:
        ventana.aplicar_preferencias(servicio.Preferencias(barra_lateral_plegada=True))
        assert ventana.barra_lateral.esta_plegada

    def test_guardar_otro_ajuste_no_despliega_la_barra(self, ventana) -> None:
        # El diálogo no muestra el plegado, pero tampoco puede perderlo al guardar el tema.
        ventana.barra_lateral.alternar_plegado()
        dialogo = DialogoConfiguracion(ventana.preferencias, ventana)
        dialogo.casilla_sonido.setChecked(False)

        assert dialogo.preferencias.barra_lateral_plegada is True

    def test_la_barra_sigue_navegando_plegada(self, ventana) -> None:
        ventana.barra_lateral.alternar_plegado()
        ventana.barra_lateral.navegacion_solicitada.emit("consulta")
        assert ventana.pantallas.currentWidget() is ventana.vista_consulta
