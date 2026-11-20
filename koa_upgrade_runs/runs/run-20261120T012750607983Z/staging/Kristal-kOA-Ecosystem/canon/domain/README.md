# Canonical domain payload location

The canonical domain payload intentionally remains at `knowledge-base/corpus/koa-ecosystem.kristal-state.json` during this 3.2.2 normalization. It is registered by `../state.index.json`. Duplicating or moving the 5+ MB state would create two plausible authorities and would break the existing native builder paths.
