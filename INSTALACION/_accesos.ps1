# Deja los accesos directos apuntando al programa nuevo, PuntoYFamaCaja.exe.
#
# Por que hace falta: hasta la fase 15 el programa se llamaba TiendaPOS.exe, y los accesos
# del escritorio y del arranque automatico apuntan a ese archivo. Si se quedaran asi, al
# encender el PC se abriria el programa VIEJO sobre una base ya migrada.
#
# Solo toca accesos que apuntan a la carpeta del programa (-Programa). Cualquier otro acceso
# directo del equipo, aunque se llame parecido, no se toca.
#
# Uso:
#   _accesos.ps1 -Programa C:\TiendaPOS                 escritorio, y el arranque si ya estaba
#   _accesos.ps1 -Programa C:\TiendaPOS -ConInicio      ademas, que se abra solo al encender
#   _accesos.ps1 -Programa C:\TiendaPOS -Listar         solo mirar (lo usa DIAGNOSTICO)
#   -Escritorio y -Inicio permiten cambiar las carpetas (para probarlo sin tocar el equipo).

param(
    [Parameter(Mandatory = $true)][string]$Programa,
    [string]$Escritorio = '',
    [string]$Inicio = '',
    [switch]$ConInicio,
    [switch]$Listar
)

$ErrorActionPreference = 'Stop'
$NOMBRE = 'Punto y Fama.lnk'
$EXE = 'PuntoYFamaCaja.exe'
$EXES_CONOCIDOS = @('TiendaPOS.exe', $EXE)

function Escribir($texto, $color = 'Gray') { Write-Host $texto -ForegroundColor $color }
function Carpeta([string]$ruta) { return [IO.Path]::GetFullPath($ruta).TrimEnd('\') }

$pruebas = ($Escritorio -ne '') -or ($Inicio -ne '')
if ($Escritorio -eq '') { $Escritorio = [Environment]::GetFolderPath('Desktop') }
if ($Inicio -eq '') { $Inicio = [Environment]::GetFolderPath('Startup') }

$Programa = Carpeta $Programa
$exeNuevo = Join-Path $Programa $EXE
$shell = New-Object -ComObject WScript.Shell

$carpetas = @($Escritorio, $Inicio)
if (-not $pruebas) {
    # Tambien el escritorio de todos los usuarios y la barra de tareas, donde alguien pudo
    # anclarlo. Solo en el equipo de verdad, nunca en una prueba.
    $carpetas += [Environment]::GetFolderPath('CommonDesktopDirectory')
    $carpetas += Join-Path $env:APPDATA 'Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar'
}

# --- buscar los accesos al programa --------------------------------------------------------
$encontrados = @()
foreach ($c in $carpetas) {
    if (-not $c -or -not (Test-Path -LiteralPath $c)) { continue }
    foreach ($archivo in Get-ChildItem -LiteralPath $c -Filter '*.lnk' -File -ErrorAction SilentlyContinue) {
        try { $acceso = $shell.CreateShortcut($archivo.FullName) } catch { continue }
        $destino = $acceso.TargetPath
        if (-not $destino) { continue }
        $nombreExe = [IO.Path]::GetFileName($destino)
        $dirExe = ''
        try { $dirExe = Carpeta ([IO.Path]::GetDirectoryName($destino)) } catch { continue }
        if (($EXES_CONOCIDOS -contains $nombreExe) -and ($dirExe -ieq $Programa)) {
            $encontrados += [pscustomobject]@{ Archivo = $archivo.FullName; Carpeta = (Carpeta $c); Acceso = $acceso }
        }
    }
}

if ($Listar) {
    if ($encontrados.Count -eq 0) {
        Escribir "  *** No hay ningun acceso directo al programa ***" 'Yellow'
    }
    foreach ($e in $encontrados) {
        $ok = Test-Path -LiteralPath $e.Acceso.TargetPath
        $color = 'White'
        $nota = ''
        if (-not $ok) { $color = 'Red'; $nota = '   <-- ESE ARCHIVO NO EXISTE' }
        elseif ([IO.Path]::GetFileName($e.Acceso.TargetPath) -ne $EXE) { $color = 'Red'; $nota = '   <-- PROGRAMA VIEJO' }
        Escribir ("  " + $e.Archivo) $color
        Escribir ("      abre: " + $e.Acceso.TargetPath + " " + $e.Acceso.Arguments + $nota) $color
    }
    exit 0
}

if (-not (Test-Path -LiteralPath $exeNuevo)) {
    Escribir "  ERROR: no existe $exeNuevo" 'Red'
    exit 1
}

function Apuntar($acceso) {
    $acceso.TargetPath = $exeNuevo
    $acceso.WorkingDirectory = $Programa
    $acceso.IconLocation = "$exeNuevo,0"
    if ($acceso.Arguments -match '--demo') {
        # --demo carga productos y usuarios de ejemplo en una base vacia: nunca en la tienda.
        $acceso.Arguments = (($acceso.Arguments -replace '--demo', '') -split '\s+' | Where-Object { $_ }) -join ' '
        Escribir "      (se le quito --demo, que no debe usarse en la tienda)" 'Yellow'
    }
    $acceso.Save()
}

# --- corregir los que ya habia -------------------------------------------------------------
$inicioTenia = $false
foreach ($e in $encontrados) {
    $enInicio = ($e.Carpeta -ieq (Carpeta $Inicio))
    if ($enInicio) { $inicioTenia = $true }
    try {
        Apuntar $e.Acceso
        $final = $e.Archivo
        # En el escritorio y en el arranque, el acceso pasa a llamarse como el programa.
        if (($enInicio -or ($e.Carpeta -ieq (Carpeta $Escritorio))) -and ([IO.Path]::GetFileName($e.Archivo) -ne $NOMBRE)) {
            $final = Join-Path $e.Carpeta $NOMBRE
            if (Test-Path -LiteralPath $final) { Remove-Item -LiteralPath $e.Archivo -Force }
            else { Move-Item -LiteralPath $e.Archivo -Destination $final }
        }
        Escribir ("  Corregido: " + $final) 'Green'
    } catch {
        Escribir ("  No se pudo corregir " + $e.Archivo + ": " + $_.Exception.Message) 'Yellow'
    }
}

function Asegurar([string]$carpeta) {
    if (-not (Test-Path -LiteralPath $carpeta)) { New-Item -ItemType Directory -Path $carpeta | Out-Null }
    $ruta = Join-Path $carpeta $NOMBRE
    Apuntar ($shell.CreateShortcut($ruta))
    return $ruta
}

$enEscritorio = Asegurar $Escritorio
Escribir ("  Acceso en el escritorio: " + $enEscritorio) 'Green'

if ($ConInicio -or $inicioTenia) {
    $enArranque = Asegurar $Inicio
    Escribir ("  Se abre solo al encender: " + $enArranque) 'Green'
} else {
    Escribir "  Este PC no abria el programa al encender, y se deja igual."
}
exit 0
