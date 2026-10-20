Truite Retranscription 1.0.0 — transcription audio vers texte, 100 % en local.

## Installation
1. Téléchargez et décompressez l'archive.
2. Double-cliquez sur **Installer.bat** (télécharge le modèle IA ~460 Mo une seule fois, crée les raccourcis Bureau et Menu Démarrer).
3. Ou lancez directement `TruiteRetranscription\TruiteRetranscription.exe` (modèle téléchargé automatiquement à la première transcription).

## Alerte antivirus ?
C'est un faux positif connu : exécutable non signé + PyInstaller (même comportement technique que certains malwares, mais le code est intégralement open-source et rien n'est envoyé sur le réseau). **Avast/AVG** : « Continuer quand même ». **Windows SmartScreen** : « Informations supplémentaires » → « Exécuter quand même ». Détails dans le README, section « Alertes antivirus ».

## Contenu
- Dossier autonome, aucun Python requis
- Modèle faster-whisper « small » (téléchargé au premier lancement)
- Sorties .txt / .srt / .vtt, glisser-déposer, détection automatique de la langue
