@echo off
setlocal
title Tienda POS - PASO 2 - Actualizar el programa

set "ORIGEN=%~dp0"
if not defined PROGRAMA set "PROGRAMA=C:\TiendaPOS"

echo.
echo ===========================================================
echo   PASO 2 - ACTUALIZAR EL PROGRAMA
echo   Se hace en LOS DOS PC
echo ===========================================================
echo.
echo   Copia solo el programa a %PROGRAMA%
echo.
echo   *** ESTE ARCHIVO NO TOCA NINGUNA BASE DE DATOS ***
echo   El catalogo del PC 1 se queda exactamente como esta.
echo.
echo   Cierra Tienda POS antes de seguir.
echo.
pause

if not exist "%ORIGEN%TiendaPOS\TiendaPOS.exe" (
    echo.
    echo   ERROR: no encuentro la carpeta TiendaPOS en el pendrive.
    pause
    exit /b 1
)

echo.
echo   Copiando... (115 MB, tarda un poco)
xcopy "%ORIGEN%TiendaPOS" "%PROGRAMA%\" /E /I /Y /Q >nul
if errorlevel 1 (
    echo   ERROR al copiar.
    pause
    exit /b 1
)

powershell -NoProfile -Command ^
  "$s=(New-Object -COM WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\Tienda POS.lnk');" ^
  "$s.TargetPath='%PROGRAMA%\TiendaPOS.exe'; $s.WorkingDirectory='%PROGRAMA%'; $s.Save()" >nul 2>&1

echo.
echo   LISTO. Programa actualizado y acceso directo en el escritorio.
echo.
echo   En el PC 1 sigue con:  PASO-3-PC1-PRINCIPAL.bat
echo   En el PC 2 sigue con:  PASO-4-PC2-SECUNDARIA.bat
echo.
pause
