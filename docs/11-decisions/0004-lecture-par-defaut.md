# ADR 0004 — Lecture seule par défaut et publication contrôlée

**Date** : 2026-10-31 · **Statut** : PRINCIPE ACTIF.

## Contexte

Les opérations historiques ont déjà impliqué des overlays sur les 127 sources, des changements de fingerprint Discovery et un incident GitHub lié à une base SQLite de 189 Mo. Un gestionnaire de lecture ne doit pas transformer une analyse en modification de production.

## Décision

Le parcours standard n'écrit jamais dans `locals`, le canon, GitHub ou le registre de décisions approuvées. Les corrections futures sont des plans séparés utilisant le Kit, avec aperçu, sauvegarde, hash, approbation et tests. La publication Git est une fonction avancée opt-in.

## Conséquences

Les utilisateurs voient des propositions au lieu de corrections silencieuses. Les avertissements sémantiques peuvent persister jusqu'à revue justifiée : c'est voulu. La protection est mesurable par un diff source avant/après.

## Alternative rejetée

« Réparer automatiquement jusqu'à 127 PASS » en modifiant les capacités/empreintes, ou activer GitSink pour satisfaire d'anciens tests.

## Validation

AC-02, AC-14, AC-16 obligatoires; audit de code sur les endroits écrivant à `locals` et tests de subprocess/permission.
