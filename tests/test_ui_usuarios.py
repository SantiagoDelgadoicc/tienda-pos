"""Pruebas de la fase 15: la pantalla de usuarios, la sesión obligatoria y el rescate.

Se apoyan en las fixtures `ventana` y `como_admin` de conftest.py. Los diálogos que piden un
dato o enseñan un PIN se sustituyen por dobles que responden solos y guardan lo que vieron.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="La interfaz requiere PySide6")

from tienda_pos import app as modulo_app  # noqa: E402
from tienda_pos.db.connection import transaccion  # noqa: E402
from tienda_pos.db.inicio import abrir_base_datos  # noqa: E402
from tienda_pos.db.seed import codigo_demo  # noqa: E402
from tienda_pos.domain.models import Rol  # noqa: E402
from tienda_pos.red.sesion import SesionLocal  # noqa: E402
from tienda_pos.repositories import ventas as repo_ventas  # noqa: E402
from tienda_pos.services import auth  # noqa: E402
from tienda_pos.ui import dialogos, usuarios_view  # noqa: E402


@pytest.fixture
def pines(monkeypatch) -> list[tuple[str, str]]:
    """Recoge cada PIN que la pantalla enseña, como (nombre del usuario, PIN)."""
    vistos: list[tuple[str, str]] = []
    monkeypatch.setattr(
        usuarios_view.DialogoPin,
        "mostrar",
        staticmethod(lambda _titulo, usuario, pin, _padre=None: vistos.append((usuario.nombre, pin))),
    )
    return vistos


@pytest.fixture
def errores(monkeypatch) -> list[str]:
    """Recoge los mensajes de error en lugar de mostrarlos."""
    vistos: list[str] = []
    monkeypatch.setattr(dialogos, "mostrar_error", lambda _padre, mensaje, *a, **k: vistos.append(mensaje))
    return vistos


def _alta_desde_la_pantalla(monkeypatch, vista, nombre: str, rol: Rol = Rol.CAJERO) -> None:
    class _Formulario:
        def __init__(self, _padre=None) -> None:
            self.nombre, self.rol = nombre, rol

        def exec(self) -> bool:
            return True

    monkeypatch.setattr(usuarios_view, "DialogoUsuario", _Formulario)
    vista.crear()


def _fila_de(vista, nombre: str) -> int:
    return next(i for i, u in enumerate(vista._usuarios) if u.nombre == nombre)


class TestPantallaDeUsuarios:
    def test_el_administrador_entra_y_ve_a_los_usuarios(self, como_admin) -> None:
        ventana = como_admin
        ventana.mostrar_usuarios()
        assert ventana.pantallas.currentWidget() is ventana.vista_usuarios
        assert {u.nombre for u in ventana.vista_usuarios._usuarios} >= {"Administrador", "Cajero"}

    def test_un_cajero_sin_autorizacion_no_entra(self, ventana, monkeypatch) -> None:
        from tienda_pos.ui import main_window

        monkeypatch.setattr(main_window.DialogoLogin, "pedir", staticmethod(lambda *a, **k: None))
        ventana.mostrar_usuarios()
        assert ventana.pantallas.currentWidget() is ventana.vista_venta

    def test_quien_opera_aparece_marcado(self, como_admin) -> None:
        como_admin.mostrar_usuarios()
        tabla = como_admin.vista_usuarios.tabla
        nombres = [tabla.item(f, 0).text() for f in range(tabla.rowCount())]
        assert "Administrador  (usted)" in nombres

    def test_dar_de_alta_enseña_un_pin_que_sirve(self, como_admin, conexion, monkeypatch, pines) -> None:
        como_admin.mostrar_usuarios()
        _alta_desde_la_pantalla(monkeypatch, como_admin.vista_usuarios, "Marta")

        assert [nombre for nombre, _ in pines] == ["Marta"]
        assert auth.autenticar(conexion, "Marta", pines[0][1]).nombre == "Marta"
        assert "Marta" in [u.nombre for u in como_admin.vista_usuarios._usuarios]

    def test_un_nombre_repetido_se_explica_y_no_enseña_pin(
        self, como_admin, monkeypatch, pines, errores
    ) -> None:
        como_admin.mostrar_usuarios()
        _alta_desde_la_pantalla(monkeypatch, como_admin.vista_usuarios, "Cajero")
        assert pines == []
        assert errores == ["Ya existe un usuario llamado Cajero."]

    def test_los_botones_siguen_a_la_fila_elegida(self, como_admin) -> None:
        como_admin.mostrar_usuarios()
        vista = como_admin.vista_usuarios
        cajero_id = vista._usuarios[_fila_de(vista, "Cajero")].id

        vista.tabla.clearSelection()
        assert not vista.boton_pin.isEnabled() and not vista.boton_baja.isEnabled()

        vista.seleccionar(cajero_id)
        assert vista.boton_pin.isEnabled() and vista.boton_baja.isEnabled()
        assert not vista.boton_reactivar.isEnabled()

        vista.dar_de_baja()
        vista.casilla_bajas.setChecked(True)
        vista.seleccionar(cajero_id)
        assert vista.boton_reactivar.isEnabled()
        assert not vista.boton_pin.isEnabled() and not vista.boton_baja.isEnabled()

    def test_dar_de_baja_la_saca_de_la_lista_y_del_acceso(self, como_admin, conexion) -> None:
        como_admin.mostrar_usuarios()
        vista = como_admin.vista_usuarios
        vista.seleccionar(vista._usuarios[_fila_de(vista, "Cajero")].id)
        vista.dar_de_baja()

        assert "Cajero" not in [u.nombre for u in vista._usuarios]
        assert "Cajero" not in [u.nombre for u in auth.listar_usuarios(conexion)]
        vista.casilla_bajas.setChecked(True)
        assert not vista._usuarios[_fila_de(vista, "Cajero")].activo

    def test_nadie_se_da_de_baja_a_si_mismo_desde_la_pantalla(self, como_admin, errores) -> None:
        como_admin.mostrar_usuarios()
        vista = como_admin.vista_usuarios
        vista.seleccionar(vista._usuarios[_fila_de(vista, "Administrador")].id)
        vista.dar_de_baja()
        assert errores == ["No puede darse de baja a sí mismo."]

    def test_reactivar_enseña_un_pin_nuevo(self, como_admin, conexion, pines) -> None:
        como_admin.mostrar_usuarios()
        vista = como_admin.vista_usuarios
        cajero_id = vista._usuarios[_fila_de(vista, "Cajero")].id
        vista.seleccionar(cajero_id)
        vista.dar_de_baja()
        vista.casilla_bajas.setChecked(True)
        vista.seleccionar(cajero_id)
        vista.reactivar()

        assert [nombre for nombre, _ in pines] == ["Cajero"]
        assert auth.autenticar(conexion, "Cajero", pines[0][1]).activo

    def test_pin_nuevo_enseña_uno_que_sirve(self, como_admin, conexion, pines) -> None:
        como_admin.mostrar_usuarios()
        vista = como_admin.vista_usuarios
        vista.seleccionar(vista._usuarios[_fila_de(vista, "Cajero")].id)
        vista.nuevo_pin()
        assert auth.autenticar(conexion, "Cajero", pines[0][1]).nombre == "Cajero"

    def test_sin_seleccion_se_avisa_y_no_se_rompe(self, como_admin, errores) -> None:
        como_admin.mostrar_usuarios()
        vista = como_admin.vista_usuarios
        vista.tabla.clearSelection()
        vista.tabla.setCurrentCell(-1, -1)
        for accion in (vista.nuevo_pin, vista.reactivar, vista.dar_de_baja):
            accion()
        assert errores == ["Seleccione primero un usuario de la lista."] * 3


class TestCobroSinUsuario:
    def test_sin_usuario_no_se_cobra_y_el_carrito_queda(self, ventana, conexion) -> None:
        venta = ventana.vista_venta
        venta.agregar_por_codigo(codigo_demo(0))
        ventana.establecer_usuario(None)
        venta.cobrar()

        assert repo_ventas.del_dia(conexion) == []
        assert not venta.carrito.esta_vacio


class TestArranqueSinUsuarios:
    """Antes, una base sin usuarios dejaba entrar sin sesión. Ahora nunca."""

    def test_una_base_vacia_crea_al_primer_administrador_y_pide_el_acceso(self, app, monkeypatch) -> None:
        conexion = abrir_base_datos(":memory:", con_datos_demo=False)
        sesion = SesionLocal(conexion)
        vistos: list[str] = []

        class _Formulario:
            nombre = "Dueño"

            def exec(self) -> bool:
                return True

            def fallar(self, mensaje: str) -> None:  # pragma: no cover - no debe fallar
                raise AssertionError(mensaje)

        from tienda_pos.ui import login_dialog

        monkeypatch.setattr(usuarios_view, "DialogoPrimerAdministrador", _Formulario)
        monkeypatch.setattr(
            usuarios_view.DialogoPin,
            "mostrar",
            staticmethod(lambda _t, usuario, pin, _p=None: vistos.append(pin)),
        )
        # El acceso de después se hace con el PIN que se acaba de enseñar: si no se anotó, no
        # se entra. Es lo que confirma que no se va a perder.
        monkeypatch.setattr(
            login_dialog.DialogoLogin,
            "pedir",
            staticmethod(lambda s, *a, **k: s.autenticar("Dueño", vistos[0])),
        )

        usuario = modulo_app._iniciar_sesion(sesion, conexion)
        assert usuario.nombre == "Dueño" and usuario.es_admin

    def test_cancelar_el_primer_administrador_no_deja_entrar(self, app, monkeypatch) -> None:
        conexion = abrir_base_datos(":memory:", con_datos_demo=False)

        class _Cancela:
            def exec(self) -> bool:
                return False

        monkeypatch.setattr(usuarios_view, "DialogoPrimerAdministrador", _Cancela)
        assert modulo_app._iniciar_sesion(SesionLocal(conexion), conexion) is modulo_app._CANCELADO
        assert not auth.hay_usuarios(conexion)

    def test_usuarios_todos_de_baja_no_deja_entrar_ni_crea_otro(self, app, monkeypatch) -> None:
        conexion = abrir_base_datos(":memory:", con_datos_demo=False)
        with transaccion(conexion):
            viejo = auth.crear_usuario(conexion, "Viejo", Rol.CAJERO, "5706")
        conexion.execute("UPDATE usuario SET activo = 0 WHERE id = ?", (viejo.id,))
        avisos: list[str] = []
        monkeypatch.setattr(modulo_app.QMessageBox, "critical", lambda _p, _t, texto: avisos.append(texto))

        assert modulo_app._iniciar_sesion(SesionLocal(conexion), conexion) is modulo_app._CANCELADO
        assert "--reiniciar-admin" in avisos[0]
        assert auth.listar_usuarios(conexion) == []

    def test_la_caja_secundaria_sin_usuarios_manda_a_crearlos_en_la_principal(
        self, app, monkeypatch
    ) -> None:
        # Sin conexión propia es la caja secundaria: crear un administrador desde aquí sería
        # hacerlo por la red, que es justo lo que no se permite.
        sesion = SesionLocal(abrir_base_datos(":memory:", con_datos_demo=False))
        avisos: list[str] = []
        monkeypatch.setattr(modulo_app.QMessageBox, "critical", lambda _p, _t, texto: avisos.append(texto))

        assert modulo_app._iniciar_sesion(sesion, None) is modulo_app._CANCELADO
        assert "caja principal" in avisos[0]


class TestRescateDeAdministrador:
    @pytest.fixture
    def datos(self, tmp_path, monkeypatch):
        from tienda_pos.utils import logging_setup

        monkeypatch.setenv("TIENDA_POS_HOME", str(tmp_path / "datos"))
        logging_setup.reiniciar_para_pruebas()
        yield tmp_path / "datos"
        logging_setup.reiniciar_para_pruebas()

    def test_recupera_al_administrador_y_enseña_un_pin_que_sirve(self, app, datos, monkeypatch) -> None:
        from PySide6.QtWidgets import QInputDialog

        vistos: list[str] = []
        monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("Dueño", True)))
        monkeypatch.setattr(
            usuarios_view.DialogoPin,
            "mostrar",
            staticmethod(lambda _t, usuario, pin, _p=None: vistos.append(pin)),
        )

        assert modulo_app.reiniciar_admin() == 0
        conexion = abrir_base_datos(con_datos_demo=False)
        try:
            assert auth.autenticar(conexion, "Dueño", vistos[0]).es_admin
        finally:
            conexion.close()

    def test_en_la_caja_secundaria_se_niega_sin_tocar_nada(self, app, datos, monkeypatch) -> None:
        from tienda_pos.red import config_red
        from tienda_pos.red.config_red import ConfiguracionRed, Modo

        avisos: list[str] = []
        monkeypatch.setattr(config_red, "cargar", lambda *a, **k: ConfiguracionRed(modo=Modo.CAJA))
        monkeypatch.setattr(modulo_app.QMessageBox, "warning", lambda _p, _t, texto: avisos.append(texto))

        assert modulo_app.reiniciar_admin() == 1
        assert "caja principal" in avisos[0]
        assert not any(datos.glob("*.db"))

    def test_cancelar_no_toca_la_base(self, app, datos, monkeypatch) -> None:
        from PySide6.QtWidgets import QInputDialog

        monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("", False)))
        assert modulo_app.reiniciar_admin() == 0
        assert not any(datos.glob("*.db"))
