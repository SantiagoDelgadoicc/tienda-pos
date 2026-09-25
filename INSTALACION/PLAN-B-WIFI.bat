@echo off
setlocal
title Punto y Fama - PLAN B - Conectar por wifi

net session >nul 2>&1
if errorlevel 1 (
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs" >nul 2>&1
    exit /b
)

set "ORIGEN=%~dp0"
if not defined DATOS set "DATOS=%LOCALAPPDATA%\TiendaPOS"

echo.
echo ===========================================================
echo   PLAN B - CONECTAR LAS CAJAS POR WIFI
echo ===========================================================
echo.
echo   Usa esto SOLO si el cable no funciono.
echo.
echo   Es peor que el cable por dos motivos, y conviene saberlo:
echo     - el wifi tiene cortes y tirones
echo     - el router puede cambiarle la direccion al PC 1 solo,
echo       y entonces el PC 2 deja de conectar sin motivo aparente
echo.
pause

echo.
echo   Que PC es este?
echo.
echo     1 = PC 1  (el que tiene el catalogo)
echo     2 = PC 2  (la caja secundaria)
echo.
set "CUAL="
set /p CUAL=  Escribe 1 o 2 y pulsa Enter:

if "%CUAL%"=="1" goto principal
if "%CUAL%"=="2" goto secundaria
echo   Opcion no valida.
pause
exit /b 1

:principal
echo.
echo -----------------------------------------------------------
echo   PC 1 POR WIFI
echo -----------------------------------------------------------
netsh advfirewall firewall delete rule name="TiendaPOS" >nul 2>&1
netsh advfirewall firewall add rule name="TiendaPOS" dir=in action=allow protocol=TCP localport=8477 profile=any
echo   Cortafuegos: listo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%ORIGEN%_red_json.ps1" -Datos "%DATOS%" -Modo servidor -NombrePorDefecto "Caja 1"
if errorlevel 1 (
    echo   ERROR: no se pudo escribir red.json
    pause
    exit /b 1
)

echo.
echo -----------------------------------------------------------
echo   APUNTA ESTA DIRECCION, la necesitas en el PC 2
echo -----------------------------------------------------------
echo.
powershell -NoProfile -Command "Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } | Select-Object InterfaceAlias, IPAddress | Format-Table -AutoSize"
echo.
echo   Usa la de la tarjeta Wi-Fi.
echo.
echo   MUY IMPORTANTE: entra al router y reserva esa direccion
echo   para este PC, o dejara de funcionar cualquier dia.
echo.
pause
exit /b 0

:secundaria
echo.
echo -----------------------------------------------------------
echo   PC 2 POR WIFI
echo -----------------------------------------------------------
echo.
set "IP="
set /p IP=  Direccion wifi del PC 1 (ej 192.168.1.45):
if "%IP%"=="" (
    echo   No escribiste nada.
    pause
    exit /b 1
)

if exist "%DATOS%\tienda.db" (
    move /y "%DATOS%\tienda.db" "%DATOS%\tienda-NO-USAR.db" >nul
    echo   Catalogo propio apartado como tienda-NO-USAR.db
)
del /q "%DATOS%\tienda.db-wal" 2>nul
del /q "%DATOS%\tienda.db-shm" 2>nul

powershell -NoProfile -ExecutionPolicy Bypass -File "%ORIGEN%_red_json.ps1" -Datos "%DATOS%" -Modo caja -Servidor "%IP%" -NombrePorDefecto "Caja 2"
if errorlevel 1 (
    echo   ERROR: no se pudo escribir red.json
    pause
    exit /b 1
)

echo.
call "%ORIGEN%PROBAR-CONEXION.bat" %IP%
exit /b 0
