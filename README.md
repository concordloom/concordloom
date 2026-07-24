# Concord Loom

**Turn repository evidence and operator decisions into a versioned system of
bounded development loops.**

[![CI](https://github.com/PullDakar/concordloom/actions/workflows/ci.yml/badge.svg)](https://github.com/PullDakar/concordloom/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)

Concord Loom inspects a Git repository without executing it, separates facts
from inferred intent, asks an operator the questions that would change the
model most, and compiles accepted answers into nested loop contracts. Its v0.1
harness pins candidates and records scoped per-loop attempts, evidence, and
independent gates; the same contracts drive an offline Atlas and proposal-only
evolution.

The core model is simple: an SDLC is a cycle of cycles. Requirements,
implementation, testing, release, and operations are themselves feedback
loops. Testing may invoke smaller scenario loops. A child should report what
it proved; its parent decides what that proof means.

Concord Loom does not claim to invent iteration, nested workflows, code
graphs, or continuous improvement. Its v0.1 contribution is to govern their
composition, evidence, authority, termination, and evolution as one
content-addressed artifact chain.

## What v0.1 includes

- Safe, bounded inspection of repository structure and Git history.
- Provenance-rich observed and inferred project graphs.
- Ranked operator questions and immutable decision records.
- Separate acceptance of project intent, loop design, and binding activation.
- A compiler for finite containment plus bounded local feedback.
- Candidate manifests, scoped run cards, factual route records, and evidence.
- Independent review constraints and parent-owned acceptance.
- A deterministic, self-contained offline Atlas.
- Evolution proposals that cannot activate themselves.
- A Codex plugin with the `design-project-loops` skill.
- Seventeen public JSON Schemas and an exact-digest generic SDLC example.

## Install

Python 3.11 or newer and Git are required. The portable core has no runtime
Python dependencies.

```bash
python3 -m pip install \
  "concordloom @ git+https://github.com/PullDakar/concordloom@v0.1.0"
concordloom --version
```

For release-wheel and checksum verification, see
[Release verification](docs/RELEASE.md).

## Inspect a repository

Inspection reads repository bytes and bounded Git metadata. It does not import
or execute the target project.

```bash
mkdir -p .concord/discovery
concordloom inspect . \
  --output .concord/discovery/observed-project-graph.json
concordloom questions \
  --graph .concord/discovery/observed-project-graph.json \
  --output .concord/discovery/questions.json
```

These commands produce evidence and hypotheses, not accepted intent. Continue
with the [10-minute walkthrough](docs/QUICKSTART.md) to record decisions,
accept a loop design, compile and activate a binding, create a run, generate
an Atlas, and propose an evolution.

## Artifact chain

```text
repository evidence
  → observed/inferred graph
  → ranked questions
  → operator decisions
  → accepted graph
  → loop-design proposal
  → explicit design acceptance
  → registry + binding proposal
  → explicit binding activation
  → catalog + governed runs + Atlas
  → evolution proposal
```

Each arrow persists a new artifact. Later stages cite exact digests; they do
not rewrite earlier evidence.

## Two graphs make a loop system

Containment and feedback are deliberately separate:

- The **containment graph** says which loop refines a composite step. It is a
  finite DAG, so nesting has a maximum depth.
- Each loop's **local control-flow graph** may contain feedback. Every cyclic
  strongly connected component must consume a finite budget and retain a path
  to termination or escalation.

This makes recursive navigation useful without authorizing unbounded runtime
recursion.

## Commands

| Command | Result |
|---|---|
| `inspect` | Observed/inferred repository graph |
| `questions` | Ranked unresolved intent questions |
| `decide` | One explicit decision record |
| `accept` | Accepted project graph or accepted loop design |
| `propose` | Reviewable loop-design proposal |
| `compile` | Cycle registry and binding proposal |
| `activate` | Binding accepted through a separate decision |
| `catalog` | Append-only active-binding chain |
| `candidate` | Content-addressed candidate manifest |
| `run` | Governed execution lifecycle |
| `atlas` | Deterministic offline HTML projection |
| `evolve` | Successor proposal, never activation |
| `validate` | Schema and cross-artifact validation |

Every command has local help:

```bash
concordloom run --help
concordloom run authorize --help
```

## Codex plugin

The repository is also a Codex marketplace:

```bash
codex plugin marketplace add PullDakar/concordloom --ref v0.1.0
codex plugin add concordloom@concordloom
```

Then ask Codex to use `$design-project-loops` in a repository. The skill starts
with bounded, read-only discovery and refuses to turn inferred intent into
authority without an operator decision. See [Codex plugin](docs/CODEX_PLUGIN.md).

## Trust boundary

Concord Loom validates declarative artifacts and policy boundaries. It is not
an operating-system sandbox, credential provider, durable workflow engine, or
cryptographic identity service. The local portable runner's identities support
accountability and separation checks; deployments that need adversarial
identity assurance must add signed attestations and platform enforcement.

v0.1 validates local state and containment structures but does not step every
declared transition or launch durable child workflows. Execution adapters
perform that work and return evidence; the harness never infers parent
acceptance from a child's green status.

Read [Trust model](docs/TRUST_MODEL.md) before using it for high-impact
delivery decisions.

## Documentation

- [Quickstart](docs/QUICKSTART.md)
- [Core concepts](docs/CONCEPTS.md)
- [Architecture](docs/ARCHITECTURE.md)
- [v0.1 specification](docs/SPEC_V0.1.md)
- [Trust model](docs/TRUST_MODEL.md)
- [Codex plugin](docs/CODEX_PLUGIN.md)
- [Release verification](docs/RELEASE.md)
- [Article: *Cycles of Cycles*](docs/ARTICLE.md)
- [Offline Atlas](docs/ATLAS.html)

## Development

```bash
./tools/check.sh
```

The gate runs the standard-library test suite, parses every shipped JSON
artifact, checks deterministic example generation, exercises the CLI, and
checks the working diff. A green gate is development evidence, not product or
release authority.

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
