@echo off
setlocal
title Punto y Fama - Recuperar el PIN del administrador

rem Para cuando nadie recuerda el PIN del administrador. Solo funciona en el PC 1, que es
rem donde esta la base de datos: en el PC 2 el programa se niega y lo dice. Hace un
rem respaldo antes de tocar nada y deja constancia en el registro. No toca productos,
rem ventas ni cierres: solo le da un PIN nuevo al administrador.
if not defined PROGRAMA set "PROGRAMA=C:\TiendaPOS"
set "EXE=%PROGRAMA%\PuntoYFamaCaja.exe"
set "BUSCAR=%SystemRoot%\System32\find.exe"

echo.
echo ===========================================================
echo   RECUPERAR EL PIN DEL ADMINISTRADOR   (solo en el PC 1)
echo ===========================================================
echo.
echo   1. Se abre una ventana que pide el nombre del administrador.
echo      Deja "Administrador" (o el nombre que tenga) y Aceptar.
echo   2. Aparece el PIN NUEVO. ANOTALO: se muestra una sola vez.
echo.
echo   Los productos, las ventas y los cierres NO se tocan.
echo.
echo   Cierra el programa de la caja y pulsa una tecla.
pause >nul

if not exist "%EXE%" (
    echo.
    echo   ERROR: no encuentro el programa en %PROGRAMA%
    echo.
    pause
    exit /b 1
)
tasklist /FI "IMAGENAME eq PuntoYFamaCaja.exe" 2>nul | "%BUSCAR%" /I "PuntoYFamaCaja.exe" >nul
if not errorlevel 1 (
    echo.
    echo   El programa esta ABIERTO. Cierralo y vuelve a ejecutar esto.
    echo.
    pause
    exit /b 1
)

echo.
echo   Abriendo la ventana de recuperacion...
start "" /wait "%EXE%" --reiniciar-admin
echo.
echo   Listo. Abre el programa y entra como administrador con el
echo   PIN nuevo. Si no alcanzaste a anotarlo, repite esto: sale otro.
echo.
pause
