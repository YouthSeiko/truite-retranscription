Truite Retranscription 1.1.0 — le mode distant arrive : utilisez votre PC et son modèle IA depuis votre téléphone.

## Nouveauté : Mode distant

- Bouton **Mode distant** dans l'application : définissez un mot de passe, scannez le **QR code** avec votre téléphone.
- Page web mobile intégrée (aucun site externe) : envoyez vos fichiers audio, suivez la progression en temps réel, téléchargez le résultat en .txt / .srt / .vtt.
- **Même réseau** : fonctionne immédiatement sur votre Wi-Fi (autorisez le port au pare-feu à la première activation).
- **Depuis l'extérieur** : installez [Tailscale](https://tailscale.com/download) (gratuit) sur le PC et le téléphone — l'adresse 100.x s'affiche automatiquement, aucun port ouvert, tout chiffré.
- Commande serveur sans interface : `TruiteRetranscription.exe serve --port 8722`.

## Sécurité

- Mot de passe haché (scrypt), sessions sécurisées, blocage après 8 tentatives, aucune requête traitée sans session.
- Audio distant supprimé automatiquement après transcription ; rien n'est envoyé sur Internet.

## Installation

1. Téléchargez et décompressez l'archive.
2. Double-cliquez sur **Installer.bat** (modèle IA ~460 Mo une seule fois + raccourcis).
3. Ou lancez `TruiteRetranscription\TruiteRetranscription.exe`.

## Alertes antivirus ?

Faux positif connu (exécutable non signé + PyInstaller). Avast/AVG : « Continuer quand même ». SmartScreen : « Informations supplémentaires » → « Exécuter quand même ». Détails dans le README.
