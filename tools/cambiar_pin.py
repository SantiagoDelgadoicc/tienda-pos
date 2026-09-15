"""Cambia el PIN de un usuario desde la línea de órdenes.

Existe porque la pantalla de gestión de usuarios todavía no está construida (fase 12), y
mientras tanto los únicos PIN que existen son los de demostración —`1234` y `1111`—, que
están **publicados en `docs/MANUAL-USUARIO.md`**. Poner el sistema en una tienda con esos PIN
equivale a no tener PIN.

La lógica no es nueva: `services/auth.py::cambiar_pin` ya existía y estaba probada; lo único
que faltaba era una forma de llamarla. Esta herramienta desaparece cuando exista la pantalla.

    python tools/cambiar_pin.py --listar
    python tools/cambiar_pin.py --usuario Administrador
    python tools/cambiar_pin.py --usuario Administrador --base E:\\tienda.db

El PIN se pide por teclado y no se pasa como argumento a propósito: un PIN escrito en la
línea de órdenes queda en el historial de la consola.
"""

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from tienda_pos import config  # noqa: E402
from tienda_pos.db.connection import conectar, transaccion  # noqa: E402
from tienda_pos.db.respaldo import cerrar_limpiamente  # noqa: E402
from tienda_pos.domain.errors import ErrorDominio  # noqa: E402
from tienda_pos.services import auth  # noqa: E402


def main() -> int:
    analizador = argparse.ArgumentParser(description=__doc__)
    analizador.add_argument("--base", type=Path, default=None, help="Ruta de la base de datos")
    analizador.add_argument("--usuario", help="Nombre del usuario cuyo PIN se cambia")
    analizador.add_argument("--listar", action="store_true", help="Solo muestra los usuarios")
    argumentos = analizador.parse_args()

    ruta = argumentos.base or config.ruta_base_datos()
    if not ruta.exists():
        print(f"No existe la base de datos: {ruta}")
        return 1

    conexion = conectar(ruta)
    usuarios = auth.listar_usuarios(conexion)

    if argumentos.listar or not argumentos.usuario:
        print(f"Usuarios en {ruta}:\n")
        for u in usuarios:
            print(f"  · {u.nombre}  ({u.rol})")
        if not argumentos.listar:
            print("\nIndique cuál con --usuario NOMBRE")
        return 0

    objetivo = next((u for u in usuarios if u.nombre == argumentos.usuario), None)
    if objetivo is None:
        print(f"No hay ningún usuario activo llamado '{argumentos.usuario}'.")
        print("Usuarios disponibles: " + ", ".join(u.nombre for u in usuarios))
        return 1

    print(f"Cambiando el PIN de {objetivo.nombre} ({objetivo.rol}).")
    print(f"Debe tener entre {config.PIN_LONGITUD_MIN} y {config.PIN_LONGITUD_MAX} dígitos.\n")

    nuevo = getpass.getpass("PIN nuevo: ")
    repetido = getpass.getpass("Repítalo:  ")
    if nuevo != repetido:
        print("\nLos dos PIN no coinciden. No se cambió nada.")
        return 1

    try:
        with transaccion(conexion):
            auth.cambiar_pin(conexion, objetivo, nuevo)
    except ErrorDominio as error:
        print(f"\n{error}")
        return 1

    cerrar_limpiamente(conexion)
    conexion.close()
    print(f"\nPIN de {objetivo.nombre} cambiado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
