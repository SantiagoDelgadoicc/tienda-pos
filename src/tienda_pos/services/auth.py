"""Autenticación por PIN y control de permisos.

El PIN se guarda con scrypt y una sal distinta por usuario, usando solo la biblioteca
estándar. Nunca se almacena ni se registra en el log el PIN en claro.

Sobre el alcance real de esta protección, para no engañarnos: un PIN de cuatro dígitos
protege frente a un empleado que curiosea, no frente a alguien con acceso físico al disco.
Es la medida proporcionada a un prototipo monopuesto. Ver D-007 en docs/DECISIONES.md.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import sqlite3

from ..config import LONGITUD_PIN_GENERADO, PIN_LONGITUD_MAX, PIN_LONGITUD_MIN
from ..db.connection import transaccion
from ..domain.errors import CredencialesInvalidas, DatosInvalidos, PermisoDenegado
from ..domain.models import Rol, Usuario
from ..repositories import usuarios as repo_usuarios

# Parámetros de scrypt. Con estos valores, verificar un PIN tarda unas décimas de segundo:
# imperceptible para quien entra a la caja, y costosísimo para quien quiera probar los diez
# mil PIN posibles por fuerza bruta.
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_LONGITUD_CLAVE = 32
_LONGITUD_SAL = 16

_logger = logging.getLogger(__name__)


def _hashear(pin: str, sal: bytes) -> str:
    clave = hashlib.scrypt(
        pin.encode("utf-8"), salt=sal, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=_LONGITUD_CLAVE
    )
    return clave.hex()


def validar_formato_pin(pin: str) -> None:
    """Comprueba que el PIN sea numérico y de longitud razonable.

    Raises:
        DatosInvalidos: con un mensaje ya redactado para mostrar en pantalla.
    """
    if not pin or not pin.isdigit():
        raise DatosInvalidos("El PIN debe contener solo números.")
    if not PIN_LONGITUD_MIN <= len(pin) <= PIN_LONGITUD_MAX:
        raise DatosInvalidos(
            f"El PIN debe tener entre {PIN_LONGITUD_MIN} y {PIN_LONGITUD_MAX} dígitos."
        )


def listar_usuarios(conexion: sqlite3.Connection) -> list[Usuario]:
    """Usuarios activos, para poblar el desplegable del inicio de sesión.

    No devuelve ni el hash ni la sal: `repo_usuarios.listar` ya construye `Usuario` sin las
    credenciales. Importa porque esta lista viaja por la red hasta la caja secundaria (D-015).
    """
    return repo_usuarios.listar(conexion)


def crear_usuario(conexion: sqlite3.Connection, nombre: str, rol: Rol, pin: str) -> Usuario:
    """Da de alta un usuario con su PIN. Debe llamarse dentro de una transacción."""
    nombre = nombre.strip()
    if not nombre:
        raise DatosInvalidos("El nombre del usuario no puede estar vacío.")
    validar_formato_pin(pin)

    sal = secrets.token_bytes(_LONGITUD_SAL)
    return repo_usuarios.crear(conexion, nombre, rol, _hashear(pin, sal), sal.hex())


def autenticar(conexion: sqlite3.Connection, nombre: str, pin: str) -> Usuario:
    """Verifica el PIN y devuelve el usuario.

    Si el usuario no existe se calcula igualmente un hash descartable. Sin eso, la respuesta
    sería visiblemente más rápida para un nombre inexistente que para uno real, lo que
    permitiría averiguar qué usuarios existen simplemente midiendo el tiempo.

    Raises:
        CredencialesInvalidas: tanto si el usuario no existe como si el PIN es incorrecto.
            El mensaje es el mismo a propósito: decir cuál de las dos cosas falló es
            regalarle información a quien esté probando.
    """
    credenciales = repo_usuarios.obtener_credenciales(conexion, nombre.strip())
    if credenciales is None:
        _hashear(pin, secrets.token_bytes(_LONGITUD_SAL))
        raise CredencialesInvalidas()

    pin_hash, sal_hex = credenciales
    calculado = _hashear(pin, bytes.fromhex(sal_hex))
    # compare_digest tarda lo mismo acierte o falle, para no filtrar información por tiempo.
    if not hmac.compare_digest(calculado, pin_hash):
        raise CredencialesInvalidas()

    usuario = repo_usuarios.obtener_por_nombre(conexion, nombre.strip())
    if usuario is None:  # pragma: no cover - solo si el usuario se desactiva a mitad del login
        raise CredencialesInvalidas()
    return usuario


def cambiar_pin(conexion: sqlite3.Connection, usuario: Usuario, pin_nuevo: str) -> None:
    """Cambia el PIN de un usuario. Debe llamarse dentro de una transacción."""
    validar_formato_pin(pin_nuevo)
    sal = secrets.token_bytes(_LONGITUD_SAL)
    assert usuario.id is not None
    repo_usuarios.actualizar_pin(conexion, usuario.id, _hashear(pin_nuevo, sal), sal.hex())


def exigir_admin(usuario: Usuario | None, accion: str) -> None:
    """Corta la ejecución si el usuario no es administrador.

    La comprobación vive en la capa de servicios y no en la interfaz: ocultar un botón no es
    control de acceso, solo es cortesía visual.

    Raises:
        PermisoDenegado
    """
    if usuario is None or not usuario.es_admin:
        raise PermisoDenegado(accion)


# --------------------------------------------------------------------------- administración
#
# Lo que sigue es la gestión de usuarios que pidió el cliente el 2026-09-18: un usuario por
# empleado, con su propia clave. Las reglas de negocio viven aquí y no en la pantalla, porque
# en modo red la pantalla está en otro PC y lo único que llega de vuelta es el texto del error
# (`red/protocolo.levantar_error`). Por eso todos los errores son `DatosInvalidos` o
# `PermisoDenegado`, que ya viajan por la red, con el mensaje redactado para el dueño.


def generar_pin() -> str:
    """Un PIN al azar que no sea de los que cualquiera prueba primero.

    Se descartan los de un solo dígito repetido y las escaleras (`1111`, `1234`, `9876`). Son
    los primeros que prueba quien curiosea, y dos de ellos están publicados en el manual como
    PIN de demostración. `secrets`, no `random`: es una credencial.
    """
    while True:
        pin = "".join(secrets.choice("0123456789") for _ in range(LONGITUD_PIN_GENERADO))
        if not _es_obvio(pin):
            return pin


def _es_obvio(pin: str) -> bool:
    if len(set(pin)) == 1:
        return True
    pasos = {int(b) - int(a) for a, b in zip(pin, pin[1:])}
    return pasos in ({1}, {-1})


def _usuario_existente(conexion: sqlite3.Connection, usuario_id: int) -> Usuario:
    usuario = repo_usuarios.obtener_por_id(conexion, usuario_id)
    if usuario is None:
        raise DatosInvalidos("Ese usuario ya no existe.")
    return usuario


def listar_para_administrar(
    conexion: sqlite3.Connection, admin: Usuario | None, incluir_inactivos: bool = False
) -> list[Usuario]:
    """Usuarios para la pantalla de administración. Solo administradores.

    Es distinta de `listar_usuarios`, que alimenta el acceso y la puede pedir cualquiera: esta
    enseña también a los dados de baja, y eso es asunto del dueño.
    """
    exigir_admin(admin, "administrar los usuarios")
    return repo_usuarios.listar(conexion, incluir_inactivos=incluir_inactivos)


def alta_usuario(
    conexion: sqlite3.Connection, admin: Usuario | None, nombre: str, rol: Rol
) -> tuple[Usuario, str]:
    """Da de alta un empleado y le genera un PIN. Solo administradores.

    Devuelve el usuario y **el PIN en claro, una sola vez**, para que la pantalla lo muestre y
    alguien lo anote. Después no se puede recuperar: en la base solo queda su hash.

    Raises:
        PermisoDenegado, DatosInvalidos
    """
    exigir_admin(admin, "dar de alta usuarios")
    nombre = nombre.strip()
    existente = repo_usuarios.buscar_por_nombre(conexion, nombre) if nombre else None
    if existente is not None and not existente.activo:
        # El nombre es único y la baja es lógica: sin este aviso, volver a contratar a alguien
        # que ya trabajó aquí daría un "ya existe" que nadie entendería.
        raise DatosInvalidos(
            f"Ya existe un usuario llamado {nombre}, dado de baja. "
            "Reactívelo en lugar de crearlo de nuevo."
        )
    pin = generar_pin()
    with transaccion(conexion):
        usuario = crear_usuario(conexion, nombre, rol, pin)
    return usuario, pin


def reiniciar_pin(conexion: sqlite3.Connection, admin: Usuario | None, usuario_id: int) -> str:
    """Le da a un empleado un PIN nuevo, generado. Para cuando lo olvida. Solo administradores.

    Devuelve el PIN en claro, una sola vez. El anterior deja de servir en el acto.
    """
    exigir_admin(admin, "cambiar el PIN de un usuario")
    usuario = _usuario_existente(conexion, usuario_id)
    if not usuario.activo:
        raise DatosInvalidos(f"{usuario.nombre} está dado de baja. Reactívelo primero.")
    pin = generar_pin()
    with transaccion(conexion):
        cambiar_pin(conexion, usuario, pin)
    return pin


def desactivar_usuario(
    conexion: sqlite3.Connection, admin: Usuario | None, usuario_id: int
) -> None:
    """Da de baja a un empleado. Solo administradores. Sus ventas siguen a su nombre.

    Dos reglas que la pantalla no puede saltarse:

    - **no se da de baja uno a sí mismo**, que es la forma más rápida de quedarse fuera;
    - **no se da de baja al último administrador activo**: la tienda quedaría sin nadie que
      pueda crear usuarios, cambiar precios o ver el cierre, y sin forma de arreglarlo desde
      el programa.
    """
    exigir_admin(admin, "dar de baja usuarios")
    usuario = _usuario_existente(conexion, usuario_id)
    if not usuario.activo:
        return
    if admin is not None and admin.id == usuario.id:
        raise DatosInvalidos("No puede darse de baja a sí mismo.")
    with transaccion(conexion):
        if usuario.es_admin and repo_usuarios.contar_admins_activos(conexion) <= 1:
            raise DatosInvalidos(
                f"{usuario.nombre} es el único administrador. Dé de alta otro administrador "
                "antes de darlo de baja."
            )
        repo_usuarios.cambiar_activo(conexion, usuario_id, False)


def reactivar_usuario(
    conexion: sqlite3.Connection, admin: Usuario | None, usuario_id: int
) -> str:
    """Vuelve a dar de alta a un empleado dado de baja, con PIN nuevo. Solo administradores.

    El PIN se renueva siempre: el viejo pudo quedar anotado en cualquier parte mientras la
    persona no trabajaba aquí.
    """
    exigir_admin(admin, "reactivar usuarios")
    usuario = _usuario_existente(conexion, usuario_id)
    pin = generar_pin()
    with transaccion(conexion):
        repo_usuarios.cambiar_activo(conexion, usuario_id, True)
        cambiar_pin(conexion, usuario, pin)
    return pin


# --------------------------------------------------------------------------- sin sesión
#
# Los dos únicos caminos para tener un administrador sin haber entrado antes como uno. Ninguno
# de los dos puede estar en `red/sesion.py` ni en `red/servidor.py`: por la red serían una
# puerta abierta para cualquiera del mismo cable. Una prueba lo comprueba.


def hay_usuarios(conexion: sqlite3.Connection) -> bool:
    """Si la base tiene algún usuario, activo o no."""
    return repo_usuarios.contar_todos(conexion) > 0


def crear_primer_administrador(conexion: sqlite3.Connection, nombre: str) -> tuple[Usuario, str]:
    """Crea el administrador de una instalación nueva. Solo si **no hay ningún usuario**.

    Es lo que usa el arranque cuando la base está vacía, en lugar de dejar entrar sin sesión.
    Si ya hay usuarios se niega: si no, sería una forma de crear administradores sin permiso.
    """
    pin = generar_pin()
    with transaccion(conexion):
        if repo_usuarios.contar_todos(conexion) > 0:
            raise PermisoDenegado("crear el primer administrador, porque ya hay usuarios")
        usuario = crear_usuario(conexion, nombre, Rol.ADMIN, pin)
    _logger.info("Primer administrador creado: %s", usuario.nombre)
    return usuario, pin


def rescatar_administrador(conexion: sqlite3.Connection, nombre: str) -> tuple[Usuario, str]:
    """Recupera un administrador cuando nadie recuerda el PIN. **Solo desde el propio equipo.**

    Lo usa `PuntoYFamaCaja.exe --reiniciar-admin`. Si el nombre es de un administrador, le da
    un PIN nuevo y lo reactiva si estaba de baja; si no existe, lo crea como administrador. Si
    es de un cajero, se niega: ascender a alguien no es rescatar la tienda.

    No pide PIN porque quien lo ejecuta ya tiene el equipo delante, y con eso el archivo de la
    base: no abre nada que no estuviera abierto. Lo que sí hace es **dejar constancia en el
    registro**, que es lo que lo distingue de una puerta trasera. Nunca se registra el PIN.
    """
    nombre = nombre.strip()
    if not nombre:
        raise DatosInvalidos("Escriba el nombre del administrador.")
    pin = generar_pin()
    with transaccion(conexion):
        existente = repo_usuarios.buscar_por_nombre(conexion, nombre)
        if existente is None:
            usuario = crear_usuario(conexion, nombre, Rol.ADMIN, pin)
            accion = "creado"
        elif not existente.es_admin:
            raise DatosInvalidos(
                f"{nombre} es cajero, no administrador. Use otro nombre para el rescate."
            )
        else:
            assert existente.id is not None
            repo_usuarios.cambiar_activo(conexion, existente.id, True)
            cambiar_pin(conexion, existente, pin)
            usuario = existente
            usuario.activo = True
            accion = "restablecido"
    _logger.warning(
        "RESCATE DE ADMINISTRADOR desde la línea de comandos: %s %s", usuario.nombre, accion
    )
    return usuario, pin
