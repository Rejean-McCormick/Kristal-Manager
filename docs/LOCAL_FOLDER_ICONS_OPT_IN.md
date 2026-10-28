# Gestion des icônes Windows locales — opt-in

Version : `alpha.15-ui-unesco.3` (Icon Generator intégré `2.7.0`).

## Procédure Windows

1. Installer **Python avec Tkinter** et **Node.js**, puis lancer Kristal-Manager.
2. Choisir `C:\mycode\Kristal\locals` (ou une autre racine parent de dossiers `Kristal-*`).
3. Dans **Icons**, ouvrir « Gérer les icônes de locals… » : sans rien activer, seul un aperçu est accessible. Aucun fichier source n'est modifié.
4. Pour personnaliser les icônes Windows, cocher **« Activer icônes personnalisées sur dossiers Windows (session) »** et confirmer. La coche est **désactivée par défaut** à chaque démarrage du Manager.
5. Rouvrir le générateur, cocher son autorisation propre, puis cliquer **Générer et appliquer toutes les icônes** et confirmer.
6. Vérifier les icônes dans l'Explorateur de fichiers Windows. Utiliser « Refresh icons » dans Manager pour actualiser l'aperçu.

## Politique et limites

- Les classifications de sujets proviennent **exclusivement** des déclarations UNESCO explicites et cohérentes du `kristal.workspace.json` ; les domaines sont `1..7`, les identifiants de fichiers utilisent `UT1..UT7` et les microthésaurus servent à la classification détaillée.
- Les profils de domaines ISCED existants ne produisent aucune catégorie UNESCO. Les dossiers non classés restent visibles mais sans icône applicable.
- Le mode `--locals` ne construit pas de Registry sur disque et ne modifie rien au lancement. L'autorisation côté serveur et le contrôle dans le navigateur sont deux barrières distinctes.
- Après consentement explicite, pour chaque dossier éligible, des fichiers de présentation `.kristal/*.ico` et `.kristal/icon-profile.json` sont créés / mis à jour, et `desktop.ini` personnalisé ; les attributs Windows nécessaires sont ajustés. Un rapport est écrit sous `%LOCALAPPDATA%\Kristal-Manager\icon-reports` quand disponible.
- Les fichiers canoniques (`canon/`, états, identité `state_ref`, assertions) ne sont jamais modifiés par cette fonction.
- Le Manager n'utilise plus `Ouvrir_Generateur.cmd` pour ses dossiers locaux. Ce lanceur demeure un flux **distinct** ciblant la collection historique.
- Le programme Node.js et le navigateur restent des composants de l'outil embarqué dans Manager ; le moteur n'est pas encore réécrit en Tkinter.
- Les tests automatisés valident le fonctionnement des fichiers en simulation. L'effet de rafraîchissement réel dans l'Explorateur Windows doit encore être vérifié sur Windows ; une confirmation visuelle ne peut pas être établie par les tests Linux.

## Tests

`pytest -q tests/test_local_folder_icons.py tests/test_unesco_classification.py tests/test_icon_integration_updated.py`
