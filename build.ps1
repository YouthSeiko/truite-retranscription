# Truite Retranscription - Construction du dossier TruiteRetranscription/
param(
    [switch]$Clean,
    [string]$OfferUrl = "",
    [string]$OfferUser = "",
    [string]$OfferPassword = "",
    [string]$OfferLabel = "Gregre"
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
$WebData = "{0};app\web" -f (Join-Path $Root "app\web")
$pyArgs = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    "--onedir",
    "--windowed",
    "--name", "TruiteRetranscription",
    "--icon", (Join-Path $Root "app\icon.ico"),
    "--add-data", $LogoData,
    "--add-data", $WebData,
    "--collect-data", "tkinterdnd2",
    "--collect-submodules", "uvicorn",
    "--hidden-import", "tkinterdnd2",
    "--hidden-import", "tkinterdnd2.TkinterDnD",
    "--hidden-import", "python_multipart",
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

Get-Process -Name "TruiteRetranscription" -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 1
Remove-Item -Recurse -Force $outDir -ErrorAction SilentlyContinue
if (Test-Path $outDir) {
    Write-Host "Impossible de vider le dossier $outDir (fichier utilise ?)." -ForegroundColor Red
    exit 1
}
Copy-Item -Recurse $distDir $outDir
if ($OfferUrl -and $OfferPassword) {
    $offer = [ordered]@{
        url = $OfferUrl
        password = $OfferPassword
    }
    if ($OfferUser) { $offer.username = $OfferUser }
    $offer.label = $OfferLabel
    $offerDir = Split-Path -Parent $outDir
    $offer | ConvertTo-Json | Set-Content -Path (Join-Path $offerDir "offer.json") -Encoding UTF8
    Write-Host "  Offre ecrite : $offerDir\offer.json ($OfferLabel -> $OfferUrl)" -ForegroundColor Gray
}
$size = [math]::Round((Get-ChildItem $outDir -Recurse -File | Measure-Object Length -Sum).Sum / 1MB, 1)
Write-Host ""
Write-Host "  Build OK : dossier TruiteRetranscription ($size Mo)" -ForegroundColor Green
Write-Host "  Pret pour l'installateur et pour la release GitHub." -ForegroundColor Gray
Write-Host ""
