@echo off
setlocal enabledelayedexpansion
title Tienda POS - Diagnostico
set "DATOS=%LOCALAPPDATA%\TiendaPOS"

echo.
echo ===========================================================
echo   DIAGNOSTICO DE ESTE PC
echo ===========================================================
echo.
echo   Carpeta de datos: %DATOS%
echo.

echo -----------------------------------------------------------
echo  1. QUE PAPEL CREE QUE JUEGA ESTE PC
echo -----------------------------------------------------------
if exist "%DATOS%\red.json" (
    echo   red.json SI existe. Dice esto:
    echo.
    type "%DATOS%\red.json"
    echo.
) else (
    echo   *** red.json NO EXISTE ***
    echo.
    echo   Sin ese archivo el programa funciona SUELTO: se crea su
    echo   propia base de datos y carga el catalogo de ejemplo.
    echo   ES EXACTAMENTE EL SINTOMA DE VER PRODUCTOS INVENTADOS.
    echo.
)

echo -----------------------------------------------------------
echo  2. TIENE CATALOGO PROPIO?
echo -----------------------------------------------------------
if exist "%DATOS%\tienda.db" (
    for %%A in ("%DATOS%\tienda.db") do echo   tienda.db existe  -  %%~zA bytes
    echo.
    echo   En el PC PRINCIPAL esto es correcto.
    echo   En la CAJA SECUNDARIA esto ESTA MAL: no debe tener
    echo   catalogo propio, tiene que pedirselo al principal.
) else (
    echo   No hay tienda.db.
    echo   Correcto si este PC es la caja secundaria.
)
echo.

echo -----------------------------------------------------------
echo  3. QUE PROGRAMA HAY INSTALADO
echo -----------------------------------------------------------
if exist "C:\TiendaPOS\TiendaPOS.exe" (
    for %%A in ("C:\TiendaPOS\TiendaPOS.exe") do echo   C:\TiendaPOS\TiendaPOS.exe  -  del %%~tA
) else (
    echo   *** No hay nada en C:\TiendaPOS ***
)
echo.

echo -----------------------------------------------------------
echo  4. ULTIMAS LINEAS DEL REGISTRO
echo -----------------------------------------------------------
if exist "%DATOS%\logs\tienda_pos.log" (
    powershell -NoProfile -Command "Get-Content '%DATOS%\logs\tienda_pos.log' -Tail 12"
) else (
    echo   No hay registro todavia.
)
echo.

echo ===========================================================
echo   QUE HACER CON ESTO
echo ===========================================================
echo.
echo   Si este es la CAJA SECUNDARIA y arriba ves que red.json
echo   no existe, o que si existe un tienda.db, ejecuta:
echo.
echo        REPARAR-SECUNDARIA.bat
echo.
pause
