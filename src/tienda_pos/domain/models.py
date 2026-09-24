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

    El descuento de la línea se guarda como monto o como porcentaje, nunca los dos a la vez.
    Se conserva el porcentaje en lugar de convertirlo a pesos porque si después cambia la
    cantidad, el trato con el cliente sigue siendo "el 10% de este producto" y no un importe
    que quedó obsoleto.
    """

    producto_id: int
    codigo_barras: str
    nombre: str
    precio_unit_clp: int
    cantidad: int = 1
    descuento_monto_clp: int = 0
    descuento_porcentaje: float | None = None

    @property
    def subtotal_clp(self) -> int:
        """Importe bruto de la línea, antes de su descuento."""
        return self.precio_unit_clp * self.cantidad

    @property
    def descuento_clp(self) -> int:
        """Descuento efectivo de la línea, nunca mayor que su propio subtotal."""
        from ..utils.money import porcentaje_de

        if self.descuento_porcentaje is not None:
            return porcentaje_de(self.subtotal_clp, self.descuento_porcentaje)
        return min(self.descuento_monto_clp, self.subtotal_clp)

    @property
    def total_clp(self) -> int:
        """Lo que aporta la línea al subtotal de la venta, ya con su descuento aplicado."""
        return self.subtotal_clp - self.descuento_clp

    @property
    def tiene_descuento(self) -> bool:
        return self.descuento_clp > 0


@dataclass(slots=True)
class LineaVenta:
    codigo_barras: str
    nombre: str
    precio_unit_clp: int
    cantidad: int
    subtotal_clp: int
    descuento_clp: int = 0
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
    #: Identificador del intento de cobro, generado por la caja. Permite reintentar un
    #: cobro cuyo resultado se perdió por la red sin duplicar la venta (D-024). Las ventas
    #: registradas antes de la migración 3 lo tienen a None.
    intento_id: str | None = None
    #: Nombre de la caja donde se hizo, tal como se llamaba en ese momento (fase 16). Las
    #: ventas anteriores a la migración 4 lo tienen a None: no se sabe y no se inventa.
    caja: str | None = None
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
