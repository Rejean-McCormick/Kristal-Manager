# Content catalogue — local read-only scanner

**Available in the 2026-11-23 `0.1.0-alpha.15` source snapshot.** The catalogue is a local descriptive SQLite index and HTML overview, **not** a public semantic release, dump validator or hosted API.

```powershell
python -m kristal_manager catalog "C:\mycode\Kristal\locals" --db "C:\Catalogues\content.sqlite3" --overview "C:\Catalogues\content.html"
python -m kristal_manager catalog-query Terre --db "C:\Catalogues\content.sqlite3"
```

The GUI provides **Scan content → SQLite + overview** and **Open content overview**. The scanner reads a recognized registered v11 graph/dictionary set or supported native v6 assertion payload, and reports source, lexical, Wikidata and assertion metrics when supported. Unknown or missing source data remain **partial/unsupported**, not zero. It detects changed content for incremental updates; **it does not execute code from scanned Kristals or modify their sources**. Treat the SQLite database and HTML overview as local derived data, and protect them accordingly.

**Code/tests:** `kristal_manager/content_catalog.py`, `kristal_manager/cli.py`, `tests/test_content_catalog.py`. Use the root README for install/requirements. No network upload, source mutation, independent semantic approval or publication is authorized by these commands.
