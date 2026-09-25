@echo off
setlocal
title Punto y Fama - PASO 4 - PC 2 (caja secundaria)

net session >nul 2>&1
if errorlevel 1 (
    echo.
    echo   Pidiendo permisos de administrador...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs" >nul 2>&1
    exit /b
)

set "ORIGEN=%~dp0"
if not defined DATOS set "DATOS=%LOCALAPPDATA%\TiendaPOS"
if not defined PROGRAMA set "PROGRAMA=C:\TiendaPOS"
set "IP_PC2=192.168.50.2"
set "IP_PC1=192.168.50.1"

echo.
echo ===========================================================
echo   PASO 4 - CONFIGURAR EL PC 2 COMO CAJA SECUNDARIA
echo ===========================================================
echo.
echo   Este PC no guarda catalogo: se lo pide al PC 1.
echo   Si tiene un catalogo propio, se aparta (no se borra).
echo.
echo   Antes de seguir, en el PC 1 tiene que estar:
echo     - hecho el PASO 3
echo     - el programa ABIERTO
echo.
pause

if not exist "%PROGRAMA%\PuntoYFamaCaja.exe" (
    echo.
    echo   ERROR: el programa no esta instalado en %PROGRAMA%
    echo   Ejecuta antes PASO-2-ACTUALIZAR-PROGRAMA.bat
    echo.
    pause
    exit /b 1
)

echo.
echo -----------------------------------------------------------
echo  [1/4] Direccion fija en el cable
echo -----------------------------------------------------------
powershell -NoProfile -ExecutionPolicy Bypass -File "%ORIGEN%_red_cable.ps1" -Ip %IP_PC2%
if errorlevel 1 (
    echo.
    echo   No se pudo configurar el cable.
    echo   Si no vas a usar cable, ejecuta PLAN-B-WIFI.bat
    echo.
    pause
    exit /b 1
)

echo.
echo -----------------------------------------------------------
echo  [2/4] Apartar el catalogo propio, si lo hay
echo -----------------------------------------------------------
if exist "%DATOS%\tienda.db" (
    move /y "%DATOS%\tienda.db" "%DATOS%\tienda-NO-USAR.db" >nul
    echo       Guardado como tienda-NO-USAR.db  ^(no se borra^)
) else (
    echo       No habia catalogo. Bien.
)
del /q "%DATOS%\tienda.db-wal" 2>nul
del /q "%DATOS%\tienda.db-shm" 2>nul

echo.
echo -----------------------------------------------------------
echo  [3/4] Modo caja, apuntando al PC 1, y nombre de la caja
echo -----------------------------------------------------------
powershell -NoProfile -ExecutionPolicy Bypass -File "%ORIGEN%_red_json.ps1" -Datos "%DATOS%" -Modo caja -Servidor "%IP_PC1%" -NombrePorDefecto "Caja 2"
if errorlevel 1 (
    echo.
    echo   ERROR: no se pudo escribir red.json
    echo.
    pause
    exit /b 1
)

echo.
echo -----------------------------------------------------------
echo  [4/4] Que se abra solo al encender
echo -----------------------------------------------------------
powershell -NoProfile -ExecutionPolicy Bypass -File "%ORIGEN%_accesos.ps1" -Programa "%PROGRAMA%" -ConInicio
if errorlevel 1 echo       No se pudo. Se abrira a mano.

echo.
echo -----------------------------------------------------------
echo  COMPROBACION
echo -----------------------------------------------------------
echo.
echo   Probando la conexion de verdad...
echo.
call "%ORIGEN%PROBAR-CONEXION.bat" %IP_PC1%
