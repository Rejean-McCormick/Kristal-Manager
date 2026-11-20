# Kristal Grand Challenges

Ce dépôt est **l’atelier de recherche** des 12 grands problèmes sélectionnés. Il est séparé de **Kristal Math** (corpus canonique global) et de **Formulator** (moteur de calcul et de preuve).

## Architecture

```text
                       Kristal Math
                  corpus canonique reconnu
                           |
                    import / résolution
                           v
Challenge docs  <-->  Challenge Kristal  ----+
notes humaines       mémoire structurée       |
hypothèses           propre au problème       v
sources/calculs                         Formulator
                                          |
                                  calcul / vérification
                                          |
                                      ProofBundle
                                          |
                                  résultats validés
                                          v
                              Challenge Kristal local
                                          |
                              promotion explicite éventuelle
                                          v
                                    Kristal Math
```

### Kristal Math

Le référentiel mathématique global : définitions, formules, théorèmes, réfutations, dépendances et provenance reconnues. Il reste indépendant de tout problème particulier.

### Challenge

Le dossier humain de recherche : énoncé, stratégie, synthèses IA, sources, notes, hypothèses, calculs narratifs et handoff courant.

### Challenge Kristal

Chaque Challenge possède **son propre Kristal local v6** dans `challenges/<slug>/kristal/`. C’est la mémoire machine structurée du problème. Le corpus MathKristal global reste en lecture seule; `imports/` n’est qu’une projection reconstruisible.

Il contient cinq couches logiques :

1. `imported` — faits/référents hérités d’un snapshot précis de Kristal Math ;
2. `established_external` — résultats reconnus et sourcés, utiles au problème mais pas encore présents dans le corpus global ;
3. `research` — nos hypothèses, calculs, lemmes et résultats provisoires ;
4. `validated_local` — résultats du Challenge fermés par une chaîne de vérification ;
5. `promotion_candidates` — résultats proposés pour intégration ultérieure au Kristal Math global.

### Formulator

Formulator est générique. Il reçoit :

```text
Challenge docs + Challenge Kristal + Kristal Math snapshot
```

Il calcule, résout les dépendances, teste les hypothèses, cherche des contre-exemples, compile vers des vérificateurs et tente de produire un `ProofBundle`.

## Structure d’un Challenge

```text
challenges/<slug>/
├── README.md
├── challenge.json
├── KRISTAL_INVENTORY.md
├── HYPOTHESES.md
├── CALCULATIONS.md
├── RESEARCH_LOG.md
├── SOURCES.md
├── FORMULATOR_HANDOFF.md
├── map/                  # optionnel: circuit de couverture non canonique
│   ├── <circuit>.json
│   ├── junctions.json
│   ├── gaps.json
│   └── satellites.json
└── kristal/
    ├── manifest.json
    ├── README.md
    ├── imports/
    │   ├── kristal-global.assertions.json
    │   └── kristal-global.referents.json
    ├── known/
    │   ├── core.json
    │   └── INDEX.md
    ├── research/
    │   ├── research-graph.json
    │   ├── active-frontier.json
    │   ├── frames.json
    │   ├── hypotheses.json
    │   ├── calculations.jsonl
    │   ├── results.jsonl
    │   ├── proof-obligations.jsonl
    │   ├── attempts.jsonl
    │   ├── agent-contributions.jsonl
    │   └── strategy-observations.jsonl
    ├── evidence/
    ├── promotion/
    │   └── candidates.json
    └── indexes/
        └── summary.json
```

## Les 12 dossiers

- [Birch–Swinnerton-Dyer](challenges/birch-swinnerton-dyer/README.md)
- [Hypothèse de Riemann](challenges/riemann-hypothesis/README.md)
- [Fonctorialité de Langlands](challenges/langlands-functoriality/README.md)
- [Problème de Galois inverse sur ℚ](challenges/inverse-galois/README.md)
- [Conjecture de Tate](challenges/tate-conjecture/README.md)
- [Conjecture de Hodge](challenges/hodge-conjecture/README.md)
- [P vs NP](challenges/p-vs-np/README.md)
- [Conjecture de Littlewood](challenges/littlewood-conjecture/README.md)
- [Kakeya en dimension ≥ 4](challenges/kakeya-higher-dimensional/README.md)
- [Conjecture de Schanuel](challenges/schanuel-conjecture/README.md)
- [Conjecture de Poincaré lisse en dimension 4](challenges/smooth-4d-poincare/README.md)
- [Yang–Mills et mass gap](challenges/yang-mills-mass-gap/README.md)

## Principe central

```text
connu globalement              -> Kristal Math
connu utile au problème        -> Challenge Kristal / known
hypothèse ou calcul de recherche -> Challenge Kristal / research
preuve locale vérifiée         -> Challenge Kristal / validated_local
fait candidat au canon global  -> promotion explicite, jamais automatique
```

Voir [`docs/09_CHALLENGE_KRISTAL_ARCHITECTURE.md`](docs/09_CHALLENGE_KRISTAL_ARCHITECTURE.md).


## Alignement MathKristal

Voir [`docs/10_MATHKRISTAL_ALIGNMENT.md`](docs/10_MATHKRISTAL_ALIGNMENT.md). Le builder utilise le `reverse-index`, `proof-closure`, Formula IR et la provenance du snapshot MathKristal épinglé. Le fichier `kristal/state.json` de chaque Challenge est un `kristal_state` v6 distinct du canon global.

## Dynamiques de recherche

Chaque Challenge contient maintenant deux états distincts sous `kristal/research/` :

- `research-graph.json` — objectifs, obligations et dépendances de recherche ;
- `active-frontier.json` — cache borné et reconstruisible du voisinage MathKristal actuellement utile.

Les essais sont append-only dans `attempts.jsonl`. Les observations de stratégie vivent dans `strategy-observations.jsonl` et peuvent être agrégées par Formulator entre les 12 Challenges. Elles ne deviennent jamais des faits mathématiques. Voir `docs/11_RESEARCH_DYNAMICS.md`.

## Console opérateur

Les 12 dossiers sont directement pilotables depuis **Formulator Console**. Aucun script propre au Challenge n'est requis : la console lit `challenge.json`, le Kristal local et les mémoires `kristal/research/`, puis écrit les nouvelles tentatives et contributions dans ces mêmes structures.

Depuis le repo Formulator v5 :

```bash
PYTHONPATH=src python -m formulator console \
  --challenges-root /path/to/Kristal-Grand-Challenges/challenges \
  --kristal /path/to/Kristal-Math \
  --workspace ./workspace
```

Le premier onglet contient **DO ALL** pour le Challenge sélectionné et **Run all 12** pour le portefeuille. Le canon MathKristal reste en lecture seule.

## Coverage first

Un Challenge peut activer une carte stratégique `map/` pour compresser le problème en une boucle de grands carrefours. Pendant cette phase, le but est de **relier les régions**, pas d'optimiser les chemins. Un détour certifié compte comme connexion; la recherche de shortcuts commence après couverture. Voir `docs/12_COVERAGE_CIRCUIT_METHOD.md`.
