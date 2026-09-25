"""Genera el manual de usuario en PDF a partir de docs/manual/manual.html.

    python tools/manual_pdf.py            escribe docs/Manual-de-usuario-Punto-y-Fama.pdf

Por qué HTML y un navegador y no una biblioteca de PDF: el manual lleva la tipografía, los
colores y las capturas del programa, y así se maqueta con CSS sin añadir dependencias. Se usa
Edge, que viene con Windows, o Chrome si no está. Las capturas salen de `tools/capturas.py`:
regenerarlas antes si cambió la interfaz.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
FUENTE = RAIZ / "docs" / "manual" / "manual.html"
DESTINO = RAIZ / "docs" / "Manual-de-usuario-Punto-y-Fama.pdf"

_NAVEGADORES = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
)


def _navegador() -> str:
    for ruta in _NAVEGADORES:
        if Path(ruta).exists():
            return ruta
    for nombre in ("msedge", "chrome", "chromium"):
        if encontrado := shutil.which(nombre):
            return encontrado
    raise SystemExit("No encuentro Edge ni Chrome para generar el PDF.")


def generar(destino: Path = DESTINO) -> Path:
    with tempfile.TemporaryDirectory() as perfil:
        subprocess.run(
            [
                _navegador(),
                "--headless=new",
                "--disable-gpu",
                "--allow-file-access-from-files",
                f"--user-data-dir={perfil}",
                # Tiempo para que carguen las capturas y corra el script que numera las hojas.
                "--virtual-time-budget=5000",
                "--no-pdf-header-footer",
                f"--print-to-pdf={destino}",
                FUENTE.as_uri(),
            ],
            check=True,
            capture_output=True,
        )
    if not destino.exists() or destino.stat().st_size == 0:
        raise SystemExit("El navegador no generó el PDF.")
    return destino


if __name__ == "__main__":
    ruta = generar(Path(sys.argv[1]) if len(sys.argv) > 1 else DESTINO)
    print(f"Listo: {ruta}  ({ruta.stat().st_size / 1e6:.1f} MB)")
