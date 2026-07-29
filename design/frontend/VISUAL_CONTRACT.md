# Signal Constellation visual contract

Status: accepted concept, implementation target  
Reference: `reference/signal-constellation-concept.png`  
SHA-256: `4226c0ac5a181d5f26f9e2270b8973c153e80949fc5de5537f223502df22a619`

This contract is the visual source of truth for the Concord Loom website and
Atlas. Product data and documentation remain the factual sources of truth. A
candidate may simplify the composition for a smaller screen, but it may not
replace this visual world with a generic dashboard.

## Visual world

The interface is a dark precision instrument built from blackened metal,
concentric mechanisms, fine engraved lines, restrained off-white type, and one
acid signal color. Texture creates depth; live HTML and SVG carry meaning.

Required:

- near-black material field with subtle stone and machined-metal variation;
- thin structural lines, screws, rings, rails, ticks, and inset panels;
- acid yellow-green only for the active path, current focus, and primary action;
- compact uppercase mono labels for instruments and navigation;
- calm off-white sans-serif type for reading and large editorial display type;
- square controls, deliberate borders, and no soft dashboard cards;
- local assets and fonts only; the site must work without third-party runtime
  requests.

Forbidden:

- flat black panels that discard the material depth of the reference;
- decorative background lines pretending to be live graph data;
- glassmorphism, gradients used as generic decoration, rounded SaaS cards,
  emoji, stock illustrations, or unrelated neon colors;
- giant text used as scenery when it overlaps or obscures content;
- a permanently highlighted lifecycle step that is not backed by page state.

## Desktop Atlas composition

At widths of 1440 CSS pixels and above, the Atlas is one viewport instrument:

- the Atlas consumes the full viewport below compact site chrome; it is not a
  document section or a dashboard inside a page;
- the graph itself is the primary material surface: rings, rails, nodes, and
  signal light create depth without a photographic or raster stage background;
- two constellations are visible at once: contextual structure on the left and
  the active loop on the right;
- at least 18 physical node assemblies are visible at the root;
- a luminous signal bridge visibly connects the two constellations;
- nodes use engraved glyphs inside metal housings; long human labels belong in
  the inspector and never orbit the graph;
- the inspector contains a large mechanical dial for the selected loop and
  reads as part of the same instrument, not a generic text sidebar;
- total top chrome occupies at most 14% of viewport height;
- graph field occupies at least 72% of viewport width;
- inspector occupies 18–22% of viewport width;
- navigation context is integrated into the breadcrumb and graph; a permanent
  desktop path column is forbidden;
- the parent constellation is fully visible in the left 0–36% of the graph;
- the current constellation is centered in the 48–64% region;
- the inspector begins in the 78–83% region of the viewport;
- the parent diameter is at least 32% of graph height;
- the current mechanism diameter is at least 42% of graph height;
- parent structural contrast is at least 70% of current structural contrast;
- header, graph, and inspector fit inside one viewport; the inspector scrolls
  internally when necessary and never increases the shared grid row.

The live SVG is the semantic and visual signal layer. Selecting a node changes
the acid route, current mechanism, breadcrumbs, URL, and inspector. Atlas stage
CSS may use restrained tokenized light falloff, but it may not render a
photographic or raster background image. Material artwork may appear elsewhere
on the site only when it does not compete with live information.

A single radial chart, even when placed over the accepted texture and colored
with the accepted acid signal, is a contract failure. Palette and background
similarity do not count as composition fidelity.

A live graph placed over decorative machinery is also a contract failure. The
machinery must be expressed by the graph's own assemblies, rails, rings, and
motion so that every visually prominent object carries current system meaning.

## Responsive transformation

At 880 CSS pixels and below, the layout becomes:

1. compact header and command bar;
2. horizontally scrollable, snap-aligned path;
3. graph;
4. inspector.

The graph receives at least 55% of the first viewport after chrome. The first
screen must expose the current mechanism rather than only navigation. At
360–390 pixels, controls remain at least 44×44 pixels, Russian labels wrap
without clipping, and the document has no horizontal overflow.

At 200% zoom, the half-width CSS layout follows the same responsive contract.
No fixed or sticky element may cover focused content.

## Typography and copy

- Display headings: fluid, never below line-height `0.9`, and never used below
  the width at which the full phrase fits.
- Reading text: 16–19 pixels, line-height 1.55–1.72, measure 58–74 characters.
- Instrument labels: 11–14 pixels, uppercase or concise title case.
- Atlas labels: at least 14 pixels on desktop and 12 pixels on mobile.
- Inspector titles: 20–36 pixels, line-height at least 1, no more than three
  lines, with safe breaking for Russian and English.

Every visible phrase must explain the product in ordinary language. Protocol
identifiers may remain English only when rendered as code.

## Motion

Motion explains containment:

- selecting a child moves the parent constellation left and brings the child
  mechanism into focus;
- the active signal travels along the connecting rail;
- the inspector changes after the spatial transition has established context;
- browser back reverses the transition and restores the previous focus;
- durations stay between 180 and 650 milliseconds with no perpetual motion.

With `prefers-reduced-motion: reduce`, the final state appears immediately:
no animation, transform, parallax, or delayed opacity.

## Required states

The production workshop and tests cover:

- default, hover, focus, active, and selected;
- Atlas root, parent, child, leaf, and browser back/forward;
- English and Russian;
- loading, empty, error, and stale data;
- mobile navigation open and closed;
- inspector sections closed and open;
- reduced motion;
- long Russian labels and 30% text expansion;
- JavaScript-disabled reading for Concept, Theory, Quickstart, and Docs.

## Browser acceptance

The release gate must run pinned Playwright and axe checks.

Viewports:

- 360×800
- 390×844
- 768×1024
- 1024×768
- 1440×900
- 1920×1080
- 2048×1152

For every applicable viewport, locale, route, and motion mode:

- document width is no greater than the visual viewport plus one pixel;
- visible text stays inside its owner;
- unrelated visible text boxes do not intersect;
- header and active content do not intersect;
- graph labels do not collide;
- graph and inspector do not overlap;
- direct URLs, reload, language change, browser back, and browser forward
  preserve semantic location;
- no runtime request leaves the site origin;
- axe reports no serious or critical findings;
- focus remains visible and every essential target is at least 44×44 pixels.

Automated checks are necessary but not sufficient. A fresh independent visual
critic must compare the exact candidate screenshots with the exact reference.
The critic may return `PASS`, `REVISE`, or `INDETERMINATE`; only `PASS` permits
publication.

## Baseline policy

Golden screenshots live under `design/frontend/baselines/` and belong to the
accepted visual contract, not to the test harness. CI never updates them.
Changing a baseline requires a new exact visual-contract decision.

Allowed screenshot masks are limited to provenance digest text and a 16-pixel
halo around the live signal LED. Header, hero, graph, node labels, path,
inspector, and responsive boundaries may not be masked.

For a stable candidate:

- pixel comparison uses the pinned Playwright container and one worker;
- reference-fidelity review uses the composition ratios above, not just color;
- a large contiguous changed region fails even when the mostly black page makes
  the global difference percentage look small.

## Ownership

- Concept author owns this contract and approved baselines.
- Workshop author owns isolated state fixtures.
- Frontend implementer owns production HTML, CSS, JavaScript, and assets.
- Harness author owns tests and CI, but cannot change production code or
  baselines.
- Deterministic verifier and visual critic are read-only.
- Publisher may deploy only a candidate carrying both verifier and critic
  receipts.
