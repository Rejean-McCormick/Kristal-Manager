# Diagnostic intégré — Kristal Manager

## Utilisation (sans saisie de commandes)

1. Décompresser **toute l'archive** dans un nouveau dossier. Ne pas déplacer séparément `Kristal-Manager.pyw` : le moteur de diagnostic accompagne l'application dans `tools/KristalDiag/`.
2. Lancer `Launch-Kristal-Manager.cmd`.
3. Garder `C:\mycode\Kristal\locals` et cliquer sur **Analyser le dossier**.
4. Sélectionner un **Kristal principal** (p. ex. `Kristal-Architecture`) et cliquer sur **Diagnostic…**.
5. Dans la fenêtre ouverte, conserver **État du Kristal — recommandé** et cliquer sur **Lancer le diagnostic**.
6. Consulter le verdict, les anomalies et les preuves. Les boutons permettent **Copier le résultat**, **Exporter le rapport…**, **Ouvrir les preuves**.

Aucun programme ou argument n'est à saisir. Le Manager emploie automatiquement la copie de **KristalDiag 1.0.0-alpha.4** fournie par l'utilisateur et sa CLI documentée (`conform`, profil V9-State-Reader). La configuration externe historique est conservée uniquement pour les usages avancés.

## Prérequis

- Python 3.11+ avec Tkinter, nécessaire au Manager existant.
- Le module Python **jsonschema >=4.20**, requis par le vrai KristalDiag. S'il manque, la fenêtre propose **Installer le prérequis…**, action facultative confirmée explicitement (pip, peut nécessiter Internet).

## Où se trouvent les rapports ?

- Windows : `%LOCALAPPDATA%\Kristal-Manager\diagnostics\Kristal-NOM-AAAAMMJJ-...\current\summary.json` (ou selon la variable d'environnement habituelle de Python si `%LOCALAPPDATA%` n'est pas défini).
- Les preuves sont créées en dehors des dossiers `locals`.
- Les résultats du tableau sont conservés pour la session. Les preuves sur disque persistent après fermeture.

## Limites de la validation

- **PASS** est le verdict du **profil précis** fourni par KristalDiag, **pas** une qualification signée C1, une validation V11, une publication ou une autorisation.
- Cette copie de KristalDiag vise le Framework **10.0.0-draft.3.1**. La conformité au Framework V11 demande son propre protocole.
- Les profils avancés V10 peuvent échouer sur un Kristal local qui ne contient pas de surface d'hébergement.
- Le Manager ne lance ni commandes arbitraires ni exécution de code de la cible (`--allow-exec` absent). Il ne promet pas un sandbox complet du programme Python tiers.
- Le Manager compare les empreintes de fichiers d'état connus avant/après ; cette vérification n'inclut pas tous les fichiers sources.

## Autre correctif

Les dossiers imbriqués `_HISTORIQUE_AVANT_KRISTALIZER` sont maintenant traités comme **archives historiques**, comme `original-snapshot-before-activation`. Rien n'est déplacé ou supprimé.
