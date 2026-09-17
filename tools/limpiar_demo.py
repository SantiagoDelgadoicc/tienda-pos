"""Quita del catálogo los productos de ejemplo, dejando solo los del cliente.

Hace falta porque el programa carga un catálogo demo de 65 productos inventados la primera
vez que arranca con la base vacía (`db/seed.py`), y si alguien empieza a cargar los productos
reales encima, acaban mezclados. Puesto en la tienda, eso significa 65 productos que no
existen apareciendo en las búsquedas del cajero.

**Por defecto no borra nada:** enseña lo que haría y termina. Para aplicarlo de verdad hay que
pasar `--aplicar` a conciencia.

    python tools/limpiar_demo.py                          # en seco, sobre la base real
    python tools/limpiar_demo.py --base E:\\tienda.db       # en seco, sobre otro archivo
    python tools/limpiar_demo.py --aplicar                 # borra, tras hacer respaldo

Se niega a borrar un producto de ejemplo que alguien haya llegado a vender: en ese caso deja
de ser un dato inventado y pasa a ser historial, y el historial no se toca (`D-005`).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from tienda_pos import config  # noqa: E402
from tienda_pos.db.connection import conectar, transaccion  # noqa: E402
from tienda_pos.db.respaldo import crear_respaldo  # noqa: E402
from tienda_pos.db.seed import _PRODUCTOS  # noqa: E402


def _nombres_demo() -> set[str]:
    return {nombre for nombre, _precio, _stock in _PRODUCTOS}


def main() -> int:
    analizador = argparse.ArgumentParser(description=__doc__)
    analizador.add_argument("--base", type=Path, default=None, help="Ruta de la base de datos")
    analizador.add_argument(
        "--aplicar", action="store_true", help="Borra de verdad (por defecto solo informa)"
    )
    argumentos = analizador.parse_args()

    ruta = argumentos.base or config.ruta_base_datos()
    if not ruta.exists():
        print(f"No existe la base de datos: {ruta}")
        return 1

    conexion = conectar(ruta)
    nombres_demo = _nombres_demo()

    filas = conexion.execute("SELECT id, codigo_barras, nombre FROM producto").fetchall()
    demo = [f for f in filas if f["nombre"] in nombres_demo]
    reales = [f for f in filas if f["nombre"] not in nombres_demo]

    print(f"Base de datos: {ruta}")
    print(f"  productos en total ......... {len(filas)}")
    print(f"  del catálogo de ejemplo .... {len(demo)}")
    print(f"  cargados por el cliente .... {len(reales)}")

    if not demo:
        print("\nNo hay productos de ejemplo. No hay nada que hacer.")
        return 0

    if not reales:
        # Si se borraran todos, la base quedaría vacía y el propio programa volvería a cargar
        # el catálogo demo en el siguiente arranque. Sería un viaje de ida y vuelta inútil.
        print("\nTodos los productos son de ejemplo: no se borra nada, porque la base quedaría")
        print("vacía y el programa los volvería a cargar al arrancar.")
        return 1

    marcadores = ",".join("?" for _ in demo)
    vendidos = conexion.execute(
        f"SELECT DISTINCT producto_id FROM venta_linea WHERE producto_id IN ({marcadores})",
        [f["id"] for f in demo],
    ).fetchall()
    ids_vendidos = {f["producto_id"] for f in vendidos}

    borrables = [f for f in demo if f["id"] not in ids_vendidos]
    intocables = [f for f in demo if f["id"] in ids_vendidos]

    if intocables:
        print(f"\n  {len(intocables)} productos de ejemplo tienen ventas y NO se tocan:")
        for f in intocables:
            print(f"    · {f['nombre']}")
        print("    (dan de baja lógica desde la pantalla de productos si estorban)")

    if not argumentos.aplicar:
        print(f"\nEn seco. Se borrarían {len(borrables)} productos de ejemplo, por ejemplo:")
        for f in borrables[:8]:
            print(f"    · {f['nombre']}  [{f['codigo_barras']}]")
        if len(borrables) > 8:
            print(f"    · ... y {len(borrables) - 8} más")
        print(f"\nQuedarían {len(reales)} productos, los del cliente.")
        print("Para hacerlo de verdad: volver a ejecutar con --aplicar")
        return 0

    copia = crear_respaldo(origen=ruta)
    print(f"\nRespaldo previo: {copia}")

    with transaccion(conexion):
        conexion.execute(
            f"DELETE FROM producto WHERE id IN ({','.join('?' for _ in borrables)})",
            [f["id"] for f in borrables],
        )

    restantes = conexion.execute("SELECT COUNT(*) FROM producto").fetchone()[0]
    print(f"Borrados {len(borrables)} productos de ejemplo. Quedan {restantes}.")
    conexion.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
