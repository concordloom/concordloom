# Concord Loom v0.1 product specification

[Русская версия](ru/SPEC_V0.1.md)

## Outcome

An operator can turn bounded evidence into an accepted, executable, and
inspectable system of loops without making any domain engine, workflow
runtime, model provider, hosting platform, or repository layout mandatory.
Concord Loom preserves the chain from observation through decision, binding,
execution, verification, publication, and evolution.

The v0.1 distribution proves this model through a local Git observation
adapter, a file-backed runner, an offline Atlas, a Codex skill, and a generic
SDLC reference binding. Those components form the first portable vertical
slice; the SDLC example is not the product definition.

## Users

- An operator who owns intended outcomes and accepts consequential changes.
- An orchestrator that chooses machinery within accepted policy.
- Scoped executors that produce candidates and factual evidence.
- Independent reviewers that evaluate pinned candidates.
- Publishers with explicit authority for external effects.
- Maintainers that propose successors from accumulated signals.

## Required capabilities

### 1. Observation

`concordloom inspect` reads a bounded source through the built-in Git adapter
and emits deterministic JSON containing:

- source and revision identity;
- files, categories, and detected languages;
- commit-derived churn, renames, authors, and co-change;
- detected decision, build, test, CI, documentation, and agent surfaces;
- provenance references for every fact or hypothesis; and
- coverage, truncation, status, and confidence.

The adapter treats source material as data. It does not execute target code,
hooks, or historical revisions. No inference counts as accepted intent.

The public artifact model permits future observation adapters, but v0.1 ships
only the local Git implementation.

### 2. Negotiation and accepted intent

`concordloom questions` ranks unresolved hypotheses by expected graph impact.
Every question exposes evidence and the graph delta for each answer.

`concordloom decide` records an explicit confirmation, rejection, or
correction with actor and rationale. `concordloom accept` produces accepted
intent only after all blocking questions have authorized decisions.

### 3. Loop design and binding

`concordloom propose` turns accepted intent into a reviewable loop-design
delta. It exposes proposed loops, child invocations, gates, authority, scope,
and budgets. An authorized actor must accept the exact proposal digest.

`concordloom compile` validates the accepted design and policy and produces:

- a finite loop registry;
- routing, authority, compute, and evolution policy;
- a content-addressed binding proposal;
- an initial evolution history; and
- Atlas input.

Each loop defines typed inputs and outputs, local states and transitions,
children, evidence predicates, capabilities, budgets, escalation, and terminal
outcomes.

The compiler rejects:

- missing child loops or cyclic containment;
- unreachable states, nonterminal dead ends, or missing terminal paths;
- cyclic local flow without a decreasing finite budget;
- budget exhaustion without terminal or escalation behavior;
- child scope, budget, or authority broader than its parent;
- child invocations without a deadline and failure path; and
- independent gates that permit author self-certification.

Binding activation requires a separate authorized decision. Compilation cannot
authorize its own output.

### 4. Governed execution

`concordloom run` creates, authorizes, guards, records, and completes run cards.
A public card pins an accepted binding, candidate manifest, route, policy, and
evidence contract.

The default route contains only the root coordinator. `--target-loop` adds the
selected responsibility and its ancestors. The complete reachable tree is used
only when a caller explicitly selects `--portfolio`.

Actual attempts record the effective principal, agent, model, reasoning, skill,
subagents, tools, times, result, policy digest, and candidate digest. Structured
evidence identifies its predicate, provenance, producer, checks, payload,
candidate, policy, and attempt.

The built-in repository candidate manifest covers tracked and explicitly
included untracked paths, content, modes, symlink targets, submodule commits,
revision, and inventory. The runner checks identity at evidence and completion
boundaries.

The active binding grants the runner a narrow control-plane capability to
append lifecycle receipts. That grant does not grant candidate writes.
`guard` enforces declared policy scope but is not an operating-system sandbox.

Concord Loom v0.1 validates local state machines and containment while treating
each planned node as one governed unit. It does not step every transition or
schedule durable child workflows. Execution adapters perform work and return
candidate-bound evidence.

### 5. Independent verification

Parent acceptance evaluates the parent's evidence contract. Child receipts do
not compose automatically.

When policy requires independence, the reviewer must differ from recorded
candidate authors. A `PASSED` node means its declared evidence contract was met
for its pinned candidate. It does not authorize publication or broaden any
capability.

### 6. Publication

Publication is an explicit external effect. It requires a verified candidate,
a publisher capability, and scope that names the allowed mutation.

A publish node records one of three outcomes: the authorized effect, a
deliberate no-op, or escalation. Verification alone never implies permission
to publish.

### 7. Atlas

`concordloom atlas` generates one deterministic, self-contained HTML projection
from accepted artifacts and optional run data. It provides:

- one-level-at-a-time containment navigation;
- distinct rendering for containment and local feedback;
- planned, actual, verified, and drift layers;
- evidence, authority, budget, and terminal-outcome inspection; and
- keyboard, reduced-motion, focus, and narrow-viewport support.

The Atlas is a projection, not an authority or trace database.

### 8. Evolution

`concordloom evolve` reduces repeated content-addressed signals into a proposed
graph or policy delta. A proposal names the active base binding, contributing
signals, preconditions, risk, and required decision authority.

The reducer cannot modify the active catalog. The proposal cannot accept or
activate itself. A successor requires a separate authorized decision under the
active binding and a separate activation step.

### 9. Codex distribution

The repository contains a Codex plugin with the `design-project-loops` skill.
The skill:

- performs bounded read-only discovery;
- asks high-information questions;
- displays graph deltas before acceptance;
- compiles and validates contracts;
- records routes and evidence; and
- proposes, but never self-authorizes, evolution.

Model-assisted output remains untrusted input to schemas, policy, and
invariant checks.

## Accepted Concord Loom development system

Concord Loom's repository uses an operator-accepted development configuration
rooted at `steward-concordloom`. Its ten responsibility areas contain 58
cycles, including product direction, theory, protocol, runtime, assurance,
adapters, knowledge, release, adoption, and system evolution.

Every run still separates observation from accepted intent, design acceptance
from activation, candidate production from independent verification,
verification from publication, and successor proposal from activation. The
current configuration succeeded the earlier seven-loop example through
explicit operator decisions. It governs Concord Loom itself; adopters may
accept different topologies.

## Reference bindings

The shipped generic SDLC binding models a software service with delivery,
requirements, implementation, testing, release, and operations loops. Testing
contains a runtime-scenario child. This binding demonstrates containment,
bounded retry, escalation, and parent-owned acceptance without requiring a
game engine or cloud service.

It is one example binding. The framework's schemas and invariants do not
require SDLC phases or software-delivery vocabulary.

## Verification

v0.1 is acceptable only when the applicable checks pass:

- unit and integration tests on Python 3.11+;
- deterministic repeated inspection and Atlas generation;
- validation of every public JSON artifact;
- adversarial tests for paths, Git output, containment, retry, authority,
  self-review, evidence mismatch, and self-authorizing evolution;
- Codex skill and plugin validation;
- installed-package CLI smoke in a clean environment;
- independent reference, visual, quality, and release reviews; and
- public-release retrieval and smoke tests.

Canonical digests cover documented payload envelopes and exclude declared
wall-clock display metadata.

## Historical context and limits of the claim

The first release used a one-time, separate bootstrap protocol under
`concord/`. Bootstrap receipts are trust-seed artifacts, not public v0.1 run
cards. Public runs use `schemas/run-card.schema.json` and bind accepted
registry, policy, binding, candidate, route, evidence, and authority.

v0.1 does not claim to invent iteration, nested workflows, statecharts,
provenance, graphs, or continuous improvement. It makes no measured
productivity or universal-safety claim and ships no durable workflow runtime.
Its testable contribution is the governed composition of bounded loops into a
versioned, inspectable artifact chain.
