# Configura la tarjeta de red por CABLE con una direccion fija.
#
# Por que fija y no automatica: en un cable directo entre dos PC no hay router que
# reparta direcciones. Windows acabaria inventandose una (169.254.x.x), tardaria casi
# un minuto en hacerlo y cambiaria cada vez. Con direcciones fijas, el enlace esta
# listo en cuanto arranca Windows y el numero nunca cambia, que es lo que permite
# "encender y trabajar".
#
# Uso:  powershell -ExecutionPolicy Bypass -File _red_cable.ps1 -Ip 192.168.50.1

param(
    [Parameter(Mandatory = $true)][string]$Ip,
    [int]$Prefijo = 24
)

$ErrorActionPreference = 'Stop'

function Escribir($texto, $color = 'Gray') { Write-Host $texto -ForegroundColor $color }

Escribir ""
Escribir "  Buscando la tarjeta de red por cable..." 'Cyan'

# Se descartan las inalambricas: el aparatito USB de wifi tambien es "fisico".
$tarjetas = @(Get-NetAdapter -Physical | Where-Object {
    $_.InterfaceDescription -notmatch 'Wireless|Wi-Fi|WiFi|802\.11|WLAN' -and
    $_.Name -notmatch 'Wi-Fi|Wireless'
})

if ($tarjetas.Count -eq 0) {
    Escribir ""
    Escribir "  No encuentro ninguna tarjeta de red por cable." 'Red'
    Escribir "  Comprueba que el cable este enchufado en los dos PC." 'Red'
    exit 1
}

if ($tarjetas.Count -eq 1) {
    $elegida = $tarjetas[0]
} else {
    Escribir ""
    Escribir "  Hay varias tarjetas por cable:" 'Yellow'
    for ($i = 0; $i -lt $tarjetas.Count; $i++) {
        $t = $tarjetas[$i]
        Escribir ("    {0} = {1}   [{2}]   estado: {3}" -f ($i + 1), $t.Name, $t.InterfaceDescription, $t.Status)
    }
    Escribir ""
    $n = Read-Host "  Escribe el numero de la que tiene el cable conectado"
    $idx = 0
    if (-not [int]::TryParse($n, [ref]$idx) -or $idx -lt 1 -or $idx -gt $tarjetas.Count) {
        Escribir "  Numero no valido." 'Red'
        exit 1
    }
    $elegida = $tarjetas[$idx - 1]
}

Escribir ""
Escribir ("  Tarjeta: {0}   [{1}]" -f $elegida.Name, $elegida.InterfaceDescription) 'White'
Escribir ("  Estado del cable: {0}" -f $elegida.Status) 'White'

if ($elegida.Status -ne 'Up') {
    Escribir ""
    Escribir "  AVISO: esa tarjeta dice que el cable NO esta conectado." 'Yellow'
    Escribir "  Se va a configurar igualmente, pero revisa el cable en los dos PC." 'Yellow'
}

# --- limpiar lo que hubiera y poner la direccion fija ---------------------------------
Escribir ""
Escribir "  Poniendo la direccion $Ip ..." 'Cyan'

Remove-NetIPAddress -InterfaceAlias $elegida.Name -AddressFamily IPv4 -Confirm:$false -ErrorAction SilentlyContinue
Remove-NetRoute -InterfaceAlias $elegida.Name -AddressFamily IPv4 -Confirm:$false -ErrorAction SilentlyContinue
# Sin puerta de enlace a proposito: este cable une los dos PC y nada mas. Poner una
# haria que Windows intentara salir a internet por aqui y rompiera el wifi.
New-NetIPAddress -InterfaceAlias $elegida.Name -IPAddress $Ip -PrefixLength $Prefijo | Out-Null

# --- red privada, o el cortafuegos bloquea aunque haya regla --------------------------
try {
    Set-NetConnectionProfile -InterfaceAlias $elegida.Name -NetworkCategory Private -ErrorAction Stop
    Escribir "  Red marcada como privada." 'Gray'
} catch {
    # Windows a veces tarda en clasificar una red recien creada. No es fatal.
    Escribir "  (No se pudo marcar como privada todavia; se reintentara al reiniciar.)" 'DarkGray'
}

Escribir ""
Escribir "  LISTO. Esta tarjeta tiene ahora la direccion $Ip" 'Green'
Escribir ""
Get-NetIPAddress -InterfaceAlias $elegida.Name -AddressFamily IPv4 |
    Select-Object InterfaceAlias, IPAddress, PrefixLength | Format-Table -AutoSize
exit 0
