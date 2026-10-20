# Truite Retranscription

**Transcription audio → texte, 100 % en local.**  
Glissez un fichier MP3, obtenez un fichier TXT/SRT/VTT. Aucun envoi sur Internet : tout se passe sur votre machine.

## Fonctionnalités

- **Glisser-déposer** de fichiers audio (MP3, WAV, M4A, FLAC, OGG, MP4...)
- Transcription hors-ligne via l'IA **faster-whisper** (modèle « small » préchargé)
- Détection automatique de la langue ou choix forcé (fr, en, es, de, it...)
- Plusieurs modèles : `tiny` (ultra rapide) → `large-v3` (très précis)
- Sortie **.txt** (texte brut), **.srt** et **.vtt** (sous-titres)
- Sauvegarde automatique dans un dossier `transcriptions/` à côté de l'audio
- Interface sombre marine, barre de progression, journal horodaté
- Dossier autonome : aucun Python requis sur le poste cible

## Installation

### Téléchargement (recommandé)

1. Téléchargez **`TruiteRetranscription-*-win64.zip`** depuis les [Releases](https://github.com/YouthSeiko/truite-retranscription/releases).
2. Décompressez-le où vous voulez.
3. Double-cliquez sur **`Installer.bat`** à côté du dossier `TruiteRetranscription/` : le modèle IA (~460 Mo, une seule fois) est téléchargé, les raccourcis **Bureau** et **Menu Démarrer** sont créés, puis le programme se lance.

Sinon, double-cliquez simplement sur `TruiteRetranscription\TruiteRetranscription.exe` : le modèle se téléchargera automatiquement à la première transcription.

### Depuis les sources

Prérequis : [Python 3.10+](https://www.python.org/downloads/) avec « Add python.exe to PATH » coché.

1. Double-cliquez sur **`Installer.bat`** : l'environnement virtuel, les dépendances et le modèle IA sont installés automatiquement.
2. Le programme se lance et les raccourcis sont créés.

## Alertes antivirus (faux positif)

**Le programme est sûr** : le code est intégralement open-source, rien n'est envoyé sur le réseau hormis le téléchargement des modèles IA. Toutefois, Avast, AVG, Windows SmartScreen et d'autres affichent parfois un avertissement, et ce pour trois raisons techniques :

1. L'exécutable est **non signé** (pas de certificat de signature de code).
2. Il est construit avec **PyInstaller** : l'exe libère ses fichiers dans un dossier temporaire avant de démarrer — un comportement identique à celui observé chez certains malwares, donc signalé par les heuristiques.
3. Binaire **peu téléchargé** : les antivirus « apprennent » un fichier via les téléchargements, ça prend du temps.

### Que faire en cas d'alerte

| Antivirus | Action |
|---|---|
| **Avast / AVG** | Alerte « Fichier inconnu » → choisir **Continuer quand même**. Vous pouvez aussi déposer le faux positif sur [ce formulaire](https://www.avast.com/false-positive-file-form.php) (colonne *File hash*). |
| **Windows SmartScreen** | **Informations supplémentaires** → **Exécuter quand même**. |
| **Microsoft** | Accélérer la reconnaissance : [soumettre le fichier](https://www.microsoft.com/wdsi/filesubmission). |

### Signature de code

Le workflow [`.github/workflows/build-and-sign.yml`](.github/workflows/build-and-sign.yml) est prêt pour la **signature gratuite [SignPath](https://signpath.io/)** (programme open-source) : dès qu'un compte SignPath est lié à ce dépôt, les releases sont signées automatiquement et la plupart des avertissements disparaissent. Configuration à faire une fois :

1. Créer un compte sur [signpath.io](https://signpath.io/) avec votre compte GitHub (programme open-source gratuit).
2. Ajouter le dépôt `YouthSeiko/truite-retranscription` comme *Project* SignPath.
3. Créer un *API token* et l'enregistrer dans les secrets GitHub `SIGNPATH_API_TOKEN`.
4. Définir les variables GitHub : `SIGNPATH_ORGANIZATION_ID`, `SIGNPATH_PROJECT_SLUG`, `SIGNPATH_SIGNING_POLICY_SLUG`, `SIGNPATH_ARTIFACT_CONFIGURATION_SLUG`.
5. Pousser un tag `v*` (ou lancer le workflow manuellement) : build → signature → release.

## Utilisation à distance (Mode distant)

Le PC peut servir ses transcriptions à d'autres appareils (téléphone, tablette, autre PC) via une **page web intégrée** — aucun site externe, tout tourne dans l'application.

### Activation

1. Dans la fenêtre principale, cliquez sur **Mode distant**.
2. Définissez le **mot de passe** d'accès (8 caractères minimum).
3. Une fenêtre affiche le **QR code** et l'adresse à saisir depuis l'appareil distant.
4. Si Windows bloque la connexion, cliquez sur **« Autoriser le port au pare-feu »** (validation UAC).

Sur le même Wi-Fi : scannez le QR code avec l'appareil photo, connectez-vous, choisissez vos fichiers audio — la transcription se fait sur le PC (modèle IA local), le résultat se télécharge en .txt/.srt/.vtt.

### Depuis l'extérieur de votre réseau

**Recommandé — Tailscale (gratuit, aucun port ouvert) :**

1. Installez [Tailscale](https://tailscale.com/download) sur ce PC et sur vos appareils, connectez-vous avec le même compte.
2. L'appareil distant rejoint votre PC via l'adresse `http://100.x.y.z:8722` — automatiquement affichée dans la fenêtre Mode distant quand Tailscale est détecté.
3. Tout le trafic reste chiffré (WireGuard) et le PC n'est jamais exposé sur Internet.

**Alternative :** Cloudflare Tunnel ou port forwarding + DDNS (déconseillé sans HTTPS : le mot de passe transiterait en clair).

> Le mode LAN fonctionne en HTTP : acceptable sur un réseau domestique fiable. Pour un accès via Internet, passez impérativement par Tailscale ou un tunnel HTTPS.

### Sans interface graphique

```bash
TruiteRetranscription.exe serve --port 8722   # serveur seul (après activation du mot de passe)
```

## Utilisation

1. Glissez vos fichiers audio dans la fenêtre (ou bouton **+ Ajouter**).
2. Choisissez le **modèle** et la **langue** (détection automatique par défaut).
3. Cliquez sur **Lancer la retranscription**.
4. Le texte apparaît dans la zone **Résultat** : copiez-le, enregistrez-le, ou ouvrez le dossier de sortie.

### Mode ligne de commande

```bash
TruiteRetranscription.exe transcribe mon_audio.mp3              # écrit mon_audio.txt
TruiteRetranscription.exe transcribe mon_audio.mp3 --model tiny --language fr
TruiteRetranscription.exe warmup --model small                  # pré-télécharger un modèle
```

## Construction de l'exécutable

```powershell
.\build.ps1            # construit le dossier TruiteRetranscription\ à la racine
.\build.ps1 -Clean      # reconstruction complète
```

Le dépôt contient aussi un workflow GitHub Actions (`Build & Sign`) qui construit, signe (si SignPath est configuré) et publie la release automatiquement à chaque tag `v*`.

## Structure du projet

```
retranscription/
├── app/
│   ├── main.py             # interface graphique (customtkinter + glisser-déposer)
│   ├── transcriber.py       # moteur de transcription (faster-whisper) + exports
│   ├── jobs.py              # file de jobs partagée (local + distant)
│   ├── server.py            # serveur web intégré (FastAPI, auth, WebSocket)
│   ├── web/index.html       # page web mobile (embarquée dans l'exe)
│   ├── warmup_model.py      # pré-téléchargement du modèle IA
│   ├── make_icon.py         # génération de l'icône/logo (Pillow)
│   └── requirements.txt
├── .github/workflows/      # build + signature SignPath + release
├── Installer.bat           # installateur (double-clic)
├── install.ps1             # logique d'installation
├── build.ps1               # construction du dossier TruiteRetranscription\
├── Lancer Truite Retranscription.bat
└── TruiteRetranscription/  # dossier autonome (généré)
    └── TruiteRetranscription.exe
```

## Données locales

- `.models/` : modèles IA téléchargés (supprimables à tout moment)
- `transcriptions/` : fichiers texte générés (à côté des audios)
- `config.json` : préférences (modèle, langue, options)

Aucune donnée n'est envoyée sur le réseau, à part le téléchargement initial des modèles IA.
