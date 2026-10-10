"""Modelos del dominio.

Son estructuras de datos puras: no saben nada de SQLite ni de Qt. Esa separación es lo que
permite probar la lógica de negocio sin abrir una ventana ni crear una base de datos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum


class Rol(StrEnum):
    CAJERO = "cajero"
    ADMIN = "admin"


class EstadoVenta(StrEnum):
    COMPLETADA = "completada"
    ANULADA = "anulada"


class MedioPago(StrEnum):
    """Con qué pagó el cliente (fase 17). Lo marca el cajero al cobrar.

    El cliente los pidió **separados**: efectivo, débito y crédito. Lo que se ve en pantalla
    ("Débito") vive en la interfaz; aquí solo el valor que se guarda.
    """

    EFECTIVO = "efectivo"
    DEBITO = "debito"
    CREDITO = "credito"

    @classmethod
    def leer(cls, valor: object) -> "MedioPago | None":
        """Lo guardado en la base o llegado por la red, **sin fallar** ante lo que no conoce.

        La columna no tiene `CHECK` (migración 5), así que un valor desconocido es posible:
        escrito a mano o por una versión más nueva. Se lee como no registrado, que es lo que
        esta versión sabe de él, en lugar de tumbar el cierre del día.
        """
        if valor in (None, ""):
            return None
        try:
            return cls(valor)
        except ValueError:
            return None


@dataclass(slots=True)
class Producto:
    codigo_barras: str
    nombre: str
    #: Con `por_peso`, es el precio de **un kilo**.
    precio_clp: int
    #: Con `por_peso`, en **gramos**; si no, en unidades.
    stock: int = 0
    activo: bool = True
    id: int | None = None
    creado_en: str | None = None
    actualizado_en: str | None = None
    #: Se vende por peso, como el pan o el jamón (D-037): el precio es por kilo y cada venta
    #: lleva los gramos. Si no, por unidad, como todo lo anterior.
    por_peso: bool = False
    #: Es una cajetilla de cigarros (fase 26, D-040): pagada con débito o crédito, lleva un
    #: recargo fijo por unidad. Nunca a la vez que `por_peso`.
    es_cigarro: bool = False


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
    #: Solo en los productos por peso (D-037): los gramos pesados. Entonces `precio_unit_clp` es
    #: el precio del kilo y `cantidad` vale 1, así que la línea cuenta como un artículo.
    gramos: int | None = None
    #: Copia de `Producto.es_cigarro` al agregarlo (fase 26): cada unidad lleva recargo si se
    #: paga con tarjeta. El servidor lo vuelve a mirar en la base al cobrar.
    es_cigarro: bool = False

    @property
    def por_peso(self) -> bool:
        return self.gramos is not None

    @property
    def subtotal_clp(self) -> int:
        """Importe bruto de la línea, antes de su descuento."""
        if self.gramos is not None:
            from ..utils.money import precio_por_gramos

            return precio_por_gramos(self.precio_unit_clp, self.gramos)
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
    #: Los gramos vendidos, si el producto se vendió por peso (D-037). Entonces
    #: `precio_unit_clp` es el precio del kilo y `cantidad` es 1.
    gramos: int | None = None


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
    #: Con qué se pagó (fase 17). None en las ventas anteriores a la migración 5: no registrado.
    medio_pago: MedioPago | None = None
    #: El turno de caja en que se cobró (fase 19): decide a qué cajón fue el efectivo. None en
    #: las ventas anteriores al arqueo y en las que no llevan caja.
    turno_id: int | None = None
    #: Recargo de los cigarros pagados con tarjeta (fase 26, D-040), ya sumado en `total_clp`:
    #: total = subtotal - descuento + recargo. Cero en efectivo y en las ventas anteriores.
    recargo_clp: int = 0
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


# --------------------------------------------------------------------------- cierre de caja


@dataclass(slots=True)
class TotalPorMedio:
    medio_pago: MedioPago | None  # None: ventas de antes de registrar el medio
    ventas: int
    total_clp: int


@dataclass(slots=True)
class TotalPorEmpleado:
    usuario_id: int | None  # None: ventas de antes de que la sesión fuera obligatoria
    nombre: str | None
    ventas: int
    total_clp: int
    articulos: int


@dataclass(slots=True)
class CierreCaja:
    """El cierre diario de una caja (fase 18): lo que pidió el cliente.

    Es un informe que se calcula al pedirlo, no un registro guardado: no cierra nada ni
    bloquea la caja. Los totales **se derivan de `ventas`**, la misma lista que se enseña venta
    por venta, en lugar de pedirse con consultas aparte. Así la suma por medio, la suma por
    empleado y el total salen siempre iguales —por construcción, no por cuidado—, y por la red
    viaja una sola cosa.
    """

    dia: date
    #: La caja del informe. None es el grupo de ventas anteriores a registrar la caja.
    caja: str | None
    #: Las ventas completadas de esa caja ese día, de la más reciente a la más antigua, con sus
    #: líneas cargadas: el cliente quiere ver qué productos llevó cada venta.
    ventas: list[Venta] = field(default_factory=list)
    #: Las cajas que vendieron ese día, para poder mirar la otra.
    cajas_del_dia: list[str | None] = field(default_factory=list)

    @property
    def total_clp(self) -> int:
        return sum(v.total_clp for v in self.ventas)

    @property
    def cantidad_ventas(self) -> int:
        return len(self.ventas)

    @property
    def articulos(self) -> int:
        return sum(v.cantidad_articulos for v in self.ventas)

    @property
    def por_medio(self) -> list[TotalPorMedio]:
        """Los tres medios siempre, aunque sea en cero: "débito $0" también es información. Las
        ventas sin medio registrado aparecen al final, y solo si las hay."""
        filas = {medio: TotalPorMedio(medio, 0, 0) for medio in MedioPago}
        sin_registrar = TotalPorMedio(None, 0, 0)
        for venta in self.ventas:
            fila = filas.get(venta.medio_pago, sin_registrar)
            fila.ventas += 1
            fila.total_clp += venta.total_clp
        return list(filas.values()) + ([sin_registrar] if sin_registrar.ventas else [])

    @property
    def por_empleado(self) -> list[TotalPorEmpleado]:
        """Quién vendió cuánto en esta caja, de más a menos."""
        filas: dict[int | None, TotalPorEmpleado] = {}
        for venta in self.ventas:
            fila = filas.setdefault(
                venta.usuario_id,
                TotalPorEmpleado(venta.usuario_id, venta.usuario_nombre, 0, 0, 0),
            )
            fila.ventas += 1
            fila.total_clp += venta.total_clp
            fila.articulos += venta.cantidad_articulos
        return sorted(filas.values(), key=lambda f: (-f.total_clp, f.nombre or ""))


# --------------------------------------------------------------------------- arqueo de caja


class TipoMovimiento(StrEnum):
    """Lo que entra o sale del cajón sin ser una venta (fase 19, D-036)."""

    #: El dueño saca plata. Solo con PIN de administrador.
    RETIRO = "retiro"
    #: Se le paga en efectivo a un proveedor, desde la caja. Lo anota quien atiende.
    PAGO_PROVEEDOR = "pago_proveedor"
    #: Se agrega sencillo.
    INGRESO = "ingreso"

    @property
    def es_salida(self) -> bool:
        return self is not TipoMovimiento.INGRESO

    @classmethod
    def leer(cls, valor: object) -> "TipoMovimiento | None":
        """Como `MedioPago.leer`: lo desconocido no tumba la pantalla, se lee como None."""
        try:
            return cls(valor)
        except ValueError:
            return None


@dataclass(slots=True)
class MovimientoEfectivo:
    """Una salida o entrada de efectivo del cajón. No se borra ni se edita."""

    turno_id: int
    tipo: TipoMovimiento | None  # None: un tipo que esta versión no conoce
    monto_clp: int
    motivo: str
    usuario_id: int
    fecha_hora: datetime
    usuario_nombre: str | None = None
    id: int | None = None
    intento_id: str | None = None

    @property
    def efecto_clp(self) -> int:
        """Cuánto cambia el efectivo del cajón: negativo si sale. Un tipo desconocido cuenta
        como salida, que es lo prudente: nunca aumenta lo que "debería haber"."""
        return self.monto_clp if self.tipo is TipoMovimiento.INGRESO else -self.monto_clp


@dataclass(slots=True)
class TurnoCaja:
    """Una caja abierta con el efectivo que tenía, y cerrada contándolo (fase 19, D-036).

    `ventas_efectivo_clp` es None cuando quien pregunta no es administrador: el conteo es a
    ciegas, y sin esa cifra no se puede calcular cuánto debería haber. El servidor no la manda,
    así que tampoco se puede ver desde la otra caja.
    """

    caja: str
    abierto_en: datetime
    abierto_por_id: int
    apertura_clp: int
    id: int | None = None
    abierto_por_nombre: str | None = None
    #: Suma de las ventas en efectivo del turno, y cuántas son. None: no visible para quien pide.
    ventas_efectivo_clp: int | None = None
    ventas_efectivo: int | None = None
    movimientos: list[MovimientoEfectivo] = field(default_factory=list)
    cerrado_en: datetime | None = None
    cerrado_por_id: int | None = None
    cerrado_por_nombre: str | None = None
    #: Lo que debería haber al cerrar, guardado en ese momento. None si está abierto o no visible.
    esperado_al_cerrar_clp: int | None = None
    contado_clp: int | None = None
    nota: str | None = None

    @property
    def abierto(self) -> bool:
        return self.cerrado_en is None

    def _suma(self, *tipos: TipoMovimiento) -> int:
        return sum(m.monto_clp for m in self.movimientos if m.tipo in tipos)

    @property
    def retiros_clp(self) -> int:
        return self._suma(TipoMovimiento.RETIRO)

    @property
    def pagos_clp(self) -> int:
        return self._suma(TipoMovimiento.PAGO_PROVEEDOR)

    @property
    def ingresos_clp(self) -> int:
        return self._suma(TipoMovimiento.INGRESO)

    @property
    def esperado_clp(self) -> int | None:
        """Cuánto debería haber en el cajón ahora: apertura + ventas en efectivo + ingresos −
        salidas. El vuelto no entra: sale del mismo cajón y el neto es el total de la venta.

        Cerrado, es lo guardado al cerrar. None si quien pregunta no puede verlo.
        """
        if not self.abierto:
            return self.esperado_al_cerrar_clp
        if self.ventas_efectivo_clp is None:
            return None
        return (
            self.apertura_clp
            + self.ventas_efectivo_clp
            + sum(m.efecto_clp for m in self.movimientos)
        )

    @property
    def diferencia_clp(self) -> int | None:
        """Contado menos esperado: negativo si falta plata, positivo si sobra."""
        if self.contado_clp is None or self.esperado_al_cerrar_clp is None:
            return None
        return self.contado_clp - self.esperado_al_cerrar_clp
