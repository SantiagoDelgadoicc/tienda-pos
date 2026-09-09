"""Respaldos automáticos de la base de datos.

Se hace una copia al iniciar la aplicación. Es la protección más barata que existe contra el
peor escenario realista de una tienda: el archivo se corrompe por un corte de luz y con él se
va el catálogo entero y el historial de ventas.

Se usa la API `backup` de SQLite y no una copia del archivo. En modo WAL, copiar el `.db` a
secas puede dejar fuera transacciones que todavía viven en el archivo `-wal`, produciendo un
respaldo silenciosamente incompleto: el peor tipo de respaldo, el que parece existir.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime
from pathlib import Path

from .. import config
from .connection import conectar

_logger = logging.getLogger(__name__)

_PATRON = "tienda-%Y%m%d-%H%M%S.db"
_PREFIJO = "tienda-"


def crear_respaldo(
    origen: Path | str | None = None,
    carpeta: Path | None = None,
    conservar: int | None = None,
) -> Path | None:
    """Copia la base de datos y elimina los respaldos más antiguos.

    Devuelve la ruta del respaldo creado, o None si no había base que copiar.

    No lanza excepciones al llamador: que falle un respaldo es motivo para dejar constancia
    en el log, no para impedir que la tienda abra la caja.
    """
    origen = Path(origen) if origen else config.ruta_base_datos()
    carpeta = carpeta or config.directorio_respaldos()
    conservar = conservar if conservar is not None else config.RESPALDOS_A_CONSERVAR

    if not origen.exists():
        return None

    carpeta.mkdir(parents=True, exist_ok=True)
    destino = carpeta / datetime.now().strftime(_PATRON)

    try:
        conexion_origen = conectar(origen)
        try:
            conexion_destino = sqlite3.connect(str(destino))
            try:
                conexion_origen.backup(conexion_destino)
            finally:
                conexion_destino.close()
        finally:
            conexion_origen.close()
    except Exception:
        _logger.exception("No se pudo crear el respaldo en %s", destino)
        # Un respaldo a medias es peor que ninguno: se borra.
        destino.unlink(missing_ok=True)
        return None

    _logger.info("Respaldo creado: %s", destino.name)
    _limpiar_antiguos(carpeta, conservar)
    return destino


def listar_respaldos(carpeta: Path | None = None) -> list[Path]:
    """Respaldos existentes, del más reciente al más antiguo."""
    carpeta = carpeta or config.directorio_respaldos()
    if not carpeta.exists():
        return []
    return sorted(carpeta.glob(f"{_PREFIJO}*.db"), reverse=True)


def _limpiar_antiguos(carpeta: Path, conservar: int) -> None:
    """Borra los respaldos que sobran, empezando por el más antiguo.

    El nombre lleva la fecha en formato ordenable, así que ordenar por nombre equivale a
    ordenar por antigüedad sin tener que consultar el sistema de archivos.
    """
    sobrantes = listar_respaldos(carpeta)[conservar:]
    for archivo in sobrantes:
        try:
            archivo.unlink()
            _logger.info("Respaldo antiguo eliminado: %s", archivo.name)
        except OSError:
            _logger.warning("No se pudo eliminar el respaldo %s", archivo.name)
