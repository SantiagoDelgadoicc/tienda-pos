"""Crea el acceso directo en el escritorio.

Es el último paso de la instalación en el equipo del cliente: a partir de aquí, abrir el
sistema es hacer doble clic en un icono, que es exactamente lo que se pidió.

    python tools/crear_acceso_directo.py [ruta_al_exe]

Sin argumentos usa dist/PuntoYFamaCaja/PuntoYFamaCaja.exe. Para deshacerlo basta con borrar el acceso
directo del escritorio: no toca el registro ni ninguna configuración del sistema.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
NOMBRE_ACCESO = "Punto y Fama.lnk"

# Se usa el objeto WScript.Shell de Windows a través de PowerShell. Es la forma estándar de
# crear un .lnk sin añadir dependencias como pywin32 solo para esto.
_PLANTILLA = """
$escritorio = [Environment]::GetFolderPath('Desktop')
$destino = Join-Path $escritorio '{nombre}'
$shell = New-Object -ComObject WScript.Shell
$acceso = $shell.CreateShortcut($destino)
$acceso.TargetPath = '{exe}'
$acceso.WorkingDirectory = '{carpeta}'
$acceso.IconLocation = '{icono}'
$acceso.Description = 'Sistema de punto de venta'
$acceso.Save()
Write-Output $destino
"""


def crear(exe: Path | None = None) -> Path:
    exe = Path(exe) if exe else RAIZ / "dist" / "PuntoYFamaCaja" / "PuntoYFamaCaja.exe"
    exe = exe.resolve()
    if not exe.exists():
        raise FileNotFoundError(
            f"No existe {exe}. Ejecute antes: python tools/construir.py"
        )

    icono = RAIZ / "assets" / "tienda_pos.ico"
    guion = _PLANTILLA.format(
        nombre=NOMBRE_ACCESO,
        exe=exe,
        carpeta=exe.parent,
        icono=icono if icono.exists() else exe,
    )

    resultado = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", guion],
        capture_output=True,
        text=True,
        check=True,
    )
    destino = Path(resultado.stdout.strip())
    print(f"Acceso directo creado: {destino}")
    return destino


if __name__ == "__main__":
    if sys.platform != "win32":
        raise SystemExit("Este script solo tiene sentido en Windows.")
    crear(Path(sys.argv[1]) if len(sys.argv) > 1 else None)
