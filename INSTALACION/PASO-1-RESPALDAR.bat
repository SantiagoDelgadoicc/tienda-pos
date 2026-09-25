@echo off
setlocal enabledelayedexpansion
title Punto y Fama - PASO 1 - Respaldar el catalogo del PC 1

if not defined DATOS set "DATOS=%LOCALAPPDATA%\TiendaPOS"
set "DESTINO=%~dp0RESPALDOS"

echo.
echo ===========================================================
echo   PASO 1 - RESPALDAR EL CATALOGO   (solo en el PC 1)
echo ===========================================================
echo.
echo   Esto NO cambia nada. Solo copia lo que hay al pendrive.
echo   Hazlo ANTES que ninguna otra cosa.
echo.
echo   CIERRA EL PROGRAMA DE LA CAJA ANTES DE SEGUIR.
echo   Con el programa abierto, la copia puede salir incompleta.
echo.
pause

if not exist "%DATOS%\tienda.db" (
    echo.
    echo   No hay ningun catalogo en %DATOS%
    echo   Este PC no es el principal, o el programa nunca se abrio aqui.
    echo.
    pause
    exit /b 1
)

rem La fecha con PowerShell y no con wmic: Windows 11 ya no trae wmic, y sin fecha cada
rem respaldo nuevo iria a la misma carpeta que el anterior y lo pisaria.
set "SELLO="
for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"`) do set "SELLO=%%I"
if not defined SELLO set "SELLO=sin-fecha-%RANDOM%%RANDOM%"
set "CARPETA=%DESTINO%\PC1-%SELLO%"

echo.
echo   Copiando a: %CARPETA%
if not exist "%DESTINO%" mkdir "%DESTINO%"
mkdir "%CARPETA%" 2>nul

rem Se copian tambien -wal y -shm si existen: son parte del catalogo mientras el
rem programa no los haya integrado. Copiar solo el .db puede dar un archivo vacio.
copy /Y "%DATOS%\tienda.db"     "%CARPETA%\" >nul
copy /Y "%DATOS%\tienda.db-wal" "%CARPETA%\" >nul 2>&1
copy /Y "%DATOS%\tienda.db-shm" "%CARPETA%\" >nul 2>&1
if exist "%DATOS%\backups" xcopy "%DATOS%\backups" "%CARPETA%\backups\" /E /I /Y /Q >nul 2>&1

echo.
echo ===========================================================
echo   RESPALDO HECHO
echo ===========================================================
echo.
dir /b "%CARPETA%"
echo.
for %%A in ("%CARPETA%\tienda.db") do echo   tienda.db = %%~zA bytes
echo.
echo   Si tienda.db son solo 4096 bytes, el catalogo esta en el
echo   archivo -wal. Por eso se copian los dos. No borres ninguno.
echo.
echo   AHORA SI, sigue con PASO-2-ACTUALIZAR-PROGRAMA.bat
echo.
pause
