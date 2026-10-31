# Accessibilité et ergonomie Windows

## Principes

Les couleurs ne suffisent pas à exprimer un verdict; libellés explicites et icônes secondaires. Prévoir ordre de tabulation, focus visible, raccourcis clavier documentés, annonce de progression non intrusive, taille de texte respectant DPI Windows, gestion Unicode, chemins longs et localisations françaises/anglaises.

## Spécificités Tk

La boucle Tk ne doit jamais attendre un subprocess ou un scan récursif complet. Les résultats en arrière-plan passent par une file et une mise à jour du thread UI. Une ouverture de panneau ne déclenche pas de diagnostic. Chaque écran restaure son focus logique après fermeture de dialogue.

## Tables

Les 127 lignes doivent rester utilisables au clavier; tri stable, sélection persistante au changement de filtre, colonnes techniques facultatives et export facile. Dans les grandes listes de findings, pagination et recherche plutôt qu'un unique bloc texte sans repères.

## Tests manuels minimum

DPI 100%/150%/200%; écran portable; Windows 10/11 selon support décidé; navigation clavier complète; thème clair/sombre si existant; noms de Kristals contenant accents; export vers chemin comportant espaces; aucun défilement horizontal obligatoire pour l'information prioritaire.

**Hors portée de cette livraison documentaire** : maquettes finales pixel-perfect ou charte colorimétrique. Le guide UX joint privilégie d'abord la structure des tâches.
