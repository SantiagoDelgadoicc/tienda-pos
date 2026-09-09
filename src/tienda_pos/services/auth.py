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
import secrets
import sqlite3

from ..config import PIN_LONGITUD_MAX, PIN_LONGITUD_MIN
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
