# ReTranscription

**Transcription audio → texte, 100 % en local.**  
Glissez un fichier MP3, obtenez un fichier TXT/SRT/VTT. Aucun envoi sur Internet : tout se passe sur votre machine.

## Fonctionnalités

- **Glisser-déposer** de fichiers audio (MP3, WAV, M4A, FLAC, OGG, MP4...)
- Transcription hors-ligne via l'IA **faster-whisper** (modèle « small » préchargé)
- Détection automatique de la langue ou choix forcé (fr, en, es, de, it...)
- Plusieurs modèles : `tiny` (ultra rapide) → `large-v3` (très précis)
- Sortie **.txt** (texte brut), **.srt** et **.vtt** (sous-titres)
- Sauvegarde automatique dans un dossier `transcriptions/` à côté de l'audio
- Interface sombre moderne, barre de progression, journal horodaté
- Exécutable autonome : aucun Python requis sur le poste cible

## Installation

### Avec l'exécutable (recommandé)

1. Récupérez `ReTranscription.exe` à la racine du projet (ou construisez-le, voir plus bas).
2. Double-cliquez sur **`Installer.bat`**.
3. L'installateur télécharge le modèle IA (~460 Mo, une seule fois), crée les raccourcis **Bureau** et **Menu Démarrer**, puis lance le programme.

### Sans exécutable (depuis les sources)

Prérequis : [Python 3.10+](https://www.python.org/downloads/) avec « Add python.exe to PATH » coché.

1. Double-cliquez sur **`Installer.bat`** : l'environnement virtuel, les dépendances et le modèle IA sont installés automatiquement.
2. Le programme se lance et les raccourcis sont créés.

## Utilisation

1. Glissez vos fichiers audio dans la fenêtre (ou bouton **+ Ajouter**).
2. Choisissez le **modèle** et la **langue** (détection automatique par défaut).
3. Cliquez sur **Lancer la retranscription**.
4. Le texte apparaît dans la zone **Résultat** : copiez-le, enregistrez-le, ou ouvrez le dossier de sortie.

### Mode ligne de commande

```bash
ReTranscription.exe transcribe mon_audio.mp3              # écrit mon_audio.txt
ReTranscription.exe transcribe mon_audio.mp3 --model tiny --language fr
ReTranscription.exe warmup --model small                  # pré-télécharger un modèle
```

## Construction de l'exécutable

```powershell
.\build.ps1            # construit dist\ReTranscription.exe puis le copie à la racine
.\build.ps1 -Clean      # reconstruction complète
```

## Structure du projet

```
retranscription/
├── app/
│   ├── main.py             # interface graphique (customtkinter + glisser-déposer)
│   ├── transcriber.py       # moteur de transcription (faster-whisper) + exports
│   ├── warmup_model.py      # pré-téléchargement du modèle IA
│   └── requirements.txt
├── Installer.bat           # installateur (double-clic)
├── install.ps1             # logique d'installation
├── build.ps1               # construction de ReTranscription.exe
├── Lancer ReTranscription.bat
└── ReTranscription.exe     # exécutable autonome (généré)
```

## Données locales

- `.models/` : modèles IA téléchargés (supprimables à tout moment)
- `transcriptions/` : fichiers texte générés (à côté des audios)
- `config.json` : préférences (modèle, langue, options)

Aucune donnée n'est envoyée sur le réseau, à part le téléchargement initial des modèles IA.
