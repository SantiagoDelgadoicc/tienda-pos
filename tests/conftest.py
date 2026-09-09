"""Fixtures compartidas.

Las pruebas usan una base de datos en memoria: son rápidas, no dejan basura en el disco y no
pueden tocar por accidente los datos reales de la carpeta de la aplicación.
"""

from __future__ import annotations

import sqlite3

import pytest

from tienda_pos.db.inicio import abrir_base_datos
from tienda_pos.db.connection import transaccion
from tienda_pos.domain.models import Producto, Rol, Usuario
from tienda_pos.repositories import productos as repo_productos
from tienda_pos.services import auth


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
