> **Édition consolidée :** KristalDiag est désormais inclus et le bouton **Diagnostic…** lance sa fenêtre guidée. Voir `DEMARRER_DIAGNOSTIC.md` et `CONSOLIDATION_2026-10-27.md`. Les instructions historiques de configuration d’un outil externe ci-dessous ne concernent que le mode avancé.

# Intégration externe KristalDiag dans Kristal Manager

## État de l’intégration

Le dépôt reçu fournit le nom et la responsabilité de **KristalDiag / C1** (qualification indépendante d'une révision candidate précise), mais **ne contient ni son programme, ni sa documentation CLI, ni son format de preuve C1**. Le Manager ne doit pas inventer ce protocole.

Cette version fournit un **pont d'exécution paramétrable**. Un opérateur peut sélectionner un fichier local de confiance `.exe`, `.py`, `.js` ou `.mjs`, puis saisir les arguments CLI *réels* de sa version de KristalDiag. Aucun téléchargement, installation ou connexion au réseau n'est effectué par le Manager.

## Utilisation

1. Installer KristalDiag séparément, à l’extérieur de `C:\mycode\Kristal\locals`.
2. Ouvrir le nouveau Kristal Manager et analyser `C:\mycode\Kristal\locals`.
3. Dans **Actions → Configurer KristalDiag**, choisir le programme installé.
4. Saisir les **arguments exacts** tirés de l’aide de la version installée. La variable **`{workspace}`** est obligatoire et reçoit le chemin complet du Kristal sélectionné. La variable **`{report}`** est facultative et reçoit le chemin temporaire d'un fichier JSON qui peut être écrit par le programme.
5. Sélectionner un **Kristal principal** puis cliquer sur **KristalDiag (C1)…** ; une confirmation explicite précède le lancement.
6. Lire la colonne **KristalDiag**, la fiche et l'onglet **Détails JSON** ; exporter les résultats depuis **Actions → Exporter les diagnostics observés (JSON)…**.

> Les exemples de syntaxe affichés dans la configuration sont **fictifs**. Ne pas les prendre pour des commandes officielles KristalDiag. Tant qu'on ne connaît pas sa CLI, aucun diagnostic officiel n'a pu être lancé ni qualifié ici.

### Limites techniques

- **Aucun shell** utilisé ; le programme est lancé avec une liste d'arguments construite sans interpolation de commandes shell.
- Les fichiers de sortie de l'exécution sont stockés temporairement **hors des sources**, puis lus avec des limites de taille. Le Manager ne modifie pas volontairement les sources.
- **Un outil externe peut malgré tout modifier les sources ou se connecter au réseau** : sa fiabilité et son mode de fonctionnement doivent être établis avant exécution. Le Manager demande confirmation mais ne sandboxe pas le programme externe.
- Le Manager compare les empreintes de `kristal.workspace.json` et de certaines surfaces d’état connues avant/après le diagnostic. Il ne surveille **pas tous les fichiers**.
- Le code retour (y compris 0) et le texte retourné sont des **observations**, pas une attestation C1 indépendante. La sortie JSON est conservée telle quelle sans interprétation normative tant que le schéma de KristalDiag n'est pas fourni.
- Le rapport n'est conservé **que pour la session d'inventaire en cours** ; exporter le JSON avant de lancer un nouvel inventaire. Les anciens contrôles sont invalidés lors d’un scan neuf.
- La version ne lance **pas de validation en lot automatiquement**. Les validations de nombreux Kristals demanderont de connaître et sécuriser le protocole concret de KristalDiag.
- Les archives historiques imbriquées ne sont pas des Kristals principaux et ne peuvent pas être envoyées au pont.

## Contrat à intégrer lors de la livraison de KristalDiag

Pour une intégration C1 de bout en bout, fournir :

1. Le projet ou le binaire KristalDiag **et ses dépendances**.
2. La commande documentée pour valider un workspace et écrire un rapport machine JSON.
3. Le schéma exact du rapport, notamment statuts, issues, référence et engagement de révision, empreintes de preuve, et éventuelle signature/attestation.
4. Les politiques d'effets de bord (lecture seule, sorties, réseau), les codes de retour et la durée maximale attendue.

On pourra alors remplacer les états provisoires `EXECUTED_EXIT_0` / `EXECUTED_NONZERO` par un **affichage fidèle des verdicts KristalDiag**, valider les preuves, détecter une révision périmée et autoriser des campagnes en lot explicites. Cela nécessitera des tests contre le véritable KristalDiag.
