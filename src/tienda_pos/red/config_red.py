"""Modo de funcionamiento del equipo: servidor, caja secundaria o suelto.

Se guarda en `red.json`, dentro de la carpeta de datos, y se puede editar con el Bloc de
notas. `D-015` pide poder cambiar el modo sin reinstalar, y un archivo de texto es la forma
más simple de cumplirlo y la más fácil de arreglar por teléfono.
"""

from __future__ import annotations

import json
import logging
import platform
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


#: Tope del nombre de una caja. Lo escribe una persona en `red.json`, a mano o en el instalador.
LARGO_MAX_NOMBRE_CAJA = 40


def normalizar_nombre_caja(texto: object) -> str:
    """Espacios de sobra fuera y un tope de largo. Nunca falla: es un dato de informe."""
    return " ".join(str(texto or "").split())[:LARGO_MAX_NOMBRE_CAJA]


@dataclass(slots=True)
class ConfiguracionRed:
    modo: Modo = Modo.SUELTO
    #: Solo se usa en modo CAJA: dónde está el servidor.
    servidor_host: str = ""
    puerto: int = config.PUERTO_SERVIDOR
    #: Cómo se llama esta caja en el cierre: "Caja 1", "Mostrador". Lo decide el cliente y se
    #: escribe el día de la instalación. Vacío, se usa el nombre del PC.
    nombre_caja: str = ""

    @property
    def usa_red(self) -> bool:
        return self.modo is not Modo.SUELTO

    @property
    def caja(self) -> str:
        """El nombre con que esta caja firma sus ventas. Nunca vacío.

        Si no se configuró, el nombre del PC, que es estable y distinto en cada equipo de la
        red local. **No se deriva del modo** ("principal", "secundaria"): el modo se puede
        cambiar editando este archivo, y entonces las ventas de un mismo equipo aparecerían
        en el cierre bajo dos cajas distintas.
        """
        return (
            normalizar_nombre_caja(self.nombre_caja)
            or normalizar_nombre_caja(platform.node())
            or "Caja"
        )


def _leer_texto(ruta: Path) -> str:
    """El texto de `red.json` tal como lo haya guardado quien lo editó.

    Se edita con el Bloc de notas, y según la versión de Windows eso deja UTF-8 con BOM o,
    en los antiguos, ANSI. Leído como UTF-8 estricto, un nombre de caja con tilde hacía el
    archivo ilegible, y el PC 2 arrancaba en modo suelto con una base propia y vacía.
    """
    crudo = ruta.read_bytes()
    try:
        return crudo.decode("utf-8-sig")
    except UnicodeDecodeError:
        _logger.warning("red.json no está en UTF-8; se lee como ANSI (cp1252)")
        return crudo.decode("cp1252", errors="replace")


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
        datos = json.loads(_leer_texto(ruta))
        return ConfiguracionRed(
            modo=Modo(datos.get("modo", Modo.SUELTO)),
            servidor_host=str(datos.get("servidor_host", "")).strip(),
            puerto=int(datos.get("puerto", config.PUERTO_SERVIDOR)),
            nombre_caja=normalizar_nombre_caja(datos.get("nombre_caja")),
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
                    "nombre_caja": configuracion.nombre_caja,
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
