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

### Relais : faire transcrire par un autre PC

Un PC faible peut **déléguer ses transcriptions à un PC plus puissant** de la maison (ou réciproquement) :

1. Sur le **PC moteur** : activez le *Mode distant* (mot de passe) comme décrit ci-dessus.
2. Sur le **PC client** : cliquez sur le bouton **Relais**, saisissez l'adresse du PC moteur (ex. `http://192.168.1.14:8722`), son mot de passe, puis le **pseudo du compte** à utiliser (laisser vide pour le mot de passe global). Le bouton passe en « Relais : actif ».
3. Désormais, tout fichier déposé sur le PC client (interface ou page web locale) est **envoyé au PC moteur** : la progression et le texte reviennent en temps réel, le fichier `.txt` est écrit localement sur le client. Le PC client ne charge jamais le modèle IA.

Les deux PC peuvent faire tourner leur application en même temps. Le choix du **modèle et de la langue** reste celui du PC client (le PC moteur le téléchargera si nécessaire). Pour retirer le relais, recliquez sur le bouton *Relais*.

### Comptes utilisateurs et quota

L'accès à distance peut être ouvert à plusieurs personnes avec des **comptes** :

- **Création** : depuis la page web (bouton *Créer un compte*), ou en ligne de commande sur le PC moteur :
  ```bash
  TruiteRetranscription.exe register --user gregre --password ********
  ```
- **Quota** : chaque compte dispose d'un pool de **300 minutes** d'audio, régénéré de **1 minute toutes les 6 minutes** (plafonné à 300). Le quota se décompte de la durée audio réellement transcrite, et **uniquement** pour les fichiers envoyés par ce compte (page web ou relais) — les transcriptions locales sur le PC moteur ne sont jamais comptées.
- **Isolation** : chaque compte ne voit et ne télécharge que **ses** propres transcriptions.
- Le **mot de passe global** (Mode distant) reste un accès **administrateur** : illimité, il voit tous les jobs et tous les comptes avec leur solde.
- À quota épuisé, l'envoi est refusé (403) avec un message rappelant la régénération.
- Pour **supprimer un compte** : ouvrez `accounts.json` (uniquement des hachés scrypt) et effacez sa ligne.

### Version pré-configurée : bouton « Connexion sur Gregre »

Pour livrer l'application à une tierce personne (ex. Gregre) déjà reliée à votre PC, sans qu'elle ait à saisir d'adresse ni de mot de passe :

```powershell
.\build.ps1 -OfferUrl "http://192.168.1.14:8722" -OfferUser gregre -OfferPassword "********" -OfferLabel "Gregre"
```

Le dossier construit contient alors un `offer.json` **à côté** de lui (à la racine du projet — l'exe congelé le lit dans son dossier parent, comme tous ses fichiers de config) ; livrez le dossier **avec** ce `offer.json`. Au premier lancement, le bouton du header affiche **« Connexion sur Gregre »** (bleu) — un clic teste la connexion et le bouton passe en **« Gregre : actif »** (vert). Sans `offer.json`, le bouton *Relais* ouvre le dialogue manuel habituel.

> Utilisez de préférence les identifiants d'un **compte** dans l'offre : la transcription est alors soumise au quota. Le mot de passe global donne un accès administrateur illimité.

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
TruiteRetranscription.exe register --user gregre --password ****  # créer un compte distant
```

## Construction de l'exécutable

```powershell
.\build.ps1            # construit le dossier TruiteRetranscription\ à la racine
.\build.ps1 -Clean      # reconstruction complète
.\build.ps1 -OfferUrl "http://192.168.1.14:8722" -OfferUser gregre -OfferPassword "********" -OfferLabel "Gregre"
                        # idem + offer.json à côté du dossier (bouton « Connexion sur Gregre »)
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
│   ├── relay.py             # relais vers un PC moteur (forward des jobs)
│   ├── accounts.py          # comptes distants + quota (haché scrypt, 300 min)
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
- `remote_config.json` : mot de passe du mode distant (haché scrypt)
- `relay_config.json` : adresse + identifiants du relais (PC client uniquement)
- `accounts.json` : comptes distants (pseudo, haché scrypt, solde de quota)
- `offer.json` : offre de connexion pré-configurée (générée par `build.ps1 -Offer*`, jamais versionnée)
- `remote_uploads/` : copies reçues des appareils distants (supprimées après transcription)

Aucune donnée n'est envoyée sur Internet, à part le téléchargement initial des modèles IA. Sur le réseau local, transitent les fichiers audio vers le PC moteur et le texte en retour.
