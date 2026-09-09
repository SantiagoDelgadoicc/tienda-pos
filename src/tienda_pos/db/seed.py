"""Catálogo de ejemplo para la demostración.

IMPORTANTE: estos datos son inventados. No son los productos ni los precios del cliente.
Sirven para que el prototipo se pueda mostrar sin cargar nada a mano.

Los códigos de barras se generan como EAN-13 válidos, con su dígito verificador calculado.
Eso importa más de lo que parece: si en la demo alguien escanea uno de estos códigos impreso
con una pistola real, tiene que leerlo. Un código inventado al azar no lo haría.
"""

from __future__ import annotations

import sqlite3

from ..domain.models import Producto, Rol
from ..repositories import productos as repo_productos
from ..repositories import usuarios as repo_usuarios
from ..utils.codigo_barras import generar_ean13

# Prefijo 780 = Chile en el sistema GS1. Los cuatro dígitos siguientes simulan la empresa.
_PREFIJO = "7801234"

# PIN por defecto de la demostración. Están documentados en el manual de usuario a propósito:
# un PIN secreto que nadie conoce convertiría la demo en un problema. En una instalación real
# lo primero es cambiarlos.
PIN_ADMIN_DEMO = "1234"
PIN_CAJERO_DEMO = "1111"

# (nombre, precio CLP, stock inicial)
_PRODUCTOS: list[tuple[str, int, int]] = [
    # Bebidas
    ("Bebida Cola 1.5 L", 2290, 48),
    ("Bebida Lima Limón 1.5 L", 2190, 36),
    ("Bebida Naranja 1.5 L", 2190, 30),
    ("Bebida Cola 350 ml lata", 890, 96),
    ("Agua Mineral sin gas 1.6 L", 1190, 60),
    ("Agua Mineral con gas 1.6 L", 1190, 42),
    ("Jugo Naranja 1 L", 1490, 40),
    ("Néctar Durazno 1 L", 1290, 38),
    ("Bebida Energética 250 ml", 1690, 24),
    ("Cerveza Lager 350 ml lata", 1390, 72),
    # Lacteos
    ("Leche Entera 1 L", 1290, 60),
    ("Leche Descremada 1 L", 1290, 45),
    ("Leche Chocolatada 200 ml", 690, 50),
    ("Yogur Natural 155 g", 590, 60),
    ("Yogur Frutilla pack 4", 2290, 30),
    ("Queso Gauda laminado 250 g", 3490, 20),
    ("Mantequilla 250 g", 2790, 18),
    ("Huevos docena", 3290, 25),
    ("Crema de leche 200 ml", 1190, 22),
    # Abarrotes
    ("Arroz Grado 2 1 kg", 1590, 55),
    ("Fideos Espirales 400 g", 990, 60),
    ("Fideos Espagueti 400 g", 990, 58),
    ("Azúcar 1 kg", 1390, 44),
    ("Sal de mesa 1 kg", 690, 40),
    ("Aceite Maravilla 900 ml", 2690, 36),
    ("Harina sin polvos 1 kg", 1290, 42),
    ("Lentejas 500 g", 1890, 25),
    ("Porotos Negros 500 g", 1990, 20),
    ("Atún en agua 160 g", 1790, 48),
    ("Salsa de Tomate 200 g", 890, 50),
    ("Café Instantáneo 170 g", 5490, 18),
    ("Té 20 bolsitas", 1490, 30),
    ("Mermelada Frutilla 250 g", 1990, 22),
    ("Manjar 250 g", 2190, 20),
    ("Avena Instantánea 500 g", 1690, 26),
    # Snacks
    ("Papas Fritas 250 g", 2790, 34),
    ("Ramitas 130 g", 1290, 40),
    ("Galletas Soda 250 g", 1090, 45),
    ("Chocolate Barra 100 g", 1890, 36),
    ("Oblea Chocolate", 590, 80),
    ("Chicles Menta", 490, 90),
    ("Maní Salado 100 g", 990, 38),
    ("Cereal Hojuelas 300 g", 3290, 20),
    ("Alfajor unidad", 690, 55),
    # Panaderia y congelados
    ("Pan de Molde Blanco 500 g", 2190, 24),
    ("Pan de Molde Integral 500 g", 2490, 20),
    ("Tortillas de Trigo 6 un", 1890, 18),
    ("Helado Vainilla 1 L", 4290, 12),
    ("Pizza Congelada Jamón Queso", 4990, 10),
    # Limpieza y aseo
    ("Detergente en polvo 1 kg", 4290, 22),
    ("Cloro 1 L", 1290, 30),
    ("Lavalozas 500 ml", 1690, 28),
    ("Papel Higiénico 4 rollos", 2990, 40),
    ("Toalla de Papel 2 rollos", 2490, 26),
    ("Jabón de Tocador 3 un", 2190, 30),
    ("Shampoo 400 ml", 3990, 16),
    ("Pasta Dental 90 g", 2290, 24),
    ("Cepillo Dental", 1890, 20),
    ("Desodorante en barra", 3490, 15),
    ("Esponja de Cocina 3 un", 1290, 25),
    # Varios
    ("Pilas AA 2 un", 2490, 18),
    ("Fósforos caja", 490, 40),
    ("Bolsas de Basura 10 un", 1790, 28),
    ("Servilletas 100 un", 1190, 30),
    ("Vela unidad", 690, 24),
]


def codigo_demo(indice: int) -> str:
    """Código EAN-13 válido y estable para el producto número `indice` (empezando en 0)."""
    return generar_ean13(f"{_PREFIJO}{indice:05d}")


def catalogo_demo() -> list[Producto]:
    """Construye la lista de productos de ejemplo, sin tocar la base de datos."""
    return [
        Producto(
            codigo_barras=codigo_demo(i),
            nombre=nombre,
            precio_clp=precio,
            stock=stock,
        )
        for i, (nombre, precio, stock) in enumerate(_PRODUCTOS)
    ]


def cargar_datos_demo(conexion: sqlite3.Connection) -> int:
    """Inserta el catálogo y los usuarios por defecto si la base está vacía.

    Es idempotente: si ya hay productos, no hace nada. Así, arrancar el programa muchas veces
    no duplica el catálogo ni pisa los cambios que se hayan hecho durante una demostración.

    Devuelve el número de productos insertados.

    Debe llamarse dentro de una transacción.
    """
    from ..services.auth import crear_usuario  # local: evita un ciclo de importación

    insertados = 0
    if repo_productos.contar(conexion) == 0:
        for producto in catalogo_demo():
            repo_productos.crear(conexion, producto)
            insertados += 1

    if repo_usuarios.contar(conexion) == 0:
        crear_usuario(conexion, "Administrador", Rol.ADMIN, PIN_ADMIN_DEMO)
        crear_usuario(conexion, "Cajero", Rol.CAJERO, PIN_CAJERO_DEMO)

    return insertados
