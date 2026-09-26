"""Manejador global de errores inesperados.

Regla del proyecto: la aplicación no se cierra sola. Un fallo no previsto se registra en el
log, se le explica al usuario en lenguaje llano y la caja sigue abierta. Cerrarse a mitad de
una venta es la peor cosa que puede hacer un punto de venta.

Los errores del dominio (código inválido, sin stock, sin permiso) no llegan hasta aquí: los
atienden las pantallas, que saben explicarlos en su contexto. Aquí solo llega lo que nadie
previó.
"""

from __future__ import annotations

import logging
import sys
import time
import traceback
from types import TracebackType

from PySide6.QtWidgets import QApplication, QMessageBox

from .. import config

_logger = logging.getLogger(__name__)

# Si algo falla en bucle (por ejemplo dentro de un repintado), mostrar un diálogo por cada
# error dejaría la pantalla inutilizable. Pasado este límite se sigue registrando todo en el
# log, pero se deja de interrumpir al usuario.
_MAX_DIALOGOS = 3
_VENTANA_SEGUNDOS = 30

_mostrados: list[float] = []

#: Si ya hay un aviso de error abierto. Ver `manejar_excepcion`.
_mostrando = False


def _puede_mostrar_dialogo() -> bool:
    ahora = time.monotonic()
    _mostrados[:] = [t for t in _mostrados if ahora - t < _VENTANA_SEGUNDOS]
    if len(_mostrados) >= _MAX_DIALOGOS:
        return False
    _mostrados.append(ahora)
    return True


def _resumir(excepcion: BaseException) -> str:
    """Una línea entendible por alguien que no programa."""
    texto = str(excepcion).strip()
    return texto or excepcion.__class__.__name__


def manejar_excepcion(
    tipo: type[BaseException],
    valor: BaseException,
    traza: TracebackType | None,
) -> None:
    """Reemplaza a sys.excepthook."""
    if issubclass(tipo, KeyboardInterrupt):  # pragma: no cover - solo desde la consola
        sys.__excepthook__(tipo, valor, traza)
        return

    _logger.critical(
        "Error no controlado:\n%s", "".join(traceback.format_exception(tipo, valor, traza))
    )

    global _mostrando
    # Con un aviso ya abierto, el siguiente error solo se anota (fase 23). Un error que se
    # repite en cada evento abría un aviso dentro de otro, cada uno con su propio bucle de
    # eventos, y la caja quedaba congelada con "No responde".
    if QApplication.instance() is None or _mostrando or not _puede_mostrar_dialogo():
        return

    caja = QMessageBox()
    caja.setIcon(QMessageBox.Icon.Critical)
    caja.setWindowTitle("Ocurrió un error")
    caja.setText(
        "Ocurrió un error inesperado, pero el programa sigue funcionando.\n\n"
        "Si estaba a mitad de una venta, revise el carrito antes de cobrar."
    )
    caja.setInformativeText(
        f"Detalle: {_resumir(valor)}\n\n"
        f"Se guardó un informe en:\n{config.directorio_logs() / 'tienda_pos.log'}"
    )
    caja.setStandardButtons(QMessageBox.StandardButton.Ok)
    caja.button(QMessageBox.StandardButton.Ok).setText("Continuar")
    _mostrando = True
    try:
        caja.exec()
    finally:
        _mostrando = False


def instalar() -> None:
    """Activa el manejador global. Idempotente."""
    sys.excepthook = manejar_excepcion


def reiniciar_contador() -> None:
    """Solo para pruebas: olvida los diálogos ya mostrados."""
    _mostrados.clear()
