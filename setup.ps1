# setup.ps1
Write-Host "[1/5] Instalando Python..."
winget install 9NQ7512CXL7T --source msstore

Write-Host "[2/5] Descargando proyecto..."
Invoke-WebRequest -Uri "https://github.com/BrunoRavelo/demo-bitcoin/archive/refs/heads/main.zip" -OutFile "$env:USERPROFILE\Desktop\blockchain.zip"
Expand-Archive "$env:USERPROFILE\Desktop\blockchain.zip" -DestinationPath "$env:USERPROFILE\Desktop" -Force
Set-Location "$env:USERPROFILE\Desktop\demo-bitcoin-main"

Write-Host "[3/5] Creando entorno virtual..."
python -m venv venv
.\venv\Scripts\activate

Write-Host "[4/5] Instalando dependencias..."
python -m pip install -r requirements.txt

Write-Host "[5/5] Listo. Ejecuta: python main.py"
pause