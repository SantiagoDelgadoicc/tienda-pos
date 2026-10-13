"""Consulta y administración del catálogo de productos.

Aquí vive el corazón de lo que pidió el cliente: dado un código de barras, encontrar el
producto y su precio.
"""

from __future__ import annotations

import sqlite3

from .. import config
from ..db.connection import escribir_meta, leer_meta, transaccion
from ..domain.errors import (
    CodigoInvalido,
    DatosInvalidos,
    ProductoNoEncontrado,
)
from ..domain.models import Producto, Usuario
from ..repositories import codigos as repo_codigos
from ..repositories import productos as repo_productos
from ..utils import codigo_barras as cb

#: Dónde se guarda el recargo por cajetilla (fase 26). En la base y no en las preferencias de
#: cada PC: tiene que ser el mismo en las dos cajas, y lo aplica el servidor.
CLAVE_RECARGO_CIGARRO = "recargo_cigarro_tarjeta_clp"

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


def _codigo_interno(conexion: sqlite3.Connection) -> str:
    """Un código para un producto que no trae código de barras, como el pan (D-037).

    Siete cifras que empiezan por el prefijo de uso interno: "2000001", "2000002"... Cortas, para
    poder teclearlas si hace falta, y distintas de cualquier EAN de fábrica, que tienen 8 o 13.
    """
    prefijo = config.PREFIJO_CODIGO_INTERNO
    ultimo = repo_productos.ultimo_codigo_interno(conexion, prefijo)
    siguiente = int(ultimo[len(prefijo):]) + 1 if ultimo else 1
    while True:
        codigo = f"{prefijo}{siguiente:06d}"
        if repo_productos.obtener_por_codigo(conexion, codigo, incluir_inactivos=True) is None:
            return codigo
        siguiente += 1


def _validar_datos(
    codigo: str, nombre: str, precio_clp: int, stock: int, stock_anterior: int | None = None
) -> tuple[str, str]:
    if not cb.es_valido(codigo):
        raise DatosInvalidos("El código de barras no es válido.")
    nombre = nombre.strip()
    if not nombre:
        raise DatosInvalidos("El nombre del producto no puede estar vacío.")
    if len(nombre) > _NOMBRE_LONGITUD_MAX:
        raise DatosInvalidos(f"El nombre no puede superar los {_NOMBRE_LONGITUD_MAX} caracteres.")
    if precio_clp < 0:
        raise DatosInvalidos("El precio no puede ser negativo.")
    # Un stock negativo sale de vender sin stock (D-009). Se acepta si no baja del que había:
    # igual, para poder cambiarle el precio a ese producto, o más alto, porque entró mercadería
    # y el -3 pasa a -1 (fase 22). Lo que no se puede es escribir uno negativo de la nada.
    if stock < 0 and (stock_anterior is None or stock < stock_anterior):
        raise DatosInvalidos("El stock no puede ser negativo.")
    return cb.normalizar(codigo), nombre


def _validar_cigarro(por_peso: bool, es_cigarro: bool) -> None:
    """El recargo es por cajetilla: un producto por peso no tiene cajetillas que contar."""
    if por_peso and es_cigarro:
        raise DatosInvalidos("Un cigarro se vende por unidad, no por peso.")


def recargo_cigarro(conexion: sqlite3.Connection) -> int:
    """Lo que se suma por cada cajetilla de cigarros pagada con débito o crédito (D-040).

    Mientras el administrador no fije otro, el que pidió el cliente: $500. Un valor ilegible en
    la base vuelve a ese y no tumba el cobro.
    """
    valor = leer_meta(conexion, CLAVE_RECARGO_CIGARRO)
    try:
        monto = int(valor) if valor not in (None, "") else config.RECARGO_CIGARRO_DEFECTO_CLP
    except ValueError:
        return config.RECARGO_CIGARRO_DEFECTO_CLP
    return monto if 0 <= monto <= config.RECARGO_CIGARRO_MAXIMO_CLP else config.RECARGO_CIGARRO_DEFECTO_CLP


def fijar_recargo_cigarro(
    conexion: sqlite3.Connection, admin: Usuario | None, monto_clp: int
) -> None:
    """Cambia el recargo por cajetilla. Solo administradores: cambia lo que pagan los clientes.

    Cero lo apaga. Vale para las dos cajas desde la próxima venta.
    """
    from .auth import exigir_admin

    exigir_admin(admin, "cambiar el recargo de los cigarros")
    if isinstance(monto_clp, bool) or not isinstance(monto_clp, int):
        raise DatosInvalidos("El recargo debe ser un monto en pesos, sin decimales.")
    if not 0 <= monto_clp <= config.RECARGO_CIGARRO_MAXIMO_CLP:
        raise DatosInvalidos(
            f"El recargo debe estar entre $0 y ${config.RECARGO_CIGARRO_MAXIMO_CLP:,}.".replace(",", ".")
        )
    with transaccion(conexion):
        escribir_meta(conexion, CLAVE_RECARGO_CIGARRO, str(monto_clp))


def crear_producto(
    conexion: sqlite3.Connection,
    usuario: Usuario | None,
    codigo: str,
    nombre: str,
    precio_clp: int,
    stock: int = 0,
    por_peso: bool = False,
    es_cigarro: bool = False,
) -> Producto:
    """Da de alta un producto. Cualquier usuario con sesión (D-038).

    Con `es_cigarro` (fase 26, D-040), cada unidad pagada con tarjeta lleva el recargo de
    `recargo_cigarro`. Un cigarro no se vende por peso.

    Con `por_peso` (D-037), `precio_clp` es el precio del kilo y `stock` son gramos. Sin código
    de barras, el sistema le da uno interno: el pan no trae etiqueta y se vende buscándolo.

    Raises:
        DatosInvalidos, ProductoDuplicado
    """
    from .auth import exigir_sesion  # importación local: evita un ciclo entre servicios

    exigir_sesion(usuario, "crear productos")
    with transaccion(conexion):
        if not cb.normalizar(codigo):
            codigo = _codigo_interno(conexion)
        codigo, nombre = _validar_datos(codigo, nombre, precio_clp, stock)
        _validar_cigarro(bool(por_peso), bool(es_cigarro))
        producto = repo_productos.crear(
            conexion,
            Producto(
                codigo_barras=codigo,
                nombre=nombre,
                precio_clp=precio_clp,
                stock=stock,
                por_peso=bool(por_peso),
                es_cigarro=bool(es_cigarro),
            ),
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
    stock: int | None,
    por_peso: bool | None = None,
    es_cigarro: bool | None = None,
) -> Producto:
    """Modifica un producto existente, precio y stock incluidos. Cualquier usuario con sesión
    (D-038).

    `por_peso` None lo deja como estaba. Cambiarlo no toca las ventas pasadas: cada línea
    guarda si se vendió por peso.

    `stock` None también lo deja como está **en la base en este momento**, y es lo que debe
    mandar quien no lo cambió. El formulario se abre con el stock de cuando se cargó la lista;
    si lo devolviera tal cual, cambiarle el precio a un producto borraría lo que las cajas
    vendieron mientras tanto (fase 22). Por eso el producto se lee dentro de la transacción.
    """
    from .auth import exigir_sesion

    exigir_sesion(usuario, "modificar productos")
    with transaccion(conexion):
        existente = repo_productos.obtener_por_id(conexion, producto_id)
        if existente is None:
            raise DatosInvalidos("El producto que intenta modificar ya no existe.")
        if not cb.normalizar(codigo):
            codigo = existente.codigo_barras
        if stock is None:
            stock = existente.stock
        codigo, nombre = _validar_datos(codigo, nombre, precio_clp, stock, existente.stock)
        if por_peso is not None:
            existente.por_peso = bool(por_peso)
        # None lo deja como estaba, como `por_peso`: quien no sabe de cigarros no lo borra.
        if es_cigarro is not None:
            existente.es_cigarro = bool(es_cigarro)
        _validar_cigarro(existente.por_peso, existente.es_cigarro)

        existente.codigo_barras = codigo
        existente.nombre = nombre
        existente.precio_clp = precio_clp
        existente.stock = stock
        repo_productos.actualizar(conexion, existente)
    return existente


def desactivar_producto(
    conexion: sqlite3.Connection, usuario: Usuario | None, producto_id: int
) -> None:
    """Da de baja un producto sin borrarlo, para no romper el historial de ventas."""
    from .auth import exigir_sesion

    exigir_sesion(usuario, "eliminar productos")
    with transaccion(conexion):
        repo_productos.desactivar(conexion, producto_id)


def codigos_pendientes(conexion: sqlite3.Connection, usuario: Usuario | None):
    """Códigos escaneados que aún no existen en el catálogo. Cualquier usuario con sesión."""
    from .auth import exigir_sesion

    exigir_sesion(usuario, "ver los códigos pendientes")
    return repo_codigos.listar_pendientes(conexion)
