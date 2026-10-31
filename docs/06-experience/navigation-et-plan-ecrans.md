# Navigation cible — application orientée Kristals

## Structure principale (CIBLE)

```text
Manager
├── Vue d'ensemble        [priorités, historique récent, actions restantes]
├── Kristals              [liste unifiée, filtre, sélection]
│   └── Fiche Kristal
│       ├── Aperçu        [identité, structure, statut]
│       ├── Résultats     [diagnostics, analyse, preuves et historique]
│       ├── Contenu       [KQ/KP, limites de lecture et recherche]
│       └── Classement    [ARK, PRF, UNESCO, propositions et décisions]
├── Centre d'analyse      [lancer/monitorer scan et diagnostics par sélection]
└── Avancé                [imports, maintenance, publication contrôlée, préférences]
```

**Pas de page supplémentaire** si le centre et la liste peuvent partager le même contexte. Les « 4 espaces » sont une proposition de regroupement, pas un quota graphique fixe.

## Fonctions à fusionner

Les anciennes actions `Scan folder`, `Analyse globale`, `Diagnostic`, `catalogue`, `vérification` doivent utiliser des commandes d'application communes. Les anciens menus peuvent rediriger vers les mêmes actions mais ne doivent pas créer des pipelines parallèles. Le nouveau centre montre le **résultat courant** et les sorties au même endroit où on lance le travail.

## Détails de la liste

Colonnes par défaut : nom, readiness, dernière analyse et date, diagnostic (profil + fraîcheur), action requise. Colonnes facultatives : `state_ref`, URI UNESCO, ARK détaillés, nombre d'assertions, empreinte, artefacts. Filtres par `READY`, `WARN`, `FAILED`, `STALE`, `PROPOSED`, sans transformer une revue sémantique en erreur.

## Fiche Kristal

En-tête : titre, identité, chemin, type natif/v9/v11, dernier scan. Bandeau « état vérifié à telle date / périmé / inconnu ». Chaque onglet possède **son** état de chargement, ses preuves et actions proches. Le retour à la liste restaure sélection et filtres.

## Commandes avancées

GitHub/publishing, installation dépendances, logs, reconstructions de catalogue et maintenance des caches restent hors parcours principal et explicitement confirmés lorsqu'ils peuvent écrire.
