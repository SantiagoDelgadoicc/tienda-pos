"""Modo de funcionamiento del equipo: servidor, caja secundaria o suelto.

Se guarda en `red.json`, dentro de la carpeta de datos, y se puede editar con el Bloc de
notas. `D-015` pide poder cambiar el modo sin reinstalar, y un archivo de texto es la forma
más simple de cumplirlo y la más fácil de arreglar por teléfono.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from .. import config

_logger = logging.getLogger(__name__)


class Modo(StrEnum):
    #: Un solo PC, sin red. Es el modo por defecto y el de todo lo anterior a la fase 13.
    SUELTO = "suelto"
    #: Dueño de la base de datos. Atiende a su propia interfaz y a las cajas secundarias.
    SERVIDOR = "servidor"
    #: No tiene base de datos: se la pide al servidor.
    CAJA = "caja"


@dataclass(slots=True)
class ConfiguracionRed:
    modo: Modo = Modo.SUELTO
    #: Solo se usa en modo CAJA: dónde está el servidor.
    servidor_host: str = ""
    puerto: int = config.PUERTO_SERVIDOR

    @property
    def usa_red(self) -> bool:
        return self.modo is not Modo.SUELTO


def cargar(ruta: Path | None = None) -> ConfiguracionRed:
    """Lee la configuración de red. Si no existe o está rota, devuelve el modo suelto.

    Nunca lanza: un archivo de configuración corrupto no puede impedir que la tienda abra la
    caja. Se deja constancia en el log y se sigue en el modo más conservador, que es el que
    funciona sin depender de nadie.
    """
    ruta = ruta or config.archivo_configuracion_red()
    if not ruta.exists():
        return ConfiguracionRed()

    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        return ConfiguracionRed(
            modo=Modo(datos.get("modo", Modo.SUELTO)),
            servidor_host=str(datos.get("servidor_host", "")).strip(),
            puerto=int(datos.get("puerto", config.PUERTO_SERVIDOR)),
        )
    except (OSError, ValueError, TypeError):
        _logger.exception("red.json ilegible; se arranca en modo suelto")
        return ConfiguracionRed()


def guardar(configuracion: ConfiguracionRed, ruta: Path | None = None) -> bool:
    """Escribe la configuración. Devuelve si lo consiguió."""
    ruta = ruta or config.archivo_configuracion_red()
    try:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(
            json.dumps(
                {
                    "modo": str(configuracion.modo),
                    "servidor_host": configuracion.servidor_host,
                    "puerto": configuracion.puerto,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return True
    except OSError:
        _logger.exception("No se pudo guardar red.json")
        return False
