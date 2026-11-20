# Médiathèque kOA

**Médiathèque kOA** is a local media and document cataloging application.

It provides a simple Excel-like inventory backed by SQLite, with local file storage, ChatGPT metadata intake, XLSX round-trip editing, and a compact Streamlit GUI.

```text
Médiathèque kOA = local library table + local file storage + ChatGPT intake + XLSX round-trip + compact GUI
````

SQLite is the source of truth. XLSX is only a bulk-edit interface. ChatGPT provides structured metadata suggestions, but the app recalculates technical facts locally.

---

## Project identity

```text
APP_PUBLIC_NAME = Médiathèque kOA
APP_SHORT_NAME = kOA
APP_TECHNICAL_NAME = koa-mediatheque
APP_COMPONENT = koa_mediatheque
APP_DB_FILENAME = koa_mediatheque.sqlite
APP_PRIMARY_LANGUAGE = fr
APP_STORAGE_MODEL = local_filesystem
APP_DB_MODEL = sqlite_single_sheet_with_support_logs
```

---

## Scope

Médiathèque kOA is a local cataloging tool for:

```text
documents
PDFs
images
audio
video
transcripts
spreadsheets
presentations
source packages
external references
Kristal corpora
Kristal publications
AI-generated documents
non-public records
UCKK-related records
non-UCKK records
future export candidates
```

The app is not a full UCKK system and does not require Moodle.

UCKK is represented only as a possible classification/export target through fields such as:

```text
uckk_relevance
target_system
target_export_allowed
export_to_uckk
```

Non-UCKK, non-public, private, third-party, uncertain, and non-exportable records are valid first-class records.

---

## Canonical folder structure

```text
KOA_MEDIATHEQUE/
├── 01_DB/
│   ├── koa_mediatheque.sqlite
│   └── schema_versions/
├── 02_STORAGE/
│   ├── media_original/
│   ├── media_preview/
│   ├── media_thumbnail/
│   ├── media_derivative/
│   ├── media_caption/
│   ├── media_transcript/
│   ├── media_attachment/
│   ├── content_review_files/
│   ├── external_work_reference_files/
│   ├── cultural_protocol_files/
│   ├── kristal_source_files/
│   ├── kristal_corpora/
│   └── kristal_publications/
├── 03_IMPORTS/
│   ├── google_drive_raw/
│   ├── google_drive_scanned/
│   ├── ai_generated_docs/
│   └── pending_review/
├── 04_EXPORTS/
│   ├── xlsx/
│   ├── manifests/
│   ├── uckkarchive/
│   └── public_review/
├── 05_TOOLS/
├── 06_GUI/
│   └── koa_mediatheque_gui/
├── 07_BACKUPS/
├── 08_LOGS/
└── docs/
```

Canonical paths:

```text
KOA_ROOT = KOA_MEDIATHEQUE
KOA_DB_DIR = 01_DB
KOA_DB_PATH = 01_DB/koa_mediatheque.sqlite
KOA_STORAGE_DIR = 02_STORAGE
KOA_IMPORTS_DIR = 03_IMPORTS
KOA_EXPORTS_DIR = 04_EXPORTS
KOA_TOOLS_DIR = 05_TOOLS
KOA_GUI_DIR = 06_GUI
KOA_DOCS_DIR = docs
```

---

## Database model

The first implementation uses one canonical table:

```text
library_rows
```

Support tables:

```text
chatgpt_intake_log
xlsx_import_log
file_scan_log
audit_log
schema_meta
kristal_registry
kristal_sources
kristal_source_links
kristal_source_snapshots
kristal_source_representations
kristal_artifacts
kristal_versions
kristal_publications
kristal_bridge_log
```

A row in `library_rows` represents one physical file version or one external-reference version.

Identifier rules:

```text
id = local SQLite autoincrement row id
media_uuid = stable intellectual-object identity
version_uuid = stable file/version identity
sha256 = local file content hash
import_batch = batch identity for scan/import sessions
```

Rules:

```text
version_uuid is unique.
Multiple rows may share the same media_uuid.
The app generates UUIDs locally if needed.
The app never trusts ChatGPT for sha256, filesize, mimetype, filename, extension, or filesystem paths.
```

---

## Technical facts

The app recalculates these locally:

```text
sha256
filesize
mimetype
filename
extension
original_path
storage_path
created_at
updated_at
```

ChatGPT and XLSX must not overwrite protected technical facts during normal operation.

---

## ChatGPT intake

The GUI must support this workflow:

```text
Select current file
Copier template ChatGPT
Coller réponse ChatGPT
Valider JSON
Prévisualiser entrée
Valider et intégrer
```

ChatGPT output is treated as a suggestion. The app validates the JSON, normalizes values, applies blocking rules, recalculates file facts, then writes controlled records to SQLite.

Default validation rule:

```text
canonical_validation_state = unverified
```

AI may set local AI validation fields, but AI must not set:

```text
canonical_validation_state = verified
```

unless there is an explicit human override.

---

## XLSX round-trip

The XLSX workflow is:

```text
SQLite -> XLSX -> human edits -> import preview -> validated update -> SQLite
```

Rules:

```text
SQLite remains the source of truth.
XLSX is a bulk-edit interface.
version_uuid is the import key.
Deleting an XLSX row must not delete a SQLite row.
Protected technical fields cannot be overwritten from XLSX unless explicit repair mode is used.
Every import must create a backup and an import log.
```

XLSX sheets:

```text
Library
Lists
Import_Report
```

Allowed XLSX actions:

```text
update
ignore
archive
new
```

---


## Kristal media bridge

Local media can be linked explicitly to Kristal while remaining owned and stored by Médiathèque kOA. Links use `relations_json` entries such as `kristal:state:<id>`. The bridge exports IK 1.1 `ArtifactRef` and `ExportManifest` documents with SHA-256 integrity and opaque `koa-media://` locators; local filesystem paths are not exposed.

```text
04_EXPORTS/kristal/kristal-artifact-refs.json
04_EXPORTS/kristal/kristal-export-manifest.json
```

See `docs/18_kristal_media_alignment.md`.

---

## Export manifests

Canonical manifest filename:

```text
manifest.json
```

Supported export types:

```text
xlsx_inventory
koa_manifest
uckkarchive_candidate
public_review_package
backup_snapshot
```

A manifest must include:

```text
app name
app component
export uuid
export timestamp
export actor
export reason
row count
media uuids
version uuids
file hashes
file sizes
mime types
visibility
public state
restricted flags
audience suitability
provenance
collections
tags
relations
validation state
export policy
```

---

## Runtime requirements

Required runtime:

```text
Python >= 3.11
PowerShell 7+
SQLite
Streamlit
```

Python dependencies are listed in:

```text
requirements.txt
06_GUI/koa_mediatheque_gui/requirements.txt
```

---

## Installation

From the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

On macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## Launch the GUI

Windows PowerShell 7:

```powershell
.\Start-KoaGui.ps1
```

Windows double-click wrapper:

```text
Start-KoaGui.bat
```

Manual Streamlit launch:

```powershell
streamlit run 06_GUI/koa_mediatheque_gui/app.py
```

---

## Default local paths

The app expects these defaults unless overridden by config or environment variables:

```text
KOA_DB_PATH=01_DB/koa_mediatheque.sqlite
KOA_STORAGE_ROOT=02_STORAGE
KOA_IMPORTS_ROOT=03_IMPORTS
KOA_EXPORTS_ROOT=04_EXPORTS
KOA_BACKUPS_ROOT=07_BACKUPS
KOA_LOGS_ROOT=08_LOGS
KOA_GUI_ROOT=06_GUI/koa_mediatheque_gui
```

---

## Configuration

Example environment file:

```text
.env.example
```

GUI configuration example:

```text
06_GUI/koa_mediatheque_gui/config.example.toml
```

Streamlit configuration:

```text
06_GUI/koa_mediatheque_gui/.streamlit/config.toml
```

Local `.env` files may be created from `.env.example`, but they should not be committed.

---

## Safety and validation rules

The app must block or require human review when:

```text
canonical_validation_state is verified without explicit human override
public export is requested for non-public/private/restricted/confidential/unknown records
UCKK export is requested for not_uckk records
rights_status is unknown
source_type or source_ownership is unknown
restricted or culturally sensitive content requires review
protected technical fields are modified from XLSX in normal mode
```

Unknown rights do not mean public access is allowed.

Source information does not grant rights.

Visibility, public state, access level, restrictions, and export policy must remain distinct.

---

## Development rule

All implementation must stay aligned with:

```text
docs/01_alignment_variables.md
```

If any file conflicts with `docs/01_alignment_variables.md`, the other file is wrong and must be corrected.

Implementation rules:

```text
Use exact canonical names.
Do not invent alternate paths, table names, field names, or enum names.
Keep SQLite as the source of truth.
Keep the app small from the user perspective.
Preserve compatibility with future UCKK/media-library export.
Treat non-UCKK and non-public records as valid cases.
```

---

## Generated runtime files

These files are created locally and should not be committed:

```text
01_DB/koa_mediatheque.sqlite
04_EXPORTS/xlsx/*.xlsx
04_EXPORTS/manifests/manifest.json
04_EXPORTS/uckkarchive/*
04_EXPORTS/public_review/*
07_BACKUPS/*.sqlite
08_LOGS/*.log
02_STORAGE/**/*
```

---

## Current implementation group

This group covers only root configuration and GUI bootstrap files:

```text
README.md
requirements.txt
pyproject.toml
.gitignore
.env.example
Start-KoaGui.ps1
Start-KoaGui.bat
06_GUI/koa_mediatheque_gui/requirements.txt
06_GUI/koa_mediatheque_gui/config.example.toml
06_GUI/koa_mediatheque_gui/.streamlit/config.toml
```

It does not implement database schema, services, repositories, Streamlit pages, business PowerShell tools, or tests.




## Sources locales Kristal

La Médiathèque inclut maintenant un catalogue normalisé des sources locales liées aux Kristals (Source → Snapshot → Représentation), avec déduplication SHA-256 globale et stockage standard `02_STORAGE/kristal_source_files`. Voir `docs/19_kristal_local_source_library.md` et `05_TOOLS/KoaKristalSources.py`.
---

## Kristal corpus catalog and UCKK bridge

A Kristal is now a first-class versioned knowledge artifact, distinct from its downloaded sources. The source catalog remains `Kristal → Source → Snapshot → Representation`; the corpus catalog adds `Kristal → Version → optional package`.

Physical corpus packages are stored as `media_type = kristal` under `02_STORAGE/kristal_corpora/`. A publication toward UCKK is a separate `kristal_publication` record tied to one immutable Kristal version. Publication bundles carry source identity, corpus SHA-256, transformation version, language/jurisdiction/audience, rights, source references, payload hash and provenance.

UCKK returns a receipt containing the UCKK object identity. Applying that receipt updates only the publication link; it never changes the canonical Kristal corpus.

CLI:

```text
python 05_TOOLS/KoaKristalCatalog.py register-all --db <db> --root <kristals-root>
python 05_TOOLS/KoaKristalCatalog.py package --db <db> --storage-root <02_STORAGE> --kristal-version-uuid <uuid>
python 05_TOOLS/KoaKristalCatalog.py publish-draft --db <db> --kristal-version-uuid <uuid> --language fr
python 05_TOOLS/KoaKristalCatalog.py export-publication --db <db> --publication-uuid <uuid> --output-dir <dir>
python 05_TOOLS/KoaKristalCatalog.py apply-uckk-receipt --db <db> --receipt <receipt.json>
```

See `docs/21_kristal_corpus_uckk_bridge.md`.

