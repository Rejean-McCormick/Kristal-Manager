# Kristal Farms

Kristal Farms is a northern energy-and-compute infrastructure project built around a simple inversion:

> **Bring flexible compute to remote renewable energy and export digital value by fibre instead of defaulting to long roads and long high-voltage export corridors.**

The project focuses on northern Québec and Labrador, where hydro resources, marine logistics, community infrastructure and telecommunications can be evaluated as one system.

## What Kristal Farms is

Kristal Farms combines seven infrastructure and governance layers:

1. **Remote renewable generation** — primarily hydro where technically, environmentally and socially justified.
2. **Protected community interface** — community and critical loads have priority over flexible compute.
3. **Serviced compute sites** — power, cooling interface, fibre handoff, physical security, metering and logistics; tenants may bring and control their own hardware and software.
4. **Digital export by fibre** — move computation and data products rather than defaulting to long-distance electrical export.
5. **Responsible international tenancy** — screen jurisdictions, legal counterparties, beneficial ownership/control and sanctions/trade exposure before access; the current owner policy excludes United States-based or United States-controlled counterparties from tenant/anchor-offtaker/tenant-operator roles.
6. **Content-blind tenant environments** — tenants control private compute and cryptographic keys; Kristal Farms operates shared physical services without routine inspection of private models, datasets or application content.
7. **International distributed resilience** — diversify eligible tenants, jurisdictions, telecom paths and site dependencies while treating any diplomatic/security benefit as a hypothesis rather than a defence guarantee.

The current site doctrine emphasizes **new renewable generation consumed locally + practical marine access + high-capacity standard telecom + comparatively low ecological sensitivity**. Existing dams may support construction where appropriate but are not the long-term commercial resource thesis.

Marine access, local roads, heat reuse, storage and short electrical interties remain site-specific components; no individual port, fibre route or hydro project is established merely by this doctrine.

## Application

The repository also contains the architecture, data contracts, and an initial Observatory Explorer web implementation for the Kristal Farms application:

- **Showcase** — guided public narrative;
- **Explorer** — evidence-first professional geospatial workspace; the first MapLibre Observatory vertical slice lives in [`apps/web/`](apps/web/);
- **Scenario Studio** — reproducible infrastructure and economic comparisons.

The application is data-driven. PostgreSQL/PostGIS is the intended operational source of truth; MapLibre/deck.gl, OGC APIs, QGIS workflows and immutable public releases consume derived views and artifacts.

### Monorepo boundaries

Kristal Farms stays in **one canonical repository**, but development is divided into three logical systems:

```text
research/ -> pipelines + data + contracts/packages -> apps/services
KNOWLEDGE        DATA PLATFORM / CONTRACT              PRODUCT
```

`apps/web` may consume governed APIs, stable packages/contracts and immutable `data/publish` artifacts. It must not import or execute code from `research/` or `pipelines/`. See [Workspace boundaries](docs/architecture/workspace-boundaries.md) and [ADR-020](docs/adr/0020-one-monorepo-three-logical-systems.md).

## Evidence discipline

The repository deliberately separates facts, observations, derived values, assumptions and unknowns.

Core rules:

- planning margin is **not** validated compute-hosting capacity;
- community loads are priority loads;
- external projects are references unless explicitly reclassified;
- evidence may be valid without geometry;
- a gauge point is not a dam site;
- terrain drop is not project head;
- a benchmark is not a site cost;
- unknown or unpriced values remain explicit;
- site ranking is disabled until a transparent methodology and governance decision exist.

## Repository layout

```text
kristal-farms/
├── research/               # Active exploratory work; never a product runtime dependency
├── pipelines/              # Reproducible ingest, transformation, validation and publishing
├── database/               # PostGIS migrations, views, functions and seeds
├── contracts/              # Machine-readable API/data/policy contracts
├── packages/               # Schemas, catalog, map style, UI/shared packages
├── data/                   # Raw, processed/current and immutable publish artifacts
├── apps/                   # Product applications, including Observatory
├── services/               # Domain API, OGC API and tile services
├── docs/                   # Project/domain + software/data-platform documentation
├── tools/                  # Specialist local/developer utilities
├── sources/                # Controlled source material and project-direction records
├── tests/                  # Automated model/data/economic/architecture tests
├── infra/                  # Deployment configuration
└── archive/                # Superseded material and historical research snapshots
```

## Start here

### Project and domain

- [Project state](docs/00-control/PROJECT_STATE.md)
- [Strategic principles](docs/00-control/STRATEGIC_PRINCIPLES.md)
- [Project reference architecture — English](docs/10-core/Kristal_Farms_Project_Reference_Architecture_EN.md)
- [Architecture de référence du projet — français](docs/10-core/Architecture_de_reference_du_projet_Kristal_Farms_FR.md)
- [Deployment strategy — English](docs/10-core/deployment/DEPLOYMENT_STRATEGY_EN.md)
- [Stratégie de déploiement — français](docs/10-core/deployment/STRATEGIE_DE_DEPLOIEMENT_FR.md)
- [Corridor dossier strategy](docs/00-control/CORRIDOR_DOSSIER_STRATEGY.md)
- [Responsible international tenant governance](docs/00-control/INTERNATIONAL_TENANT_GOVERNANCE.md)
- [Plan de mobilisation internationale — français](docs/10-core/strategy/PLAN_MOBILISATION_INTERNATIONALE_KRISTAL_FARMS_FR.md)
- [Tenant-controlled encrypted environment — English](docs/10-core/tenancy/BLACK_BOX_TENANCY_MODEL_EN.md)
- [Environnement chiffré sous contrôle du locataire — français](docs/10-core/tenancy/MODELE_LOCATION_BLACK_BOX_FR.md)

### Application and data

- [Documentation index](docs/index.md)
- [Product vision](docs/product/vision.md)
- [Software & data platform architecture](docs/architecture/overview.md)
- [Information architecture](docs/architecture/information-architecture.md)
- [Data model](docs/data/data-model.md)
- [Evidence model](docs/data/evidence-model.md)
- [Explorer](docs/product/explorer.md)
- [Map observatory interaction](docs/frontend/map-observatory-interaction.md)
- [Showcase](docs/product/showcase.md)
- [Scenario Studio](docs/product/scenario-studio.md)

### Research methods

- [Hydro Resource Atlas method](docs/30-site-screening/hydro-atlas/HYDRO_RESOURCE_ATLAS_METHOD.md)
- [Hydro geometry pipeline](docs/30-site-screening/hydro-atlas/GEOMETRY_PIPELINE_METHOD.md)
- [Economic architecture frontier](docs/40-economics/ECONOMIC_ARCHITECTURE_FRONTIER.md)
- [Economic benchmark register](docs/40-economics/ECONOMIC_BENCHMARK_REGISTER.md)
- [Mine reuse screening method](docs/30-site-screening/mine-reuse/MINE_REUSE_SCREENING_METHOD.md)
- [Underground compute / mine infrastructure reuse](docs/30-site-screening/mine-reuse/UNDERGROUND_COMPUTE_REUSE.md)
- [Mine-pit reservoir / pumped-storage research](docs/30-site-screening/mine-reuse/MINE_RESERVOIR_PUMPED_STORAGE.md)
- [Northern mine-reuse research inventory](docs/50-research/mines/NORTHERN_MINE_REUSE_INVENTORY.md)

## Current status

The repository contains a substantial evidence base, current canonical fixtures, reproducible research pipelines, PostGIS schema/migrations, economic sensitivity tooling and public-release artifacts. It does **not** yet establish a selected project site, buildable hydro capacity, environmental authorization, community authorization, fibre route, heavy-lift logistics plan, committed international anchor tenant/offtake agreement or bankable project economics.

Development now proceeds through named **corridor and site dossiers** that replace general proxies with real geometry, hydrology, engineering, logistics, rights/governance work, commercial quotations and project-specific economics.

A new exploratory mine-reuse workstream also tests whether existing mining assets can reduce new-build scope. It treats **recent underground/care-and-maintenance mines** as potential infrastructure-reuse analogues and **open-pit mines of any age** as possible pumped-storage reservoir research objects where geometry, environment and system value justify study. No mine is selected by this policy.

## Wiki

The GitHub Wiki is maintained as a separate repository: `Kristal_Farms.wiki`. It is an explanatory surface, not the technical source of truth.

## Long-horizon concepts

Optional human-infrastructure, learning and education concepts are isolated under [`docs/70-long-horizon/`](docs/70-long-horizon/README.md). They are not prerequisites for the first energy/compute project and must not be presented as committed institutions or programs.

## Local Observatory workflow

After repository files change, double-click `REBUILD_OBSERVATORY.pyw`. It is the controlled Windows rebuild path: it safely stops the current Kristal dev server, cleans generated caches, creates or repairs `.venv` from `requirements-dev.txt`, republishes governed artifacts, runs `pytest`, runs the web TypeScript typecheck and production build, then starts the Observatory only when all checks pass.

Use `START_OBSERVATORY.bat` only for a quick start when repository files have not changed. Specialist diagnostics, Sentinel/watershed acquisition and PMTiles helpers live under `tools/`; see [`tools/README.md`](tools/README.md).

