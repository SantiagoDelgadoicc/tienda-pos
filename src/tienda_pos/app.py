"""Arranque de la aplicación.

Orden de inicio, y el motivo de cada paso:

1. Registro de sucesos, para que cualquier fallo posterior quede documentado.
2. Manejador global de errores, para que nada cierre la aplicación por sorpresa.
3. Respaldo de la base de datos, antes de tocarla.
4. Apertura y migración de la base.
5. Acceso con PIN.
6. Ventana principal.
"""

from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from . import config
from .db.inicio import abrir_base_datos
from .db.respaldo import crear_respaldo
from .ui import errores, estilos
from .ui.main_window import VentanaPrincipal

_logger = logging.getLogger(__name__)

# Centinela para distinguir "canceló el acceso" de "no hay usuarios configurados".
_CANCELADO = object()


def _crear_aplicacion() -> QApplication:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(config.NOMBRE_COMERCIAL)
    app.setApplicationVersion(config.VERSION)
    app.setOrganizationName(config.NOMBRE_APP)
    estilos.aplicar(app)
    return app


def _iniciar_sesion(conexion):
    """Pide el PIN al arrancar.

    Si la base no tiene usuarios (una instalación limpia sin datos de ejemplo) se entra sin
    sesión, para que el sistema no quede inutilizable antes de poder crear el primero.
    """
    from .repositories import usuarios as repo_usuarios
    from .ui.login_dialog import DialogoLogin

    if repo_usuarios.contar(conexion) == 0:
        _logger.warning("No hay usuarios configurados: se entra sin sesión")
        return None

    usuario = DialogoLogin.pedir(conexion)
    if usuario is None:
        return _CANCELADO

    _logger.info("Sesión iniciada: %s (%s)", usuario.nombre, usuario.rol)
    return usuario


def ejecutar() -> int:
    """Punto de entrada. Devuelve el código de salida del proceso."""
    from .utils.logging_setup import configurar

    config.asegurar_directorios()
    configurar()
    errores.instalar()

    app = _crear_aplicacion()

    # El respaldo se hace antes de abrir la base: si el archivo estuviera dañado, al menos
    # queda una copia del estado previo a que este arranque lo toque.
    crear_respaldo()

    try:
        conexion = abrir_base_datos()
    except Exception as error:  # noqa: BLE001 - aquí sí queremos atrapar cualquier cosa
        # Sin base de datos no hay nada que hacer, pero el usuario merece saber por qué en
        # lugar de ver una ventana que nunca aparece.
        _logger.exception("No se pudo abrir la base de datos")
        QMessageBox.critical(
            None,
            "No se pudo iniciar",
            "No fue posible abrir la base de datos.\n\n"
            f"{error}\n\nUbicación: {config.ruta_base_datos()}",
        )
        return 1

    usuario = _iniciar_sesion(conexion)
    if usuario is _CANCELADO:
        # El usuario cerró la ventana de acceso: se sale sin ruido, sin ventana huérfana.
        conexion.close()
        return 0

    ventana = VentanaPrincipal(conexion)
    ventana.establecer_usuario(usuario)
    ventana.show()
    ventana.mostrar_venta()

    codigo = app.exec()
    conexion.close()
    _logger.info("Aplicación cerrada con código %s", codigo)
    return codigo
