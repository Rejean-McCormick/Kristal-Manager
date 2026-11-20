# Architecture du package v0.5

Le canon est `knowledge-base/corpus/koa-ecosystem.kristal-state.json`. Les catalogues éditoriaux vivent sous `knowledge-base/sources/`; les vues sont dérivées et reconstruisibles.

## Couches de lecture

1. **Structure** — composants, fonctions opératoires, autorités, contrats.
2. **Capacité** — capacités et besoins.
3. **Utilité** — familles d'usage orientées résultat.
4. **Workflow** — patterns réutilisables qui composent plusieurs capacités.
5. **Scénario** — instances éditoriales servant à tester/comprendre la composition.
6. **Preuve** — sources, status et runtime evidence restent séparés.

## Invariants

- scenario ≠ deployment;
- offer ≠ component;
- repository ≠ authority;
- hosting ≠ ownership;
- projection ≠ canon;
- prepared integration ≠ activated integration;
- feedback ≠ mutation cachée;
- utilité ≠ produit unique.

## Repository/evidence layer v0.5

`Repository` is now an explicit external-source-library/evidence/discovery layer with current-local and retained-historical observations. Repository records may realize/support a `Component`, `Artifact`, or `ExternalReference`; promotion to `Component` requires role evidence. Root README snapshots are retained under `external-source-library/evidence/repository-readmes-20261003/`.

## Enveloppe Kristal v9

La couche `.kristal/v9/` ne remplace pas ce modèle. Elle sépare explicitement :

- **canon logique** : le `kristal_state/6.0` existant;
- **build provenance** : les 18 catalogues JSON sous `knowledge-base/sources/`;
- **matérialisation** : les fichiers physiques et leurs digests;
- **read models** : `.kristal/v8/`, `knowledge-base/corpus/index.json` et les vues reconstruisibles;
- **lifecycle** : State Snapshot immuable + Activation séparée.

Le State Snapshot v9 n'acquiert aucune autorité simplement parce qu'il compose le state existant. Les frontières `repository ≠ authority`, `hosting ≠ ownership`, `scenario ≠ deployment` et `projection ≠ canon` restent normatives pour ce package.
