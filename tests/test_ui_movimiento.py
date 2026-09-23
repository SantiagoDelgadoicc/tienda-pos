"""Pruebas del movimiento (D-029).

El resto de la suite corre con las animaciones apagadas, para no depender del reloj. Estas
las encienden a propósito y comprueban las tres reglas del módulo `ui/movimiento.py`: que el
estado cambia en el acto aunque el dibujo tarde, que todo se puede interrumpir y que la
preferencia las apaga de verdad.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6", reason="La interfaz requiere PySide6")

from tienda_pos.db.seed import codigo_demo  # noqa: E402
from tienda_pos.services import preferencias as servicio  # noqa: E402
from tienda_pos.ui import estilos, movimiento  # noqa: E402

from .conftest import esperar  # noqa: E402

COLA = codigo_demo(0)
LECHE = codigo_demo(10)

#: Margen sobre la duración más larga para dar por terminada una animación.
_HOLGURA_MS = 250


class TestBarraLateral:
    def test_ctrl_b_cambia_el_estado_al_instante_y_el_ancho_despues(
        self, ventana, con_movimiento
    ) -> None:
        barra = ventana.barra_lateral
        barra.alternar_plegado()

        assert barra.esta_plegada
        assert barra.minimumWidth() > estilos.ANCHO_BARRA_LATERAL_PLEGADA

        esperar(movimiento.BARRA_MS + _HOLGURA_MS)
        assert barra.minimumWidth() == estilos.ANCHO_BARRA_LATERAL_PLEGADA

    def test_desplegar_devuelve_los_textos_al_final(self, ventana, con_movimiento) -> None:
        barra = ventana.barra_lateral
        barra.plegar(True)
        barra.alternar_plegado()

        # A medio camino todavía se dibuja como tira: sin textos partidos.
        assert not barra._textos_marca.isVisible()
        esperar(movimiento.BARRA_MS + _HOLGURA_MS)
        assert barra._textos_marca.isVisible()
        assert barra.minimumWidth() == estilos.ANCHO_BARRA_LATERAL

    def test_un_segundo_ctrl_b_a_medio_camino_da_la_vuelta(
        self, ventana, con_movimiento
    ) -> None:
        barra = ventana.barra_lateral
        barra.alternar_plegado()
        esperar(movimiento.BARRA_MS // 3)
        barra.alternar_plegado()

        assert not barra.esta_plegada
        esperar(movimiento.BARRA_MS + _HOLGURA_MS)
        assert barra.minimumWidth() == estilos.ANCHO_BARRA_LATERAL
        assert barra._textos_marca.isVisible()

    def test_al_aplicar_preferencias_no_se_anima(self, ventana, con_movimiento) -> None:
        # Arrancar el programa o guardar la configuración no debe enseñar el menú recogiéndose.
        ventana.aplicar_preferencias(servicio.Preferencias(barra_lateral_plegada=True))
        assert ventana.barra_lateral.minimumWidth() == estilos.ANCHO_BARRA_LATERAL_PLEGADA

    def test_con_las_animaciones_apagadas_se_pliega_de_golpe(
        self, ventana, con_movimiento
    ) -> None:
        ventana.aplicar_preferencias(servicio.Preferencias(animaciones=False))
        ventana.barra_lateral.alternar_plegado()
        assert ventana.barra_lateral.minimumWidth() == estilos.ANCHO_BARRA_LATERAL_PLEGADA

    def test_los_iconos_no_cambian_de_altura_al_plegar(self, ventana) -> None:
        # Es lo que hace que el plegado se lea como un cajón que se cierra y no como un menú
        # que se reordena: lo único que se mueve es el borde derecho.
        from PySide6.QtWidgets import QApplication

        barra = ventana.barra_lateral
        alturas = {c: b.mapTo(barra, b.rect().center()).y() for c, b in barra._botones.items()}

        barra.plegar(True)
        QApplication.processEvents()
        plegadas = {c: b.mapTo(barra, b.rect().center()).y() for c, b in barra._botones.items()}

        assert plegadas == alturas


class TestAvisoDeEscaneo:
    def test_entra_con_fundido_y_queda_nitido(self, ventana, con_movimiento) -> None:
        vista = ventana.vista_venta
        vista.agregar_por_codigo(COLA)

        efecto = vista.mensaje.graphicsEffect()
        assert vista.mensaje.isVisible()
        assert efecto.isEnabled()

        esperar(movimiento.ENTRADA_MS + _HOLGURA_MS)
        # Terminado el fundido, el efecto se quita: con él puesto, el texto pierde ClearType.
        assert not efecto.isEnabled()
        assert efecto.opacity() == 1.0

    def test_se_va_con_fundido_al_vencer_el_tiempo(self, ventana, con_movimiento) -> None:
        vista = ventana.vista_venta
        vista.agregar_por_codigo(COLA)
        esperar(movimiento.ENTRADA_MS + _HOLGURA_MS)

        vista._temporizador_mensaje.timeout.emit()
        assert vista._fundido_mensaje.saliendo
        esperar(movimiento.SALIDA_MS + _HOLGURA_MS)
        assert not vista.mensaje.isVisible()

    def test_un_aviso_durante_la_salida_la_cancela(self, ventana, con_movimiento) -> None:
        vista = ventana.vista_venta
        vista.agregar_por_codigo(COLA)
        esperar(movimiento.ENTRADA_MS + _HOLGURA_MS)

        vista._temporizador_mensaje.timeout.emit()
        esperar(movimiento.SALIDA_MS // 3)
        vista.agregar_por_codigo(LECHE)

        esperar(movimiento.SALIDA_MS + _HOLGURA_MS)
        assert vista.mensaje.isVisible()
        assert "Leche" in vista.mensaje.text()
        assert vista.mensaje.graphicsEffect().opacity() == 1.0

    def test_un_aviso_nuevo_con_el_anterior_a_la_vista_parpadea(
        self, ventana, con_movimiento
    ) -> None:
        vista = ventana.vista_venta
        vista.agregar_por_codigo(COLA)
        esperar(movimiento.ENTRADA_MS + _HOLGURA_MS)

        vista.agregar_por_codigo(COLA)
        esperar(movimiento.PULSO_MS // 2)
        assert vista.mensaje.graphicsEffect().opacity() < 1.0

        esperar(movimiento.PULSO_MS + _HOLGURA_MS)
        assert vista.mensaje.graphicsEffect().opacity() == 1.0


class TestDestelloDeLinea:
    def test_la_linea_agregada_destella_y_se_apaga(self, ventana, con_movimiento) -> None:
        vista = ventana.vista_venta
        vista.agregar_por_codigo(COLA)

        assert vista.intensidad_destello(0) == pytest.approx(1.0)
        esperar(movimiento.DESTELLO_MS + _HOLGURA_MS)
        assert vista.intensidad_destello(0) == 0.0

    def test_solo_destella_la_linea_que_cambio(self, ventana, con_movimiento) -> None:
        vista = ventana.vista_venta
        vista.agregar_por_codigo(COLA)
        vista.agregar_por_codigo(LECHE)

        assert vista.intensidad_destello(0) == 0.0
        assert vista.intensidad_destello(1) > 0.0

    def test_quitar_una_unidad_no_destella(self, ventana, con_movimiento) -> None:
        # El verde dice «entró», y al quitar no entró nada.
        vista = ventana.vista_venta
        vista.agregar_por_codigo(COLA)
        vista.agregar_por_codigo(COLA)
        vista.disminuir_cantidad(COLA)

        assert vista.intensidad_destello(0) == 0.0

    def test_sin_animaciones_no_hay_destello(self, ventana) -> None:
        vista = ventana.vista_venta
        vista.agregar_por_codigo(COLA)
        assert vista.intensidad_destello(0) == 0.0


class TestPreferencia:
    def test_viene_encendida_y_se_guarda(self, tmp_path) -> None:
        assert servicio.Preferencias().animaciones is True
        servicio.guardar(servicio.Preferencias(animaciones=False), tmp_path)
        assert servicio.cargar(tmp_path).animaciones is False

    def test_la_rueda_de_configuracion_la_devuelve(self, ventana) -> None:
        from tienda_pos.ui.configuracion_dialog import DialogoConfiguracion

        dialogo = DialogoConfiguracion(servicio.Preferencias(), ventana)
        dialogo.casilla_animaciones.setChecked(False)
        assert dialogo.preferencias.animaciones is False

    def test_aplicarla_enciende_y_apaga_el_modulo(self, ventana) -> None:
        ventana.aplicar_preferencias(servicio.Preferencias(animaciones=False))
        assert movimiento.habilitado is False
        ventana.aplicar_preferencias(servicio.Preferencias(animaciones=True))
        assert movimiento.habilitado is True


class TestConsultaDePrecio:
    def test_el_precio_entra_con_fundido(self, ventana, con_movimiento) -> None:
        vista = ventana.vista_consulta
        ventana.mostrar_consulta()
        vista.consultar(COLA)

        efecto = vista._resultado.graphicsEffect()
        assert vista.etiqueta_precio.isVisible()
        assert efecto.isEnabled()
        esperar(movimiento.ENTRADA_MS + _HOLGURA_MS)
        assert not efecto.isEnabled()

    def test_limpiar_no_espera_al_fundido(self, ventana, con_movimiento) -> None:
        # El aviso de espera ocupa el mismo sitio: los dos a la vez empujarían el precio.
        vista = ventana.vista_consulta
        ventana.mostrar_consulta()
        vista.consultar(COLA)
        vista.limpiar()

        assert not vista._resultado.isVisible()
        assert vista.etiqueta_espera.isVisible()

    def test_un_codigo_desconocido_tambien_se_funde(self, ventana, con_movimiento) -> None:
        vista = ventana.vista_consulta
        ventana.mostrar_consulta()
        vista.consultar("7790000000017")
        assert vista._resultado.graphicsEffect().isEnabled()


class TestDialogos:
    def _dialogo(self, ventana):
        from tienda_pos.ui.dialogos import DialogoTexto

        return DialogoTexto("Prueba", "Escriba algo", padre=ventana)

    def test_se_abre_con_fundido_y_queda_opaco(self, ventana, con_movimiento) -> None:
        dialogo = self._dialogo(ventana)
        dialogo.show()
        assert dialogo.windowOpacity() < 1.0

        esperar(movimiento.DIALOGO_MS + _HOLGURA_MS)
        assert dialogo.windowOpacity() == pytest.approx(1.0)
        dialogo.close()

    def test_cerrar_a_medio_fundido_no_lo_deja_transparente(
        self, ventana, con_movimiento
    ) -> None:
        dialogo = self._dialogo(ventana)
        dialogo.show()
        dialogo.hide()
        assert dialogo.windowOpacity() == pytest.approx(1.0)

    def test_sin_animaciones_se_abre_entero(self, ventana) -> None:
        dialogo = self._dialogo(ventana)
        dialogo.show()
        assert dialogo.windowOpacity() == pytest.approx(1.0)
        dialogo.close()


class TestPinIncorrecto:
    def _login(self, ventana):
        from tienda_pos.ui.login_dialog import DialogoLogin

        dialogo = DialogoLogin(ventana._sesion, ventana)
        dialogo.show()
        esperar(movimiento.DIALOGO_MS + _HOLGURA_MS)
        return dialogo

    def test_sacude_la_ventana_y_la_devuelve_a_su_sitio(
        self, ventana, con_movimiento
    ) -> None:
        dialogo = self._login(ventana)
        origen = dialogo.pos()
        dialogo.campo_pin.setText("0000")
        dialogo._intentar()

        assert dialogo.error.isVisible()
        assert dialogo._sacudida is not None
        esperar(movimiento.SACUDIDA_MS + _HOLGURA_MS)
        assert dialogo.pos() == origen
        dialogo.close()

    def test_dos_errores_seguidos_no_la_dejan_corrida(self, ventana, con_movimiento) -> None:
        dialogo = self._login(ventana)
        origen = dialogo.pos()
        for _ in range(2):
            dialogo.campo_pin.setText("0000")
            dialogo._intentar()
            esperar(movimiento.SACUDIDA_MS // 3)

        esperar(movimiento.SACUDIDA_MS + _HOLGURA_MS)
        assert dialogo.pos() == origen
        dialogo.close()

    def test_sin_animaciones_no_se_mueve(self, ventana) -> None:
        dialogo = self._login(ventana)
        origen = dialogo.pos()
        dialogo.campo_pin.setText("0000")
        dialogo._intentar()

        assert getattr(dialogo, "_sacudida", None) is None
        assert dialogo.pos() == origen
        dialogo.close()
