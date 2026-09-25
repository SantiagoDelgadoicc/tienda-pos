@echo off
setlocal
title Punto y Fama - PASO 2 - Actualizar el programa

rem PROGRAMA, DATOS, ESCRITORIO e INICIO se pueden fijar desde fuera para probar este
rem archivo sin tocar el equipo. En la tienda no se fija ninguno.
set "ORIGEN=%~dp0"
set "EXE=PuntoYFamaCaja.exe"
if not defined PROGRAMA set "PROGRAMA=C:\TiendaPOS"
if not defined DATOS set "DATOS=%LOCALAPPDATA%\TiendaPOS"
set "ACCESOS=-Programa "%PROGRAMA%""
if defined ESCRITORIO set "ACCESOS=%ACCESOS% -Escritorio "%ESCRITORIO%""
if defined INICIO set "ACCESOS=%ACCESOS% -Inicio "%INICIO%""

echo.
echo ===========================================================
echo   PASO 2 - ACTUALIZAR EL PROGRAMA
echo   Se hace en LOS DOS PC, en la misma visita
echo ===========================================================
echo.
echo   Instala el programa nuevo en %PROGRAMA%
echo   El programa anterior se aparta, no se borra.
echo.
echo   *** ESTE ARCHIVO NO TOCA NINGUNA BASE DE DATOS ***
echo   El catalogo y las ventas del PC 1 se quedan como estan.
echo.
echo   Cierra el programa de la caja antes de seguir.
echo.
if not defined EN_CADENA pause

echo.
echo -----------------------------------------------------------
echo  [1/5] Comprobaciones
echo -----------------------------------------------------------
if not exist "%ORIGEN%PuntoYFamaCaja\%EXE%" (
    echo.
    echo   ERROR: no encuentro PuntoYFamaCaja\%EXE% en el pendrive.
    echo   No se ha cambiado nada.
    echo.
    pause
    exit /b 1
)
if not exist "%ORIGEN%PuntoYFamaCaja\_internal" (
    echo.
    echo   ERROR: al programa del pendrive le falta la carpeta _internal.
    echo   No se ha cambiado nada.
    echo.
    pause
    exit /b 1
)
tasklist /FI "IMAGENAME eq %EXE%" 2>nul | "%SystemRoot%\System32\find.exe" /I "%EXE%" >nul
if not errorlevel 1 goto abierto
tasklist /FI "IMAGENAME eq TiendaPOS.exe" 2>nul | "%SystemRoot%\System32\find.exe" /I "TiendaPOS.exe" >nul
if not errorlevel 1 goto abierto
echo       Todo en orden.

echo.
echo -----------------------------------------------------------
echo  [2/5] Apartar el programa anterior
echo -----------------------------------------------------------
set "SELLO="
for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"`) do set "SELLO=%%I"
if not defined SELLO set "SELLO=%RANDOM%%RANDOM%"
set "ANTERIOR=%PROGRAMA%-ANTERIOR-%SELLO%"
set "APARTADO="
if exist "%PROGRAMA%\" (
    move "%PROGRAMA%" "%ANTERIOR%" >nul
    if errorlevel 1 goto no_se_aparta
    set "APARTADO=1"
    echo       Guardado en %ANTERIOR%
) else (
    echo       No habia programa instalado. Bien.
)

echo.
echo -----------------------------------------------------------
echo  [3/5] Copiar el programa nuevo  (unos 115 MB, tarda un poco)
echo -----------------------------------------------------------
rem robocopy y no xcopy: aguanta mejor los pendrives. Devuelve 8 o mas si fallo.
robocopy "%ORIGEN%PuntoYFamaCaja" "%PROGRAMA%" /E /R:2 /W:2 /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 goto fallo_copia
if not exist "%PROGRAMA%\%EXE%" goto fallo_copia
if not exist "%PROGRAMA%\_internal\" goto fallo_copia
echo       Listo.

echo.
echo -----------------------------------------------------------
echo  [4/5] Accesos directos
echo -----------------------------------------------------------
powershell -NoProfile -ExecutionPolicy Bypass -File "%ORIGEN%_accesos.ps1" %ACCESOS%
if errorlevel 1 (
    echo.
    echo   AVISO: no se pudieron rehacer los accesos directos.
    echo   El programa esta instalado: se abre con %PROGRAMA%\%EXE%
)

echo.
echo -----------------------------------------------------------
echo  [5/5] Nombre de esta caja
echo -----------------------------------------------------------
powershell -NoProfile -ExecutionPolicy Bypass -File "%ORIGEN%_red_json.ps1" -Datos "%DATOS%" -SoloSiFaltaNombre
if errorlevel 1 (
    echo.
    echo   AVISO: no se pudo poner el nombre de la caja.
    echo   Ejecuta DIAGNOSTICO.bat y avisame.
)

echo.
echo ===========================================================
echo   LISTO. PROGRAMA ACTUALIZADO
echo ===========================================================
if defined EN_CADENA goto fin_ok
echo.
echo   Si es la primera vez en este PC, sigue con:
echo     PC 1:  PASO-3-PC1-PRINCIPAL.bat
echo     PC 2:  PASO-4-PC2-SECUNDARIA.bat
echo.
echo   Si solo estas actualizando: haz este mismo PASO 2 en el
echo   otro PC y despues abre el programa, PRIMERO EN EL PC 1.
echo.
:fin_ok
if not defined EN_CADENA pause
exit /b 0


:abierto
echo.
echo   El programa de la caja esta ABIERTO en este PC.
echo   Cierralo y vuelve a ejecutar este archivo.
echo   No se ha cambiado nada.
echo.
pause
exit /b 1

:no_se_aparta
echo.
echo   ERROR: no se pudo apartar %PROGRAMA%
echo   Suele ser una ventana del explorador abierta en esa carpeta,
echo   o el programa todavia cerrandose. Cierra todo y reintenta.
echo   No se ha cambiado nada.
echo.
pause
exit /b 1

:fallo_copia
echo.
echo   ERROR al copiar el programa nuevo.
if defined APARTADO (
    echo   Se deja el programa anterior como estaba...
    if exist "%PROGRAMA%\" rmdir /s /q "%PROGRAMA%"
    move "%ANTERIOR%" "%PROGRAMA%" >nul
    if errorlevel 1 (
        echo   *** NO SE PUDO. El programa anterior esta en:
        echo   *** %ANTERIOR%
        echo   *** Cambiale el nombre a %PROGRAMA% a mano.
    ) else (
        echo   Hecho: el equipo queda con el programa anterior.
    )
)
echo.
echo   Revisa que el pendrive este bien y reintenta.
echo.
pause
exit /b 1
