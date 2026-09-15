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
    CodigoNoEncontrado,
    EstadoVenta,
    LineaVenta,
    Producto,
    Rol,
    Usuario,
    Venta,
)

_FORMATO_FECHA_HORA = "%Y-%m-%d %H:%M:%S"

#: Versión del protocolo. Sube cuando cambia la forma de los mensajes, que no es lo mismo que
#: la versión del esquema de la base: dos programas pueden entenderse hablando y aun así tener
#: bases incompatibles, y al revés. Se comprueban las dos al conectar.
VERSION_PROTOCOLO = 1


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
