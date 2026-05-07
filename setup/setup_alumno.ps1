# setup_alumno.ps1
# Ejecutar con: powershell -ExecutionPolicy Bypass -File setup_alumno.ps1
# Parametros opcionales:
#   -SeedHost  IP del instructor  (default: 192.168.1.100)
#   -MyPort    Puerto P2P propio  (default: 5000)
#   -Dashboard Puerto dashboard   (default: 8000)

param(
    [string]$SeedHost = "192.168.1.100",
    [int]$MyPort      = 5000,
    [int]$Dashboard   = 8000
)

$project = "$env:USERPROFILE\Desktop\demo-bitcoin-main"
$python  = "$project\venv\Scripts\python.exe"

Write-Host ""
Write-Host "=== BLOCKCHAIN DEMO — Setup Alumno ==="
Write-Host ""

# 1. Python
Write-Host "[1/4] Instalando Python..."
winget install 9NQ7512CXL7T --source msstore --accept-package-agreements --accept-source-agreements
Write-Host ""

# 2. Descargar proyecto
Write-Host "[2/4] Descargando proyecto..."
curl.exe -L "https://github.com/BrunoRavelo/demo-bitcoin/archive/refs/heads/main.zip" -o "$env:USERPROFILE\Desktop\blockchain.zip"
Expand-Archive "$env:USERPROFILE\Desktop\blockchain.zip" -DestinationPath "$env:USERPROFILE\Desktop" -Force
Write-Host ""

# 3. Entorno virtual e instalacion
Write-Host "[3/4] Creando entorno e instalando dependencias..."
Set-Location $project
python -m venv venv
& $python -m pip install -r requirements.txt --quiet
Write-Host ""

# 4. Detectar IP propia
Write-Host "[4/4] Detectando IP..."
$MyHost = (Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.IPAddress -notmatch "^127\." -and $_.IPAddress -notmatch "^169\." } |
    Select-Object -First 1).IPAddress

Write-Host ""
Write-Host "=== Listo ==="
Write-Host "Mi IP:      $MyHost"
Write-Host "Dashboard:  http://$($MyHost):$($Dashboard)"
Write-Host "Instructor: $($SeedHost):8888"
Write-Host ""
Write-Host "Comando para arrancar:"
Write-Host "python main.py --host $MyHost --seed-host $SeedHost"
Write-Host ""

$r = Read-Host "Arrancar ahora? (s/n)"
if ($r -eq "s") {
    & $python main.py --host $MyHost --seed-host $SeedHost
}
