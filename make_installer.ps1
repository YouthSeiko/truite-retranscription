# Truite Retranscription - Construit l'application puis l'installateur Windows
param(
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

$Iscc = @(
    (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
    (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
    (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe")
) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1

if (-not $Iscc) {
    Write-Host "Inno Setup 6 introuvable." -ForegroundColor Red
    Write-Host "Installation : winget install --id JRSoftware.InnoSetup --scope user" -ForegroundColor Gray
    exit 1
}

if (-not $SkipBuild) {
    & (Join-Path $Root "build.ps1")
    if ($LASTEXITCODE -ne 0) { exit 1 }
}

& $Iscc "/Qp" (Join-Path $Root "installer.iss")
if ($LASTEXITCODE -ne 0) {
    Write-Host "Echec de la compilation de l'installateur." -ForegroundColor Red
    exit 1
}

$setup = Join-Path $Root "installer_out\Installateur Truite Retranscription.exe"
if (-not (Test-Path $setup)) {
    Write-Host "Installateur introuvable apres compilation." -ForegroundColor Red
    exit 1
}

$size = [math]::Round((Get-Item $setup).Length / 1MB, 1)
Write-Host ""
Write-Host "  Installateur OK : $setup ($size Mo)" -ForegroundColor Green
Write-Host "  Copier ce fichier sur la cle USB, a cote de offer.json." -ForegroundColor Gray
Write-Host ""
