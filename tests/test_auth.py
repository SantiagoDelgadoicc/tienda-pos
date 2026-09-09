"""Pruebas de autenticación y permisos."""

from __future__ import annotations

import pytest

from tienda_pos.db.connection import transaccion
from tienda_pos.domain.errors import CredencialesInvalidas, DatosInvalidos, PermisoDenegado
from tienda_pos.domain.models import Rol
from tienda_pos.services import auth


class TestCreacionDeUsuarios:
    def test_crea_un_usuario_con_su_rol(self, conexion) -> None:
        with transaccion(conexion):
            usuario = auth.crear_usuario(conexion, "Ana", Rol.ADMIN, "4321")
        assert usuario.id is not None
        assert usuario.es_admin

    def test_el_pin_nunca_se_guarda_en_claro(self, conexion) -> None:
        with transaccion(conexion):
            auth.crear_usuario(conexion, "Ana", Rol.CAJERO, "4321")

        fila = conexion.execute("SELECT pin_hash, salt FROM usuario WHERE nombre = 'Ana'").fetchone()
        assert "4321" not in fila["pin_hash"]
        assert len(fila["pin_hash"]) == 64  # 32 bytes en hexadecimal
        assert len(fila["salt"]) == 32

    def test_dos_usuarios_con_el_mismo_pin_tienen_hashes_distintos(self, conexion) -> None:
        # Es lo que consigue la sal: que ver un hash no revele quién más usa el mismo PIN.
        with transaccion(conexion):
            auth.crear_usuario(conexion, "Ana", Rol.CAJERO, "1234")
            auth.crear_usuario(conexion, "Beto", Rol.CAJERO, "1234")

        hashes = [f["pin_hash"] for f in conexion.execute("SELECT pin_hash FROM usuario")]
        assert hashes[0] != hashes[1]

    @pytest.mark.parametrize("pin", ["", "123", "abcd", "12a4", "123456789"])
    def test_rechaza_pines_invalidos(self, conexion, pin) -> None:
        with pytest.raises(DatosInvalidos), transaccion(conexion):
            auth.crear_usuario(conexion, "Ana", Rol.CAJERO, pin)

    def test_rechaza_nombre_vacio(self, conexion) -> None:
        with pytest.raises(DatosInvalidos), transaccion(conexion):
            auth.crear_usuario(conexion, "   ", Rol.CAJERO, "1234")


class TestAutenticacion:
    def test_entra_con_el_pin_correcto(self, conexion, admin) -> None:
        usuario = auth.autenticar(conexion, "Administrador", "1234")
        assert usuario.nombre == "Administrador"
        assert usuario.es_admin

    def test_rechaza_el_pin_incorrecto(self, conexion, admin) -> None:
        with pytest.raises(CredencialesInvalidas):
            auth.autenticar(conexion, "Administrador", "9999")

    def test_rechaza_un_usuario_inexistente(self, conexion) -> None:
        with pytest.raises(CredencialesInvalidas):
            auth.autenticar(conexion, "Fantasma", "1234")

    def test_el_mensaje_no_revela_cual_de_los_dos_datos_falla(self, conexion, admin) -> None:
        # Decir "ese usuario no existe" le regala información a quien esté probando.
        with pytest.raises(CredencialesInvalidas) as sin_usuario:
            auth.autenticar(conexion, "Fantasma", "1234")
        with pytest.raises(CredencialesInvalidas) as mal_pin:
            auth.autenticar(conexion, "Administrador", "9999")
        assert str(sin_usuario.value) == str(mal_pin.value)

    def test_cambiar_el_pin_invalida_el_anterior(self, conexion, admin) -> None:
        with transaccion(conexion):
            auth.cambiar_pin(conexion, admin, "5678")

        assert auth.autenticar(conexion, "Administrador", "5678").id == admin.id
        with pytest.raises(CredencialesInvalidas):
            auth.autenticar(conexion, "Administrador", "1234")


class TestPermisos:
    def test_el_admin_pasa(self, admin) -> None:
        auth.exigir_admin(admin, "hacer algo")  # no debe lanzar

    def test_el_cajero_no_pasa(self, cajero) -> None:
        with pytest.raises(PermisoDenegado) as error:
            auth.exigir_admin(cajero, "cambiar precios")
        assert "cambiar precios" in str(error.value)

    def test_sin_sesion_no_se_pasa(self) -> None:
        with pytest.raises(PermisoDenegado):
            auth.exigir_admin(None, "cambiar precios")
