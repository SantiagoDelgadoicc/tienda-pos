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


def cerrar_limpiamente(conexion: sqlite3.Connection) -> None:
    """Deja el archivo `.db` autocontenido antes de cerrar.

    En modo WAL, lo que se ha escrito vive en `tienda.db-wal` hasta que SQLite lo integra en
    el archivo principal. Mientras tanto, **copiar solo `tienda.db` produce una base vacía**:
    comprobado, y es silencioso, que es lo peligroso. Un `wal_checkpoint(TRUNCATE)` al cerrar
    integra todo y vacía el `-wal`, de modo que a partir de ahí copiar el `.db` a un pendrive
    es seguro aunque quien lo haga no sepa nada de esto.

    No lanza: un fallo aquí no puede impedir que el programa cierre.
    """
    try:
        conexion.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    except sqlite3.Error:
        _logger.warning("No se pudo integrar el WAL al cerrar", exc_info=True)


def listar_respaldos(carpeta: Path | None = None) -> list[Path]:
    """Respaldos existentes, del más reciente al más antiguo."""
    carpeta = carpeta or config.directorio_respaldos()
    if not carpeta.exists():
        return []
    return sorted(carpeta.glob(f"{_PREFIJO}*.db"), reverse=True)


def _limpiar_antiguos(carpeta: Path, conservar: int, dias: int | None = None) -> None:
    """Borra los respaldos que sobran: se quedan los `conservar` más recientes y, además, el
    último de cada uno de los `dias` días más recientes con respaldo.

    Lo segundo existe porque se respalda al abrir y al cerrar el programa: con solo los últimos
    siete, un día con varios arranques se llevaba por delante la semana entera.

    El nombre lleva la fecha en formato ordenable, así que ordenar por nombre equivale a
    ordenar por antigüedad sin tener que consultar el sistema de archivos.
    """
    dias = config.RESPALDOS_DIAS if dias is None else dias
    respaldos = listar_respaldos(carpeta)
    quedan = set(respaldos[:conservar])
    dias_vistos: set[str] = set()
    for archivo in respaldos:  # del más reciente al más antiguo
        dia = archivo.name[len(_PREFIJO) : len(_PREFIJO) + 8]
        if dia not in dias_vistos and len(dias_vistos) < dias:
            dias_vistos.add(dia)
            quedan.add(archivo)

    sobrantes = [archivo for archivo in respaldos if archivo not in quedan]
    for archivo in sobrantes:
        try:
            archivo.unlink()
            _logger.info("Respaldo antiguo eliminado: %s", archivo.name)
        except OSError:
            _logger.warning("No se pudo eliminar el respaldo %s", archivo.name)
