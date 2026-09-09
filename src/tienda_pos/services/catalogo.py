"""Consulta y administración del catálogo de productos.

Aquí vive el corazón de lo que pidió el cliente: dado un código de barras, encontrar el
producto y su precio.
"""

from __future__ import annotations

import sqlite3

from ..db.connection import transaccion
from ..domain.errors import (
    CodigoInvalido,
    DatosInvalidos,
    ProductoNoEncontrado,
)
from ..domain.models import Producto, Usuario
from ..repositories import codigos as repo_codigos
from ..repositories import productos as repo_productos
from ..utils import codigo_barras as cb

# Límite defensivo para el nombre: evita que un pegado accidental de un texto enorme
# desfigure la tabla del carrito.
_NOMBRE_LONGITUD_MAX = 120


def consultar_por_codigo(
    conexion: sqlite3.Connection, codigo: str, registrar_faltante: bool = True
) -> Producto:
    """Busca un producto por su código de barras.

    Args:
        codigo: lo que llegó del lector o del teclado, sin limpiar.
        registrar_faltante: si es True, un código inexistente se anota para que el dueño lo
            revise más tarde. Se desactiva en las pantallas de administración, donde buscar
            un código que no existe es parte del trabajo normal y no un incidente.

    Raises:
        CodigoInvalido: el código está vacío o tiene caracteres imposibles.
        ProductoNoEncontrado: el código es válido pero no está en el catálogo.
    """
    if not cb.es_valido(codigo):
        raise CodigoInvalido(codigo.strip())

    limpio = cb.normalizar(codigo)
    producto = repo_productos.obtener_por_codigo(conexion, limpio)
    if producto is None:
        if registrar_faltante:
            # En su propia transacción: dejar constancia del código no encontrado no debe
            # arrastrar ni verse afectado por lo que esté haciendo la venta en curso.
            with transaccion(conexion):
                repo_codigos.registrar(conexion, limpio)
        raise ProductoNoEncontrado(limpio)

    return producto


def buscar_por_nombre(conexion: sqlite3.Connection, texto: str) -> list[Producto]:
    """Búsqueda parcial por nombre, para cuando el código no se puede leer.

    Con menos de dos caracteres devuelve una lista vacía en lugar de medio catálogo: una
    lista de cuatrocientos resultados no le sirve a nadie en una caja.
    """
    texto = texto.strip()
    if len(texto) < 2:
        return []
    return repo_productos.buscar_por_nombre(conexion, texto)


def listar(conexion: sqlite3.Connection, incluir_inactivos: bool = False) -> list[Producto]:
    return repo_productos.listar(conexion, incluir_inactivos=incluir_inactivos)


def _validar_datos(codigo: str, nombre: str, precio_clp: int, stock: int) -> tuple[str, str]:
    if not cb.es_valido(codigo):
        raise DatosInvalidos("El código de barras no es válido.")
    nombre = nombre.strip()
    if not nombre:
        raise DatosInvalidos("El nombre del producto no puede estar vacío.")
    if len(nombre) > _NOMBRE_LONGITUD_MAX:
        raise DatosInvalidos(f"El nombre no puede superar los {_NOMBRE_LONGITUD_MAX} caracteres.")
    if precio_clp < 0:
        raise DatosInvalidos("El precio no puede ser negativo.")
    if stock < 0:
        raise DatosInvalidos("El stock no puede ser negativo.")
    return cb.normalizar(codigo), nombre


def crear_producto(
    conexion: sqlite3.Connection,
    usuario: Usuario | None,
    codigo: str,
    nombre: str,
    precio_clp: int,
    stock: int = 0,
) -> Producto:
    """Da de alta un producto. Solo administradores.

    Raises:
        PermisoDenegado, DatosInvalidos, ProductoDuplicado
    """
    from .auth import exigir_admin  # importación local: evita un ciclo entre servicios

    exigir_admin(usuario, "crear productos")
    codigo, nombre = _validar_datos(codigo, nombre, precio_clp, stock)

    with transaccion(conexion):
        producto = repo_productos.crear(
            conexion,
            Producto(codigo_barras=codigo, nombre=nombre, precio_clp=precio_clp, stock=stock),
        )
        # Si este código estaba en la lista de "no encontrados", ya dejó de estarlo.
        repo_codigos.marcar_resuelto(conexion, codigo)
    return producto


def actualizar_producto(
    conexion: sqlite3.Connection,
    usuario: Usuario | None,
    producto_id: int,
    codigo: str,
    nombre: str,
    precio_clp: int,
    stock: int,
) -> Producto:
    """Modifica un producto existente. Solo administradores."""
    from .auth import exigir_admin

    exigir_admin(usuario, "modificar productos")
    codigo, nombre = _validar_datos(codigo, nombre, precio_clp, stock)

    existente = repo_productos.obtener_por_id(conexion, producto_id)
    if existente is None:
        raise DatosInvalidos("El producto que intenta modificar ya no existe.")

    existente.codigo_barras = codigo
    existente.nombre = nombre
    existente.precio_clp = precio_clp
    existente.stock = stock

    with transaccion(conexion):
        repo_productos.actualizar(conexion, existente)
    return existente


def desactivar_producto(
    conexion: sqlite3.Connection, usuario: Usuario | None, producto_id: int
) -> None:
    """Da de baja un producto sin borrarlo, para no romper el historial de ventas."""
    from .auth import exigir_admin

    exigir_admin(usuario, "eliminar productos")
    with transaccion(conexion):
        repo_productos.desactivar(conexion, producto_id)


def codigos_pendientes(conexion: sqlite3.Connection, usuario: Usuario | None):
    """Códigos escaneados que aún no existen en el catálogo. Solo administradores."""
    from .auth import exigir_admin

    exigir_admin(usuario, "ver los códigos pendientes")
    return repo_codigos.listar_pendientes(conexion)
