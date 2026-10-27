# Kristal Manager — Interface refondue (27 octobre 2026)

### Nouveautés — catégories, organisation et exports

- **Catégorie** : colonne triable en cliquant l’en-tête, filtre déroulant fondé sur les données Discovery ou sur `subject.domain`, `state_scope.domain` et `native_model.kind`.
- **Archives internes** : les snapshots `archive/original-snapshot-before-activation` restent sur disque et sont visibles via la case « Afficher les archives internes / snapshots ». Ils ne sont plus comptés parmi les Kristals principaux.
- **Organiser / exporter ▾** (après sélection d’un Kristal) : proposer un nom `Kristal-...` fondé sur `title` ou `slug` déclaré dans `kristal.workspace.json`, ou exporter la totalité du dossier.
- **Renommage** : seule la racine directement sous `locals` est autorisée. Aucun renommage en lot ; prévisualisation et confirmation obligatoires. Pas de réécriture du JSON. Attention : les scripts ou liens contenant des chemins absolus pourront nécessiter un ajustement. Conserver des sauvegardes avant renommage.
- **ZIP** : copie complète du dossier source dans une archive standard, dehors des sources, sans remplacement de fichier existant.
- **.kristal expérimental** : conteneur ZIP, même contenu, avec un manifeste `kristal.manager-local-archive/0.1-experimental` supplémentaire. Ce n’est **PAS** un paquet canonique ou un format d’échange certifié par le Framework ; ne pas le confondre avec la conformité ou la publication.
- Les exports **incluent potentiellement des données privées** du Kristal source ; conserver localement les archives et les examiner avant de les partager.

Cette archive est une **variante de l'interface du Manager alpha.15 fourni par l'utilisateur**. Le moteur de récupération local reste le même, à l'exception de deux correctifs du catalogue : le `fsync` Windows et le ciblage exact d'un Kristal. Elle n'est **pas** une nouvelle version qualifiée du Framework.

## Identité visuelle (mise à jour du 27 octobre 2026)

- Le logo SVG fourni (`kristal_manager/assets/logo_k.svg`) est intégré dans l’en-tête de la fenêtre et dans les aperçus HTML locaux.
- Couleur principale officielle : **`#1E6864`** (titres, bouton principal, sélection, onglets et en-têtes des aperçus).
- Les fichiers PNG et ICO pré-rendus évitent toute dépendance de rendu SVG sur les postes Windows : **aucune installation additionnelle**.
- Une icône de fenêtre est chargée au lancement. Sous Windows, l’icône propre au raccourci `.cmd` dépend du raccourci Windows, mais le fichier `kristal_manager/assets/app_icon.ico` peut lui être attribué.
- Cette mise à jour n’affecte ni les règles de lecture seule ni les contrôles du moteur.

## Installation sous Windows

1. **Conserver une copie** de l'ancien dossier Kristal Manager. Ne pas écraser vos Kristals ni le dossier `C:\mycode\Kristal\locals`.
2. Décompresser **l'archive complète de ce Manager** dans un dossier neuf, par exemple `C:\mycode\Kristal\Kristal-Manager-Refonte`.
3. Vérifier que Python 3.11 ou plus récent est disponible. Aucun package externe n'est requis pour ouvrir la GUI Tkinter.
4. Double-cliquer `Launch-Kristal-Manager.cmd` dans ce nouveau dossier.
5. Sous Windows, le champ « Dossier à examiner » proposera `C:\mycode\Kristal\locals` si aucun autre dossier valide n'a déjà été mémorisé. Le Manager mémorise automatiquement le dernier dossier **analysé avec succès**. Pour forcer un chemin depuis une variable d'environnement, définir `KRISTAL_LOCALS`.

## Parcours recommandé

1. Cliquer sur **Analyser le dossier**. Cela réalise l'inventaire structurel de la racine affichée et de ses sous-dossiers.
2. Utiliser **Rechercher** pour trouver `Kristal-Architecture` (ou un autre Kristal).
3. Cliquer sur sa ligne. La **Fiche / prochaine étape** explique ce qui a réellement été mesuré.
4. Cliquer sur **Vérifier ce Kristal** pour contrôler localement les fichiers enregistrés.
5. Cliquer sur **Cataloguer ce Kristal** et enregistrer la base SQLite **en dehors** du dossier `locals` (par exemple sur le Bureau). L'analyse est limitée au dossier exact du Kristal, même s'il contient des sous-Kristals.
6. Ouvrir l'aperçu HTML depuis **Toutes les fonctions** > **Ouvrir un aperçu HTML** ou le menu **Actions**.
7. Consulter l'onglet **Journal des opérations** pour les résultats/erreurs ; utiliser **Copier**, **Effacer** ou **Enregistrer**.

Les fonctions moins fréquentes restent disponibles via **Toutes les fonctions ▾** et les menus : catalogue de toute la racine, inventaire JSON, aperçu privé Konstellation, journal et aide.

### Important : catalogue de sélection et catalogue global

- **Cataloguer ce Kristal** analyse *seulement* le workspace choisi avec `kristal.workspace.json` ; le répertoire sélectionné, et non le champ racine, détermine le périmètre.
- **Cataloguer tous les Kristals du dossier** explore récursivement le champ racine. Une confirmation le précise avant le choix du fichier de sortie.
- Les entrées de type `STATE-ONLY` sans fichier `kristal.workspace.json` ne sont pas éligibles au catalogue descriptif.
- Les catalogues et journaux sont des **fichiers dérivés locaux**, à enregistrer hors des Kristals sources. La fenêtre bloque les sorties sous les racines source connues ; le moteur de catalogue bloque aussi les sorties dans les workspaces analysés.
- Un nouveau scan structurel **invalide les anciens résultats** de vérification et catalogue à l'écran pour éviter de présenter une preuve périmée.

## Sécurité et limites

- `READY` signifie seulement que la structure et les états locaux sont reconnus.
- `LOCAL_CHECKS_PASSED` vérifie les sources enregistrées, pas les fichiers absents de l'inventaire.
- `active_v11` signifie que le catalogue descriptif reconnaît le graphe v11 sélectionné, pas qu'une conformité Framework v11 a été certifiée.
- Sans une référence Framework compatible, la vérification des engagements demeure `NOT_EVALUATED`. Qualification, publication, activation et droits d'accès ne sont pas établis.
- La récupération alpha.15 **ne restaure pas** les commandes historiques de synchronisation GitHub ou de publication ; elles demeurent bloquées par le backend.

## Modifications techniques

- `kristal_manager/gui.py` : interface Tk restructurée, libellés français, log dédié, menus et accès contextuels, fichier d'export sécurisé, gestion du contexte et tâches d'arrière-plan.
- `kristal_manager/ui_prefs.py` : répertoire de départ Windows, dernier dossier mémorisé dans `%LOCALAPPDATA%\Kristal-Manager\preferences.json`, sans écriture dans `locals`.
- `kristal_manager/content_catalog.py` : correction Windows de `fsync` (`r+b`), et `direct_only` pour une analyse ciblée sans sous-workspaces.
- `tests/test_ui_refonte.py` : tests de chemin par défaut, des préférences, de la portée exacte du catalogue et de l'interface graphique.

## Vérification réalisée sur le code livré

- **70 tests ciblés réussis** (tests d'interface ajoutés + catalogue, Discovery, vérification opérationnelle, récupération et contrôle C2).
- Ancienne suite intégrale : **14 échecs préexistants** dans `tests/test_core.py`, liés aux fonctions du backend historique volontairement désactivées et à une attente `VALID` obsolète (86 réussites avant nos ajouts ; la baseline en donne autant). Nous n'avons **pas** réactivé ces fonctions dangereuses pour simplement faire passer les tests.
- Essai graphique avec Tkinter sous un affichage Linux virtuel : analyse, sélection, copier/effacer le journal, catalogue de sélection.
- Essai du moteur sur le ZIP **Kristal-Architecture** fourni : `READY`, `LOCAL_CHECKS_PASSED`, Discovery `verified`, mode de catalogue `active_v11`, **248 assertions descriptives**, sans anomalies signalées au catalogue. Ce n'est pas une certification Framework.
- **Non vérifié physiquement sur Windows** dans cette session : le correctif de compatibilité Windows est présent et le scénario GUI reste à confirmer sur le poste utilisateur.

## Validation supplémentaire de l'organisation

- **70 tests ciblés réussis** dans l'environnement de test graphique Linux, dont tests du journal, des catégories, du masquage d'archives internes, du renommage confirmé et des exports.
- Essai réel avec `Kristal-Architecture.zip` : classe `architecture`, 1 sous-dossier historique distinct, export de 233 fichiers en ZIP et `.kristal`, CRC validés. Aucune modification de l'archive d'origine.
- Les 14 tests du backend historique (publication/synchronisation/migration) demeurent en échec **préexistant** dans la suite globale, car ces fonctions sont intentionnellement bloquées dans le code fourni.
- Les manipulations de dossiers et archives restent à valider physiquement sous Windows, notamment sur les volumes non-NTFS.

## Extension optionnelle — KristalDiag (pont expérimental)

L’interface comprend désormais une colonne **KristalDiag**, un bouton **KristalDiag (C1)…** pour le Kristal principal sélectionné, une configuration de programme externe et un **export des diagnostics observés en JSON**.

**Attention : KristalDiag n'était pas présent dans les archives remises.** Cette version sait lancer un programme local explicitement configuré, mais **ne connaît pas encore la commande officielle de KristalDiag ni son schéma d’attestation**. Un code de sortie 0 n'est pas une conformité Framework. Consulter `KRISTALDIAG_INTEGRATION.md` avant utilisation.
