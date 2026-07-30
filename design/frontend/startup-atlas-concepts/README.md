# Serious Atlas concepts

This gallery compares five restrained product directions against the same
accepted Concord Loom graph. The pages fetch the repository catalog, discover
available self-binding revisions, and render the selected revision in the
browser.

Run a local server from the repository root:

```bash
python3 -m http.server 4189
```

Open:

```text
http://127.0.0.1:4189/design/frontend/startup-atlas-concepts/
```

Compare graph readability, information density, drill-down, and the mobile
layout. Each concept supports direct links, revision switching, breadcrumbs,
`Escape` to go back, and keys `1`-`5` to switch directions.

The five directions are:

1. Systems Index
2. Dependency Flow
3. Research Map
4. Control Plane
5. Architecture Field

## Source of truth

- `framework/concordloom/catalog.json` chooses the active accepted binding.
- Each binding points to its accepted cycle registry.
- `site/data/atlas.json` supplies Russian display copy when available.
- `shared/data.js` normalizes those sources.
- `shared/engine.js` owns navigation and deterministic layout.

The concept pages contain no sample graph, saved node coordinates, remote
runtime assets, or production-site changes. A chosen direction must still pass
the production design-system and frontend delivery cycles before release.
