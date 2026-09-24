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


# --------------------------------------------------------------------------- administración


class TestPinGenerado:
    def test_tiene_el_largo_configurado_y_solo_cifras(self) -> None:
        from tienda_pos.config import LONGITUD_PIN_GENERADO

        for _ in range(200):
            pin = auth.generar_pin()
            assert pin.isdigit() and len(pin) == LONGITUD_PIN_GENERADO
            auth.validar_formato_pin(pin)

    @pytest.mark.parametrize("pin", ["1111", "0000", "1234", "4321", "6789", "9876", "0123"])
    def test_descarta_los_que_cualquiera_prueba_primero(self, pin) -> None:
        assert auth._es_obvio(pin)

    @pytest.mark.parametrize("pin", ["1396", "5706", "1122", "1357", "2468", "1243"])
    def test_acepta_los_corrientes(self, pin) -> None:
        assert not auth._es_obvio(pin)

    def test_nunca_sale_un_pin_obvio(self, monkeypatch) -> None:
        # Se fuerza al azar a proponer primero los obvios: la función debe seguir probando.
        propuestas = iter("1111" "1234" "9876" "5706")
        monkeypatch.setattr(auth.secrets, "choice", lambda _cifras: next(propuestas))
        assert auth.generar_pin() == "5706"


class TestAltaDeEmpleados:
    def test_el_alta_devuelve_un_pin_que_sirve_para_entrar(self, conexion, admin) -> None:
        usuario, pin = auth.alta_usuario(conexion, admin, "Marta", Rol.CAJERO)
        assert auth.autenticar(conexion, "Marta", pin).id == usuario.id

    def test_el_pin_no_queda_en_claro_en_la_base(self, conexion, admin) -> None:
        _, pin = auth.alta_usuario(conexion, admin, "Marta", Rol.CAJERO)
        fila = conexion.execute("SELECT pin_hash FROM usuario WHERE nombre = 'Marta'").fetchone()
        assert pin not in fila["pin_hash"]

    def test_un_cajero_no_puede_dar_de_alta(self, conexion, cajero) -> None:
        with pytest.raises(PermisoDenegado):
            auth.alta_usuario(conexion, cajero, "Marta", Rol.CAJERO)

    def test_sin_sesion_no_se_puede_dar_de_alta(self, conexion) -> None:
        with pytest.raises(PermisoDenegado):
            auth.alta_usuario(conexion, None, "Marta", Rol.CAJERO)

    def test_un_nombre_repetido_da_un_error_legible(self, conexion, admin) -> None:
        # Sin traducir, subiría "UNIQUE constraint failed: usuario.nombre" hasta la pantalla.
        auth.alta_usuario(conexion, admin, "Marta", Rol.CAJERO)
        with pytest.raises(DatosInvalidos, match="Ya existe un usuario llamado Marta"):
            auth.alta_usuario(conexion, admin, "Marta", Rol.CAJERO)

    def test_un_nombre_de_alguien_de_baja_sugiere_reactivarlo(self, conexion, admin) -> None:
        # El caso de volver a contratar a quien ya trabajó aquí.
        marta, _ = auth.alta_usuario(conexion, admin, "Marta", Rol.CAJERO)
        auth.desactivar_usuario(conexion, admin, marta.id)
        with pytest.raises(DatosInvalidos, match="Reactívelo"):
            auth.alta_usuario(conexion, admin, "Marta", Rol.CAJERO)

    def test_un_nombre_vacio_se_rechaza(self, conexion, admin) -> None:
        with pytest.raises(DatosInvalidos):
            auth.alta_usuario(conexion, admin, "   ", Rol.CAJERO)


class TestNuevoPin:
    def test_el_pin_nuevo_sirve_y_el_viejo_no(self, conexion, admin) -> None:
        marta, viejo = auth.alta_usuario(conexion, admin, "Marta", Rol.CAJERO)
        nuevo = auth.reiniciar_pin(conexion, admin, marta.id)
        assert auth.autenticar(conexion, "Marta", nuevo).id == marta.id
        if nuevo != viejo:  # uno entre diez mil: el azar puede repetir
            with pytest.raises(CredencialesInvalidas):
                auth.autenticar(conexion, "Marta", viejo)

    def test_un_cajero_no_puede_cambiar_pines(self, conexion, admin, cajero) -> None:
        with pytest.raises(PermisoDenegado):
            auth.reiniciar_pin(conexion, cajero, admin.id)

    def test_no_se_le_da_pin_a_alguien_de_baja(self, conexion, admin) -> None:
        marta, _ = auth.alta_usuario(conexion, admin, "Marta", Rol.CAJERO)
        auth.desactivar_usuario(conexion, admin, marta.id)
        with pytest.raises(DatosInvalidos, match="dado de baja"):
            auth.reiniciar_pin(conexion, admin, marta.id)

    def test_un_usuario_que_no_existe(self, conexion, admin) -> None:
        with pytest.raises(DatosInvalidos, match="ya no existe"):
            auth.reiniciar_pin(conexion, admin, 9999)


class TestBajaYReactivacion:
    def test_quien_se_da_de_baja_no_puede_entrar_ni_aparece(self, conexion, admin) -> None:
        marta, pin = auth.alta_usuario(conexion, admin, "Marta", Rol.CAJERO)
        auth.desactivar_usuario(conexion, admin, marta.id)
        with pytest.raises(CredencialesInvalidas):
            auth.autenticar(conexion, "Marta", pin)
        assert "Marta" not in [u.nombre for u in auth.listar_usuarios(conexion)]

    def test_la_baja_no_borra_sus_ventas(self, conexion, admin, productos) -> None:
        from tienda_pos.services import venta as servicio_venta

        marta, _ = auth.alta_usuario(conexion, admin, "Marta", Rol.CAJERO)
        carrito = servicio_venta.Carrito()
        carrito.agregar(productos["leche"])
        venta = servicio_venta.cerrar_venta(conexion, carrito, marta)
        auth.desactivar_usuario(conexion, admin, marta.id)

        fila = conexion.execute(
            "SELECT u.nombre FROM venta v JOIN usuario u ON u.id = v.usuario_id WHERE v.id = ?",
            (venta.id,),
        ).fetchone()
        assert fila["nombre"] == "Marta"

    def test_nadie_se_da_de_baja_a_si_mismo(self, conexion, admin) -> None:
        auth.alta_usuario(conexion, admin, "Otro admin", Rol.ADMIN)
        with pytest.raises(DatosInvalidos, match="sí mismo"):
            auth.desactivar_usuario(conexion, admin, admin.id)

    def test_no_se_da_de_baja_al_ultimo_administrador(self, conexion, admin) -> None:
        segundo, _ = auth.alta_usuario(conexion, admin, "Segundo", Rol.ADMIN)
        auth.desactivar_usuario(conexion, admin, segundo.id)  # quedan dos -> se puede
        with pytest.raises(DatosInvalidos, match="único administrador"):
            auth.desactivar_usuario(conexion, segundo, admin.id)
        assert auth.autenticar(conexion, "Administrador", "1234").activo

    def test_dar_de_baja_dos_veces_no_falla(self, conexion, admin) -> None:
        marta, _ = auth.alta_usuario(conexion, admin, "Marta", Rol.CAJERO)
        auth.desactivar_usuario(conexion, admin, marta.id)
        auth.desactivar_usuario(conexion, admin, marta.id)

    def test_reactivar_da_un_pin_nuevo_que_sirve(self, conexion, admin) -> None:
        marta, _ = auth.alta_usuario(conexion, admin, "Marta", Rol.CAJERO)
        auth.desactivar_usuario(conexion, admin, marta.id)
        pin = auth.reactivar_usuario(conexion, admin, marta.id)
        assert auth.autenticar(conexion, "Marta", pin).activo

    def test_un_cajero_no_puede_dar_de_baja_ni_reactivar(self, conexion, admin, cajero) -> None:
        marta, _ = auth.alta_usuario(conexion, admin, "Marta", Rol.CAJERO)
        with pytest.raises(PermisoDenegado):
            auth.desactivar_usuario(conexion, cajero, marta.id)
        with pytest.raises(PermisoDenegado):
            auth.reactivar_usuario(conexion, cajero, marta.id)

    def test_el_listado_de_administracion_incluye_a_los_de_baja(self, conexion, admin) -> None:
        marta, _ = auth.alta_usuario(conexion, admin, "Marta", Rol.CAJERO)
        auth.desactivar_usuario(conexion, admin, marta.id)
        activos = auth.listar_para_administrar(conexion, admin)
        todos = auth.listar_para_administrar(conexion, admin, incluir_inactivos=True)
        assert "Marta" not in [u.nombre for u in activos]
        assert "Marta" in [u.nombre for u in todos]

    def test_un_cajero_no_ve_el_listado_de_administracion(self, conexion, cajero) -> None:
        with pytest.raises(PermisoDenegado):
            auth.listar_para_administrar(conexion, cajero)


class TestSinSesion:
    """Los dos caminos para tener un administrador sin haber entrado como uno."""

    def test_el_primer_administrador_en_una_base_vacia(self, conexion) -> None:
        assert not auth.hay_usuarios(conexion)
        usuario, pin = auth.crear_primer_administrador(conexion, "Dueño")
        assert usuario.es_admin
        assert auth.autenticar(conexion, "Dueño", pin).id == usuario.id
        assert auth.hay_usuarios(conexion)

    def test_no_hay_primer_administrador_si_ya_hay_usuarios(self, conexion, cajero) -> None:
        # Si no se negara, sería una forma de crear administradores sin permiso.
        with pytest.raises(PermisoDenegado):
            auth.crear_primer_administrador(conexion, "Intruso")

    def test_un_usuario_de_baja_tambien_cuenta_como_usuario(self, conexion, admin) -> None:
        marta, _ = auth.alta_usuario(conexion, admin, "Marta", Rol.CAJERO)
        auth.desactivar_usuario(conexion, admin, marta.id)
        with pytest.raises(PermisoDenegado):
            auth.crear_primer_administrador(conexion, "Intruso")

    def test_el_rescate_restablece_a_un_administrador_existente(self, conexion, admin) -> None:
        usuario, pin = auth.rescatar_administrador(conexion, "Administrador")
        assert usuario.id == admin.id
        assert auth.autenticar(conexion, "Administrador", pin).es_admin
        if pin != "1234":
            with pytest.raises(CredencialesInvalidas):
                auth.autenticar(conexion, "Administrador", "1234")

    def test_el_rescate_reactiva_a_un_administrador_de_baja(self, conexion, admin) -> None:
        segundo, _ = auth.alta_usuario(conexion, admin, "Segundo", Rol.ADMIN)
        auth.desactivar_usuario(conexion, admin, segundo.id)
        _, pin = auth.rescatar_administrador(conexion, "Segundo")
        assert auth.autenticar(conexion, "Segundo", pin).activo

    def test_el_rescate_crea_al_administrador_si_no_existe(self, conexion, cajero) -> None:
        usuario, pin = auth.rescatar_administrador(conexion, "Dueño")
        assert usuario.es_admin
        assert auth.autenticar(conexion, "Dueño", pin).es_admin

    def test_el_rescate_no_asciende_a_un_cajero(self, conexion, cajero) -> None:
        with pytest.raises(DatosInvalidos, match="cajero"):
            auth.rescatar_administrador(conexion, "Cajero")
        assert not auth.autenticar(conexion, "Cajero", "1111").es_admin

    def test_el_rescate_queda_en_el_registro_pero_el_pin_no(self, conexion, admin, caplog) -> None:
        import logging

        with caplog.at_level(logging.WARNING, logger="tienda_pos.services.auth"):
            _, pin = auth.rescatar_administrador(conexion, "Administrador")
        assert "RESCATE DE ADMINISTRADOR" in caplog.text
        assert "Administrador" in caplog.text
        assert pin not in caplog.text

    def test_ningun_camino_sin_sesion_se_puede_pedir_por_la_red(self) -> None:
        # Por la red serían una puerta abierta para cualquiera conectado al mismo cable.
        from tienda_pos.red import servidor
        from tienda_pos.red.sesion import Sesion

        for nombre in ("crear_primer_administrador", "rescatar_administrador"):
            assert nombre not in servidor._OPERACIONES
            assert not hasattr(Sesion, nombre)
