@echo off
setlocal
title Tienda POS - PASO 4 - PC 2 (caja secundaria)

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
set "INICIO=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"

echo.
echo ===========================================================
echo   PASO 4 - CONFIGURAR EL PC 2 COMO CAJA SECUNDARIA
echo ===========================================================
echo.
echo   Este PC no guarda catalogo: se lo pide al PC 1.
echo   El catalogo de ejemplo que tiene ahora se aparta.
echo.
echo   Antes de seguir, en el PC 1 tiene que estar:
echo     - hecho el PASO 3
echo     - Tienda POS ABIERTO
echo.
pause

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
echo  [2/4] Apartar el catalogo de ejemplo
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
echo  [3/4] Modo caja, apuntando al PC 1
echo -----------------------------------------------------------
if not exist "%DATOS%" mkdir "%DATOS%"
> "%DATOS%\red.json" echo {
>>"%DATOS%\red.json" echo   "modo": "caja",
>>"%DATOS%\red.json" echo   "servidor_host": "%IP_PC1%",
>>"%DATOS%\red.json" echo   "puerto": 8477
>>"%DATOS%\red.json" echo }
echo       Listo.
echo.
type "%DATOS%\red.json"

echo.
echo -----------------------------------------------------------
echo  [4/4] Que se abra solo al encender
echo -----------------------------------------------------------
powershell -NoProfile -Command ^
  "$s=(New-Object -COM WScript.Shell).CreateShortcut('%INICIO%\Tienda POS.lnk');" ^
  "$s.TargetPath='%PROGRAMA%\TiendaPOS.exe'; $s.WorkingDirectory='%PROGRAMA%'; $s.Save()" >nul 2>&1
if exist "%INICIO%\Tienda POS.lnk" (echo       Listo.) else (echo       No se pudo. Se abrira a mano.)

echo.
echo -----------------------------------------------------------
echo  COMPROBACION
echo -----------------------------------------------------------
echo.
echo   Probando la conexion de verdad...
echo.
call "%ORIGEN%PROBAR-CONEXION.bat" %IP_PC1%
pause
