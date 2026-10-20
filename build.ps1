# Truite Retranscription - Construction de TruiteRetranscription.exe
param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "Environnement virtuel absent. Lancez d'abord Installer.bat" -ForegroundColor Red
    exit 1
}

& $VenvPython -m pip install --quiet pyinstaller pillow

$pyArgs = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    "--onefile",
    "--windowed",
    "--name", "TruiteRetranscription",
    "--icon", (Join-Path $Root "app\icon.ico"),
    "--collect-data", "tkinterdnd2",
    "--hidden-import", "tkinterdnd2",
    "--hidden-import", "tkinterdnd2.TkinterDnD",
    "--paths", (Join-Path $Root "app"),
    (Join-Path $Root "app\main.py")
)

if ($Clean) {
    Remove-Item -Recurse -Force (Join-Path $Root "build"), (Join-Path $Root "dist") -ErrorAction SilentlyContinue
}

& $VenvPython @pyArgs
if ($LASTEXITCODE -ne 0) {
    Write-Host "Echec de la construction." -ForegroundColor Red
    exit 1
}

$exe = Join-Path $Root "dist\TruiteRetranscription.exe"
if (Test-Path $exe) {
    Copy-Item -Force $exe (Join-Path $Root "TruiteRetranscription.exe")
    $size = [math]::Round((Get-Item (Join-Path $Root "TruiteRetranscription.exe")).Length / 1MB, 1)
    Write-Host ""
    Write-Host "  Build OK : TruiteRetranscription.exe ($size Mo)" -ForegroundColor Green
    Write-Host "  Copie a la racine du projet, prete pour l'installateur." -ForegroundColor Gray
    Write-Host ""
} else {
    Write-Host "Executable introuvable apres build." -ForegroundColor Red
    exit 1
}
