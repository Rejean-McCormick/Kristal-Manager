# Editorial Figure Engine 1.2.1

A deterministic, code-first SVG figure engine for books, reports, academic work, documentation, and institutional diagrams.

The engine is deliberately **not** a general-purpose graph-layout system. Figures are described semantically in YAML or JSON. A template is selected explicitly or recommended automatically, and the engine places nodes on an editorial grid with deterministic geometry.

## Features

- deterministic SVG generation;
- optional PNG and PDF export;
- 20 baseline examples covering the built-in template families;
- semantic nodes, groups, roles, relations, and routing hints;
- orthogonal, obstacle-aware relation routing;
- quality analysis for overlaps, crossings, label collisions, bends, balance, and whitespace;
- automatic spacing refinement;
- CLI and lightweight folder-based Windows GUI;
- JSON Schema plus machine-readable and human-readable catalogs.

## Repository layout

- `figure_engine/` — Python package and rendering engine.
- `figure_engine.pyw` — folder-based Windows GUI.
- `examples/` — generic runnable examples.
- `gallery/` — rendered versions of the generic examples.
- `tests/` — automated tests.
- `catalog.json` / `CATALOG.md` — template and primitive catalog.
- `figure.schema.json` — JSON Schema for figure specifications.
- `AI_GUIDE.md` — guidance for semantic/template recommendation.
- `ARROW_RULES.md` — deterministic routing rules and quality gates.

## Installation

Requires Python 3.11+.

```bash
python -m pip install -r requirements.txt
```

For an editable install:

```bash
python -m pip install -e .
```

On Windows, `install_windows.bat` installs dependencies using the same Python launcher as the bundled helpers. Run `doctor.bat` to inspect the selected interpreter and dependency state.

## Quick start

Create one `.yaml`, `.yml`, or `.json` file per figure:

```yaml
figure:
  id: example
  title: Cross-system mapping
  template: mapping_matrix
  theme: book_mono

  nodes:
    - id: source
      label: Source term
      group: A

    - id: mapping
      label: Mapping
      group: mapping
      shape: rounded_box
      role: mechanism

    - id: target
      label: Target term
      group: B

  relations:
    - from: source
      to: mapping
      type: mapping
    - from: mapping
      to: target
      type: mapping
```

Set `template: auto` to let the built-in recommender choose from the semantic structure.

## CLI

Validate specifications:

```bash
python -m figure_engine validate examples
```

Analyze template selection and quality:

```bash
python -m figure_engine analyze examples
```

Generate SVG and PNG:

```bash
python -m figure_engine generate examples --formats svg,png -o rendered
```

Use `--recursive` to include subfolders. SVG is the master production format. PNG/PDF exports use the built-in Pillow raster backend and do not require Cairo/GTK.

## Built-in templates

Baseline templates include `linear_flow`, `vertical_flow`, `feedback_loop`, `conversion_loss`, `comparison_ab`, `parallel_paths`, `hub_spoke`, `layered_architecture`, `ladder`, `mapping_matrix`, `paired_rows`, `boundary_exchange`, `recursive_scale`, `panel_ab`, `panel_abc`, `dimension_dashboard`, `routing`, `anatomy`, `timeline`, and `decision_tree`.

Additional editorial layouts are listed in `CATALOG.md`.

## Shapes, relations, and routing

Common shapes include `box`, `rounded_box`, `pill`, `circle`, `ellipse`, `diamond`, `hexagon`, `database`, `document`, `folder`, `note`, `banner`, `boundary`, `junction`, `relay`, and `ghost`.

Relations include `flow`, `information`, `authority`, `advice`, `feedback`, `bidirectional`, `association`, `dependency`, `loss`, `mapping`, `boundary_crossing`, `inhibition`, `callout`, `branch`, and `merge`.

The default router is orthogonal, obstacle-aware, lane-aware, and crossing-averse. See `ARROW_RULES.md` for routing semantics and manual waypoint guidance.

## Quality model

Candidate layouts are evaluated for node overlap, edge crossings, edge/node intrusions, label collisions, bend count, alignment, balance, aspect ratio, minimum font size, and whitespace density. With auto-refinement enabled, several spacing variants are evaluated and the highest-scoring candidate is kept.

## Design principles

The engine optimizes, in order, for comprehension, hierarchy, alignment, legibility, graphical economy, and aesthetics. Geometry remains deterministic: semantic recommendation may affect template choice and grouping, but not arbitrary pixel placement.

## Version 1.2.1

Version 1.2.1 includes deterministic editorial routing with semantic relation priority, side-consistent anchors, lane offsets, planar fan-in ordering, obstacle penalties, perimeter feedback, relay labels, repeated-label deduplication, strict arrow metrics, and optional production quality gates.

## License

No license file is included in this package. Choose and add a license before publishing the repository if you intend to grant reuse or redistribution rights.
