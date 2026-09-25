@echo off
title Punto y Fama - Direccion de este PC

echo.
echo  ==========================================================
echo   DIRECCION DE ESTE PC EN LA RED
echo  ==========================================================
echo.
echo   Apunta el numero que sale aqui abajo. Lo necesitas para
echo   instalar la caja secundaria.
echo.

for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    echo      %%a
)

echo.
echo  ==========================================================
echo.
echo   Si sale mas de un numero, usa el que empieza por 192.168
echo.
echo   CONSEJO: entra al router y reserva esa direccion para este
echo   PC. Si no, el router se la puede cambiar solo cualquier dia
echo   y la caja secundaria dejara de conectar sin motivo aparente.
echo.
pause
