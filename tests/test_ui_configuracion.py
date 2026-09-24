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


class TestTamanoDeLetra:
    """El ajuste de tamaño de letra de la pantalla F9."""

    def test_el_dialogo_devuelve_el_tamano_elegido(self, ventana) -> None:
        dialogo = DialogoConfiguracion(servicio.Preferencias(), ventana)
        dialogo.combo_letra.setCurrentIndex(
            dialogo.combo_letra.findData(servicio.TAMANO_GRANDE)
        )
        assert dialogo.preferencias.tamano_texto == servicio.TAMANO_GRANDE

    def test_el_tamano_se_previsualiza_y_cancelar_lo_deshace(self, ventana) -> None:
        vistos: list[str] = []
        dialogo = DialogoConfiguracion(
            servicio.Preferencias(), ventana, al_previsualizar_letra=vistos.append
        )
        dialogo.combo_letra.setCurrentIndex(
            dialogo.combo_letra.findData(servicio.TAMANO_MUY_GRANDE)
        )
        dialogo.reject()
        assert vistos == [servicio.TAMANO_MUY_GRANDE, servicio.TAMANO_NORMAL]

    def test_cambiar_el_tema_no_devuelve_la_letra_al_tamano_normal(self, ventana) -> None:
        # El tema y la letra viven en la misma hoja de estilos. Previsualizar un tema con la
        # letra agrandada no puede deshacer la letra: es el fallo que habría aparecido al
        # abrir la rueda de configuración y tocar solo el tema.
        ventana.aplicar_tamano_texto(servicio.TAMANO_GRANDE)
        ventana.aplicar_tema(servicio.TEMA_OSCURO)
        assert estilos.escala == estilos.ESCALA_TEXTO[servicio.TAMANO_GRANDE]
        assert estilos.actual is estilos.OSCURO

    def test_cambiar_la_letra_no_toca_el_tema(self, ventana) -> None:
        ventana.aplicar_tema(servicio.TEMA_OSCURO)
        ventana.aplicar_tamano_texto(servicio.TAMANO_MUY_GRANDE)
        assert estilos.actual is estilos.OSCURO

    def test_con_letra_grande_el_codigo_cede_su_columna(self, ventana) -> None:
        from tienda_pos.ui.venta_view import COL_CODIGO

        tabla = ventana.vista_venta.tabla
        ventana.aplicar_tamano_texto(servicio.TAMANO_NORMAL)
        assert not tabla.isColumnHidden(COL_CODIGO)
        ventana.aplicar_tamano_texto(servicio.TAMANO_GRANDE)
        assert tabla.isColumnHidden(COL_CODIGO)
        ventana.aplicar_tamano_texto(servicio.TAMANO_NORMAL)
        assert not tabla.isColumnHidden(COL_CODIGO)

    def test_las_acciones_de_linea_siguen_funcionando_con_el_codigo_oculto(
        self, ventana
    ) -> None:
        # La celda del código se oculta pero no se borra: las acciones la usan para saber
        # sobre qué producto actúan.
        from tienda_pos.db.seed import codigo_demo

        venta = ventana.vista_venta
        ventana.aplicar_tamano_texto(servicio.TAMANO_MUY_GRANDE)
        venta.agregar_por_codigo(codigo_demo(0))
        venta.aumentar_cantidad(codigo_demo(0))
        assert venta._carrito.lineas[0].cantidad == 2

    def test_agrandar_la_letra_no_corta_ningun_nombre(self, ventana) -> None:
        # El criterio que decidió el diseño: en una caja, "Bebida ..." no se puede vender.
        # No se mide contra un ancho absoluto porque depende de la fuente disponible, y la
        # plataforma sin pantalla de las pruebas no carga las del sistema. Lo que no depende
        # de nada es esto: con la letra agrandada no se puede cortar ningún nombre que con la
        # letra normal se viera entero. Antes de ceder la columna del código, con "Muy
        # grande" se cortaban los ocho.
        from PySide6.QtGui import QFontMetrics
        from PySide6.QtWidgets import QApplication

        from tienda_pos.db.seed import codigo_demo
        from tienda_pos.ui.venta_view import COL_NOMBRE

        ventana.resize(1600, 1000)
        ventana.show()
        ventana.mostrar_venta()
        for indice in (0, 10, 19, 35, 52, 44, 3, 7):
            ventana.vista_venta.agregar_por_codigo(codigo_demo(indice))
        tabla = ventana.vista_venta.tabla

        def cortados() -> set[str]:
            QApplication.processEvents()
            metricas = QFontMetrics(tabla.font())
            return {
                tabla.item(fila, COL_NOMBRE).text()
                for fila in range(tabla.rowCount())
                if metricas.horizontalAdvance(tabla.item(fila, COL_NOMBRE).text()) + 16
                > tabla.columnWidth(COL_NOMBRE)
            }

        ventana.aplicar_tamano_texto(servicio.TAMANO_NORMAL)
        con_letra_normal = cortados()
        for tamano in (servicio.TAMANO_GRANDE, servicio.TAMANO_MUY_GRANDE):
            ventana.aplicar_tamano_texto(tamano)
            assert cortados() <= con_letra_normal, tamano


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
