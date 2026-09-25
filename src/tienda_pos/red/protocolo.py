"""Traducción entre los objetos de dominio y el JSON que viaja por la red.

La conversión se escribe a mano, campo por campo, por el mismo motivo por el que el SQL se
escribe a mano (`D-003`): es el contrato entre dos programas que pueden tener versiones
distintas, y conviene que sea explícito y fácil de leer. `dataclasses.asdict` habría sido más
corto y habría convertido cualquier cambio de un modelo en un cambio silencioso del protocolo.

Este módulo **no importa Qt ni sqlite3**: solo conoce el dominio.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from ..domain import errors
from ..domain.models import (
    CierreCaja,
    CodigoNoEncontrado,
    EstadoVenta,
    LineaVenta,
    MedioPago,
    MovimientoEfectivo,
    Producto,
    Rol,
    TipoMovimiento,
    TurnoCaja,
    Usuario,
    Venta,
)

_FORMATO_FECHA_HORA = "%Y-%m-%d %H:%M:%S"

#: Versión del protocolo. Sube cuando cambia la forma de los mensajes, que no es lo mismo que
#: la versión del esquema de la base: dos programas pueden entenderse hablando y aun así tener
#: bases incompatibles, y al revés. Se comprueban las dos al conectar.
#:
#: Sube también cuando se **añaden** operaciones, aunque las viejas no cambien. Sin eso, una caja
#: actualizada conectaría con un servidor viejo y fallaría más tarde, en la pantalla que usa la
#: operación nueva y con un "Operación desconocida" delante del dueño. Subiéndola, la
#: actualización a medias se detecta al arrancar, con el aviso de `VersionIncompatible`.
#:
#: Historia: 1, dos cajas (fase 13) · 2, administración de usuarios (fase 15) · 3, cada venta
#: dice de qué caja viene (fase 16) · 4, y con qué se pagó (fase 17) · 5, el cierre por caja
#: (fase 18) · 6, el arqueo de caja (fase 19) · 7, la venta por peso (D-037).
VERSION_PROTOCOLO = 7


# --------------------------------------------------------------------------- dominio → JSON


def de_producto(p: Producto) -> dict[str, Any]:
    return {
        "id": p.id,
        "codigo_barras": p.codigo_barras,
        "nombre": p.nombre,
        "precio_clp": p.precio_clp,
        "stock": p.stock,
        "activo": p.activo,
        "creado_en": p.creado_en,
        "actualizado_en": p.actualizado_en,
        "por_peso": p.por_peso,
    }


def de_usuario(u: Usuario) -> dict[str, Any]:
    # Nunca se serializan ni el hash del PIN ni la sal: no están en el modelo, y esta función
    # es la razón por la que conviene que sigan sin estarlo.
    return {"id": u.id, "nombre": u.nombre, "rol": str(u.rol), "activo": u.activo}


def de_linea_venta(linea: LineaVenta) -> dict[str, Any]:
    return {
        "id": linea.id,
        "venta_id": linea.venta_id,
        "producto_id": linea.producto_id,
        "codigo_barras": linea.codigo_barras,
        "nombre": linea.nombre,
        "precio_unit_clp": linea.precio_unit_clp,
        "cantidad": linea.cantidad,
        "subtotal_clp": linea.subtotal_clp,
        "descuento_clp": linea.descuento_clp,
        "gramos": linea.gramos,
    }


def de_venta(v: Venta) -> dict[str, Any]:
    return {
        "id": v.id,
        "folio": v.folio,
        "fecha_hora": v.fecha_hora.strftime(_FORMATO_FECHA_HORA),
        "subtotal_clp": v.subtotal_clp,
        "descuento_clp": v.descuento_clp,
        "total_clp": v.total_clp,
        "usuario_id": v.usuario_id,
        "usuario_nombre": v.usuario_nombre,
        "estado": str(v.estado),
        "intento_id": v.intento_id,
        "caja": v.caja,
        "medio_pago": str(v.medio_pago) if v.medio_pago else None,
        "turno_id": v.turno_id,
        "lineas": [de_linea_venta(linea) for linea in v.lineas],
    }


def de_codigo_pendiente(c: CodigoNoEncontrado) -> dict[str, Any]:
    return {
        "codigo": c.codigo,
        "intentos": c.intentos,
        "primera_vez": c.primera_vez,
        "ultima_vez": c.ultima_vez,
        "resuelto": c.resuelto,
    }


# --------------------------------------------------------------------------- JSON → dominio


def a_producto(d: dict[str, Any]) -> Producto:
    return Producto(
        id=d["id"],
        codigo_barras=d["codigo_barras"],
        nombre=d["nombre"],
        precio_clp=d["precio_clp"],
        stock=d["stock"],
        activo=d["activo"],
        creado_en=d.get("creado_en"),
        actualizado_en=d.get("actualizado_en"),
        por_peso=bool(d.get("por_peso", False)),
    )


def a_usuario(d: dict[str, Any]) -> Usuario:
    return Usuario(id=d["id"], nombre=d["nombre"], rol=Rol(d["rol"]), activo=d["activo"])


def a_linea_venta(d: dict[str, Any]) -> LineaVenta:
    return LineaVenta(
        id=d.get("id"),
        venta_id=d.get("venta_id"),
        producto_id=d.get("producto_id"),
        codigo_barras=d["codigo_barras"],
        nombre=d["nombre"],
        precio_unit_clp=d["precio_unit_clp"],
        cantidad=d["cantidad"],
        subtotal_clp=d["subtotal_clp"],
        descuento_clp=d.get("descuento_clp", 0),
        gramos=d.get("gramos"),
    )


def a_venta(d: dict[str, Any]) -> Venta:
    return Venta(
        id=d["id"],
        folio=d["folio"],
        fecha_hora=datetime.strptime(d["fecha_hora"], _FORMATO_FECHA_HORA),
        subtotal_clp=d["subtotal_clp"],
        descuento_clp=d["descuento_clp"],
        total_clp=d["total_clp"],
        usuario_id=d.get("usuario_id"),
        usuario_nombre=d.get("usuario_nombre"),
        estado=EstadoVenta(d["estado"]),
        intento_id=d.get("intento_id"),
        caja=d.get("caja"),
        medio_pago=MedioPago.leer(d.get("medio_pago")),
        turno_id=d.get("turno_id"),
        lineas=[a_linea_venta(x) for x in d.get("lineas", [])],
    )


def a_codigo_pendiente(d: dict[str, Any]) -> CodigoNoEncontrado:
    return CodigoNoEncontrado(
        codigo=d["codigo"],
        intentos=d["intentos"],
        primera_vez=d["primera_vez"],
        ultima_vez=d["ultima_vez"],
        resuelto=d["resuelto"],
    )


def de_fecha(d: date | None) -> str | None:
    return d.isoformat() if d else None


def a_fecha(s: str | None) -> date | None:
    return date.fromisoformat(s) if s else None


# ------------------------------------------------------------------------------- errores

#: Errores del dominio que pueden cruzar la red. Se envían por nombre y se vuelven a levantar
#: en la caja, de modo que `except ProductoNoEncontrado` siga funcionando igual que en local.
#: Es lo que permite que `D-024` no obligue a reescribir el manejo de errores de la interfaz.
_ERRORES: dict[str, type[errors.ErrorDominio]] = {
    clase.__name__: clase
    for clase in (
        errors.CodigoInvalido,
        errors.ProductoNoEncontrado,
        errors.ProductoDuplicado,
        errors.DatosInvalidos,
        errors.StockInsuficiente,
        errors.CarritoVacio,
        errors.DescuentoInvalido,
        errors.CredencialesInvalidas,
        errors.PermisoDenegado,
        errors.CajaCerrada,
    )
}


def de_error(exc: errors.ErrorDominio) -> dict[str, Any]:
    """Serializa un error del dominio conservando su tipo y su mensaje ya redactado."""
    return {"tipo": type(exc).__name__, "mensaje": str(exc)}


def levantar_error(d: dict[str, Any]) -> None:
    """Vuelve a levantar en la caja el error que ocurrió en el servidor.

    El mensaje viaja ya redactado y se usa tal cual, en lugar de reconstruir el error con sus
    argumentos originales: así un servidor más nuevo puede mejorar un texto sin que la caja
    tenga que actualizarse, y nunca se pierde el mensaje por no saber rehacer el constructor.
    """
    clase = _ERRORES.get(d.get("tipo", ""), errors.ErrorDominio)
    raise _construir(clase, d.get("mensaje", ""))


def _construir(clase: type[errors.ErrorDominio], mensaje: str) -> errors.ErrorDominio:
    """Crea la excepción sin pasar por su `__init__`, que espera argumentos que no viajan.

    Se instancia con `__new__` y se le fija el mensaje a mano. Es deliberado: reconstruir
    `StockInsuficiente(nombre, disponible, solicitado)` exigiría transportar sus tres campos y
    mantenerlos sincronizados para siempre, cuando lo único que la interfaz hace con el error
    es mostrar su texto.
    """
    exc = clase.__new__(clase)
    errors.ErrorDominio.__init__(exc, mensaje)
    return exc


# --------------------------------------------------------------------------- cierre de caja


def de_cierre(c: CierreCaja) -> dict[str, Any]:
    """Solo lo que no se puede derivar: los totales los recalcula `CierreCaja` al otro lado,
    de las mismas ventas, así que no hay dos versiones de la cifra que puedan discrepar."""
    return {
        "dia": de_fecha(c.dia),
        "caja": c.caja,
        "ventas": [de_venta(v) for v in c.ventas],
        "cajas_del_dia": list(c.cajas_del_dia),
    }


def a_cierre(d: dict[str, Any]) -> CierreCaja:
    return CierreCaja(
        dia=a_fecha(d["dia"]),
        caja=d.get("caja"),
        ventas=[a_venta(v) for v in d.get("ventas", [])],
        cajas_del_dia=list(d.get("cajas_del_dia", [])),
    )


# --------------------------------------------------------------------------- arqueo de caja


def _de_momento(m: datetime | None) -> str | None:
    return m.strftime(_FORMATO_FECHA_HORA) if m else None


def _a_momento(s: str | None) -> datetime | None:
    return datetime.strptime(s, _FORMATO_FECHA_HORA) if s else None


def de_movimiento(m: MovimientoEfectivo) -> dict[str, Any]:
    return {
        "id": m.id,
        "turno_id": m.turno_id,
        "tipo": str(m.tipo) if m.tipo else None,
        "monto_clp": m.monto_clp,
        "motivo": m.motivo,
        "usuario_id": m.usuario_id,
        "usuario_nombre": m.usuario_nombre,
        "fecha_hora": _de_momento(m.fecha_hora),
        "intento_id": m.intento_id,
    }


def a_movimiento(d: dict[str, Any]) -> MovimientoEfectivo:
    return MovimientoEfectivo(
        id=d.get("id"),
        turno_id=d["turno_id"],
        tipo=TipoMovimiento.leer(d.get("tipo")),
        monto_clp=d["monto_clp"],
        motivo=d.get("motivo", ""),
        usuario_id=d["usuario_id"],
        usuario_nombre=d.get("usuario_nombre"),
        fecha_hora=_a_momento(d["fecha_hora"]),
        intento_id=d.get("intento_id"),
    )


def de_turno(t: TurnoCaja) -> dict[str, Any]:
    """Tal como lo devolvió el servicio: si quien pidió no es administrador, las cifras del
    conteo a ciegas ya vienen en None y así viajan (D-036)."""
    return {
        "id": t.id,
        "caja": t.caja,
        "abierto_en": _de_momento(t.abierto_en),
        "abierto_por_id": t.abierto_por_id,
        "abierto_por_nombre": t.abierto_por_nombre,
        "apertura_clp": t.apertura_clp,
        "ventas_efectivo_clp": t.ventas_efectivo_clp,
        "ventas_efectivo": t.ventas_efectivo,
        "movimientos": [de_movimiento(m) for m in t.movimientos],
        "cerrado_en": _de_momento(t.cerrado_en),
        "cerrado_por_id": t.cerrado_por_id,
        "cerrado_por_nombre": t.cerrado_por_nombre,
        "esperado_al_cerrar_clp": t.esperado_al_cerrar_clp,
        "contado_clp": t.contado_clp,
        "nota": t.nota,
    }


def a_turno(d: dict[str, Any]) -> TurnoCaja:
    return TurnoCaja(
        id=d.get("id"),
        caja=d["caja"],
        abierto_en=_a_momento(d["abierto_en"]),
        abierto_por_id=d["abierto_por_id"],
        abierto_por_nombre=d.get("abierto_por_nombre"),
        apertura_clp=d["apertura_clp"],
        ventas_efectivo_clp=d.get("ventas_efectivo_clp"),
        ventas_efectivo=d.get("ventas_efectivo"),
        movimientos=[a_movimiento(m) for m in d.get("movimientos", [])],
        cerrado_en=_a_momento(d.get("cerrado_en")),
        cerrado_por_id=d.get("cerrado_por_id"),
        cerrado_por_nombre=d.get("cerrado_por_nombre"),
        esperado_al_cerrar_clp=d.get("esperado_al_cerrar_clp"),
        contado_clp=d.get("contado_clp"),
        nota=d.get("nota"),
    )
