# Consolidation du Thésaurus UNESCO (Manager et générateur d’icônes)

## Décision

- Une seule classification de sujet active : **Thésaurus UNESCO**, domaines `1`–`7`, 88 microthésaurus, URIs conservées.
- Arketype et profil d’usage restent indépendants.
- ISCED-F retiré des filtres, de l’inventaire actif, du panneau d’audit et de la sélection d’icônes ; fichiers historiques conservés pour traçabilité.
- Aucun crosswalk implicite ISCED → UNESCO. Déclarations absentes/incohérentes ou candidates signalées pour revue manuelle.
- Le token visuel `UT#` est volontairement différent des notations UNESCO et ne remplace pas leurs URI.
- L’écriture d’icônes et `desktop.ini` demeure une action explicite de l’utilisateur. Aucun Kristal local n’est modifié par l’audit.

## Chemins touchés

`kristal_manager/classification_bridge.py`, `classification_panel.py`, `inventory.py`, `gui.py`, `tools/icon-generator/index.html`, `server.mjs`, `runtime/scan-kristals.mjs`, `runtime/kristal-domain-palette.json`, `runtime/unesco-thesaurus-profile.json` et nouvelles instructions de migration.

## Migration

1. Établir une correspondance UNESCO explicite et relue dans `kristal.workspace.json > classification.unesco_thesaurus`.
2. Contrôler cohérence domaine/microthésaurus depuis le profil épinglé.
3. Scanner la collection, examiner `unresolved_unesco`; les anciens profils ISCED restent en attente sans être reconvertis.
4. Appliquer volontairement les icônes après contrôle visuel.
5. Ne pas recopier des codes ISCED de `.kristal/icon-profile.json` ou `desktop.ini` dans les métadonnées UNESCO.

Ce correctif **ne modifie pas les Kristals locaux sur `C:`** et ne prétend pas valider des correspondances sémantiques encore absentes.
