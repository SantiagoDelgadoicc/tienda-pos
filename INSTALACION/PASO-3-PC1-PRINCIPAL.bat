@echo off
setlocal
title Tienda POS - PASO 3 - PC 1 (principal)

rem Necesita permisos de administrador para la direccion fija y el cortafuegos.
rem Si no los tiene, se relanza solo pidiendolos.
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
set "IP_PC1=192.168.50.1"
set "INICIO=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"

echo.
echo ===========================================================
echo   PASO 3 - CONFIGURAR EL PC 1 COMO PRINCIPAL
echo ===========================================================
echo.
echo   Este PC guarda el catalogo y se lo sirve al otro.
echo.
echo   *** NO TOCA LA BASE DE DATOS ***
echo   Los productos que cargaron hoy se quedan igual.
echo.
echo   Le va a poner la direccion fija %IP_PC1% a la tarjeta
echo   de red por CABLE. El wifi no se toca.
echo.
pause

echo.
echo -----------------------------------------------------------
echo  [1/4] Direccion fija en el cable
echo -----------------------------------------------------------
powershell -NoProfile -ExecutionPolicy Bypass -File "%ORIGEN%_red_cable.ps1" -Ip %IP_PC1%
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
echo  [2/4] Permiso en el cortafuegos
echo -----------------------------------------------------------
netsh advfirewall firewall delete rule name="TiendaPOS" >nul 2>&1
netsh advfirewall firewall add rule name="TiendaPOS" dir=in action=allow protocol=TCP localport=8477 profile=any
echo       Listo.

echo.
echo -----------------------------------------------------------
echo  [3/4] Modo servidor
echo -----------------------------------------------------------
if not exist "%DATOS%" mkdir "%DATOS%"
> "%DATOS%\red.json" echo {
>>"%DATOS%\red.json" echo   "modo": "servidor",
>>"%DATOS%\red.json" echo   "servidor_host": "",
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
echo ===========================================================
echo   PC 1 LISTO
echo ===========================================================
echo.
echo   Direccion de este PC por cable:  %IP_PC1%
echo.
echo   AHORA:
echo     1) Abre Tienda POS y comprueba que estan TODOS los
echo        productos que cargaron hoy.
echo     2) DEJALO ABIERTO.
echo     3) Vete al PC 2 y ejecuta PASO-4-PC2-SECUNDARIA.bat
echo.
pause
