# Kristal Icon Generator — UI OneClick + Auto Scan

Version **2.5.0**.

La collection utilisée automatiquement est :

```text
C:\mycode\Kristal\Kristal-Kollection
```

Le générateur scanne maintenant automatiquement les nouveaux dossiers :

```text
C:\mycode\Kristal\Kristal-Kollection\domains\Kristal-*
```

avant de reconstruire le Registry.

## Domaines : ISCED-F 2013 (UNESCO)

La charte maison est remplacée par les **11 grands domaines ISCED-F 2013** de l’Institut de statistique de l’UNESCO. Les codes `00` à `10` deviennent les codes de domaine canoniques des icônes et de `desktop.ini`.

Les couleurs restent une convention **Kristal** : l’UNESCO normalise les codes et intitulés, mais ne fournit pas de palette officielle pour ce système d’icônes. Voir `ISCED_F2013_POLICY.md`.

## Flux normal

```text
Ouvrir_Generateur.cmd
      ↓
scan de domains\Kristal-*
      ↓
profil explicite présent ? ── oui ──► le conserver
      │ non
      ▼
desktop.ini / métadonnées structurées / état / README
      ↓
classification de présentation déterministe
      ↓
.kristal\icon-profile.json
.kristal\auto-scan.json
      ↓
reconstruction Kristal Registry
      ↓
interface
      ↓
TON CLIC « Générer et appliquer toutes les icônes »
      ↓
ICO + .kristal + desktop.ini + Explorer
```

Aucune icône ni `desktop.ini` n'est appliqué aux dossiers avant le clic dans l'interface.

## Est-ce qu'une IA est nécessaire ?

Pas normalement.

Le scanner applique cette priorité :

1. `.kristal/icon-profile.json` complet ;
2. métadonnées explicites de `desktop.ini` ;
3. métadonnées structurées du Kristal (`applicability`, `artifact_type`, état, etc.) ;
4. README, noms de fichiers et structure du paquet ;
5. classification déterministe prudente.

Le scanner produit uniquement des **métadonnées de présentation dérivées**. Il ne modifie jamais les assertions ou le contenu sémantique du Kristal.

Une IA serait utile uniquement pour un Kristal réellement ambigu dont le domaine ou la nature ne peut pas être déterminé à partir de son paquet. Elle n'est donc pas une dépendance du générateur 2.4.0. Les cas de domaine ISCED réellement indéterminables sont signalés dans `unresolved_isced` plutôt que forcés dans une mauvaise catégorie.

## Exemple : Kristal-Pokemon

Le scanner reconnaît `Pokemon/Pokémon/game` et le rattache au grand domaine ISCED-F :

```text
02 — Arts et lettres
```

Sans nature explicitement déclarée, le choix prudent reste `REF`. La maturité dépend de la structure réelle du paquet. Par exemple, un paquet structuré mais encore modeste peut produire :

```text
KR-REF-02-M2.ico
```

avec :

```json
{
  "nature": "REF",
  "maturity": 2,
  "domains": [
    {"code":"02","name":"Arts et lettres","color":"#A85AA3"}
  ],
  "classification": {
    "scheme": "ISCED-F 2013",
    "level": "broad-field"
  }
}
```

Ce résultat est une **classification de présentation**, pas une assertion sémantique sur Pokémon.

## Maturité automatique

La maturité automatique mesure la maturité de la représentation :

```text
0  paquet vide / embryonnaire
1  paquet présent, peu structuré
2  métadonnées ou état structuré
3  structure bien cartographiée
4  structure v6 riche + sources importantes
5  jamais attribué automatiquement ; réservé à une déclaration explicite
```

## Domaine inconnu

Le scanner **ne crée plus de domaine ad hoc**. Si aucun grand domaine ISCED-F 2013 ne peut être attribué de façon défendable, il n’utilise pas `00` comme catégorie résiduelle :

```text
unresolved_isced
```

Le Kristal reste dans la collection et dans le Registry, mais aucune classification de domaine n’est inventée. Ce cas peut ensuite être résolu manuellement ou par un second avis IA.

## Fichiers de scan

Pour un Kristal nouvellement classé :

```text
<Kristal>\.kristal\
├── icon-profile.json
└── auto-scan.json
```

Le rapport global est écrit dans :

```text
C:\mycode\Kristal\Kristal-Kollection\_registry\icon-scan-report.json
```

`auto-scan.json` contient les preuves utilisées, les scores de confiance, le fichier d'état détecté et les métriques structurelles.

## Registry et fonctionnement sans Python

Le scanner est en Node.js et fonctionne même sans Python.

Si Python est disponible, le Registry 0.3 est reconstruit normalement. Si Python est absent, le serveur peut tout de même fusionner les nouveaux `icon-profile.json` dans le Registry existant pour que les nouvelles icônes restent générables.

## Application Windows

Après ton clic, pour chaque Kristal générable :

- l'ICO multi-résolutions est produit ;
- il est copié dans `<Kristal>\.kristal\` ;
- `desktop.ini` est mis à jour en UTF-16 ;
- les attributs `ReadOnly/Hidden/System` existants sont neutralisés avant écriture ;
- `Hidden/System` sont restaurés ;
- le dossier reçoit l'attribut requis par Explorer ;
- Explorer est rafraîchi.

Le correctif `EPERM` de la 2.2.2 reste donc intégré.

## Nomenclature

```text
KR-{NATURE}-{DOMAIN1}[-{DOMAIN2}][-{DOMAIN3}]-M{0..5}.ico
```

Natures : `REF`, `COL`, `MOD`, `PRT`, `TWN`, `INV`, `SRC`.

Le pictogramme central reste `#1e6864`.

## Dépendances

- **Node.js** : requis ;
- **Python** : recommandé pour reconstruire complètement le Registry, mais non requis pour détecter/classer un nouveau domaine et le rendre exploitable par le générateur ;
- aucune API IA ni clé API requise.


## Kristal v9

The generator remains presentation-only. It consumes Registry presentation profiles first and now records embedded `.kristal/v9/state-snapshot.json` identity/commitment when present as **observation metadata**, never as icon authority. The bundled v8 normalization overlay is retained only as a compatibility fallback.
