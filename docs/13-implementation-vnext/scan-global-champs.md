# Scan global des champs — livraison du 1er novembre 2026

Ce module est destiné à **tous les Kristals dans `locals`**, après installation des dépôts corrigés.

## Dans Manager

Ouvrir **Centre unifié** puis **Scan global + champs** et sélectionner le dossier des rapports **hors** de `locals`. Il effectue inventaire, analyse/catalogue et extraction des déclarations. Il ne lance pas un nouveau lot KristalDiag automatiquement.

## En PowerShell 7

```powershell
cd C:\mycode\Kristal\Kristal-Manager
py -3 -m kristal_manager.unified.cli scan-global --root C:\mycode\Kristal\locals --out C:\mycode\Kristal\RAPPORTS-SCAN-GLOBAL --avec-diag
```

`--avec-diag` relance explicitement KristalDiag V9 sur les Kristals compatibles. Sans cette option : le scan emploie les résultats diagnostiques **déjà indexés**. `--sans-catalogue` ne doit être utilisé que si le catalogue existant est fiable et présent.

Le script crée un sous-dossier horodaté et un ZIP autonome avec :

| Fichier | Description |
|---|---|
| `CHAMPS-127-COMPLETS.json` | Les valeurs déclarées (et leurs limites), une fiche par Kristal |
| `CHAMPS-127-STATUTS.csv` | Une ligne par champ avec valeur et statut |
| `CHAMPS-127-MANQUANTS.csv` | Champs réellement manquants, proposés/non déclarés, références cassées |
| `TABLEAU-MANAGER-VNEXT.json` | Dernier état des diagnostics, analyses, Arketype et décisions locales |
| `BILAN-SCAN-GLOBAL.json` | Phases terminées/échouées, comptages, provenance et limites |
| `diagnostics/.../BILAN-DIAGNOSTICS.*` | Si `--avec-diag` est demandé ; preuves complètes restent au chemin moteur |

### Statuts et rigueur

- `PRESENT` : valeur explicitement déclarée, **pas certifiée**.
- `DECLARED_UNVERIFIED` : ARK, PRF, UNESCO, mapping déclarés mais non homologués.
- `MISSING_REQUIRED` : champ nécessaire à la fiche de travail.
- `MISSING_RECOMMENDED` : amélioration documentaire utile.
- `NOT_DECLARED_REVIEW` : une classification ou un mapping n'a pas de déclaration dans le workspace; ne pas inventer.
- `OPTIONAL_ABSENT` : acceptable selon le profil et le domaine.
- `BROKEN_REFERENCE` / `INVALID_REFERENCE` : fichier pointé manquant/chemin interdit.
- `FORMAT_REVIEW` : déclaration à rapprocher du contrat attendu.

Les `status=building` existants sont rapportés tels quels. Le scan n'approuve aucune classification et ne modifie pas les 127 sources. Une phase en échec est enregistrée `FAILED`, sans produire de fausse réussite.

Les chemins et intitulés peuvent être sensibles : vérifier le ZIP avant partage externe.
