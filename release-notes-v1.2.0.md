Truite Retranscription 1.2.0 — comptes avec quota, relais vers un PC moteur et version pré-configurée pour un tiers.

## Nouveauté : comptes utilisateurs et quota

- **Inscription ouverte** depuis la page web (bouton *Créer un compte*) ou en CLI : `TruiteRetranscription.exe register --user gregre --password ********`.
- Chaque compte reçoit **300 minutes** d'audio, régénérées de **1 minute toutes les 6 minutes** (plafonné à 300).
- Le quota se décompte uniquement des fichiers envoyés **par ce compte** (page web ou relais) : vos transcriptions locales restent illimitées.
- **Isolation** : chaque compte ne voit et ne télécharge que ses propres transcriptions. Le mot de passe global reste un accès **administrateur** illimité, avec la liste des comptes et leurs soldes.
- Badge de quota affiché sur la page web ; à épuisement, l'envoi est refusé avec un message expliquant la régénération.

## Nouveauté : relais vers un PC moteur

- Bouton **Relais** : déléguez vos transcriptions à un PC plus puissant de la maison — l'IA tourne chez lui, le `.txt` revient chez vous, le PC client ne charge jamais le modèle.
- Progression et texte en temps réel, annulation à distance, choix du modèle et de la langue côté client.
- Compatible comptes : le relais peut utiliser les identifiants d'un compte, le quota s'applique alors sur le PC moteur.

## Nouveauté : version pré-configurée « Connexion sur Gregre »

- Construction avec `build.ps1 -OfferUrl ... -OfferUser ... -OfferPassword ... -OfferLabel Gregre` : le dossier livré contient un `offer.json`.
- Au premier lancement, le bouton du header affiche **« Connexion sur Gregre »** — un clic connecte et l'état passe au vert. Aucune saisie d'adresse ni de mot de passe.

## Corrections (mode distant)

- Exe ne plante plus au démarrage (sortie console nulle gérée).
- Page web retrouvée dans l'executable (chemin de secours).
- Détection Tailscale fiabilisée (timeout, secours via ipconfig).

## Installation

1. Téléchargez et décompressez l'archive.
2. Double-cliquez sur **Installer.bat** (modèle IA ~460 Mo une seule fois + raccourcis).
3. Ou lancez `TruiteRetranscription\TruiteRetranscription.exe`.

## Alertes antivirus ?

Faux positif connu (exécutable non signé + PyInstaller). Avast/AVG : « Continuer quand même ». SmartScreen : « Informations supplémentaires » → « Exécuter quand même ». Détails dans le README.
