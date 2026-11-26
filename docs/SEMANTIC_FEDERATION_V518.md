# V5.18 — Active semantic federation, local-first

## What this operation does

In one PowerShell 7 run, the coordination script retries the V5.17 accepted-evidence
precedence operation (idempotent), rebuilds the V5.16 active local read views,
and creates one private V5.18 SQLite federation plus two private JSON reports.

The database resolves each semantic identity by `(namespace_id, semantic_id)`;
`KQ1001` alone is not globally unique. Human labels, lifecycle status,
source-recorded accepted Wikidata QIDs and unresolved candidate QIDs are
separate queryable fields, never substitutions for canonical identity.

V5.18 reads only the active Authoring Kit profile, verifies its state-index,
profile, role and layer digests, and refuses stale/mutated sources. Historical
curated lexical records may provide a single-term consensus as
`UNREVIEWED_NOT_CANONICAL` hints. They do not create labels, approve matches,
or alter active canonical dictionaries. Ambiguous candidates stay in the
`review_queue` table with their original QIDs.

The private public-synchronization plan reports observed local/public drift
including new V5.17 crosswalk revisions. It is not a push manifest, publication
permission, independent C1/C2 qualification, nor a claim that all 127 local
Kristals have active V11 profiles. Any source without a complete V11 canonical
core remains unselected.

## Run

Execute the ZIP's `INSTALLER_PS7.ps1 -Apply`. It checks exact Git roots and
new-file SHA-256 preconditions, installs the tools/docs, runs focused tests,
then invokes `scripts/apply_semantic_federation_v518.ps1 -Apply`.

The user-facing command runs automatically once. Re-running after a failed
batch is supported; inspect a pending V11 transaction using Authoring Kit
`recover-v11` before resuming, never delete a journal manually.

Outputs (unique filenames, private user directory):

- `%LOCALAPPDATA%\Kristal\SEMANTIC_V518_*.sqlite`
- `%LOCALAPPDATA%\Kristal\SEMANTIC_V518_*.json`
- `%LOCALAPPDATA%\Kristal\SEMANTIC_V518_*.public-plan.json`

Example exact lookup, including historical suggestions with explicit status:

```powershell
$env:PYTHONPATH = 'C:\mycode\Kristal\Kristal-Manager'
python -m kristal_manager.active_semantic_federation_v518 `
  --lookup-db 'C:\Users\<user>\AppData\Local\Kristal\SEMANTIC_V518_<run>.sqlite' `
  --lookup 'KQ1001' --namespace-id 'kristal:bulk:kristal-ai'
```

V5.18 itself performs no canonical or public writes. The separately invoked
Kit V5.17 operation may add new versioned canonical crosswalks only where
previously accepted, KS-evidenced source mappings justify superseding
competing candidates; it does not invent new approvals.
