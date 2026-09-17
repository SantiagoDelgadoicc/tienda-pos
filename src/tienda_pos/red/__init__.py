"""Capa de red: lo que permite que dos cajas compartan una sola base de datos (D-015).

`ui → red → services → repositories → db`. Nada de aquí importa Qt.
"""

from .cliente import ServidorNoDisponible, SesionRemota, VersionIncompatible
from .config_red import ConfiguracionRed, Modo, cargar, guardar
from .sesion import Sesion, SesionLocal
from .servidor import ServidorTienda

__all__ = [
    "ConfiguracionRed",
    "Modo",
    "Sesion",
    "SesionLocal",
    "SesionRemota",
    "ServidorNoDisponible",
    "ServidorTienda",
    "VersionIncompatible",
    "cargar",
    "guardar",
]
