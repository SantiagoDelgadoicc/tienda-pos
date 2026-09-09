"""Avisos sonoros.

En una caja se trabaja mirando al cliente y a los productos, no a la pantalla. El sonido es
lo que confirma que el escaneo entró, y es la razón por la que las cajas de supermercado
pitan. Dos sonidos distintos: uno para "entró" y otro para "algo pasó".

Nunca bloquean: un pitido que detiene la interfaz medio segundo por producto haría el
sistema más lento que apuntar los precios a mano.
"""

from __future__ import annotations

import logging

_logger = logging.getLogger(__name__)

#: Permite silenciar los sonidos por completo (pruebas, o si al cliente le molestan).
habilitado = True

try:  # pragma: no cover - depende del sistema operativo
    import winsound

    _WINDOWS = True
except ImportError:  # pragma: no cover
    winsound = None  # type: ignore[assignment]
    _WINDOWS = False


def _emitir(tipo_windows: int) -> None:
    if not habilitado:
        return
    try:
        if _WINDOWS:
            # MessageBeep es asíncrono y usa los sonidos del sistema, que el usuario ya
            # reconoce. winsound.Beep, en cambio, bloquea el hilo mientras suena.
            winsound.MessageBeep(tipo_windows)
        else:
            from PySide6.QtWidgets import QApplication

            aplicacion = QApplication.instance()
            if aplicacion is not None:
                aplicacion.beep()
    except Exception:  # pragma: no cover - un pitido nunca debe tumbar la aplicación
        _logger.debug("No se pudo emitir el aviso sonoro", exc_info=True)


def exito() -> None:
    """Producto reconocido y agregado."""
    _emitir(0)  # MB_OK


def error() -> None:
    """Código no encontrado o acción rechazada."""
    _emitir(0x10)  # MB_ICONHAND


def silenciar() -> None:
    global habilitado
    habilitado = False
