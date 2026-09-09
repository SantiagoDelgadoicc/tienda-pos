"""Carrito de compra y cierre de venta.

El carrito es un objeto en memoria, sin base de datos: se puede probar entero sin abrir una
conexión. Solo al cerrar la venta se toca el disco, y siempre dentro de una transacción.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime

from ..config import PERMITIR_STOCK_NEGATIVO
from ..db.connection import transaccion
from ..domain.errors import (
    CarritoVacio,
    DatosInvalidos,
    DescuentoInvalido,
    StockInsuficiente,
)
from ..domain.models import LineaCarrito, LineaVenta, Producto, Usuario, Venta
from ..repositories import productos as repo_productos
from ..repositories import ventas as repo_ventas
from ..utils.money import porcentaje_de

#: Tope defensivo de unidades por línea. Protege contra el caso real de que la pistola se
#: quede pegada leyendo el mismo código, o de que alguien mantenga pulsada una tecla.
CANTIDAD_MAX_POR_LINEA = 999


class Carrito:
    """La venta en curso.

    Las líneas se indexan por código de barras para que escanear dos veces el mismo producto
    sume una unidad en lugar de crear una segunda línea. Es lo que espera un cajero: si pasa
    tres yogures iguales, quiere ver "Yogur x3", no tres renglones.
    """

    def __init__(self) -> None:
        self._lineas: dict[str, LineaCarrito] = {}
        self._descuento_monto: int = 0
        self._descuento_porcentaje: float | None = None

    # ------------------------------------------------------------------ productos

    def agregar(self, producto: Producto, cantidad: int = 1) -> LineaCarrito:
        """Añade un producto, o suma unidades si ya estaba en el carrito.

        Raises:
            DatosInvalidos: si la cantidad no es positiva o supera el tope por línea.
        """
        if cantidad <= 0:
            raise DatosInvalidos("La cantidad debe ser mayor que cero.")
        assert producto.id is not None, "El producto debe venir de la base de datos"

        linea = self._lineas.get(producto.codigo_barras)
        if linea is None:
            linea = LineaCarrito(
                producto_id=producto.id,
                codigo_barras=producto.codigo_barras,
                nombre=producto.nombre,
                precio_unit_clp=producto.precio_clp,
                cantidad=0,
            )
            self._lineas[producto.codigo_barras] = linea

        nueva_cantidad = linea.cantidad + cantidad
        if nueva_cantidad > CANTIDAD_MAX_POR_LINEA:
            raise DatosInvalidos(
                f"No se pueden vender más de {CANTIDAD_MAX_POR_LINEA} unidades del mismo "
                "producto en una sola venta."
            )
        linea.cantidad = nueva_cantidad
        return linea

    def cambiar_cantidad(self, codigo_barras: str, cantidad: int) -> None:
        """Fija la cantidad de una línea. Con cantidad 0 la línea se elimina."""
        if codigo_barras not in self._lineas:
            raise DatosInvalidos("Ese producto no está en el carrito.")
        if cantidad < 0:
            raise DatosInvalidos("La cantidad no puede ser negativa.")
        if cantidad > CANTIDAD_MAX_POR_LINEA:
            raise DatosInvalidos(f"El máximo por línea es {CANTIDAD_MAX_POR_LINEA} unidades.")

        if cantidad == 0:
            del self._lineas[codigo_barras]
        else:
            self._lineas[codigo_barras].cantidad = cantidad

    def quitar(self, codigo_barras: str) -> None:
        if codigo_barras not in self._lineas:
            raise DatosInvalidos("Ese producto no está en el carrito.")
        del self._lineas[codigo_barras]

    def vaciar(self) -> None:
        self._lineas.clear()
        self.quitar_descuento()

    # ------------------------------------------------------------------ descuento

    def aplicar_descuento_monto(self, monto_clp: int) -> None:
        """Descuento por un importe fijo sobre el total.

        Raises:
            DescuentoInvalido: si es negativo o supera el subtotal actual.
        """
        if monto_clp < 0:
            raise DescuentoInvalido("El descuento no puede ser negativo.")
        if monto_clp > self.subtotal_clp:
            raise DescuentoInvalido("El descuento no puede superar el total de la venta.")
        self._descuento_monto = monto_clp
        self._descuento_porcentaje = None

    def aplicar_descuento_porcentaje(self, porcentaje: float) -> None:
        """Descuento porcentual.

        Se guarda el porcentaje y no el importe, de modo que si después se añade o se quita
        un producto, el descuento siga siendo el porcentaje pactado con el cliente y no un
        importe que quedó obsoleto.
        """
        if not 0 <= porcentaje <= 100:
            raise DescuentoInvalido("El porcentaje debe estar entre 0 y 100.")
        self._descuento_porcentaje = porcentaje
        self._descuento_monto = 0

    def quitar_descuento(self) -> None:
        self._descuento_monto = 0
        self._descuento_porcentaje = None

    # ------------------------------------------------------------------ consultas

    @property
    def lineas(self) -> list[LineaCarrito]:
        """Las líneas en el orden en que se escanearon."""
        return list(self._lineas.values())

    @property
    def esta_vacio(self) -> bool:
        return not self._lineas

    @property
    def cantidad_articulos(self) -> int:
        return sum(linea.cantidad for linea in self._lineas.values())

    @property
    def subtotal_clp(self) -> int:
        return sum(linea.subtotal_clp for linea in self._lineas.values())

    @property
    def descuento_clp(self) -> int:
        """Descuento efectivo, nunca mayor que el subtotal.

        El tope importa: si se aplica un descuento de 2.000 y luego se quitan productos
        hasta dejar 1.500, el total debe ser 0 y jamás un número negativo.
        """
        if self._descuento_porcentaje is not None:
            return porcentaje_de(self.subtotal_clp, self._descuento_porcentaje)
        return min(self._descuento_monto, self.subtotal_clp)

    @property
    def descuento_porcentaje(self) -> float | None:
        return self._descuento_porcentaje

    @property
    def total_clp(self) -> int:
        return self.subtotal_clp - self.descuento_clp


def cerrar_venta(
    conexion: sqlite3.Connection, carrito: Carrito, usuario: Usuario | None = None
) -> Venta:
    """Registra la venta y descuenta el stock, todo dentro de una única transacción.

    El stock se vuelve a comprobar aquí, contra la base de datos, y no contra lo que el
    carrito recuerda: entre el escaneo y el cobro pudo cambiar. En monopuesto es improbable,
    pero la comprobación es barata y el día que haya dos cajas será imprescindible.

    Los precios que se guardan son los del carrito, es decir, los que se le mostraron al
    cliente. Si alguien cambió el precio mientras la venta estaba abierta, se respeta lo
    exhibido.

    Raises:
        CarritoVacio, StockInsuficiente, DatosInvalidos
    """
    if carrito.esta_vacio:
        raise CarritoVacio()

    subtotal = carrito.subtotal_clp
    descuento = carrito.descuento_clp
    total = subtotal - descuento

    with transaccion(conexion):
        for linea in carrito.lineas:
            producto = repo_productos.obtener_por_id(conexion, linea.producto_id)
            if producto is None or not producto.activo:
                raise DatosInvalidos(
                    f"El producto {linea.nombre} ya no está disponible. Quítelo del carrito."
                )
            if not PERMITIR_STOCK_NEGATIVO and producto.stock < linea.cantidad:
                raise StockInsuficiente(producto.nombre, producto.stock, linea.cantidad)

        venta = Venta(
            folio=repo_ventas.siguiente_folio(conexion),
            fecha_hora=datetime.now().replace(microsecond=0),
            subtotal_clp=subtotal,
            descuento_clp=descuento,
            total_clp=total,
            usuario_id=usuario.id if usuario else None,
            usuario_nombre=usuario.nombre if usuario else None,
            lineas=[
                LineaVenta(
                    producto_id=linea.producto_id,
                    codigo_barras=linea.codigo_barras,
                    nombre=linea.nombre,
                    precio_unit_clp=linea.precio_unit_clp,
                    cantidad=linea.cantidad,
                    subtotal_clp=linea.subtotal_clp,
                )
                for linea in carrito.lineas
            ],
        )

        repo_ventas.insertar(conexion, venta)
        for linea in carrito.lineas:
            repo_productos.descontar_stock(conexion, linea.producto_id, linea.cantidad)

    return venta
