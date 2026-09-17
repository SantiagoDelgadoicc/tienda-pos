"""Construye el ejecutable de Windows con PyInstaller.

    python tools/construir.py            genera dist/PuntoYFamaCaja/PuntoYFamaCaja.exe
    python tools/construir.py --unico    genera un único dist/PuntoYFamaCaja.exe

Por qué una carpeta y no un solo archivo por defecto: el formato de archivo único se
descomprime en una carpeta temporal en cada arranque, lo que añade dos o tres segundos.
El criterio de aceptación del proyecto es abrir en menos de tres segundos, así que la
distribución en carpeta es la que se entrega, con un acceso directo al ejecutable. La
opción de archivo único queda disponible para cuando convenga enviar el prototipo por
correo o por un pendrive.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
NOMBRE = "PuntoYFamaCaja"

# Módulos de Qt que este programa no usa. Excluirlos baja el tamaño del paquete de forma
# apreciable y reduce la superficie de lo que puede fallar al arrancar.
_EXCLUIDOS = (
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuick3D",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtMultimedia",
    "PySide6.QtCharts",
    "PySide6.Qt3DCore",
    "PySide6.QtDataVisualization",
    "PySide6.QtBluetooth",
    "PySide6.QtPositioning",
    "tkinter",
    "unittest",
    "pydoc",
)


def construir(unico: bool = False, limpiar: bool = True) -> Path:
    icono = RAIZ / "assets" / "punto_y_fama.ico"
    if not icono.exists():
        print("El icono no existe todavía; generándolo...")
        subprocess.run([sys.executable, str(RAIZ / "tools" / "icono.py")], check=True)

    if limpiar:
        for carpeta in ("build", "dist"):
            shutil.rmtree(RAIZ / carpeta, ignore_errors=True)

    orden = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",  # sin ventana de consola detrás de la aplicación
        f"--name={NOMBRE}",
        f"--icon={icono}",
        f"--paths={RAIZ / 'src'}",
        # El esquema SQL es un archivo de datos: sin esto, el ejecutable no sabría crear la
        # base de datos en el primer arranque.
        f"--add-data={RAIZ / 'src' / 'tienda_pos' / 'db' / 'schema.sql'}{';' if sys.platform == 'win32' else ':'}tienda_pos/db",
        # El logotipo del negocio, si lo hay. La interfaz lo busca en esta carpeta y se
        # arregla sin el, pero si esta tiene que viajar dentro del ejecutable.
        f"--add-data={RAIZ / 'assets'}{';' if sys.platform == 'win32' else ':'}assets",
        "--onefile" if unico else "--onedir",
    ]
    for modulo in _EXCLUIDOS:
        orden.append(f"--exclude-module={modulo}")
    orden.append(str(RAIZ / "main.py"))

    print("Construyendo... (puede tardar un par de minutos)")
    subprocess.run(orden, check=True, cwd=RAIZ)

    destino = (RAIZ / "dist" / f"{NOMBRE}.exe") if unico else (
        RAIZ / "dist" / NOMBRE / f"{NOMBRE}.exe"
    )
    if not destino.exists():  # pragma: no cover - depende de PyInstaller
        raise RuntimeError(f"La construcción terminó pero no se encontró {destino}")

    tamano = _tamano_total(destino.parent if not unico else destino)
    print(f"\nListo: {destino}")
    print(f"Tamaño: {tamano / 1024 / 1024:.1f} MB")
    return destino


def _tamano_total(ruta: Path) -> int:
    if ruta.is_file():
        return ruta.stat().st_size
    return sum(f.stat().st_size for f in ruta.rglob("*") if f.is_file())


if __name__ == "__main__":
    construir(unico="--unico" in sys.argv)
