# setup_instructor.ps1
# Ejecutar con: powershell -ExecutionPolicy Bypass -File setup_instructor.ps1

$project = "$env:USERPROFILE\Desktop\demo-bitcoin-main"
$python  = "$project\venv\Scripts\python.exe"

Write-Host ""
Write-Host "=== BLOCKCHAIN DEMO — Setup Instructor ==="
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

# 4. Detectar IP
Write-Host "[4/4] Detectando IP..."
$MyHost = (Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.IPAddress -notmatch "^127\." -and $_.IPAddress -notmatch "^169\." } |
    Select-Object -First 1).IPAddress

Write-Host ""
Write-Host "=== Listo ==="
Write-Host "IP del instructor: $MyHost"
Write-Host "Comparte esta IP con los alumnos."
Write-Host ""

$r = Read-Host "Arrancar seed node y dashboard global ahora? (s/n)"
if ($r -eq "s") {
    Set-Location $project

    Write-Host "Arrancando seed node..."
    Start-Process powershell -ArgumentList "-NoExit -ExecutionPolicy Bypass -Command `"cd '$project'; & '$python' main_seed.py`""
    Start-Sleep -Seconds 2

    Write-Host "Arrancando dashboard global..."
    Start-Process powershell -ArgumentList "-NoExit -ExecutionPolicy Bypass -Command `"cd '$project'; & '$python' main_global.py --seed-host $MyHost`""
    Start-Sleep -Seconds 1

    Write-Host ""
    Write-Host "Todo activo. IP para alumnos: $MyHost"
    Write-Host "Presiona Enter para cerrar..."
    Read-Host
}
