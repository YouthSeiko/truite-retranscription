# Truite Retranscription - Installateur local
# Deux modes :
#   - TruiteRetranscription.exe present -> rien d'autre a preparer que le modele IA + raccourcis
#   - Sinon, si Python est present -> environnement virtuel + dependances + modele

param(
    [switch]$NoLaunch,
    [string]$Model = "small"
)

$ErrorActionPreference = "Continue"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Exe = Join-Path $Root "TruiteRetranscription.exe"
$Venv = Join-Path $Root ".venv"
$VenvPython = Join-Path $Venv "Scripts\python.exe"
$Requirements = Join-Path $Root "app\requirements.txt"
$ModelsDir = Join-Path $Root ".models"
$ShortcutName = "Truite Retranscription"

function Write-Step($text) {
    Write-Host ""
    Write-Host "==> $text" -ForegroundColor Cyan
}

function Get-Target {
    if (Test-Path $script:Exe) { return $script:Exe }
    return (Join-Path $script:Root "Lancer Truite Retranscription.bat")
}

function Install-Shortcuts($target) {
    Write-Step "Creation des raccourcis..."
    $desktop = [Environment]::GetFolderPath("Desktop")
    $programs = [Environment]::GetFolderPath("Programs")
    $icon = Join-Path $Root "app\icon.ico"
    $created = 0
    try {
        $shell = New-Object -ComObject WScript.Shell
        foreach ($dir in @($desktop, $programs)) {
            if (-not $dir) { continue }
            $lnk = $shell.CreateShortcut((Join-Path $dir "$ShortcutName.lnk"))
            $lnk.TargetPath = $target
            $lnk.WorkingDirectory = $Root
            $lnk.Description = "Transcription audio -> texte, en local"
            if (Test-Path $icon) { $lnk.IconLocation = "$icon,0" }
            $lnk.Save()
            $created++
        }
    } catch {
        Write-Host "  Raccourcis non crees : $($_.Exception.Message)" -ForegroundColor Yellow
    }
    if ($created -gt 0) {
        Write-Host "  Bureau + Menu Demarrer : $ShortcutName" -ForegroundColor Gray
    }
}

function Remove-OldShortcuts {
    $desktop = [Environment]::GetFolderPath("Desktop")
    $programs = [Environment]::GetFolderPath("Programs")
    foreach ($dir in @($desktop, $programs)) {
        if (-not $dir) { continue }
        $old = Join-Path $dir "ReTranscription.lnk"
        if (Test-Path $old) {
            Remove-Item -Force $old -ErrorAction SilentlyContinue
            Write-Host "  Ancien raccourci retire : $old" -ForegroundColor Gray
        }
    }
}

function Get-ModelReady {
    if (-not (Test-Path $ModelsDir)) { return $false }
    $found = Get-ChildItem -Path $ModelsDir -Recurse -Filter "model.bin" -ErrorAction SilentlyContinue | Select-Object -First 1
    return [bool]$found
}

Write-Host ""
Write-Host "  $ShortcutName - Installation" -ForegroundColor Green
Write-Host "  Transcription audio -> texte, 100% en local" -ForegroundColor Green
Write-Host ""

$hasExe = Test-Path $Exe
$python = Get-Command python -ErrorAction SilentlyContinue
$useVenv = $false

if ($hasExe) {
    Write-Step "Programme detecte : TruiteRetranscription.exe"
    Write-Host "  Aucun Python requis pour l'utilisation." -ForegroundColor Gray
} elseif ($python) {
    $useVenv = $true
    Write-Step "Recherche de Python..."
    $pyVersion = & $python.Source --version 2>&1
    Write-Host "  Trouve : $pyVersion" -ForegroundColor Gray
    Write-Host "  Pas d'executable pre-construit : installation depuis les sources." -ForegroundColor Gray

    Write-Step "Creation de l'environnement virtuel..."
    if (-not (Test-Path $VenvPython)) {
        & $python.Source -m venv $Venv
        if (-not (Test-Path $VenvPython)) {
            Write-Host "  Echec de la creation de l'environnement virtuel." -ForegroundColor Red
            exit 1
        }
        Write-Host "  Cree : $Venv" -ForegroundColor Gray
    } else {
        Write-Host "  Deja present : $Venv" -ForegroundColor Gray
    }

    Write-Step "Installation des dependances (faster-whisper, customtkinter)..."
    & $VenvPython -m pip install --upgrade pip --quiet 2>$null
    & $VenvPython -m pip install --quiet -r $Requirements
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Echec de l'installation des dependances." -ForegroundColor Red
        exit 1
    }
    Write-Host "  OK" -ForegroundColor Gray
} else {
    Write-Host "Ni TruiteRetranscription.exe, ni Python 3.10+ n'ont ete trouves." -ForegroundColor Red
    Write-Host "Telechargez la version avec executable, ou installez Python depuis" -ForegroundColor Yellow
    Write-Host "https://www.python.org/downloads/ (cochez 'Add python.exe to PATH')." -ForegroundColor Yellow
    exit 1
}

if (Get-ModelReady) {
    Write-Step "Modele IA deja present dans .models - aucun telechargement."
} else {
    Write-Step "Telechargement du modele IA '$Model' (~460 Mo, une seule fois)..."
    Write-Host "  Selon votre connexion, cela peut prendre quelques minutes..." -ForegroundColor Gray
    $warmupOk = $false
    if ($hasExe) {
        $proc = Start-Process -FilePath $Exe -ArgumentList "warmup","--model",$Model -WorkingDirectory $Root -Wait -PassThru
        $warmupOk = ($proc.ExitCode -eq 0)
    } elseif ($useVenv) {
        & $VenvPython (Join-Path $Root "app\warmup_model.py") $Model 2>$null
        $warmupOk = ($LASTEXITCODE -eq 0)
    }
    if ($warmupOk) {
        Write-Host "  Modele '$Model' pret." -ForegroundColor Green
    } else {
        Write-Host "  Telechargement interrompu (connexion ?)." -ForegroundColor Yellow
        Write-Host "  Il sera relance automatiquement au premier lancement." -ForegroundColor Yellow
    }
}

$target = Get-Target
Install-Shortcuts $target
Remove-OldShortcuts

Write-Host ""
Write-Host "  Installation terminee." -ForegroundColor Green
Write-Host ""

if (-not $NoLaunch) {
    Start-Process -FilePath $target -WorkingDirectory $Root
}
