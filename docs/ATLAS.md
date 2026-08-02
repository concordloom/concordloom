# Concord Loom Atlas

The Atlas answers 3 questions:

1. Which cycle is responsible for this work?
2. What must the cycle receive and return?
3. Which facts come from an accepted plan, and which come from a recorded run?

It is a read-only view. It cannot authorize work, execute a transition, publish
an external change, or activate evolution.

## Preview a task route

Describe a task in ordinary language. Concord Loom can propose the shortest
accepted route that reaches the relevant cycles and includes the parent cycles
needed to contain them.

The preview is shown as **Proposed**, not **Planned**. It is bound to the exact
Atlas rules, development model, and candidate files, but it grants no authority
and performs no repository, network, or external action. The original request
stays outside the durable artifact; only its fingerprint is recorded.
The preview also shows the network access and external changes each step would
be allowed to use only after a later confirmation and authorization.

You can correct the selected cycles or confirm the preview. Confirmation
creates a draft run from that exact route version. It does not change the accepted
Atlas. If the binding, candidate, or development model changes, the old preview
is stale and must be rebuilt.

## Interactive project Atlas

The [public Atlas](https://concordloom.github.io/concordloom/#atlas/steward-concordloom)
shows all 66 cycles used to develop Concord Loom. Start at the root and select
a child to move one level deeper.

The first screen shows plain-language information:

- the cycle's purpose;
- the responsible role;
- its input and expected output;
- the planned model, agent instructions, tools, and MCP connections.

Open **Technical details** only when you need stable IDs, artifact names,
required claims, or the accepted source digest.

The header keeps 2 version axes separate:

```text
Product release: 0.1.5
Development rules: revision 10
```

Revision 10 is the tenth accepted version of Concord Loom's own development
rules. It is not a product release.

## Complete development system

The root cycle contains 10 responsibility areas:

```text
Steward Concord Loom
├── Product direction
├── Research and theory
├── Protocol design
├── Runtime and tooling
├── Trust and assurance
├── Bindings and adapters
├── Knowledge and experience
├── Release and distribution
├── Adoption and feedback
└── System evolution
```

Each area opens into concrete capability cycles. The complete outline remains
available below the interactive view.

## Evolution

The evolution circuit is always visible:

```text
collect signals
  → propose a successor
  → independently review it
  → activate it by a separate operator decision
  → observe the migration
```

The proposal cannot activate itself. Activation uses authority from the
currently active rules, not from the proposed successor.

## Plan and fact

The Atlas distinguishes:

| Layer | Meaning |
|---|---|
| Proposed route | A non-authorizing route preview awaiting confirmation |
| Accepted plan | The active cycle structure, roles, limits, and intended resources |
| Recorded run | The principal, model, instructions, tools, network use, effects, and result actually recorded |
| Verified result | Evidence attached to the exact candidate and checked against a contract |
| Drift | A visible difference between plan and fact |

Missing run data stays missing. The Atlas does not invent an execution record
from a plan.

## Portable offline Atlas

`concordloom atlas` generates one self-contained HTML file for any compatible
binding:

```bash
concordloom atlas \
  --binding path/to/binding.json \
  --registry path/to/cycle-registry.json \
  --policy path/to/policy.json \
  --run-card path/to/run-card.json \
  --output path/to/atlas.html
```

The run card is optional. Without it, the file shows only the accepted plan.

Use `--check` in CI to reject stale output:

```bash
concordloom atlas \
  --binding path/to/binding.json \
  --registry path/to/cycle-registry.json \
  --policy path/to/policy.json \
  --output path/to/atlas.html \
  --check
```

The generated file loads no remote scripts, fonts, APIs, or analytics.

## Source of truth

The Atlas is generated from accepted JSON artifacts and recorded run receipts.
Editing `docs/ATLAS.html` or `site/data/atlas.json` does not change the accepted
system.

After changing accepted inputs, rebuild and verify both views:

```bash
PYTHONPATH=src python3 tools/build_site.py
PYTHONPATH=src python3 tools/build_site.py --check
./tools/check.sh
```

Treat the Atlas as an explanation and inspection surface, not as a security
boundary.
