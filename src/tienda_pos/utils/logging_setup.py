"""Registro de sucesos.

Cuando algo falla en la caja de una tienda no hay un programador delante. El log es lo único
que permitirá reconstruir después qué pasó, así que se escribe siempre a disco y sobrevive a
los reinicios.

Rota por tamaño para que no crezca sin límite: un archivo de log que llena el disco de la
tienda sería un problema peor que el que pretende documentar.
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path

from .. import config

_TAMANO_MAX_BYTES = 1_000_000
_ARCHIVOS_A_CONSERVAR = 5
_FORMATO = "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s"

_configurado = False


def configurar(nivel: int = logging.INFO, carpeta: Path | None = None) -> Path:
    """Deja el registro listo. Es idempotente: llamarlo dos veces no duplica los mensajes.

    Devuelve la ruta del archivo de log.
    """
    global _configurado

    carpeta = carpeta or config.directorio_logs()
    carpeta.mkdir(parents=True, exist_ok=True)
    archivo = carpeta / "tienda_pos.log"

    if _configurado:
        return archivo

    raiz = logging.getLogger()
    raiz.setLevel(nivel)

    a_disco = logging.handlers.RotatingFileHandler(
        archivo,
        maxBytes=_TAMANO_MAX_BYTES,
        backupCount=_ARCHIVOS_A_CONSERVAR,
        encoding="utf-8",
    )
    a_disco.setFormatter(logging.Formatter(_FORMATO))
    raiz.addHandler(a_disco)

    # En desarrollo conviene ver los mensajes en la consola; en el ejecutable empaquetado no
    # hay consola y este manejador simplemente no molesta.
    a_consola = logging.StreamHandler(sys.stderr)
    a_consola.setFormatter(logging.Formatter("%(levelname)-8s %(message)s"))
    a_consola.setLevel(logging.WARNING)
    raiz.addHandler(a_consola)

    _configurado = True
    logging.getLogger(__name__).info(
        "Registro iniciado · %s %s", config.NOMBRE_COMERCIAL, config.VERSION
    )
    return archivo


def reiniciar_para_pruebas() -> None:
    """Permite que las pruebas vuelvan a configurar el registro desde cero."""
    global _configurado

    raiz = logging.getLogger()
    for manejador in list(raiz.handlers):
        manejador.close()
        raiz.removeHandler(manejador)
    _configurado = False
