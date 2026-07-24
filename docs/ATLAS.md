# Concord Loom Atlas

The Atlas is a deterministic, self-contained HTML projection of an accepted
loop system. It lets an operator move through nested loops, inspect one loop's
local flow, and compare declared plans with recorded runtime facts.

The Atlas explains bound artifacts. It does not authorize work, execute a
transition, or replace the source JSON.

## Generate the bundled Atlas

Generate the public Atlas from the accepted generic SDLC example:

```bash
concordloom atlas \
  --binding framework/generic-sdlc/binding.json \
  --registry framework/generic-sdlc/cycle-registry.json \
  --policy framework/generic-sdlc/policy.json \
  --output docs/ATLAS.html
```

Open `docs/ATLAS.html` directly in a browser. The file needs no server and
makes no network requests.

Use `--check` in CI or before a commit:

```bash
concordloom atlas \
  --binding framework/generic-sdlc/binding.json \
  --registry framework/generic-sdlc/cycle-registry.json \
  --policy framework/generic-sdlc/policy.json \
  --output docs/ATLAS.html \
  --check
```

Check mode renders the same inputs and fails if the existing output is stale.
It does not update the file.

## Attach a run

Pass an optional run card to add runtime facts:

```bash
concordloom atlas \
  --binding path/to/binding.json \
  --registry path/to/cycle-registry.json \
  --policy path/to/policy.json \
  --run-card path/to/run-card.json \
  --output path/to/atlas.html
```

The run card must refer to the same binding, registry, and policy. Its route,
attempts, evidence references, statuses, and outcome remain scoped to that
run.

The Atlas checks run-card schema, digest identity, active-loop reachability,
and evidence-reference integrity. It does not load the referenced evidence
payloads, recompute their byte digests, or repeat the runner's claim
validation. The **Verified** layer therefore labels recorded references as
**Not revalidated**.

Without `--run-card`, the Atlas shows the accepted model and its declared
plans. It labels the runtime layer **No run attached**. Missing runtime input
never means that work ran, passed, failed, or drifted.

## Read the two graphs

Concord Loom keeps containment and local feedback separate.

**Containment** answers “which loop refines this composite step?” The Atlas
shows one containment level at a time. Active-root controls switch between
bound root systems. Choose a child invocation to descend into that child loop.
Breadcrumbs return to an ancestor, and browser Back and Forward restore
visited loops. The containment graph is finite and acyclic.

**Local control flow** answers “how can this loop move between its own states?”
The central flow view shows progress, success, failure, escalation, and
feedback transitions. A feedback edge belongs to the selected loop and carries
its own finite traversal budget. It is not a containment edge.

A child result does not close its parent. The parent evaluates the child's
receipt against the parent's evidence contract.

## Read the truth layers

The Atlas keeps four runtime meanings distinct:

| Layer | Source | Meaning |
|---|---|---|
| **Planned** | Binding, registry, policy, and run route when attached | The accepted structure and intended execution route |
| **Actual** | Recorded attempts in the attached run card | The principal, agent, model, skill, tools, and result that the runner recorded |
| **Verified** | Evidence-reference metadata recorded in the run card | Which payloads the runner cited; the Atlas marks them not revalidated |
| **Drift** | Explicit comparison of planned and actual fields | A mismatch to inspect, not an automatic correction or failure |

Accepted structure is not runtime verification. A planned route becomes actual
only when the run records an attempt. A run may cite verification payloads,
but this Atlas does not turn reference presence into a fresh verification
claim. Inspect and validate the payloads at the runner boundary. Drift remains
visible so an operator can decide what it means.

## Inspect a loop contract

For the selected loop, the Atlas exposes:

- purpose, inputs, and outputs;
- entry, work, gate, child, and terminal states;
- local transitions and bounded feedback;
- child invocations and their timeout or escalation path;
- attempt, elapsed-time, cost, and exhaustion budgets;
- execute, accept, and escalate capabilities;
- evidence contracts and independence requirements; and
- attached run status, attempts, evidence-reference metadata, and root outcome.

These fields come from the input artifacts. The generated page does not infer
an unrecorded attempt, evidence result, or authority grant.

## Keyboard, motion, and narrow screens

The Atlas uses native links and buttons:

- `Tab` and `Shift+Tab` move through interactive controls.
- `Enter` activates links. `Enter` or `Space` activates focused buttons.
- Browser Back and Forward move through the loop navigation history.
- A visible focus indicator identifies the active keyboard target.

Text labels and shapes accompany state and truth colors, so color is not the
only cue. The page honors `prefers-reduced-motion`. At narrow widths, navigation,
flow, and contract details stack into one reading order; all actions remain
available without a hover gesture.

## Determinism and offline safety

The renderer uses only the supplied JSON artifacts and stable ordering. The
same validated inputs produce the same HTML bytes. Input timestamps may appear
as recorded facts; generation adds no current time.

The output embeds its styles, behavior, and data. It loads no remote scripts,
fonts, stylesheets, images, APIs, or analytics. Repository-controlled text is
escaped, and the document includes a restrictive content-security policy.

Treat the file as a readable projection, not a security boundary. Concord Loom
guards declared scope but is not an operating-system sandbox or a
cryptographic identity service.

## v0.1 execution boundary

Concord Loom v0.1 validates containment, local state contracts, candidate
identity, authority, and evidence boundaries. Its runner treats each planned
loop node as one governed execution unit.

The Atlas does not step every local transition, launch durable child
workflows, stream live execution, synthesize child receipts, or promote a
child's status into parent acceptance. External workflow, CI, agent, or local
adapters perform work and return candidate-bound evidence. The Atlas displays
only the facts that those governed artifacts record.

## Maintain the generated file

Regenerate the Atlas after an accepted binding, registry, policy, or attached
run changes. Review the source artifacts when a displayed fact looks wrong;
editing `docs/ATLAS.html` cannot change the accepted model.

Keep `--check` in the development gate so the committed projection stays
byte-for-byte aligned with its inputs.
