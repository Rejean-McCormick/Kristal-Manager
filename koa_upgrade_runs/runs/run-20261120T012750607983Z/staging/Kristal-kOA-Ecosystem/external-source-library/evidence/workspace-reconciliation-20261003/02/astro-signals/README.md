# Astro Signals V2.3

Application complète de carte natale quantitative.


## Nouveautés V2.3

- ajoute un **mode sans heure** explicite dans le formulaire;
- aucune heure fictive n'est créée : `local_time = null`, `time_accuracy = UNKNOWN`;
- balayage du jour civil local par pas de 15 minutes;
- les 12 indicateurs affichent une médiane et une enveloppe min–max;
- P10/P90 sont conservés pour l'analyse de sensibilité;
- maisons, angles, secte et proéminence angulaire ne sont pas affichés comme des faits lorsque l'heure est inconnue;
- la roue montre uniquement une position zodiacale de référence et le déplacement possible des planètes;
- l'export IA passe à `astro-signals-ai-export/v2` et expose toute l'incertitude temporelle.

## Ce qui change en V2

V1 utilisait des ancres min/max puis une interpolation linéaire. V2 abandonne cette idée.

Le pipeline est maintenant :

```text
naissance
→ positions astronomiques
→ champs géométriques continus
→ conditions astrologiques catégorielles
→ jugements planétaires
→ témoignages thématiques atomiques
→ accumulation d'évidence
→ saturation asymptotique 0–100
```

Le score public utilise :

```text
S = 100 × (1 − exp(−E / τ))
```

Il n'existe donc pas de « carte maximale » choisie arbitrairement. `100` est une asymptote.

## École incluse

`western_traditional_field@2.0.0`

- zodiaque tropical;
- maisons Whole Sign;
- sept planètes classiques;
- maîtrises traditionnelles;
- cinq familles d'aspects;
- aspects évalués par noyau circulaire continu;
- significations historiques sourcées;
- formalisation numérique explicitement moderne.

## Mega knowledge graph

Le fichier :

```text
schools/western_traditional_field_v2/compiled_knowledge.json
```

contient les combinaisons précompilées :

- 84 combinaisons planète × signe;
- 84 combinaisons planète × maison;
- 105 combinaisons paire de planètes × famille d'aspect;
- les 12 mappings de domaines.

Il est généré par `scripts/compile_knowledge.py` et ne doit pas être édité manuellement.

## Stack

### Backend

- Python 3.13+
- FastAPI
- Pydantic
- Swiss Ephemeris
- PostgreSQL optionnel

### Frontend

- Next.js 16
- React 19
- TypeScript
- TanStack Query
- CSS natif

V2.1 retire aussi Motion : les barres utilisent maintenant des transitions CSS natives. D3, Zustand et Tailwind restent absents du runtime.

## Windows — démarrage

Première fois :

```text
FIRST_RUN_INSTALL_AND_LAUNCH.bat
```

Ensuite :

```text
LAUNCH_ASTRO_APP.bat
```

Arrêt :

```text
STOP_ASTRO_APP.bat
```

## Manuel — PowerShell 7

API :

```powershell
cd C:\mycode\Astro-App\astro_app
$env:PYTHONPATH = "$PWD\packages\astrology-engine\src;$PWD\services\astrology-api"
python -m uvicorn app.main:app --app-dir services\astrology-api --reload --host 127.0.0.1 --port 8000
```

Web :

```powershell
cd C:\mycode\Astro-App\astro_app\apps\web
npm install
npm run dev
```

Puis ouvrir `http://localhost:3000`.

## Tests

```powershell
pip install -r requirements-dev.txt
pytest
```

V2 possède des tests du noyau continu, du graphe de connaissances, du moteur et de l'API.

## Exemples inclus

`examples/baie_comeau_1981_v2.json` contient un calcul complet avec heure connue pour :

- 7 juin 1981
- 14:00
- Baie-Comeau, Québec

`examples/ulm_1879_time_unknown_v23.json` contient un calcul en mode sans heure pour :

- 14 mars 1879
- heure inconnue
- Ulm, Allemagne

## Documentation

Commencer par [`docs/00_INDEX.md`](docs/00_INDEX.md).
