@echo off
setlocal
title Punto y Fama - Diagnostico
set "ORIGEN=%~dp0"
if not defined DATOS set "DATOS=%LOCALAPPDATA%\TiendaPOS"
if not defined PROGRAMA set "PROGRAMA=C:\TiendaPOS"

echo.
echo ===========================================================
echo   DIAGNOSTICO DE ESTE PC
echo ===========================================================
echo.
echo   Carpeta de datos: %DATOS%
echo   Programa:         %PROGRAMA%
echo.

echo -----------------------------------------------------------
echo  1. QUE PAPEL CREE QUE JUEGA ESTE PC, Y COMO SE LLAMA
echo -----------------------------------------------------------
if exist "%DATOS%\red.json" (
    echo   red.json SI existe. Dice esto:
    echo.
    type "%DATOS%\red.json"
    echo.
    echo.
    findstr /c:"nombre_caja" "%DATOS%\red.json" >nul
    if errorlevel 1 (
        echo   *** A ESTA CAJA LE FALTA EL NOMBRE ***
        echo   Se usara el nombre del PC. Para ponerle uno, ejecuta
        echo   PASO-2-ACTUALIZAR-PROGRAMA.bat, que lo pregunta al final.
        echo.
    )
) else (
    echo   *** red.json NO EXISTE ***
    echo.
    echo   Sin ese archivo el programa funciona SUELTO, con su propia
    echo   base de datos, sin hablar con el otro PC.
    echo   Si este PC es una de las dos cajas, ESTA MAL.
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
if exist "%PROGRAMA%\PuntoYFamaCaja.exe" (
    for %%A in ("%PROGRAMA%\PuntoYFamaCaja.exe") do echo   %PROGRAMA%\PuntoYFamaCaja.exe  -  del %%~tA
) else (
    echo   *** No esta PuntoYFamaCaja.exe en %PROGRAMA% ***
    echo   Ejecuta PASO-2-ACTUALIZAR-PROGRAMA.bat
)
if exist "%PROGRAMA%\TiendaPOS.exe" (
    echo.
    echo   *** SIGUE AHI EL PROGRAMA VIEJO: %PROGRAMA%\TiendaPOS.exe ***
    echo   Ejecuta PASO-2-ACTUALIZAR-PROGRAMA.bat, que lo aparta.
)
echo.

echo -----------------------------------------------------------
echo  4. ACCESOS DIRECTOS AL PROGRAMA
echo -----------------------------------------------------------
powershell -NoProfile -ExecutionPolicy Bypass -File "%ORIGEN%_accesos.ps1" -Programa "%PROGRAMA%" -Listar
echo.

echo -----------------------------------------------------------
echo  5. ULTIMAS LINEAS DEL REGISTRO
echo -----------------------------------------------------------
if exist "%DATOS%\logs\tienda_pos.log" (
    powershell -NoProfile -Command "Get-Content -Encoding UTF8 '%DATOS%\logs\tienda_pos.log' -Tail 12"
) else (
    echo   No hay registro todavia.
)
echo.

echo ===========================================================
echo   QUE HACER CON ESTO
echo ===========================================================
echo.
echo   Si este es la CAJA SECUNDARIA y arriba ves que red.json
echo   no existe, o que tiene un tienda.db propio, ejecuta:
echo.
echo        PASO-4-PC2-SECUNDARIA.bat
echo.
echo   Si sale algo en rojo o con asteriscos que no entiendes,
echo   mandame una foto de esta ventana.
echo.
pause
