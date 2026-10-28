> **Politique active :** [UNESCO_THESAURUS_POLICY.md](UNESCO_THESAURUS_POLICY.md). Le texte ci-dessous décrit le comportement historique ISCED-F et n’est plus appliqué.

# Politique d'auto-scan Kristal Icon Generator 2.4

## But

Détecter tout nouveau `domains/Kristal-*` et produire un profil de présentation `kristal-icon/1.0` sans modifier le contenu sémantique du Kristal.

## Ordre d'autorité

```text
1. .kristal/icon-profile.json explicite et complet
2. desktop.ini [Kristal]
3. métadonnées structurées du Kristal
4. README + noms/structure du paquet
5. classification déterministe prudente
```

Une couche méta normalisée explicite chargée ensuite par le Registry reste prioritaire sur le profil auto-scanné.

## Nature

La nature est prise explicitement si disponible. Sinon des marqueurs structuraux/lexicaux sont utilisés pour `SRC`, `TWN`, `INV`, `PRT`, `MOD` et `COL`. En l'absence de signal fort, `REF` est le fallback conservateur.

## Domaines

Le scanner utilise les grands domaines **ISCED-F 2013 (UNESCO)**. Les anciens codes Kristal sont migrés vers ces codes. Exemple : `Pokemon`, `Pokémon`, `game`, `games` → `02` (Arts et lettres).

Si aucun grand domaine ISCED-F ne peut être attribué de façon défendable, le scanner ne fabrique pas un nouveau code et n’utilise pas `00` comme catégorie fourre-tout. Le Kristal est placé dans `unresolved_isced` pour révision ou second avis.

## Maturité

M0–M4 peuvent être inférés à partir de la présence et de la richesse structurelle du paquet. M5 n'est jamais attribué automatiquement.

## Traçabilité

Le scanner écrit :

```text
<Kristal>/.kristal/icon-profile.json
<Kristal>/.kristal/auto-scan.json
<Kollection>/_registry/icon-scan-report.json
```

`auto-scan.json` contient les preuves, métriques et niveaux de confiance utilisés.

## IA

Aucune IA externe n'est requise. Une IA peut être ajoutée plus tard comme second avis pour les profils à faible confiance, mais elle ne doit pas devenir une autorité sémantique ni bloquer le pipeline.
