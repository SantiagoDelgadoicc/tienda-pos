"""Modelos del dominio.

Son estructuras de datos puras: no saben nada de SQLite ni de Qt. Esa separación es lo que
permite probar la lógica de negocio sin abrir una ventana ni crear una base de datos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class Rol(StrEnum):
    CAJERO = "cajero"
    ADMIN = "admin"


class EstadoVenta(StrEnum):
    COMPLETADA = "completada"
    ANULADA = "anulada"


@dataclass(slots=True)
class Producto:
    codigo_barras: str
    nombre: str
    precio_clp: int
    stock: int = 0
    activo: bool = True
    id: int | None = None
    creado_en: str | None = None
    actualizado_en: str | None = None


@dataclass(slots=True)
class Usuario:
    nombre: str
    rol: Rol
    id: int | None = None
    activo: bool = True

    @property
    def es_admin(self) -> bool:
        return self.rol is Rol.ADMIN


@dataclass(slots=True)
class LineaCarrito:
    """Una línea del carrito en curso.

    Guarda una copia del nombre y del precio en lugar de una referencia al producto, por el
    mismo motivo que la línea de venta: si alguien cambia el precio mientras hay un carrito
    abierto, el cliente debe pagar lo que se le mostró.
    """

    producto_id: int
    codigo_barras: str
    nombre: str
    precio_unit_clp: int
    cantidad: int = 1

    @property
    def subtotal_clp(self) -> int:
        return self.precio_unit_clp * self.cantidad


@dataclass(slots=True)
class LineaVenta:
    codigo_barras: str
    nombre: str
    precio_unit_clp: int
    cantidad: int
    subtotal_clp: int
    producto_id: int | None = None
    id: int | None = None
    venta_id: int | None = None


@dataclass(slots=True)
class Venta:
    folio: int
    fecha_hora: datetime
    subtotal_clp: int
    descuento_clp: int
    total_clp: int
    usuario_id: int | None = None
    usuario_nombre: str | None = None
    estado: EstadoVenta = EstadoVenta.COMPLETADA
    id: int | None = None
    lineas: list[LineaVenta] = field(default_factory=list)

    @property
    def cantidad_articulos(self) -> int:
        return sum(linea.cantidad for linea in self.lineas)


@dataclass(slots=True)
class CodigoNoEncontrado:
    """Un código que se escaneó y no existe en el catálogo.

    Se registra para que el dueño de la tienda vea al final del día qué productos le faltan
    por cargar. Es una sugerencia nuestra, no un requisito del cliente.
    """

    codigo: str
    intentos: int
    primera_vez: str
    ultima_vez: str
    resuelto: bool = False
