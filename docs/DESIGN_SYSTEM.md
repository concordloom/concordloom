# Concord Loom design system

Language: **English** | [Русский](ru/DESIGN_SYSTEM.md)

Status: **normative**

Version: **2.0.0**

Machine source: [`site/design-tokens.json`](../site/design-tokens.json)

The interface should feel like a precise machine that exposes how work is
connected. It must remain understandable when every decorative effect is
removed.

## Product principle

Concord Loom keeps its formal machinery behind a simple public path:

1. inspect a project;
2. see its Atlas;
3. correct or approve the map;
4. keep the Atlas current as the project changes.

The interface names what a person controls and recognizes. Protocol terms,
digests, model routes, skills, and MCP resources remain available as supporting
details. They do not lead the experience.

## Visual thesis

Concord Loom is a machine you can enter.

The visual system combines blackened metal, graphite, ceramic, warm-white
tension lines, and one acid signal. Circular gates represent cycles. Sharp
instrument panels hold navigation and explanation. The design avoids fantasy
ornament, generic dashboard cards, glass effects, and decorative gradients.

The complete system should still be recognizable with every label removed:
dark concentric mechanisms, taut paths, and one active acid route.

### Signal Constellation reference lock

[`signal-constellation-reference.png`](assets/signal-constellation-reference.png)
is the normative visual benchmark for the 2.0 system. It is not mood-board
material. Implementations must preserve its visual logic:

- blackened metal and stone have visible depth, wear, rims, fasteners, and
  concentric construction;
- the Atlas is a dense working mechanism, not a sparse chart placed on a dark
  page;
- a drilled view keeps the parent system on the left, expands the current
  system in the center, and uses the right side as an instrument inspector;
- warm structural threads show real relationships, while acid chartreuse
  marks one active route;
- labels, controls, navigation, reading surfaces, and the homepage belong to
  the same machine.

[`signal-constellation-stage.png`](assets/signal-constellation-stage.png) is the
clean material stage derived from that benchmark. Live nodes and paths remain
data-driven projections over the stage; they must never be baked into the
image.

A token-only reskin, flat circles, a generic dashboard grid, a sparse radial
diagram, or an Atlas that alone uses this style does not satisfy the reference
lock.

## Token architecture

Tokens follow four layers:

1. **Primitive tokens** store raw color, space, type, line, and timing values.
2. **Semantic tokens** name purpose, such as `surface-void`, `text-primary`,
   `line-quiet`, and `signal`.
3. **Component tokens** define reusable component roles without binding them
   to one page.
4. **Compatibility tokens** preserve supported legacy names during migration.

Component rules apply those layers to navigation, reading surfaces,
   the Atlas, controls, and status.

Canonical machine values live in
[`site/design-tokens.json`](../site/design-tokens.json).
[`site/design-tokens.css`](../site/design-tokens.css) is generated
deterministically, while
[`site/design-system.css`](../site/design-system.css) composes components from
those values. Token changes are API changes. A removed token requires a
documented replacement. Generated CSS must never be edited directly.

### Authority order

1. This document defines intent, permitted patterns, and acceptance.
2. `design-tokens.json` defines every reusable visual value.
3. Generated `design-tokens.css` exposes those values to the browser.
4. `design-system.css` composes components from the tokens.
5. Page markup and behavior consume components.

A lower layer cannot override the meaning of a higher layer. Local geometry,
such as an SVG node coordinate or a grid column count, may remain in a
component when it has no reusable meaning. Color, type, spacing rhythm,
controls, reading measure, layers, and motion timing may not.

### Coverage registry

| Domain | Source of truth | Required verification |
|---|---|---|
| Color and contrast | primitive and semantic tokens | dark/high-contrast states, non-color cues |
| Typography | font, scale, weight, leading, tracking, measure tokens | EN/RU hierarchy, 200% zoom, no runtime fonts |
| Spacing and sizing | spacing, control, header and measure tokens | 44 px targets and responsive reflow |
| Shape and material | component rules and panel tokens | no decorative card language or synthetic noise |
| Layout | component rules | desktop, tablet, mobile and long-content states |
| Motion | duration and easing tokens | forward, reverse, interruption and reduced motion |
| Interaction | component states | rest, hover, focus, active, disabled, loading, empty, error |
| Accessibility | semantic markup and component rules | keyboard, names, focus, zoom, contrast |
| Localization | EN/RU content contract | first paint, dynamic copy, ARIA and error paths |
| Atlas | active binding projection and Atlas grammar | full reachability, deep links, stale-data failure |
| Content | writing and comprehension contracts | clear next action and progressive disclosure |
| Governance | cycle ownership and evolution rules | pinned candidate, evidence and separate authority |

## Color

The surface uses one accent:

- off-black and graphite establish depth;
- warm white carries readable text and structural thread;
- silver marks supporting information;
- acid chartreuse marks the selected path, focus, and actions;
- red appears only for an actual error.

Acid chartreuse never categorizes unrelated information. If everything glows,
nothing is selected.

## Shape and material

- Cycles are circular because they contain bounded repeated work.
- Panels and controls use sharp corners because they are instruments.
- Hairlines separate real regions or connect real nodes.
- Shadows express physical depth; outer neon halos do not decorate containers.
- Texture must come from an authored material asset. Synthetic noise filters
  are not part of the system.

## Typography

Display type explains hierarchy. Body type explains meaning. Monospace is
reserved for identifiers, code, measurements, and machine values.

- The display stack is `Arial Narrow`, `Helvetica Neue`, Helvetica, Arial,
  then the system sans-serif fallback. No runtime font request is allowed.
- The technical stack is `IBM Plex Mono`, `SFMono-Regular`, Consolas, then the
  system monospace fallback.
- The scale is `2xs` 10 px, `xs` 12 px, `sm` 14 px, body 16 px, responsive
  lead, title, and display sizes.
- Body text uses 1.6 line height. Long-form reading uses 1.72.
- Display text uses weights 650 or 800 and tracking no tighter than -0.04 em.
  Labels use uppercase mono at 0.12 em.
- Body copy remains at a 72-character measure, within the accepted 65-75
  character range.
- Russian and English use the same hierarchy, not identical line breaks.
- A translated interface never mixes ordinary English prose into Russian.

All type values are primitive tokens. Semantic roles such as `type-display`,
`type-code`, and `reading-leading` consume them. Components must not introduce
a new font family, weight, or reading measure directly.

## Component language

The public surface uses a small component vocabulary:

- **gate** - a cycle node with rest, selected, focus, and unavailable states;
- **thread** - a real containment or navigation relationship;
- **instrument panel** - bounded controls or explanation;
- **path rail** - preserved navigation history;
- **reading surface** - calm long-form content inside the same material system;
- **signal control** - the one primary action or current selection.

Every component consumes semantic or component tokens. Raw color values are
limited to primitive definitions. Controls have a minimum 44 px target, visible
focus, localized accessible names, and non-color state cues.

## Atlas grammar

Atlas projects the accepted loop map. It never becomes an independent source
of truth.

At every level:

- the selected cycle occupies the center;
- its direct children occupy the active ring;
- size distinguishes current, parent, and child responsibilities;
- the path remains visible on the left;
- the plain-language contract remains visible on the right;
- models, skills, tools, and MCP resources appear only in optional details;
- evolution remains findable from every Atlas journey.

Clicking a child preserves the selected gate, moves the previous level left,
and settles the child graph in the center. Moving to a parent reverses that
direction. The transition explains containment; it does not imply unbounded
runtime recursion.

## Motion

Motion serves feedback, orientation, and continuity.

- Pointer-driven level changes use a 360 ms move curve:
  `cubic-bezier(0.25, 1, 0.5, 1)`.
- Frequent controls stay below 220 ms.
- Keyboard navigation changes levels immediately.
- Layout movement uses `transform`; visibility uses `opacity`.
- `prefers-reduced-motion: reduce` removes spatial travel and preserves the
  final state.
- Every opening state has a matching closing or reverse state.

## Interaction states

Every interactive component defines:

- rest;
- hover where hover exists;
- visible keyboard focus;
- pressed;
- disabled when applicable;
- loading;
- empty;
- error.

Focus and selection cannot rely on color alone. Atlas exposes labels, current
location, child counts, and accessible names.

## Reading surfaces

Theory and documentation inherit the same material system but optimize for
reading:

- stable table of contents;
- one main reading column;
- underlined prose links;
- readable code overflow;
- headings with stable deep links;
- no essential conclusion hidden in a disclosure.

The interface may be dramatic around the article. The article itself must be
calm.

## Responsive behavior

Desktop uses the three-part Atlas instrument: path, graph, explanation.

On narrow screens:

- navigation becomes a controlled menu;
- the path becomes a horizontal history strip;
- the graph remains the primary surface;
- the explanation follows the graph;
- targets remain at least 44 by 44 CSS pixels;
- the page reflows at 200 percent zoom without hiding information.

## Content gate

Before any new public text ships, a reviewer should be able to answer:

1. Can a newcomer say what happens next?
2. Does the copy use project language before framework language?
3. Are implementation details optional?
4. Does every action name its result?
5. Are English and Russian semantically equivalent?

If any answer is no, the interface is unfinished.

## Cycle ownership

The design system is enforced by existing development cycles. A new cycle
would duplicate responsibilities and make the Atlas harder to understand.

| Cycle | Mandatory responsibility |
|---|---|
| `design-information-architecture` | Keep the public path to inspect, Atlas, correction or approval, and continuous refresh. |
| `review-comprehension` | Reject unexplained framework language, hidden next steps, and technical detail presented before the user task. |
| `design-site-experience` | Apply the tokens, components, responsive rules, accessibility states, and motion grammar in this document. |
| `project-atlas` | Render the complete accepted cycle map, preserve drill-down context, and fail when generated data is stale. |
| `system-evolution` | Turn repeated failures into a reviewable successor proposal without granting it authority. |

Repository checks treat this document, the authored tokens, the interactive
Atlas structure, reduced-motion behavior, and the generated documentation index
as one contract. A change that breaks any part of it does not pass.

Reference acceptance also requires:

- the 1672 by 941 reference and material assets remain exact, local, and free
  of runtime dependencies;
- desktop evidence shows the parent, current system, and inspector together;
- 390 px evidence keeps the active graph legible and the inspector reachable;
- forward and back traversal communicate direction, while reduced motion
  removes travel;
- English and Russian preserve the same layout, meaning, controls, and
  accessible names;
- a reviewer compares the implementation with the reference image, not merely
  with token and component checklists.

## Evolution

The design system evolves through evidence:

- repeated comprehension failures;
- recurring visual or interaction defects;
- accessibility regressions;
- Atlas drift from accepted data;
- a new product surface that the current system cannot express.

One isolated preference does not justify a new rule. A successor proposal must
name the observed problem, the smallest token or component change, migration
impact, verification, and rollback. It cannot accept or activate itself.

### Versioning and migration

- Patch: clarification or implementation repair with no visual API change.
- Minor: additive token, component, state, or documented pattern.
- Major: removed or redefined token, component grammar, or accessibility
  contract.
- A deprecated token remains as a compatibility alias for at least one minor
  version and names its replacement.
- Every change updates both languages, regenerates token CSS and site content,
  passes the complete coverage registry, and records evidence in its governed
  run.
