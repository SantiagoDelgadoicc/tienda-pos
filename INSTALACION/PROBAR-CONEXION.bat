@echo off
setlocal
title Tienda POS - Probar la conexion con el PC 1

set "IP=%~1"
if "%IP%"=="" set "IP=192.168.50.1"

echo.
echo ===========================================================
echo   PROBANDO LA CONEXION CON EL PC 1  (%IP%)
echo ===========================================================
echo.
echo   Se ejecuta en el PC 2.
echo   El PC 1 tiene que tener Tienda POS ABIERTO.
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ip='%IP%';" ^
  "Write-Host '  [1/2] Se ve el otro PC en la red?' -ForegroundColor Cyan;" ^
  "$p = Test-Connection -ComputerName $ip -Count 2 -Quiet -ErrorAction SilentlyContinue;" ^
  "if ($p) { Write-Host '        SI - el cable esta bien' -ForegroundColor Green }" ^
  "else { Write-Host '        No responde al ping. Puede ser el cable, o solo el' -ForegroundColor Yellow; Write-Host '        cortafuegos bloqueando el ping. Sigue con la prueba 2.' -ForegroundColor Yellow };" ^
  "Write-Host '';" ^
  "Write-Host '  [2/2] Responde Tienda POS? (esta es la que importa)' -ForegroundColor Cyan;" ^
  "try {" ^
  "  $r = Invoke-WebRequest -Uri ('http://'+$ip+':8477/api/estado') -TimeoutSec 5 -UseBasicParsing;" ^
  "  Write-Host '        SI - TODO CORRECTO' -ForegroundColor Green;" ^
  "  Write-Host ('        respuesta: ' + $r.Content) -ForegroundColor Gray;" ^
  "  Write-Host '';" ^
  "  Write-Host '  Ya puedes abrir Tienda POS en este PC.' -ForegroundColor Green" ^
  "} catch {" ^
  "  Write-Host '        NO responde' -ForegroundColor Red;" ^
  "  Write-Host ('        detalle: ' + $_.Exception.Message) -ForegroundColor DarkGray;" ^
  "  Write-Host '';" ^
  "  Write-Host '  Revisa, POR ESTE ORDEN:' -ForegroundColor Yellow;" ^
  "  Write-Host '    1. Tienda POS ABIERTO en el PC 1' -ForegroundColor Yellow;" ^
  "  Write-Host '    2. Que alla se ejecutara PASO-3-PC1-PRINCIPAL.bat' -ForegroundColor Yellow;" ^
  "  Write-Host '    3. El cable enchufado en los dos PC' -ForegroundColor Yellow;" ^
  "  Write-Host '    4. Ejecuta DIAGNOSTICO.bat en los dos' -ForegroundColor Yellow" ^
  "}"

echo.
pause
