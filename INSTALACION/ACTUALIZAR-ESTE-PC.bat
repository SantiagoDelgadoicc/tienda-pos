@echo off
setlocal
title Punto y Fama - Actualizar este PC

rem Un solo doble clic por PC para la actualizacion habitual. Hace lo mismo que
rem PASO-1 y PASO-2 seguidos, sin sus pausas: si este PC tiene la base de datos
rem (el PC 1), la respalda y la comprueba ANTES de tocar nada; despues actualiza
rem el programa. No toca nunca la base de datos.
set "ORIGEN=%~dp0"
if not defined DATOS set "DATOS=%LOCALAPPDATA%\TiendaPOS"
set "EN_CADENA=1"
set "ULTIMO_RESPALDO="

set "PAPEL=PC 2 (caja secundaria)"
if exist "%DATOS%\tienda.db" set "PAPEL=PC 1 (el que tiene los productos)"

echo.
echo ===========================================================
echo   ACTUALIZAR ESTE PC
echo ===========================================================
echo.
echo   Este PC es:  %PAPEL%
echo.
if exist "%DATOS%\tienda.db" (
    echo   1. Copia los productos y las ventas al pendrive, y
    echo      comprueba que la copia sea identica.
    echo   2. Instala el programa nuevo. El viejo se aparta.
) else (
    echo   1. Instala el programa nuevo. El viejo se aparta.
)
echo.
echo   *** LA BASE DE DATOS NO SE TOCA ***
echo.
echo   Cierra el programa de la caja y pulsa una tecla.
pause >nul

if exist "%DATOS%\tienda.db" (
    call "%ORIGEN%PASO-1-RESPALDAR.bat"
    if errorlevel 1 goto parar
)

call "%ORIGEN%PASO-2-ACTUALIZAR-PROGRAMA.bat"
if errorlevel 1 goto parar

echo.
echo ===========================================================
echo   ESTE PC ESTA LISTO
echo ===========================================================
echo.
if defined ULTIMO_RESPALDO (
    echo   Respaldo comprobado en:
    echo     %ULTIMO_RESPALDO%
    echo.
    echo   AHORA: haz lo mismo en el PC 2.
    echo   Despues vuelve aqui y abre el programa, PRIMERO AQUI.
) else (
    echo   AHORA: abre el programa en el PC 1 primero, y despues
    echo   aqui. Si en el PC 1 ya esta abierto, abrelo aqui ya.
)
echo.
pause
exit /b 0

:parar
echo.
echo ===========================================================
echo   SE PARO. LEE EL MENSAJE DE ARRIBA.
echo ===========================================================
echo.
echo   La base de datos no se ha tocado.
echo   Si no sabes que hacer, ejecuta DIAGNOSTICO.bat y avisame.
echo.
pause
exit /b 1
