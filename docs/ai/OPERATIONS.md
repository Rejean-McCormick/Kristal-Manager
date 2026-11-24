<!-- kOA Doc Server · Docs IA · lot 04 · proposition non certifiante -->
# Procédure IA — Kristal-Manager

**Objet :** Inventaire et préparation, sans certification implicite.

**Source de rédaction :** `Kristal-Manager_Code_snapshot.zip` (capture datée). Ce document ne déclare pas que les commandes ont été exécutées sur le poste local.

## Parcours recommandé

1. Privilégier la lecture locale et le contrôle `python -m kristal_manager verify <racine-du-kristal>` avec interprétation de son code de retour.
2. Conserver séparés `local_readiness`, `operational_result`, les `issues`, la `qualification` et la `publication` : un `READY` ne signifie pas `QUALIFIED`.
3. Ne pas modifier les copies `koa_upgrade_runs` en cours ni les sauvegardes nécessaires aux reprises.
4. Épingler le chemin, la révision du Kristal et la version Manager dans chaque rapport; préserver les avertissements Discovery.
5. Pour construire ou publier, déléguer aux outils propriétaires; Manager ne remplace ni le Framework ni KristalDiag.

## Documents propriétaires à consulter

`README.md`, `docs/03-modele/v9-v10-v11-natifs.md`, `kristal_manager/__main__.py`.

## Vérifications avant effet

- Confirmer la racine, la révision et les versions du dépôt réellement installé.
- Ne pas substituer la présente fiche aux `AGENTS.md`, contrats, ADR et validations propriétaires.
- Ne pas copier de secrets, données privées, rapports de maturité ou sauvegardes dans un ZIP public.
- Exécuter tout diagnostic, synchronisation ou publication **seulement après décision explicite**; préserver les rapports existants.
- Le Framework v11 demeure **facultatif et non bloquant** pour Doc Server.
