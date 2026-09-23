"""Preferencias de la aplicación: lo que el usuario puede cambiar desde la rueda dentada.

Se guardan en un archivo JSON dentro de la carpeta de datos, junto a la base y los
respaldos. No van en la base de datos porque no son datos del negocio: son de la instalación
y del equipo, y deben poder leerse aunque la base esté dañada o todavía no exista.

Este módulo no importa Qt: la interfaz decide qué hacer con los valores, no al revés.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from ..config import directorio_datos

_logger = logging.getLogger(__name__)

NOMBRE_ARCHIVO = "preferencias.json"

TEMA_CLARO = "claro"
TEMA_OSCURO = "oscuro"
TEMAS = (TEMA_CLARO, TEMA_OSCURO)


@dataclass(slots=True)
class Preferencias:
    """Ajustes de la instalación. Todos tienen un valor por defecto razonable."""

    tema: str = TEMA_CLARO
    sonido: bool = True
    confirmar_cobro: bool = True
    mostrar_atajos: bool = True
    #: Barra lateral plegada a tira de iconos. No está en la rueda de configuración: se
    #: cambia con Ctrl+B o con su botón, y se guarda para que no haya que repetirlo.
    barra_lateral_plegada: bool = False
    #: Animaciones cortas: el aviso de escaneo, la línea que cambia y el plegado del menú.
    #: Apagadas, todo aparece y desaparece de golpe, como antes de D-029.
    animaciones: bool = True

    def normalizar(self) -> "Preferencias":
        """Corrige valores imposibles en lugar de fallar.

        Un archivo de preferencias editado a mano, o escrito por una versión más nueva, no
        debe impedir que la caja abra: se descarta lo que no se entiende.
        """
        if self.tema not in TEMAS:
            self.tema = TEMA_CLARO
        self.sonido = bool(self.sonido)
        self.confirmar_cobro = bool(self.confirmar_cobro)
        self.mostrar_atajos = bool(self.mostrar_atajos)
        self.barra_lateral_plegada = bool(self.barra_lateral_plegada)
        self.animaciones = bool(self.animaciones)
        return self


def ruta(base: Path | None = None) -> Path:
    return (base or directorio_datos()) / NOMBRE_ARCHIVO


def cargar(base: Path | None = None) -> Preferencias:
    """Lee las preferencias del disco. Si no hay archivo o está roto, devuelve las de fábrica."""
    archivo = ruta(base)
    if not archivo.exists():
        return Preferencias()

    try:
        datos = json.loads(archivo.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        _logger.warning("No se pudieron leer las preferencias; se usan las de fábrica", exc_info=True)
        return Preferencias()

    if not isinstance(datos, dict):
        return Preferencias()

    # Se ignoran las claves desconocidas para que un archivo de una versión posterior no
    # rompa esta.
    conocidas = {campo.name for campo in fields(Preferencias)}
    return Preferencias(**{k: v for k, v in datos.items() if k in conocidas}).normalizar()


def guardar(preferencias: Preferencias, base: Path | None = None) -> bool:
    """Escribe las preferencias. Devuelve False si no se pudo, sin lanzar excepción.

    No poder guardar un ajuste es una molestia, no un motivo para tumbar la caja en mitad de
    una venta.
    """
    archivo = ruta(base)
    try:
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_text(
            json.dumps(asdict(preferencias.normalizar()), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return True
    except OSError:
        _logger.warning("No se pudieron guardar las preferencias", exc_info=True)
        return False
