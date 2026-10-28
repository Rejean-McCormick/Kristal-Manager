# Kristal Manager — consolidation icônes Windows + diagnostic intégré

**Version :** `0.1.0-alpha.15+icons-diagnostic-integre-2026-10-27`  
**Cible utilisateur :** `C:\mycode\Kristal\locals`  
**Palette :** vert Kristal `#1E6864`

## Sources fusionnées

- `Kristal-Manager-1924-Icones-Windows(1).zip` : **base de la fusion**. Contient les icônes du tableau, le module de lecture `icon_bridge.py`, le menu Icônes et le générateur Windows 2.5.0 (non lancé automatiquement).
- `znapshot_Kristal-Manager_10272119.zip` : copie de référence du Manager, comparée aux deux éditions, sans écraser les ajouts plus récents.
- `Kristal-Manager-Diagnostic-Integre-2026-10-27.zip` : fenêtre guidée `Diagnostic…`, moteur KristalDiag embarqué, profils V9/V10, extraction de rapports et preuves locales.

## Installer sur Windows

1. **Fermer** toutes les fenêtres du Manager.
2. Décompresser l'archive complète dans un **nouveau dossier** (par exemple `C:\mycode\Kristal\Kristal-Manager-Consolide`). Ne pas décompresser dans `locals` et ne pas mélanger manuellement les fichiers avec une ancienne version.
3. Lancer `Launch-Kristal-Manager.cmd` depuis ce dossier. Python 3.11+ avec Tkinter est requis.
4. Le dossier proposé est `C:\mycode\Kristal\locals`. Cliquer sur **Analyser le dossier**.
5. Sélectionner un Kristal principal. **Diagnostic…** ouvre une fenêtre au-dessus de Manager. Le profil **État du Kristal — recommandé** est déjà sélectionné. Cliquer sur **Lancer le diagnostic**.
6. Lire le verdict, les anomalies et, au besoin, cliquer sur **Copier le résultat** ou **Exporter le rapport…**.
7. Les icônes présentes dans les `desktop.ini` ou profils locaux sont lues dans la première colonne. Menu **Icônes → Actualiser les icônes** pour les recharger, **Info icône** pour connaître leur provenance.

### Prérequis KristalDiag

Le vrai KristalDiag 1.0.0-alpha.4 est **inclus** sous `tools/KristalDiag/`. Si `jsonschema>=4.20` n'est pas installé, la fenêtre proposera l'installation **sur accord explicite** (pip, connexion éventuellement nécessaire). Aucune saisie de chemin d'exécutable ou d'arguments n'est nécessaire. L'ancien connecteur externe reste accessible en mode avancé.

Les rapports sont enregistrés **hors des sources**, sous `%LOCALAPPDATA%\Kristal-Manager\diagnostics` sur Windows. Le programme ne modifie pas les fichiers lors de l'inventaire, de la lecture d'icônes, de la vérification locale ou du catalogue. Le **renommage** de dossier reste une opération modifiante qui exige une confirmation distincte ; l'Icon Generator est aussi un outil séparé pouvant écrire dans sa propre collection lorsque l'utilisateur l'ouvre.

### Inventaire et export

Les dossiers `original-snapshot-before-activation` et `_HISTORIQUE_AVANT_KRISTALIZER` imbriqués sont classés comme archives historiques, masquées par défaut, et **ne sont ni supprimés ni déplacés**. Le classement par catégorie, le tri, les exports ZIP et `.kristal` expérimental, le catalogue SQLite et les fonctions de journal restent présents.

### Limites

- `READY` n'est pas une preuve de conformité. **PASS** dans KristalDiag vaut seulement pour le **profil effectivement exécuté** (V9/V10) ; ni validation Framework V11, ni qualification C1 signée, ni publication.
- L'affichage d'une icône de présentation ne prouve pas qu'elle est installée dans Windows Explorer. Le générateur fourni sous `tools/icon-generator/` nécessite Node.js et reste distinct, avec lancement explicite.
- Le shell Windows, le titre de fenêtre `.ico` et l'installation native des icônes doivent encore être vérifiés sur Windows (tests graphiques exécutés sous Linux/Xvfb).
- Les anciennes opérations GitHub/publication/synchronisation du backend demeurent **désactivées**.

### Tests

Voir `TEST_CONSOLIDATION.md` pour les résultats de la suite et les limites de validation.
