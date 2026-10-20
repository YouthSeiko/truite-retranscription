# Truite Retranscription - Construction du dossier TruiteRetranscription/
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

if ($Clean) {
    Remove-Item -Recurse -Force (Join-Path $Root "build"), (Join-Path $Root "dist") -ErrorAction SilentlyContinue
}

$LogoData = "{0};app" -f (Join-Path $Root "app\logo.png")
$pyArgs = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    "--onedir",
    "--windowed",
    "--name", "TruiteRetranscription",
    "--icon", (Join-Path $Root "app\icon.ico"),
    "--add-data", $LogoData,
    "--collect-data", "tkinterdnd2",
    "--hidden-import", "tkinterdnd2",
    "--hidden-import", "tkinterdnd2.TkinterDnD",
    "--paths", (Join-Path $Root "app"),
    (Join-Path $Root "app\main.py")
)

& $VenvPython @pyArgs
if ($LASTEXITCODE -ne 0) {
    Write-Host "Echec de la construction." -ForegroundColor Red
    exit 1
}

$distDir = Join-Path $Root "dist\TruiteRetranscription"
$outDir = Join-Path $Root "TruiteRetranscription"
if (-not (Test-Path (Join-Path $distDir "TruiteRetranscription.exe"))) {
    Write-Host "Executable introuvable apres build." -ForegroundColor Red
    exit 1
}

Remove-Item -Recurse -Force $outDir -ErrorAction SilentlyContinue
Copy-Item -Recurse $distDir $outDir
$size = [math]::Round((Get-ChildItem $outDir -Recurse -File | Measure-Object Length -Sum).Sum / 1MB, 1)
Write-Host ""
Write-Host "  Build OK : dossier TruiteRetranscription ($size Mo)" -ForegroundColor Green
Write-Host "  Pret pour l'installateur et pour la release GitHub." -ForegroundColor Gray
Write-Host ""
