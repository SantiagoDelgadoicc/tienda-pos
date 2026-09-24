"""Permite ejecutar la aplicacion con: python -m tienda_pos"""

from __future__ import annotations

import sys

from .app import ejecutar

if __name__ == "__main__":
    raise SystemExit(ejecutar(demo="--demo" in sys.argv))
