# Concord Loom design system

Language: **English** | [Русский](ru/DESIGN_SYSTEM.md)

Status: **normative**

Version: **4.0.0**

Product truth: [`PRODUCT.md`](PRODUCT.md)

Approved direction:
[`Patch Panel`](../design/frontend/startup-atlas-concepts/playful/04-patch-panel/)

Accepted machine contract:
[`design/frontend/visual-contract.json`](../design/frontend/visual-contract.json)

Machine values: [`site/design-tokens.json`](../site/design-tokens.json)

Component rules: [`site/design-system.css`](../site/design-system.css)

Patch Panel is the visual language for the whole public site, including
Concept, Theory, Quickstart, Atlas, Docs, navigation, loading, empty, error,
and mobile states. An Atlas-only reskin does not satisfy this contract.

## Product principle

The public path stays simple:

1. inspect a project;
2. see its Atlas;
3. correct or approve the map;
4. keep the Atlas current as the project changes.

The interface leads with recognizable project language. Protocol terms,
digests, model routes, skills, and MCP resources remain available as optional
details.

## Visual thesis

Concord Loom is a connected development workspace.

Deep navy surfaces organize work into readable modules. Cables, ports, rails,
and connection points show real relationships. One muted mint signal marks the
current route, focus, or primary action. Rounded geometry makes the tool
approachable; disciplined spacing and restrained motion keep it credible.

The system is serious without feeling corporate, and informal without looking
like a game.

### Patch Panel lock

Patch Panel v1 is the accepted machine contract. It establishes these
non-negotiable characteristics:

- dark navy, not pure black, is the page field;
- modules have visible boundaries and modest depth;
- connectors describe real project relationships;
- mint is the only primary signal color;
- text remains readable without glow, texture, or illustration;
- rounded corners are measured and consistent, not applied as pills to every
  element;
- technical identifiers are secondary to plain-language names;
- the same module grammar appears on every public route.

Do not introduce fantasy ornament, simulated stone or metal, neon halos,
decorative noise, glass effects, dashboard-card grids, or background artwork
behind the Atlas. Do not use disconnected visual styles for long-form pages.

The concept files record provenance. This document defines intent;
`design-tokens.json` defines reusable values; `design-system.css` defines
reusable components. Page CSS may place components, but it may not invent a
parallel visual system.

## Authority order

1. [`PRODUCT.md`](PRODUCT.md) defines product truth and brand commitments.
2. This document defines visual intent, component grammar, and acceptance.
3. `site/design-tokens.json` defines reusable visual values.
4. generated `site/design-tokens.css` exposes those values to the browser;
5. `site/design-system.css` composes components from tokens;
6. page markup and behavior consume components.

Generated CSS must not be edited by hand. A lower layer cannot redefine the
meaning of a higher layer.

## Token architecture

Tokens have four layers:

1. **Primitive**: raw color, type, spacing, radius, line, shadow, and timing.
2. **Semantic**: purpose such as page, panel, text, border, connection, signal,
   focus, error, and success.
3. **Component**: module, port, rail, control, reader, Atlas node, and inspector
   roles.
4. **Compatibility**: temporary aliases for supported names during migration.

Exact values belong in `site/design-tokens.json`. This document records their
meaning and constraints.

### Required token coverage

| Domain | Required roles |
|---|---|
| Color | page, panel, raised panel, text, muted text, border, connection, signal, error |
| Type | display, body, data, labels, reading measure and line height |
| Space | page gutters, section rhythm, module padding, control gaps |
| Shape | module, control, port, node and disclosure radii |
| Depth | rest, hover, selected and overlay shadows |
| Motion | control, overlay, graph enter, graph exit and reduced motion |
| Size | header, control target, reading column, inspector and graph bounds |

Raw values outside primitive tokens are allowed only for local, data-derived
geometry with no reusable meaning.

## Color and depth

- Deep navy separates the page from modules without relying on pure black.
- Slightly lighter surfaces establish hierarchy through contrast and borders.
- Text uses a high-contrast cool white; secondary text remains readable.
- Muted mint marks one current route, focus, or primary action.
- Red appears only for an actual error.
- Shadows express a small vertical lift. They do not create theatrical glow.

Selection, status, and focus never rely on color alone.

## Typography

- The display and body stacks use local system sans-serif fonts.
- Monospace is reserved for identifiers, commands, measurements, and machine
  values.
- Display headings use confident weight, compact leading, and restrained
  negative tracking.
- Body copy starts at 16 CSS pixels and uses a calm reading rhythm.
- Long-form text stays within 65–75 characters per line.
- Labels may use compact uppercase text only when the same information appears
  in a readable name.
- English and Russian share hierarchy, not forced line breaks.
- A Russian interface does not mix ordinary English prose into its controls or
  explanations.

## Component language

The public surface uses this vocabulary:

- **module**: a bounded responsibility, content group, or navigation region;
- **port**: a visible point where a real connection enters or leaves;
- **cable**: a real containment, dependency, or navigation relationship;
- **rail**: version, progress, path, or section navigation;
- **control**: a direct action with a named result;
- **reader**: a calm long-form surface;
- **inspector**: contextual details opened on demand;
- **signal**: the single current selection or primary action.

Every component defines rest, hover where available, focus, pressed, disabled
when applicable, loading, empty, error, and long-copy states. Controls have a
minimum 44 by 44 CSS pixel target and a visible keyboard focus.

## Page composition

### Concept

The first viewport states what Concord Loom does and offers one route to the
live Atlas plus one route to Quickstart. Supporting ideas appear as connected
modules, not marketing cards.

### Theory

The article uses one quiet reader with a stable table of contents, underlined
prose links, deep-linked headings, code overflow, responsive figures, and
previous/next navigation. Decorative modules stay outside the reading column.

### Quickstart

Quickstart presents one main path: install, inspect, open Atlas, review, and
continue. Each step names the expected result. Troubleshooting and advanced
governance remain secondary.

### Atlas

The graph receives the largest available area. Path and revision controls stay
compact. Details open in an overlay or drawer only when requested, so the graph
does not lose permanent width to an inspector.

### Docs

Documents are grouped by reader task. Search and filters show their active
state, empty state, and result count without becoming a generic dashboard.

## Atlas grammar

Atlas projects accepted loop data. At every level:

- the current cycle is visually dominant;
- direct children and real connections remain readable;
- the path back to the root remains visible;
- clicking a child replaces the active graph while preserving navigation
  context;
- details identify what the cycle does, needs, and produces in plain language;
- models, skills, tools, and MCP resources stay in optional technical details;
- the version rail shows history as a line and opens the latest version by
  default;
- evolution remains reachable without being shown as permanently active.

Forward and back transitions explain movement through containment. They must
not imply infinite recursion. The graph must remain legible with animation
disabled.

## Motion

- Frequent feedback finishes quickly and does not delay input.
- Graph traversal uses one consistent forward and reverse movement.
- Overlays enter from their spatial source and return on close.
- Layout movement uses transforms; visibility uses opacity.
- Interrupted animation settles safely at the current state.
- `prefers-reduced-motion: reduce` removes spatial travel and preserves state.

Motion must explain a state change. Ambient animation, parallax, and decorative
pulses are not part of the core system.

## Russian text

Russian human-facing copy follows
[`docs/ru/TEXT_STYLE.md`](ru/TEXT_STYLE.md). The pinned `ru-text` skill guides
editorial review. The repository linter catches only objective mistakes and
known onboarding jargon; it does not replace a human or model-assisted edit.

## Accessibility and localization

- Navigation exposes the current page.
- Menus and drawers support keyboard open, close, focus containment, and focus
  restoration.
- Graph selection has a programmatic current state.
- Loading, empty, stale-data, and error states are visible and localized.
- Dynamic labels, live regions, and accessible names use the current language.
- English is the first-visit default. An explicit saved language choice wins
  afterward.
- Language switching preserves the page and logical location.
- The site reflows at 200% zoom and at widths from 360 CSS pixels.
- No runtime request is required for fonts, icons, code, or other core assets.

## Content gate

Before public copy ships, review it in context:

1. Can a newcomer say what happens next?
2. Does it use project language before framework language?
3. Are optional implementation details secondary?
4. Does every action name its result?
5. Are English and Russian semantically equivalent?
6. Does the Russian version pass the editorial contract?

A negative answer blocks publication.

## Verification

Browser evidence covers:

- 360×800, 390×844, 768×1024, 1024×768, 1440×900, 1920×1080, and
  2048×1152;
- Chromium, Firefox, and WebKit where the repository harness supports them;
- English and Russian first paint, success, loading, empty, and error states;
- keyboard, visible focus, reduced motion, and 200% zoom;
- graph traversal, direct entry, reload, back/forward navigation, and language
  switching;
- overflow, clipped text, overlapping regions, unreachable controls, and
  untranslated accessible names.

Automated geometry checks do not approve visual quality by themselves. An
independent critic compares fresh screenshots with this direction and rejects
drift toward game decoration, corporate dashboard patterns, or a one-page-only
reskin.

## Cycle ownership

The accepted frontend development system assigns these exact responsibilities:

| Cycle | Responsibility |
|---|---|
| `design-site-experience` | Coordinate the complete frontend experience without replacing the evidence or authority of its child cycles. |
| `define-frontend-concept` | Pin the direction, content hierarchy, responsive behavior, and acceptance matrix. |
| `accept-frontend-concept` | Record the operator decision for the exact concept and machine-contract bytes. |
| `maintain-component-workshop` | Show production components in every required state and both languages. |
| `implement-frontend-surface` | Build every public route from the accepted design-system sources. |
| `maintain-frontend-verification` | Maintain deterministic browser, accessibility, breakpoint, and CI checks. |
| `verify-frontend-candidate` | Verify the exact candidate across browsers, languages, input modes, and sizes. |
| `critique-frontend-experience` | Independently compare fresh evidence with the approved Patch Panel direction. |

This design-system revision changes no cycle topology or authority rule.

Publication requires browser evidence and an independent visual verdict for
the exact candidate.

## Evolution

Design changes respond to repeated comprehension failures, visual defects,
accessibility regressions, or a new surface the current grammar cannot express.
A proposal names the observed problem, the smallest token or component change,
migration impact, verification, and rollback. It cannot approve or activate
itself.

Versioning follows these rules:

- patch: clarification or implementation repair with no visual API change;
- minor: additive token, component, state, or documented pattern;
- major: removed or redefined token, component grammar, or accessibility
  contract.

Every change updates both languages, generated token CSS, public projections,
and verification evidence.
