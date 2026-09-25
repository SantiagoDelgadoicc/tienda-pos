"""Errores del dominio.

Todos heredan de ErrorDominio para que la interfaz pueda distinguir entre "el usuario hizo
algo que no corresponde" (se muestra un mensaje amable) y "algo se rompió de verdad" (se
registra en el log y se muestra el diálogo de error).

Cada error lleva un mensaje ya redactado para mostrarse tal cual en pantalla: el cajero no
tiene por qué leer jerga técnica.
"""

from __future__ import annotations


class ErrorDominio(Exception):
    """Base de todos los errores previsibles del negocio."""


class CodigoInvalido(ErrorDominio):
    def __init__(self, codigo: str) -> None:
        self.codigo = codigo
        super().__init__("El código leído no es válido. Intente escanear de nuevo.")


class ProductoNoEncontrado(ErrorDominio):
    def __init__(self, codigo: str) -> None:
        self.codigo = codigo
        super().__init__(f"No hay ningún producto con el código {codigo}.")


class ProductoDuplicado(ErrorDominio):
    def __init__(self, codigo: str) -> None:
        self.codigo = codigo
        super().__init__(f"Ya existe un producto con el código {codigo}.")


class DatosInvalidos(ErrorDominio):
    """El usuario dejó un campo vacío o escribió algo que no corresponde."""


class StockInsuficiente(ErrorDominio):
    def __init__(self, nombre: str, disponible: int, solicitado: int) -> None:
        self.nombre = nombre
        self.disponible = disponible
        self.solicitado = solicitado
        super().__init__(
            f"No hay stock suficiente de {nombre}: quedan {disponible} y se piden {solicitado}."
        )


class CarritoVacio(ErrorDominio):
    def __init__(self) -> None:
        super().__init__("No se puede cerrar una venta sin productos.")


class DescuentoInvalido(ErrorDominio):
    """El descuento es negativo o supera el total de la venta."""


class CredencialesInvalidas(ErrorDominio):
    def __init__(self) -> None:
        super().__init__("Usuario o PIN incorrecto.")


class PermisoDenegado(ErrorDominio):
    def __init__(self, accion: str) -> None:
        self.accion = accion
        super().__init__(f"Se requiere permiso de administrador para {accion}.")


class CajaCerrada(ErrorDominio):
    """Se intentó cobrar o anotar efectivo con la caja sin abrir (fase 19, D-036).

    Tiene tipo propio, y no es un `DatosInvalidos`, porque la pantalla de venta lo trata distinto:
    en vez de un aviso, ofrece abrir la caja ahí mismo.
    """

    def __init__(self, caja: str | None = None) -> None:
        self.caja = caja
        super().__init__(
            "La caja está cerrada. Ábrala con el efectivo que hay en el cajón para seguir."
        )

