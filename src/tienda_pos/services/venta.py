"""Carrito de compra y cierre de venta.

El carrito es un objeto en memoria, sin base de datos: se puede probar entero sin abrir una
conexión. Solo al cerrar la venta se toca el disco, y siempre dentro de una transacción.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime

from .. import config
from ..db.connection import transaccion
from ..domain.errors import (
    CajaCerrada,
    CarritoVacio,
    DatosInvalidos,
    DescuentoInvalido,
    StockInsuficiente,
)
from ..domain.models import LineaCarrito, LineaVenta, MedioPago, Producto, Usuario, Venta
from ..repositories import arqueo as repo_arqueo
from ..repositories import productos as repo_productos
from ..repositories import ventas as repo_ventas
from ..utils.money import porcentaje_de

#: Tope defensivo de unidades por línea. Protege contra el caso real de que la pistola se
#: quede pegada leyendo el mismo código, o de que alguien mantenga pulsada una tecla.
CANTIDAD_MAX_POR_LINEA = 999


def _validar_gramos(gramos: object) -> None:
    """Un peso utilizable: gramos enteros, más que cero y bajo el tope de una línea."""
    if not isinstance(gramos, int) or isinstance(gramos, bool) or gramos <= 0:
        raise DatosInvalidos("El peso debe ser un número de gramos mayor que cero.")
    if gramos > config.GRAMOS_MAX_POR_LINEA:
        raise DatosInvalidos(
            f"El peso no puede superar los {config.GRAMOS_MAX_POR_LINEA // 1000} kg por producto."
        )


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

    def agregar(
        self, producto: Producto, cantidad: int = 1, gramos: int | None = None
    ) -> LineaCarrito:
        """Añade un producto, o suma unidades si ya estaba en el carrito.

        Un producto por peso (D-037) se agrega con `gramos` y no con unidades. Si ya estaba, los
        gramos se suman en la misma línea: dos trozos de jamón al mismo precio por kilo cuestan
        lo mismo juntos que por separado, y el cajero ve una sola línea, como con los yogures.

        Raises:
            DatosInvalidos: si la cantidad o el peso no son positivos o superan su tope, o si se
                dan gramos a un producto por unidad o se omiten en uno por peso.
        """
        assert producto.id is not None, "El producto debe venir de la base de datos"
        if producto.por_peso:
            return self._agregar_por_peso(producto, gramos)
        if gramos is not None:
            raise DatosInvalidos(f"{producto.nombre} se vende por unidad, no por peso.")
        if cantidad <= 0:
            raise DatosInvalidos("La cantidad debe ser mayor que cero.")

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

    def _agregar_por_peso(self, producto: Producto, gramos: int | None) -> LineaCarrito:
        assert producto.id is not None
        if gramos is None:
            raise DatosInvalidos(f"{producto.nombre} se vende por peso: indique los gramos.")
        _validar_gramos(gramos)
        linea = self._lineas.get(producto.codigo_barras)
        total = gramos + ((linea.gramos or 0) if linea else 0)
        _validar_gramos(total)
        if linea is None:
            linea = LineaCarrito(
                producto_id=producto.id,
                codigo_barras=producto.codigo_barras,
                nombre=producto.nombre,
                precio_unit_clp=producto.precio_clp,
                cantidad=1,
                gramos=total,
            )
            self._lineas[producto.codigo_barras] = linea
        else:
            linea.gramos = total
        return linea

    def cambiar_gramos(self, codigo_barras: str, gramos: int) -> None:
        """Fija el peso de una línea por peso. Con 0 gramos la línea se elimina."""
        linea = self._linea(codigo_barras)
        if not linea.por_peso:
            raise DatosInvalidos(f"{linea.nombre} se vende por unidad, no por peso.")
        if gramos == 0:
            del self._lineas[codigo_barras]
            return
        _validar_gramos(gramos)
        linea.gramos = gramos

    def cambiar_cantidad(self, codigo_barras: str, cantidad: int) -> None:
        """Fija la cantidad de una línea. Con cantidad 0 la línea se elimina.

        En una línea por peso solo vale 0, que la quita: sus unidades no significan nada, y
        sumarle "una más" a 350 g de jamón no es algo que un cajero quiera hacer sin querer.
        """
        if codigo_barras not in self._lineas:
            raise DatosInvalidos("Ese producto no está en el carrito.")
        if cantidad < 0:
            raise DatosInvalidos("La cantidad no puede ser negativa.")
        linea = self._lineas[codigo_barras]
        if linea.por_peso and cantidad != 0:
            raise DatosInvalidos(f"{linea.nombre} se vende por peso: cambie el peso, no la cantidad.")
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

    # ------------------------------------------------------------------ descuento de línea

    def _linea(self, codigo_barras: str) -> LineaCarrito:
        linea = self._lineas.get(codigo_barras)
        if linea is None:
            raise DatosInvalidos("Ese producto no está en el carrito.")
        return linea

    def aplicar_descuento_linea_monto(self, codigo_barras: str, monto_clp: int) -> None:
        """Descuenta un importe fijo sobre una sola línea.

        Raises:
            DatosInvalidos: si el producto no está en el carrito.
            DescuentoInvalido: si es negativo o supera el subtotal de esa línea.
        """
        linea = self._linea(codigo_barras)
        if monto_clp < 0:
            raise DescuentoInvalido("El descuento no puede ser negativo.")
        if monto_clp > linea.subtotal_clp:
            raise DescuentoInvalido(
                "El descuento no puede superar el importe de esa línea."
            )
        linea.descuento_monto_clp = monto_clp
        linea.descuento_porcentaje = None

    def aplicar_descuento_linea_porcentaje(self, codigo_barras: str, porcentaje: float) -> None:
        """Descuenta un porcentaje sobre una sola línea."""
        linea = self._linea(codigo_barras)
        if not 0 <= porcentaje <= 100:
            raise DescuentoInvalido("El porcentaje debe estar entre 0 y 100.")
        linea.descuento_porcentaje = porcentaje
        linea.descuento_monto_clp = 0

    def quitar_descuento_linea(self, codigo_barras: str) -> None:
        linea = self._linea(codigo_barras)
        linea.descuento_monto_clp = 0
        linea.descuento_porcentaje = None

    def linea_de(self, codigo_barras: str) -> LineaCarrito | None:
        return self._lineas.get(codigo_barras)

    # ------------------------------------------------------------------ descuento de la venta

    def aplicar_descuento_monto(self, monto_clp: int) -> None:
        """Descuento por un importe fijo sobre el total de la venta.

        Se calcula sobre lo que queda después de los descuentos de línea: de otro modo,
        dos descuentos del 100% (uno de línea y otro de venta) dejarían un total negativo.

        Raises:
            DescuentoInvalido: si es negativo o supera el subtotal actual.
        """
        if monto_clp < 0:
            raise DescuentoInvalido("El descuento no puede ser negativo.")
        if monto_clp > self.base_descontable_clp:
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
        """Importe bruto de la venta, antes de cualquier descuento."""
        return sum(linea.subtotal_clp for linea in self._lineas.values())

    @property
    def descuento_lineas_clp(self) -> int:
        """Suma de los descuentos aplicados producto a producto."""
        return sum(linea.descuento_clp for linea in self._lineas.values())

    @property
    def base_descontable_clp(self) -> int:
        """Lo que queda por descontar tras los descuentos de línea."""
        return self.subtotal_clp - self.descuento_lineas_clp

    @property
    def descuento_venta_clp(self) -> int:
        """Descuento aplicado al total, sin contar los de línea.

        El tope importa: si se aplica un descuento de 2.000 y luego se quitan productos
        hasta dejar 1.500, el total debe ser 0 y jamás un número negativo.
        """
        base = self.base_descontable_clp
        if self._descuento_porcentaje is not None:
            return porcentaje_de(base, self._descuento_porcentaje)
        return min(self._descuento_monto, base)

    @property
    def descuento_clp(self) -> int:
        """Descuento total de la venta: el de las líneas más el del total."""
        return self.descuento_lineas_clp + self.descuento_venta_clp

    @property
    def descuento_porcentaje(self) -> float | None:
        return self._descuento_porcentaje

    @property
    def total_clp(self) -> int:
        return self.subtotal_clp - self.descuento_clp

    # ------------------------------------------------------------------ serialización

    def a_dict(self) -> dict:
        """Describe el carrito entero para poder mandarlo a cobrar por la red (D-015).

        Vive aquí y no en la capa de red para no tener que exponer los campos privados del
        descuento. El carrito no se sincroniza nunca: cruza la red una sola vez, completo, en
        el momento del cobro.
        """
        return {
            "lineas": [
                {
                    "producto_id": linea.producto_id,
                    "codigo_barras": linea.codigo_barras,
                    "nombre": linea.nombre,
                    "precio_unit_clp": linea.precio_unit_clp,
                    "cantidad": linea.cantidad,
                    "descuento_monto_clp": linea.descuento_monto_clp,
                    "descuento_porcentaje": linea.descuento_porcentaje,
                    "gramos": linea.gramos,
                }
                for linea in self.lineas
            ],
            "descuento_monto_clp": self._descuento_monto,
            "descuento_porcentaje": self._descuento_porcentaje,
        }

    @classmethod
    def desde_dict(cls, datos: dict) -> Carrito:
        """Reconstruye en el servidor el carrito que armó la caja.

        Se reconstruye sin pasar por `agregar`, y es deliberado: `agregar` necesita un
        `Producto` de la base y volvería a validar topes que la caja ya validó. Lo que el
        servidor sí revalida, porque es lo que importa, es el stock y la existencia del
        producto, y eso ocurre dentro de la transacción de `cerrar_venta`.
        """
        carrito = cls()
        for d in datos.get("lineas", []):
            linea = LineaCarrito(
                producto_id=d["producto_id"],
                codigo_barras=d["codigo_barras"],
                nombre=d["nombre"],
                precio_unit_clp=d["precio_unit_clp"],
                cantidad=d["cantidad"],
                descuento_monto_clp=d.get("descuento_monto_clp", 0),
                descuento_porcentaje=d.get("descuento_porcentaje"),
                gramos=d.get("gramos"),
            )
            carrito._lineas[linea.codigo_barras] = linea
        carrito._descuento_monto = datos.get("descuento_monto_clp", 0)
        carrito._descuento_porcentaje = datos.get("descuento_porcentaje")
        return carrito


def cerrar_venta(
    conexion: sqlite3.Connection,
    carrito: Carrito,
    usuario: Usuario | None = None,
    intento_id: str | None = None,
    *,
    caja: str | None = None,
    medio_pago: MedioPago | str | None = MedioPago.EFECTIVO,
    exigir_turno: bool = False,
) -> Venta:
    """Registra la venta y descuenta el stock, todo dentro de una única transacción.

    El stock se vuelve a comprobar aquí, contra la base de datos, y no contra lo que el
    carrito recuerda: entre el escaneo y el cobro pudo cambiar. En monopuesto es improbable,
    pero la comprobación es barata y el día que haya dos cajas será imprescindible.

    Los precios que se guardan son los del carrito, es decir, los que se le mostraron al
    cliente. Si alguien cambió el precio mientras la venta estaba abierta, se respeta lo
    exhibido.

    Args:
        intento_id: identificador único del intento de cobro, generado por la caja. Si ya
            existe una venta con ese identificador, se devuelve **esa** en lugar de crear
            una nueva. Es lo que permite reintentar un cobro cuya respuesta se perdió por la
            red sin cobrarle dos veces al cliente (D-024). En monopuesto se puede omitir.
        caja: nombre de la caja que cobra (fase 16). Lo decide quien llama, no este servicio:
            en modo red la venta la escribe el servidor, pero la hizo la caja secundaria, y es
            su nombre el que tiene que quedar. Solo palabra clave, para que ninguna llamada
            posicional existente cambie de significado.
        medio_pago: con qué pagó el cliente (fase 17). Por defecto efectivo, que es el caso
            dominante. Se acepta el texto porque por la red llega texto; uno que no sea un medio
            conocido se rechaza. None deja la venta con el medio sin registrar.
        exigir_turno: si es True y la caja no está abierta, no se cobra (fase 19, D-036). Lo
            pone la sesión, que es la aplicación; el servicio a secas no lo exige, para no
            obligar a abrir caja a quien lo usa sin interfaz. Con o sin él, la venta queda en
            el turno abierto de su caja, si lo hay: es lo que la cuenta en el arqueo.

    Raises:
        CarritoVacio, StockInsuficiente, DatosInvalidos, CajaCerrada
    """
    if carrito.esta_vacio:
        raise CarritoVacio()
    medio = _validar_medio(medio_pago)

    # Fuera de la transacción a propósito: es una lectura, y el caso normal —que no sea un
    # reintento— no debe pagar el coste de tomar el bloqueo de escritura. El caso de carrera
    # real (dos peticiones con el mismo intento a la vez) lo ataja el índice UNIQUE de abajo.
    if intento_id:
        ya_registrada = repo_ventas.obtener_por_intento(conexion, intento_id)
        if ya_registrada is not None:
            return ya_registrada

    subtotal = carrito.subtotal_clp
    descuento = carrito.descuento_clp
    total = subtotal - descuento

    try:
        venta = _registrar(
            conexion,
            carrito,
            usuario,
            intento_id,
            subtotal,
            descuento,
            total,
            caja,
            medio,
            exigir_turno,
        )
    except sqlite3.IntegrityError:
        # Dos cobros con el mismo intento llegaron a la vez y este perdió la carrera contra el
        # índice UNIQUE. No es un fallo: la venta que la caja quería existe. La transacción ya
        # revirtió, así que basta con devolver la que ganó.
        if intento_id:
            ganadora = repo_ventas.obtener_por_intento(conexion, intento_id)
            if ganadora is not None:
                return ganadora
        raise

    return venta


def _validar_medio(valor: MedioPago | str | None) -> MedioPago | None:
    """El medio de pago como enumerado, o un error legible si no es uno conocido.

    Hace falta porque por la red llega texto arbitrario, y sin esto un "cheque" acabaría
    guardado y saldría como "sin registrar" en el cierre, sin que nadie supiera por qué.
    """
    if valor is None:
        return None
    try:
        return MedioPago(valor)
    except ValueError:
        raise DatosInvalidos(f"Medio de pago desconocido: {valor}.") from None


def _registrar(
    conexion: sqlite3.Connection,
    carrito: Carrito,
    usuario: Usuario | None,
    intento_id: str | None,
    subtotal: int,
    descuento: int,
    total: int,
    caja: str | None = None,
    medio_pago: MedioPago | None = None,
    exigir_turno: bool = False,
) -> Venta:
    """Cuerpo transaccional de `cerrar_venta`. Separado solo para que el manejo del reintento
    duplicado quede legible y fuera de la transacción."""
    with transaccion(conexion):
        # Dentro de la transacción: si la caja se cerrara entre medias desde la otra caja, el
        # bloqueo de escritura hace que esto vea el estado de verdad.
        turno_id = repo_arqueo.id_turno_abierto(conexion, caja) if caja else None
        if exigir_turno and caja and turno_id is None:
            raise CajaCerrada(caja)

        for linea in carrito.lineas:
            producto = repo_productos.obtener_por_id(conexion, linea.producto_id)
            if producto is None or not producto.activo:
                raise DatosInvalidos(
                    f"El producto {linea.nombre} ya no está disponible. Quítelo del carrito."
                )
            # Se decide con el producto de la base, no con lo que diga el carrito: la otra caja
            # pudo armarlo antes de que el dueño cambiara el producto a peso, o al revés.
            if producto.por_peso != linea.por_peso:
                raise DatosInvalidos(
                    f"{linea.nombre} cambió entre venta por peso y por unidad. "
                    "Quítelo del carrito y vuelva a agregarlo."
                )
            if linea.por_peso:
                assert linea.gramos is not None
                _validar_gramos(linea.gramos)
            elif not config.PERMITIR_STOCK_NEGATIVO and producto.stock < linea.cantidad:
                raise StockInsuficiente(producto.nombre, producto.stock, linea.cantidad)

        venta = Venta(
            folio=repo_ventas.siguiente_folio(conexion),
            fecha_hora=datetime.now().replace(microsecond=0),
            subtotal_clp=subtotal,
            descuento_clp=descuento,
            total_clp=total,
            usuario_id=usuario.id if usuario else None,
            usuario_nombre=usuario.nombre if usuario else None,
            intento_id=intento_id,
            caja=caja,
            medio_pago=medio_pago,
            turno_id=turno_id,
            lineas=[
                LineaVenta(
                    producto_id=linea.producto_id,
                    codigo_barras=linea.codigo_barras,
                    nombre=linea.nombre,
                    precio_unit_clp=linea.precio_unit_clp,
                    cantidad=linea.cantidad,
                    subtotal_clp=linea.subtotal_clp,
                    descuento_clp=linea.descuento_clp,
                    gramos=linea.gramos,
                )
                for linea in carrito.lineas
            ],
        )

        repo_ventas.insertar(conexion, venta)
        for linea in carrito.lineas:
            if linea.gramos is not None:
                # El stock de un producto por peso son gramos, y no impide vender (D-037).
                repo_productos.descontar_stock(
                    conexion, linea.producto_id, linea.gramos, sin_bajar_de_cero=True
                )
            else:
                repo_productos.descontar_stock(conexion, linea.producto_id, linea.cantidad)

    return venta
