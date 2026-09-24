"""Pruebas de la capa de red: una caja secundaria hablando con un servidor de verdad.

Levantan un `ServidorTienda` real en un puerto libre de esta máquina y le hablan con una
`SesionRemota`, que es exactamente lo que ocurre entre las dos cajas de la tienda. Lo que se
comprueba es que cada operación **cruce la red entera** —serializar, viajar, deserializar— y
que los errores lleguen al otro lado con su tipo y su mensaje.

Empiezan con la administración de usuarios de la fase 15. Las pruebas de concurrencia de la
fase 13, que siguen siendo manuales, tienen aquí su sitio cuando se traigan.
"""

from __future__ import annotations

import socket

import pytest

from tienda_pos.db.connection import transaccion
from tienda_pos.db.inicio import abrir_base_datos
from tienda_pos.domain.errors import CredencialesInvalidas, DatosInvalidos, PermisoDenegado
from tienda_pos.domain.models import Rol
from tienda_pos.red import protocolo
from tienda_pos.red.cliente import SesionRemota, VersionIncompatible
from tienda_pos.red.servidor import ServidorTienda
from tienda_pos.red.sesion import SesionLocal
from tienda_pos.services import auth


def _puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def red():
    """Un servidor con un administrador y una caja secundaria conectada a él.

    Devuelve `(remota, local, admin)`: la sesión de la caja secundaria, la del propio servidor
    y el administrador, con su PIN `1234`.
    """
    conexion = abrir_base_datos(":memory:", con_datos_demo=False, compartida_entre_hilos=True)
    with transaccion(conexion):
        admin = auth.crear_usuario(conexion, "Administrador", Rol.ADMIN, "1234")
    local = SesionLocal(conexion)
    puerto = _puerto_libre()
    with ServidorTienda(local, host="127.0.0.1", puerto=puerto):
        yield SesionRemota("127.0.0.1", puerto), local, admin
    conexion.close()


class TestUsuariosPorLaRed:
    def test_alta_en_la_secundaria_y_el_pin_sirve_en_las_dos(self, red) -> None:
        remota, local, admin = red
        marta, pin = remota.alta_usuario(admin, "Marta", Rol.CAJERO)

        assert marta.nombre == "Marta" and marta.rol is Rol.CAJERO
        assert remota.autenticar("Marta", pin).id == marta.id
        assert local.autenticar("Marta", pin).id == marta.id

    def test_el_listado_de_administracion_cruza_la_red(self, red) -> None:
        remota, _, admin = red
        marta, _ = remota.alta_usuario(admin, "Marta", Rol.CAJERO)
        remota.desactivar_usuario(admin, marta.id)

        activos = remota.listar_para_administrar(admin)
        todos = remota.listar_para_administrar(admin, incluir_inactivos=True)
        assert [u.nombre for u in activos] == ["Administrador"]
        assert {u.nombre for u in todos} == {"Administrador", "Marta"}
        assert not next(u for u in todos if u.nombre == "Marta").activo

    def test_nuevo_pin_y_reactivar_devuelven_un_pin_que_sirve(self, red) -> None:
        remota, _, admin = red
        marta, _ = remota.alta_usuario(admin, "Marta", Rol.CAJERO)

        pin = remota.reiniciar_pin(admin, marta.id)
        assert remota.autenticar("Marta", pin).id == marta.id

        remota.desactivar_usuario(admin, marta.id)
        with pytest.raises(CredencialesInvalidas):
            remota.autenticar("Marta", pin)
        pin = remota.reactivar_usuario(admin, marta.id)
        assert remota.autenticar("Marta", pin).id == marta.id

    def test_los_errores_llegan_con_su_tipo_y_su_mensaje(self, red) -> None:
        # En modo red la pantalla está en la otra caja: solo le llega esto.
        remota, _, admin = red
        remota.alta_usuario(admin, "Marta", Rol.CAJERO)
        with pytest.raises(DatosInvalidos, match="Ya existe un usuario llamado Marta"):
            remota.alta_usuario(admin, "Marta", Rol.CAJERO)
        with pytest.raises(DatosInvalidos, match="único administrador"):
            segundo, _ = remota.alta_usuario(admin, "Segundo", Rol.ADMIN)
            remota.desactivar_usuario(admin, segundo.id)
            remota.desactivar_usuario(segundo, admin.id)

    def test_un_cajero_no_administra_usuarios_desde_la_secundaria(self, red) -> None:
        remota, _, admin = red
        _, pin = remota.alta_usuario(admin, "Marta", Rol.CAJERO)
        marta = remota.autenticar("Marta", pin)
        with pytest.raises(PermisoDenegado):
            remota.alta_usuario(marta, "Intruso", Rol.ADMIN)
        with pytest.raises(PermisoDenegado):
            remota.listar_para_administrar(marta)


class TestVersionDelProtocolo:
    def test_una_caja_con_otra_version_se_detecta_al_conectar(self, red, monkeypatch) -> None:
        # Es lo que convierte una actualización a medias en un aviso al arrancar, y no en un
        # "Operación desconocida" en mitad de la pantalla de usuarios.
        # Cliente y servidor corren aquí en el mismo proceso y comparten el módulo, así que
        # no basta con cambiar la constante: se hace que el servidor **anuncie** la versión
        # anterior, que es lo que pasa en la tienda si solo se actualizó la caja secundaria.
        from tienda_pos.red import servidor

        remota, _, _ = red
        remota.comprobar_compatibilidad()

        anunciar_de_verdad = servidor._Manejador._estado

        def como_un_servidor_viejo(manejador):
            estado = anunciar_de_verdad(manejador)
            estado["version_protocolo"] = protocolo.VERSION_PROTOCOLO - 1
            return estado

        monkeypatch.setattr(servidor._Manejador, "_estado", como_un_servidor_viejo)
        with pytest.raises(VersionIncompatible):
            remota.comprobar_compatibilidad()
