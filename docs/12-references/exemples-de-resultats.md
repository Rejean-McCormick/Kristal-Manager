# Exemples d'entrées/sorties et pièges de lecture

## Observation livrée (forme simplifiée)

`central_store.record_diagnostic()` reçoit le dictionnaire produit par le bridge. Un sous-ensemble représentatif :

```json
{
  "format": "kristal.manager-kristaldiag/1.0",
  "engine": "KristalDiag (source fourni, intégré au Manager)",
  "workspace": "C:\\mycode\\Kristal\\locals\\Kristal-Accounting",
  "profile": "V9-State-Reader",
  "verdict": "PASS",
  "process_status": "EXECUTED_EXIT_0",
  "input_fingerprint": {"kristal.workspace.json": "sha256:<empreinte>"},
  "input_changed_during_run": false,
  "qualification": "NOT_ESTABLISHED",
  "attestation": "NOT_VERIFIED"
}
```

Exemple explicatif : la valeur `PASS` est **une illustration**, non un rapport daté à importer.

## Après lecture de l'index

```json
{
  "status": "PASS",
  "profile": "V9-State-Reader",
  "freshness": "CURRENT",
  "observed_at": "2026-10-31T12:00:00Z",
  "payload": {"format": "kristal.manager-kristaldiag/1.0"}
}
```

Un import d'ancien CSV porte un fingerprint vide et est `STALE_OR_UNVERIFIED`, même avec un verdict `PASS`.

## Rapport Arketype réel

```json
{
  "format": "arketype.structural-observation/0.1",
  "project": "Kristal-Accounting",
  "declaration": {"primary_archetype": "ARK-01"},
  "comparison": "BASE_INSPIREE_1_SUR_3",
  "declared_level": "1/3",
  "ambiguity": "AUCUN_CANDIDAT_PROBANT"
}
```

La comparaison utilise les noms de champs et les chemins, **pas** la signification des assertions. Dans l'interface, afficher « 1 critère structurel sur 3 observé », pas « Kristal valide à 33 % ».

## Résultat manager

`READY` et `LOCAL_CHECKS_PASSED` sont des observations de structure/intégrité locale. `review` signifie une décision sémantique en attente; une simple inférence limitée dans les 16 natifs n'établit pas une corruption de leur état.

## Tests de contrat

Valider le parseur sur des clés supplémentaires, dates absentes, anciens alias, chaînes vides, schémas non connus, evidence path externe, version supérieure du rapport et provenance inconnue. Une entrée invalide ne doit jamais être traitée comme `PASS`.
