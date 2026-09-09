"""Arranque de la aplicación."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from . import config
from .db.inicio import abrir_base_datos
from .ui import estilos
from .ui.main_window import VentanaPrincipal


def _crear_aplicacion() -> QApplication:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(config.NOMBRE_COMERCIAL)
    app.setApplicationVersion(config.VERSION)
    app.setOrganizationName(config.NOMBRE_APP)
    estilos.aplicar(app)
    return app


def ejecutar() -> int:
    """Punto de entrada. Devuelve el código de salida del proceso."""
    app = _crear_aplicacion()

    try:
        conexion = abrir_base_datos()
    except Exception as error:  # noqa: BLE001 - aquí sí queremos atrapar cualquier cosa
        # Si la base no abre no hay nada que hacer, pero el usuario merece saber por qué en
        # lugar de ver una ventana que nunca aparece.
        QMessageBox.critical(
            None,
            "No se pudo iniciar",
            "No fue posible abrir la base de datos.\n\n"
            f"{error}\n\nUbicación: {config.ruta_base_datos()}",
        )
        return 1

    ventana = VentanaPrincipal(conexion)
    ventana.show()
    ventana.mostrar_venta()

    codigo = app.exec()
    conexion.close()
    return codigo
