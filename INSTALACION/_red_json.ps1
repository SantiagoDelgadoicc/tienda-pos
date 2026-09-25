# Escribe red.json SIN perder lo que ya tenia, y se asegura de que la caja tenga nombre.
#
# Por que un script y no "echo" desde el .bat: antes cada paso reescribia el archivo entero
# y borraba el nombre de la caja. Si las dos cajas acaban con el mismo nombre, el cierre
# mezcla sus ventas sin avisar. Aqui solo se cambia lo que se pide y el resto se conserva.
#
# Se escribe en UTF-8 SIN BOM a proposito: es lo que espera el programa, y lo que
# PowerShell 5.1 NO hace por defecto con Set-Content ni Out-File.
#
# Uso:
#   _red_json.ps1 -Datos <carpeta> -Modo servidor -NombrePorDefecto "Caja 1"
#   _red_json.ps1 -Datos <carpeta> -Modo caja -Servidor 192.168.50.1 -NombrePorDefecto "Caja 2"
#   _red_json.ps1 -Datos <carpeta> -SoloSiFaltaNombre      (lo usa PASO-2)
#   _red_json.ps1 -Datos <carpeta> -Nombre "Caja 1"        (sin preguntar; para pruebas)

param(
    [Parameter(Mandatory = $true)][string]$Datos,
    [ValidateSet('', 'servidor', 'caja')][string]$Modo = '',
    [string]$Servidor = '',
    [string]$NombrePorDefecto = '',
    [string]$Nombre = '',
    [switch]$SoloSiFaltaNombre
)

$ErrorActionPreference = 'Stop'
# Lo mismo que hace el programa: espacios de sobra fuera y 40 caracteres como mucho.
$LARGO_MAX = 40

function Escribir($texto, $color = 'Gray') { Write-Host $texto -ForegroundColor $color }
function Normalizar([string]$texto) {
    $limpio = (($texto -split '\s+') | Where-Object { $_ -ne '' }) -join ' '
    if ($limpio.Length -gt $LARGO_MAX) { $limpio = $limpio.Substring(0, $LARGO_MAX) }
    return $limpio
}

$ruta = Join-Path $Datos 'red.json'

# --- leer lo que hay ---------------------------------------------------------------------
$actual = $null
if (Test-Path -LiteralPath $ruta) {
    try {
        # ReadAllText detecta el BOM si lo hay; sin BOM lee UTF-8.
        $actual = [IO.File]::ReadAllText($ruta) | ConvertFrom-Json
    } catch {
        $roto = "$ruta.roto"
        Copy-Item -LiteralPath $ruta -Destination $roto -Force
        Escribir "  red.json estaba ilegible. Se guarda una copia en red.json.roto" 'Yellow'
        $actual = $null
    }
}

if ($SoloSiFaltaNombre) {
    # PASO-2 no cambia el papel del equipo. Si nunca se configuro la red, lo hara el PASO 3 o 4.
    if ($null -eq $actual) {
        Escribir "  Este PC todavia no tiene red configurada (se hace en el PASO 3 o 4)."
        exit 0
    }
    if ((Normalizar ([string]$actual.nombre_caja)) -ne '') {
        Escribir ("  Esta caja ya tiene nombre: " + (Normalizar ([string]$actual.nombre_caja))) 'Green'
        exit 0
    }
}

# Se conservan las claves que ya hubiera, incluidas las que este script no conoce.
$config = [ordered]@{}
if ($null -ne $actual) {
    foreach ($p in $actual.PSObject.Properties) { $config[$p.Name] = $p.Value }
}
if ($Modo -ne '') { $config['modo'] = $Modo }
if ($Modo -eq 'servidor') { $config['servidor_host'] = '' }
if ($Servidor -ne '') { $config['servidor_host'] = $Servidor }
if (-not $config.Contains('modo')) { $config['modo'] = 'suelto' }
if (-not $config.Contains('servidor_host')) { $config['servidor_host'] = '' }
$puerto = 8477
if ($config.Contains('puerto')) { [void][int]::TryParse([string]$config['puerto'], [ref]$puerto) }
$config['puerto'] = $puerto

# --- el nombre de la caja ------------------------------------------------------------------
if ($NombrePorDefecto -eq '') {
    if ($config['modo'] -eq 'caja') { $NombrePorDefecto = 'Caja 2' } else { $NombrePorDefecto = 'Caja 1' }
}
$anterior = ''
if ($config.Contains('nombre_caja')) { $anterior = Normalizar ([string]$config['nombre_caja']) }

if ($Nombre -ne '') {
    $elegido = Normalizar $Nombre
} else {
    Escribir ""
    Escribir "  NOMBRE DE ESTA CAJA" 'Cyan'
    Escribir "  Es como aparece esta caja en el cierre del dia."
    Escribir "  LOS DOS PC TIENEN QUE TENER NOMBRES DISTINTOS: si se llaman" 'Yellow'
    Escribir "  igual, el cierre mezcla las ventas de las dos sin avisar." 'Yellow'
    Escribir ""
    if ($anterior -ne '') { $propuesto = $anterior } else { $propuesto = $NombrePorDefecto }
    $escrito = Read-Host ("  Nombre (Enter = " + $propuesto + ")")
    $elegido = Normalizar $escrito
    if ($elegido -eq '') { $elegido = $propuesto }
}
if ($elegido -eq '') { $elegido = $NombrePorDefecto }
$config['nombre_caja'] = $elegido

# --- escribir ------------------------------------------------------------------------------
if (-not (Test-Path -LiteralPath $Datos)) { New-Item -ItemType Directory -Path $Datos | Out-Null }
$json = $config | ConvertTo-Json
$temporal = "$ruta.nuevo"
[IO.File]::WriteAllText($temporal, $json, (New-Object System.Text.UTF8Encoding($false)))
Move-Item -LiteralPath $temporal -Destination $ruta -Force

Escribir ""
Escribir "  red.json queda asi:" 'Green'
([IO.File]::ReadAllText($ruta) -split "`r?`n") | ForEach-Object { Escribir ("    " + $_) 'White' }
exit 0
