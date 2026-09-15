"""Fixtures compartidas.

Las pruebas usan una base de datos en memoria: son rápidas, no dejan basura en el disco y no
pueden tocar por accidente los datos reales de la carpeta de la aplicación.

Las pruebas de interfaz usan la plataforma "offscreen" de Qt, de modo que funcionan igual en
un equipo de desarrollo que en un servidor de integración continua, sin abrir ventanas.
"""

from __future__ import annotations

import os
import sqlite3

import pytest

# Debe fijarse antes de que se importe Qt en cualquier módulo.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from tienda_pos.db.connection import transaccion  # noqa: E402
from tienda_pos.db.inicio import abrir_base_datos  # noqa: E402
from tienda_pos.domain.models import Producto, Rol, Usuario  # noqa: E402
from tienda_pos.red.sesion import SesionLocal  # noqa: E402
from tienda_pos.repositories import productos as repo_productos  # noqa: E402
from tienda_pos.services import auth  # noqa: E402
from tienda_pos.utils import sonido  # noqa: E402

# Las pruebas no deben hacer sonar el equipo cada vez que simulan un escaneo. Se anula la
# emisión y no solo la bandera `habilitado`, porque aplicar unas preferencias con el sonido
# activado volvería a encenderla.
sonido.silenciar()
sonido._emitir = lambda *args, **kwargs: None


# --------------------------------------------------------------------------- datos


@pytest.fixture
def conexion() -> sqlite3.Connection:
    """Base de datos vacía, con el esquema ya migrado."""
    con = abrir_base_datos(":memory:", con_datos_demo=False)
    yield con
    con.close()


@pytest.fixture
def productos(conexion: sqlite3.Connection) -> dict[str, Producto]:
    """Tres productos conocidos, suficientes para casi todas las pruebas.

    Se devuelven en un diccionario por un nombre corto para que las pruebas se lean bien:
    productos["leche"] en lugar de productos[0].
    """
    definiciones = {
        "leche": Producto(codigo_barras="7801234000019", nombre="Leche Entera 1 L", precio_clp=1290, stock=10),
        "pan": Producto(codigo_barras="7801234000026", nombre="Pan de Molde 500 g", precio_clp=2190, stock=5),
        "agua": Producto(codigo_barras="7801234000033", nombre="Agua Mineral 1.6 L", precio_clp=1190, stock=1),
    }
    with transaccion(conexion):
        for producto in definiciones.values():
            repo_productos.crear(conexion, producto)
    return definiciones


@pytest.fixture
def admin(conexion: sqlite3.Connection) -> Usuario:
    with transaccion(conexion):
        return auth.crear_usuario(conexion, "Administrador", Rol.ADMIN, "1234")


@pytest.fixture
def cajero(conexion: sqlite3.Connection) -> Usuario:
    with transaccion(conexion):
        return auth.crear_usuario(conexion, "Cajero", Rol.CAJERO, "1111")


# --------------------------------------------------------------------------- interfaz


@pytest.fixture(scope="session")
def app():
    """Aplicación Qt única para toda la sesión de pruebas.

    Qt no admite más de una QApplication por proceso, de ahí el alcance de sesión.
    """
    pytest.importorskip("PySide6", reason="La interfaz requiere PySide6")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture
def ventana(app, conexion, monkeypatch, tmp_path):
    """Ventana principal con el catálogo de ejemplo cargado y sin diálogos bloqueantes.

    Los diálogos modales se sustituyen por respuestas automáticas: sin esto, cualquier
    prueba que cobre una venta se quedaría esperando un clic para siempre.
    """
    from PySide6.QtWidgets import QApplication

    from tienda_pos.db.seed import cargar_datos_demo
    from tienda_pos.ui import dialogos
    from tienda_pos.ui.main_window import VentanaPrincipal

    with transaccion(conexion):
        cargar_datos_demo(conexion)

    # Las preferencias se leen y se escriben en la carpeta de datos. Se redirige a una
    # temporal para que las pruebas no dependan del tema que tenga puesto quien las ejecuta,
    # ni se lo cambien.
    monkeypatch.setenv("TIENDA_POS_HOME", str(tmp_path / "datos"))

    monkeypatch.setattr(dialogos, "confirmar", lambda *a, **k: True)
    monkeypatch.setattr(dialogos, "mostrar_error", lambda *a, **k: None)
    monkeypatch.setattr(dialogos, "mostrar_info", lambda *a, **k: None)

    # La ventana ya no recibe una conexión sino una Sesion (D-015): así la misma interfaz
    # sirve para la caja principal, que tiene la base al lado, y para la secundaria, que la
    # tiene al otro lado de la red. Aquí se usa la local, que es lo que hacía antes.
    ventana = VentanaPrincipal(SesionLocal(conexion))
    ventana.establecer_usuario(Usuario(id=1, nombre="Ana Pérez", rol=Rol.CAJERO))
    # Sin mostrar la ventana, Qt considera que ningún widget está visible ni tiene el foco,
    # y las comprobaciones de foco (que aquí son parte de lo que se prueba) darían siempre
    # falso.
    ventana.show()
    ventana.activateWindow()
    ventana.mostrar_venta()
    QApplication.processEvents()

    yield ventana
    ventana.close()


@pytest.fixture
def como_admin(ventana, conexion, monkeypatch):
    """Hace que cualquier petición de autorización se resuelva con el administrador demo.

    Devuelve la ventana, ya preparada para entrar a las pantallas reservadas.
    """
    from tienda_pos.ui import main_window as modulo

    administrador = auth.autenticar(conexion, "Administrador", "1234")
    monkeypatch.setattr(
        modulo.DialogoLogin, "pedir", staticmethod(lambda *a, **k: administrador)
    )
    return ventana
