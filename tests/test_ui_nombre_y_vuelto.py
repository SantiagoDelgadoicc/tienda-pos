"""Pruebas de la fase 25: buscar por nombre al lado del código, y el vuelto en efectivo (D-039).

Las dos las pidió el cliente el 2026-10-10. La búsqueda se prueba también con teclas de verdad,
porque lo delicado es el Enter: en la lista y en el campo a la vez, no debe agregar dos veces.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6", reason="La interfaz requiere PySide6")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

from tienda_pos.db.seed import codigo_demo  # noqa: E402
from tienda_pos.domain.errors import DatosInvalidos, ErrorDominio  # noqa: E402
from tienda_pos.domain.models import MedioPago  # noqa: E402
from tienda_pos.repositories import ventas as repo_ventas  # noqa: E402
from tienda_pos.services import venta as servicio_venta  # noqa: E402
from tienda_pos.ui import dialogos, venta_view  # noqa: E402

from .conftest import esperar  # noqa: E402

COLA = codigo_demo(0)  # Bebida Cola 1.5 L, $2.290
PAN = "2000001"  # Pan batido, por peso


@pytest.fixture
def vista(ventana, monkeypatch):
    """La pantalla de venta, con la ventana del peso contestando 500 g."""
    monkeypatch.setattr(ventana.vista_venta, "pedir_gramos", lambda *a, **k: 500)
    return ventana.vista_venta


def _escribir_nombre(vista, texto: str) -> None:
    """Teclea en el campo del nombre como una persona, y espera a que salga la lista."""
    vista.buscar_por_nombre()
    QTest.keyClicks(vista.campo_nombre, texto, delay=40)
    esperar(venta_view._ESPERA_NOMBRE_MS + 120)


def _lista(vista):
    return vista._completador.popup()


def _filas(vista) -> list[str]:
    modelo = vista._modelo_nombres
    return [modelo.item(f).text() for f in range(modelo.rowCount())]


# --------------------------------------------------------------------------- buscar por nombre


class TestCampoDelNombre:
    def test_esta_al_lado_del_codigo(self, vista) -> None:
        assert vista.campo_nombre.isVisible()
        assert vista.campo_nombre.parent() is vista.campo_codigo.parent()
        assert vista.campo_nombre.x() > vista.campo_codigo.x()

    def test_f3_lleva_al_campo_del_nombre(self, ventana) -> None:
        ventana._buscar_por_nombre()
        assert ventana.vista_venta.campo_nombre.hasFocus()

    def test_al_escribir_sale_la_lista_con_el_primero_marcado(self, vista) -> None:
        _escribir_nombre(vista, "leche")
        assert _lista(vista).isVisible()
        assert len(_filas(vista)) == 4
        assert _filas(vista)[0].startswith("Crema de leche")  # por orden alfabético
        assert _lista(vista).currentIndex().row() == 0

    def test_la_lista_dice_el_precio_y_si_es_por_kilo(self, vista) -> None:
        _escribir_nombre(vista, "batido")
        assert _filas(vista) == ["Pan batido   ·   $2.490 el kilo"]

    def test_enter_en_la_lista_agrega_una_sola_vez(self, vista) -> None:
        # Lo delicado: el Enter lo ve la lista y después el campo. Debe agregar uno, no dos.
        _escribir_nombre(vista, "leche")
        QTest.keyClick(_lista(vista), Qt.Key.Key_Down)  # el segundo: Leche Chocolatada
        QTest.keyClick(_lista(vista), Qt.Key.Key_Return)
        esperar(50)
        assert [(l.nombre, l.cantidad) for l in vista.carrito.lineas] == [("Leche Chocolatada 200 ml", 1)]

    def test_enter_en_la_lista_con_un_solo_resultado_agrega_una_sola_vez(self, vista) -> None:
        # El error que salió al construirla: con un solo resultado, el Enter de la lista llegaba
        # también al campo, que con un único producto lo agregaba por su cuenta. Quedaban dos.
        _escribir_nombre(vista, "chocolatada")
        QTest.keyClick(_lista(vista), Qt.Key.Key_Return)
        esperar(50)
        assert [(l.nombre, l.cantidad) for l in vista.carrito.lineas] == [("Leche Chocolatada 200 ml", 1)]

    def test_despues_de_agregar_el_foco_vuelve_al_codigo_y_el_nombre_se_vacia(self, vista) -> None:
        # La pistola escribe donde esté el foco: tiene que volver al campo del código.
        _escribir_nombre(vista, "leche")
        QTest.keyClick(_lista(vista), Qt.Key.Key_Return)
        esperar(50)
        assert vista.campo_codigo.hasFocus()
        assert vista.campo_nombre.text() == ""
        assert not _lista(vista).isVisible()

    def test_el_pan_por_nombre_pide_el_peso(self, vista) -> None:
        _escribir_nombre(vista, "batido")
        QTest.keyClick(_lista(vista), Qt.Key.Key_Return)
        esperar(50)
        (linea,) = vista.carrito.lineas
        assert (linea.codigo_barras, linea.gramos, linea.total_clp) == (PAN, 500, 1245)

    def test_enter_rapido_con_un_solo_resultado_lo_agrega(self, vista) -> None:
        # Sin esperar a la lista: escribir y Enter de inmediato.
        vista.buscar_por_nombre()
        vista.campo_nombre.setText("chocolatada")
        vista.campo_nombre.returnPressed.emit()
        assert [l.nombre for l in vista.carrito.lineas] == ["Leche Chocolatada 200 ml"]

    def test_enter_rapido_con_varios_abre_la_lista_y_no_agrega(self, vista) -> None:
        vista.buscar_por_nombre()
        vista.campo_nombre.setText("pan de molde")
        vista.campo_nombre.returnPressed.emit()
        assert vista.carrito.esta_vacio
        assert _lista(vista).isVisible() and len(_filas(vista)) == 2

    def test_sin_resultados_la_lista_lo_dice_y_enter_no_agrega(self, vista) -> None:
        _escribir_nombre(vista, "caviar")
        assert _filas(vista) == ["No hay productos con ese nombre"]
        QTest.keyClick(_lista(vista), Qt.Key.Key_Return)
        esperar(50)
        assert vista.carrito.esta_vacio

    def test_sin_resultados_y_enter_rapido_avisa(self, vista, monkeypatch) -> None:
        avisos = []
        monkeypatch.setattr(vista, "_avisar", lambda texto, exito, **k: avisos.append(texto))
        vista.buscar_por_nombre()
        vista.campo_nombre.setText("caviar")
        vista.campo_nombre.returnPressed.emit()
        assert vista.carrito.esta_vacio
        assert avisos == ["No se encontró ningún producto con ese nombre."]

    def test_con_una_letra_no_busca(self, vista) -> None:
        _escribir_nombre(vista, "l")
        assert not _lista(vista).isVisible()

    def test_un_codigo_escrito_ahi_se_agrega_como_codigo(self, vista) -> None:
        vista.buscar_por_nombre()
        vista.campo_nombre.setText(COLA)
        vista.campo_nombre.returnPressed.emit()
        assert [l.codigo_barras for l in vista.carrito.lineas] == [COLA]

    def test_la_pistola_sobre_un_nombre_a_medias_agrega_el_codigo(self, vista) -> None:
        # Empezó a escribir "pan", se arrepintió y pasó la bebida por la pistola sin volver.
        vista.buscar_por_nombre()
        vista.campo_nombre.setText("pan" + COLA)
        vista.campo_nombre.returnPressed.emit()
        assert [l.codigo_barras for l in vista.carrito.lineas] == [COLA]

    def test_un_nombre_con_cifras_no_se_toma_por_codigo(self, vista) -> None:
        assert vista._codigo_en_nombre("Bebida Cola 1500") is None
        assert vista._codigo_en_nombre("pan2000001") == "2000001"

    def test_si_la_red_falla_avisa_y_no_revienta(self, vista, monkeypatch) -> None:
        avisos = []
        monkeypatch.setattr(vista, "_avisar", lambda texto, exito, **k: avisos.append((texto, exito)))

        def falla(_texto):
            raise ErrorDominio("No hay conexión con la caja principal.")

        monkeypatch.setattr(vista._sesion, "buscar_por_nombre", falla)
        _escribir_nombre(vista, "leche")
        assert avisos[-1] == ("No hay conexión con la caja principal.", False)
        assert not _lista(vista).isVisible()

    def test_volver_a_la_venta_vacia_el_nombre(self, ventana) -> None:
        vista = ventana.vista_venta
        _escribir_nombre(vista, "leche")
        ventana.mostrar_venta()  # Esc
        assert vista.campo_nombre.text() == ""
        assert not _lista(vista).isVisible()
        assert vista.campo_codigo.hasFocus()

    def test_el_codigo_no_encontrado_ofrece_buscar_por_nombre(self, vista, monkeypatch) -> None:
        class _Dialogo:
            buscar_por_nombre = True

            def __init__(self, *a, **k) -> None: ...

            def exec(self) -> int:
                return 1

            def deleteLater(self) -> None: ...

        monkeypatch.setattr(dialogos, "DialogoCodigoNoEncontrado", _Dialogo)
        vista.agregar_por_codigo("7809999999999")
        assert vista.campo_nombre.hasFocus()


# --------------------------------------------------------------------------- vuelto, servicio


class TestCalcularVuelto:
    @pytest.mark.parametrize(
        "total, recibido, vuelto",
        [(3500, None, 0), (3500, 3500, 0), (3500, 5000, 1500), (3500, 20_000, 16_500), (0, None, 0)],
    )
    def test_calcula(self, total, recibido, vuelto) -> None:
        assert servicio_venta.calcular_vuelto(total, recibido) == vuelto

    def test_si_no_alcanza_dice_cuanto_falta(self) -> None:
        with pytest.raises(DatosInvalidos, match=r"Faltan \$500"):
            servicio_venta.calcular_vuelto(3500, 3000)

    @pytest.mark.parametrize("recibido", [-1, servicio_venta.PAGO_EFECTIVO_MAXIMO_CLP + 1])
    def test_rechaza_montos_absurdos(self, recibido) -> None:
        with pytest.raises(DatosInvalidos):
            servicio_venta.calcular_vuelto(3500, recibido)


# --------------------------------------------------------------------------- vuelto, ventana


class TestVentanaDelVuelto:
    @pytest.fixture
    def dialogo(self, ventana):
        d = dialogos.DialogoVuelto(3500, ventana)
        yield d
        d.deleteLater()

    def test_vacio_es_pago_justo(self, dialogo) -> None:
        assert dialogo.vuelto.text() == "Paga justo, sin vuelto"
        assert dialogo._cobrar.isEnabled()
        dialogo._confirmar()
        assert dialogo.result() and dialogo.recibido is None

    @pytest.mark.parametrize("texto", ["5000", "5.000", "$5.000", " 5000 "])
    def test_calcula_el_vuelto_mientras_se_escribe(self, dialogo, texto) -> None:
        dialogo.campo.setText(texto)
        assert dialogo.vuelto.text() == "Vuelto  $1.500"
        assert dialogo._cobrar.isEnabled()
        assert dialogo.aviso.isHidden()

    def test_si_no_alcanza_no_deja_cobrar(self, dialogo) -> None:
        dialogo.campo.setText("3000")
        assert not dialogo._cobrar.isEnabled()
        assert dialogo.aviso.text() == "Faltan $500."
        dialogo._confirmar()
        assert not dialogo.result() and dialogo.recibido is None

    def test_texto_que_no_es_monto(self, dialogo) -> None:
        dialogo.campo.setText("veinte")
        assert not dialogo._cobrar.isEnabled()
        assert "por ejemplo 20.000" in dialogo.aviso.text()

    def test_un_vuelto_muy_grande_pide_revisar_pero_deja_cobrar(self, dialogo) -> None:
        # "200000" en vez de "20000": un cero de más. Se avisa; no se prohíbe.
        dialogo.campo.setText("200000")
        assert dialogo.vuelto.text() == "Vuelto  $196.500"
        assert "Revise el monto" in dialogo.aviso.text()
        assert dialogo._cobrar.isEnabled()

    def test_cobrar_guarda_lo_recibido(self, dialogo) -> None:
        dialogo.campo.setText("10.000")
        dialogo._confirmar()
        assert dialogo.result() and dialogo.recibido == 10_000

    def test_trae_escrito_el_monto_de_un_intento_anterior(self, ventana) -> None:
        d = dialogos.DialogoVuelto(3500, ventana, recibido_inicial=10_000)
        assert d.campo.text() == "10.000"
        assert d.vuelto.text() == "Vuelto  $6.500"
        d.deleteLater()


# --------------------------------------------------------------------------- vuelto, cobro


class TestCobroEnEfectivo:
    @pytest.fixture
    def pagos(self, vista, monkeypatch):
        """Contesta la ventana del vuelto con lo de la lista y anota con qué se abrió."""
        respuestas: list[tuple[bool, int | None]] = []
        llamadas: list[tuple[int, int | None]] = []

        def pedir(total, recibido=None):
            llamadas.append((total, recibido))
            return respuestas.pop(0)

        monkeypatch.setattr(vista, "pedir_pago_efectivo", pedir)
        return respuestas, llamadas

    @pytest.fixture
    def avisos(self, vista, monkeypatch):
        anotados: list[tuple[str, int | None]] = []
        monkeypatch.setattr(
            vista, "_avisar", lambda texto, exito, duracion_ms=None: anotados.append((texto, duracion_ms))
        )
        return anotados

    def test_el_aviso_dice_el_vuelto_y_se_queda_mas(self, vista, pagos, avisos, conexion) -> None:
        respuestas, llamadas = pagos
        respuestas.append((True, 5000))
        vista.agregar_por_codigo(COLA)
        vista.cobrar()
        assert llamadas == [(2290, None)]
        texto, duracion = avisos[-1]
        assert texto.endswith("Vuelto: $2.710") and duracion == venta_view._MENSAJE_VUELTO_MS
        assert len(repo_ventas.del_dia(conexion)) == 1

    def test_pago_justo_no_habla_de_vuelto(self, vista, pagos, avisos) -> None:
        pagos[0].append((True, None))
        vista.agregar_por_codigo(COLA)
        vista.cobrar()
        assert "Vuelto" not in avisos[-1][0]

    def test_cancelar_no_cobra_y_conserva_el_carrito(self, vista, pagos, conexion) -> None:
        pagos[0].append((False, None))
        vista.agregar_por_codigo(COLA)
        vista.cobrar()
        assert repo_ventas.del_dia(conexion) == []
        assert not vista.carrito.esta_vacio

    def test_reemplaza_a_la_confirmacion(self, vista, pagos, monkeypatch) -> None:
        from tienda_pos.services.preferencias import Preferencias

        def no_debe(*a, **k):
            raise AssertionError("En efectivo no se pide la otra confirmación")

        monkeypatch.setattr(dialogos, "confirmar", no_debe)
        vista.preferencias = Preferencias(confirmar_cobro=True)
        pagos[0].append((True, None))
        vista.agregar_por_codigo(COLA)
        vista.cobrar()
        assert vista.carrito.esta_vacio

    def test_aparece_aunque_la_confirmacion_este_apagada(self, vista, pagos) -> None:
        from tienda_pos.services.preferencias import Preferencias

        vista.preferencias = Preferencias(confirmar_cobro=False)
        pagos[0].append((True, None))
        vista.agregar_por_codigo(COLA)
        vista.cobrar()
        assert len(pagos[1]) == 1

    @pytest.mark.parametrize("medio", [MedioPago.DEBITO, MedioPago.CREDITO])
    def test_con_tarjeta_no_aparece(self, vista, pagos, medio) -> None:
        vista.agregar_por_codigo(COLA)
        vista.elegir_medio_pago(medio)
        vista.cobrar()
        assert pagos[1] == [] and vista.carrito.esta_vacio

    def test_una_venta_en_cero_no_pregunta(self, vista, pagos) -> None:
        # Un descuento del 100 %: no hay nada que pagar ni vuelto que dar.
        vista.agregar_por_codigo(COLA)
        vista.carrito.aplicar_descuento_monto(2290)
        vista.cobrar()
        assert pagos[1] == [] and vista.carrito.esta_vacio

    def test_al_reintentar_trae_lo_que_se_tecleo(self, vista, pagos, monkeypatch) -> None:
        respuestas, llamadas = pagos
        respuestas.extend([(True, 5000), (True, 5000)])
        original = vista._sesion.cerrar_venta

        def falla(*a, **k):
            raise ErrorDominio("La red se cayó")

        monkeypatch.setattr(vista._sesion, "cerrar_venta", falla)
        vista.agregar_por_codigo(COLA)
        vista.cobrar()
        monkeypatch.setattr(vista._sesion, "cerrar_venta", original)
        vista.cobrar()
        assert llamadas == [(2290, None), (2290, 5000)]
        assert vista.carrito.esta_vacio

    def test_la_venta_siguiente_empieza_en_blanco(self, vista, pagos) -> None:
        respuestas, llamadas = pagos
        respuestas.extend([(True, 5000), (True, None)])
        vista.agregar_por_codigo(COLA)
        vista.cobrar()
        vista.agregar_por_codigo(COLA)
        vista.cobrar()
        assert llamadas[1] == (2290, None)


# --------------------------------------------------------------------------- ventanas que se sueltan


class TestLasVentanasNoSeAcumulan:
    """Cada ventana del vuelto o del peso quedaba viva y oculta hasta cerrar el programa.

    Con el vuelto en cada venta en efectivo eran cientos por caja y por día, cada una con su
    fundido enganchado: lo que hace que una caja se ponga lenta con las horas.
    """

    @staticmethod
    def _cerrar_al_aparecer(como) -> None:
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication

        def intentar() -> None:
            ventana = QApplication.activeModalWidget()
            if ventana is None:
                QTimer.singleShot(10, intentar)
                return
            como(ventana)

        QTimer.singleShot(10, intentar)

    @staticmethod
    def _vivas(vista) -> list[str]:
        from PySide6.QtCore import QEvent
        from PySide6.QtWidgets import QApplication, QDialog

        QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        return [type(d).__name__ for d in vista.findChildren(QDialog)]

    def test_la_del_vuelto_se_destruye_al_cerrar(self, vista) -> None:
        for _ in range(5):
            self._cerrar_al_aparecer(lambda d: (d.campo.setText("5000"), d._confirmar()))
            assert dialogos.DialogoVuelto(3500, vista).pedir() == (True, 5000)
        assert self._vivas(vista) == []

    def test_la_del_peso_se_destruye_al_cerrar(self, vista) -> None:
        for _ in range(5):
            self._cerrar_al_aparecer(lambda d: (d.campo.setText("350"), d._confirmar()))
            assert dialogos.DialogoPeso("Pan batido", 2490, vista).pedir() == 350
        assert self._vivas(vista) == []

    def test_cancelar_tambien_la_suelta(self, vista) -> None:
        self._cerrar_al_aparecer(lambda d: d.reject())
        assert dialogos.DialogoVuelto(3500, vista).pedir() == (False, None)
        assert self._vivas(vista) == []
