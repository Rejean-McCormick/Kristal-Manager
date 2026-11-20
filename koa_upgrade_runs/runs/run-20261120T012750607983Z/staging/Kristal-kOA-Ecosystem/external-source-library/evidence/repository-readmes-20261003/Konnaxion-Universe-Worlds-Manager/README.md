# Konnaxion Universe & Worlds Manager V1

Standalone Windows/Tk manager for canonical Konnaxion Universe/World seed packs.

## Expected repo

The manager auto-detects a repo containing:

- `backend/docker-compose.local.yml`
- `backend/konnaxion/worlds/`
- `seed-data/worlds/`
- `seed-data/universes/`

For the current development tree this is normally:

`C:\mycode\Konnaxion\Konnaxion`

## Run

Double-click `Konnaxion_Universe_Worlds_Manager.pyw`, or:

```powershell
python .\Konnaxion_Universe_Worlds_Manager.pyw
```

The manager uses Docker Compose and calls the canonical Django Worlds services/management command inside the running `django` service.

## Important

`seed-policy.yaml` is intentionally not used to authorize Universe Packs. It remains module/importer-specific. Universe/World discovery and validation are governed by their own contracts and seed roots.
