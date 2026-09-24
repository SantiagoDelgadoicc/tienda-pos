"""Punto de entrada del ejecutable.

PyInstaller necesita un script normal en la raíz del proyecto. En desarrollo se puede usar
igualmente `python main.py` o `python -m tienda_pos`.
"""

from __future__ import annotations

import sys
from pathlib import Path

# En desarrollo el paquete vive en src/. Dentro del ejecutable ya está empaquetado y esta
# línea no estorba porque la carpeta no existe.
_SRC = Path(__file__).resolve().parent / "src"
if _SRC.is_dir():
    sys.path.insert(0, str(_SRC))

from tienda_pos.app import ejecutar, reiniciar_admin, verificar  # noqa: E402

if __name__ == "__main__":
    # --verificar arranca el sistema entero sin mostrar nada y sale. Sirve para comprobar
    # que el ejecutable funciona en un equipo ajeno sin tener que hacer una venta a mano.
    if "--verificar" in sys.argv:
        raise SystemExit(verificar())
    # --reiniciar-admin recupera un administrador cuando nadie recuerda el PIN. Solo en la
    # caja principal, y deja constancia en el registro.
    if "--reiniciar-admin" in sys.argv:
        raise SystemExit(reiniciar_admin())
    # --demo llena una base vacía con el catálogo y los usuarios de ejemplo, cuyos PIN están
    # publicados en el manual. Solo para demostraciones: nunca en el acceso directo de una tienda.
    raise SystemExit(ejecutar(demo="--demo" in sys.argv))
