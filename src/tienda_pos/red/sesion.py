"""La `Sesion`: lo que la interfaz usa en lugar de una conexión a la base.

Antes, cada pantalla recibía un `sqlite3.Connection` y llamaba a `services/` con él. Eso ata
la interfaz a que los datos estén en el mismo proceso, que es exactamente lo que `D-015`
rompe. Una `Sesion` es la misma lista de operaciones sin decir dónde se ejecutan:

- `SesionLocal` las ejecuta aquí mismo, contra su propia conexión. Es lo que hace la caja
  principal, que además es el servidor, y lo que hace una instalación de un solo PC.
- `SesionRemota` (en `cliente.py`) las manda por la red al servidor.

La interfaz no distingue entre las dos, y ese es el objetivo: `ui/` no sabe si hay red.

**Este módulo no importa Qt.** La regla de capas de `CLAUDE.md` sigue en pie: la nueva capa es
`ui → red → services → repositories → db`.
"""

from __future__ import annotations

import functools
import sqlite3
import threading
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import date
from typing import Any, TypeVar

from ..domain.models import CodigoNoEncontrado, Producto, Usuario, Venta
from ..services import auth, catalogo, reportes
from ..services import venta as servicio_venta
from ..services.venta import Carrito


class Sesion(ABC):
    """Las 13 operaciones que la interfaz necesita. Nada más.

    Es deliberadamente corta: cada método que se añada aquí es un método que habrá que
    implementar dos veces y hacer viajar por la red. Si algo se puede calcular en la caja con
    los datos que ya tiene, se calcula en la caja.
    """

    # ------------------------------------------------------------------ estado

    @abstractmethod
    def esta_conectada(self) -> bool:
        """Si la sesión puede atender operaciones ahora mismo."""

    @abstractmethod
    def descripcion(self) -> str:
        """Texto corto para la barra de estado: dónde vive la base de datos."""

    # ------------------------------------------------------------------ catálogo

    @abstractmethod
    def consultar_por_codigo(self, codigo: str, registrar_faltante: bool = True) -> Producto: ...

    @abstractmethod
    def buscar_por_nombre(self, texto: str) -> list[Producto]: ...

    @abstractmethod
    def listar_productos(self, incluir_inactivos: bool = False) -> list[Producto]: ...

    @abstractmethod
    def crear_producto(
        self, usuario: Usuario | None, codigo: str, nombre: str, precio_clp: int, stock: int
    ) -> Producto: ...

    @abstractmethod
    def actualizar_producto(
        self,
        usuario: Usuario | None,
        producto_id: int,
        codigo: str,
        nombre: str,
        precio_clp: int,
        stock: int,
    ) -> Producto: ...

    @abstractmethod
    def desactivar_producto(self, usuario: Usuario | None, producto_id: int) -> None: ...

    @abstractmethod
    def codigos_pendientes(self, usuario: Usuario | None) -> list[CodigoNoEncontrado]: ...

    # ------------------------------------------------------------------ venta

    @abstractmethod
    def cerrar_venta(
        self, carrito: Carrito, usuario: Usuario | None, intento_id: str | None = None
    ) -> Venta: ...

    # ------------------------------------------------------------------ acceso

    @abstractmethod
    def listar_usuarios(self) -> list[Usuario]: ...

    @abstractmethod
    def autenticar(self, nombre: str, pin: str) -> Usuario: ...

    # ------------------------------------------------------------------ reportes

    @abstractmethod
    def resumen_del_dia(self, dia: date | None = None) -> dict[str, int]: ...

    @abstractmethod
    def ventas_del_dia(self, dia: date | None = None) -> list[Venta]: ...


_R = TypeVar("_R")


def _serializado(metodo: Callable[..., _R]) -> Callable[..., _R]:
    """Toma el cerrojo de la sesión durante toda la operación.

    Hace falta porque en modo servidor hay **dos hilos** tocando la misma conexión: el de la
    interfaz de la caja principal y el que atiende a la caja secundaria. SQLite prohíbe usar
    una conexión desde varios hilos justamente para evitar ese desastre, y `conectar` solo
    levanta esa prohibición si alguien garantiza el turno. Este cerrojo es esa garantía.

    El coste es nulo en la práctica: cada operación dura milisegundos y como mucho hay dos
    cajas. Y el cerrojo abarca la operación entera, transacción incluida, de modo que nadie
    puede colarse entre el `BEGIN` y el `COMMIT`.
    """

    @functools.wraps(metodo)
    def envoltorio(self: SesionLocal, *args: Any, **kwargs: Any) -> _R:
        with self._cerrojo:
            return metodo(self, *args, **kwargs)

    return envoltorio


class SesionLocal(Sesion):
    """Ejecuta las operaciones en este mismo proceso, contra su propia conexión.

    Es lo que usa la caja principal —que es también el servidor— y cualquier instalación de un
    solo PC. No hay red de por medio, así que no hay tiempos límite ni estado de conexión que
    valga: siempre está conectada.
    """

    def __init__(self, conexion: sqlite3.Connection) -> None:
        self._conexion = conexion
        # Reentrante porque una operación puede llamar a otra de la misma sesión.
        self._cerrojo = threading.RLock()

    @property
    def conexion(self) -> sqlite3.Connection:
        """La conexión subyacente.

        La exponen el servidor y las pruebas. La interfaz **no debería usarla**: si una
        pantalla la necesita, es que falta una operación en `Sesion`.
        """
        return self._conexion

    def esta_conectada(self) -> bool:
        return True

    def descripcion(self) -> str:
        return "Base de datos local"

    # ------------------------------------------------------------------ catálogo

    @_serializado
    def consultar_por_codigo(self, codigo: str, registrar_faltante: bool = True) -> Producto:
        return catalogo.consultar_por_codigo(self._conexion, codigo, registrar_faltante)

    @_serializado
    def buscar_por_nombre(self, texto: str) -> list[Producto]:
        return catalogo.buscar_por_nombre(self._conexion, texto)

    @_serializado
    def listar_productos(self, incluir_inactivos: bool = False) -> list[Producto]:
        return catalogo.listar(self._conexion, incluir_inactivos=incluir_inactivos)

    @_serializado
    def crear_producto(
        self, usuario: Usuario | None, codigo: str, nombre: str, precio_clp: int, stock: int
    ) -> Producto:
        return catalogo.crear_producto(self._conexion, usuario, codigo, nombre, precio_clp, stock)

    @_serializado
    def actualizar_producto(
        self,
        usuario: Usuario | None,
        producto_id: int,
        codigo: str,
        nombre: str,
        precio_clp: int,
        stock: int,
    ) -> Producto:
        return catalogo.actualizar_producto(
            self._conexion, usuario, producto_id, codigo, nombre, precio_clp, stock
        )

    @_serializado
    def desactivar_producto(self, usuario: Usuario | None, producto_id: int) -> None:
        catalogo.desactivar_producto(self._conexion, usuario, producto_id)

    @_serializado
    def codigos_pendientes(self, usuario: Usuario | None) -> list[CodigoNoEncontrado]:
        return catalogo.codigos_pendientes(self._conexion, usuario)

    # ------------------------------------------------------------------ venta

    @_serializado
    def cerrar_venta(
        self, carrito: Carrito, usuario: Usuario | None, intento_id: str | None = None
    ) -> Venta:
        return servicio_venta.cerrar_venta(self._conexion, carrito, usuario, intento_id)

    # ------------------------------------------------------------------ acceso

    @_serializado
    def listar_usuarios(self) -> list[Usuario]:
        return auth.listar_usuarios(self._conexion)

    @_serializado
    def autenticar(self, nombre: str, pin: str) -> Usuario:
        return auth.autenticar(self._conexion, nombre, pin)

    # ------------------------------------------------------------------ reportes

    @_serializado
    def resumen_del_dia(self, dia: date | None = None) -> dict[str, int]:
        return reportes.resumen_del_dia(self._conexion, dia)

    @_serializado
    def ventas_del_dia(self, dia: date | None = None) -> list[Venta]:
        return reportes.ventas_del_dia(self._conexion, dia)
