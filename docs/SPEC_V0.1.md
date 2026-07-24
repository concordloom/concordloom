# Concord Loom v0.1 product specification

## Outcome

A developer can point Concord Loom at a Git repository, inspect provenance-rich
project observations, answer a short generated interview, compile the accepted
model into a valid bounded loop system, open an offline Atlas, and create an
evidence-bound run card. A Codex skill guides the same workflow.

## Users

- A product or engineering operator who owns intended outcomes.
- An orchestrating coding agent that chooses execution machinery.
- Executors and independent reviewers working under scoped run cards.
- Maintainers evolving the loop system from accumulated execution evidence.

## Required artifacts

### 1. Observed project graph

`concordloom inspect <repository>` emits deterministic JSON containing:

- repository and revision identity;
- files, categories, and detected languages;
- commit-derived churn, renames, and co-change edges;
- detected decision, build, test, CI, and agent-governance surfaces;
- provenance references for every edge;
- `observed` or `inferred` status and confidence.

No inferred edge is presented as operator-approved intent.

### 2. Operator interview and accepted graph

`concordloom questions` ranks unresolved hypotheses by expected graph impact.
Questions expose the evidence and the graph delta that each answer would cause.

`concordloom decide` records an explicit `confirmed`, `rejected`, or corrected
decision with actor and rationale. `concordloom accept` produces an accepted
graph only when every blocking question has a decision.

### 3. Loop-system compiler

`concordloom propose` turns an accepted project graph into a reviewable loop
design. The proposal exposes every inferred loop, child invocation, gate,
authority grant, and budget as a graph delta. An actor with `accept_intent`
capability must sign a decision over its digest.

`concordloom compile` validates and binds the accepted loop design plus policy
into:

- a loop registry;
- a routing and authority policy;
- a content-addressed binding;
- an initial evolution history;
- Atlas input.

Each loop defines typed input/output descriptions, local states and
transitions, child-loop invocations, evidence requirements, authority,
retry/time/cost budgets, escalation, and terminal outcomes.

The compiler rejects:

- missing child cycles;
- cycles in the containment graph;
- unreachable states, nonterminal dead ends, and states that cannot reach a
  terminal or escalation outcome;
- cyclic strongly connected components that do not consume a finite budget;
- budget exhaustion without a terminal path;
- child invocations without a finite deadline and escalation;
- child write authority broader than its parent grant;
- independent gates that permit author self-certification.

### 4. Governed execution

`concordloom run` supports creating, authorizing, guarding, recording, and
completing run cards. A card pins the accepted binding. Actual attempts record
the effective agent, model, reasoning level, skill, subagents, tools, and
policy digest.

Structured evidence identifies its scope, provenance, candidate tree digest,
policy digest, producer, and result. Parent acceptance evaluates its own
contract; child receipts do not compose automatically.

v0.1 validates local state machines and containment but treats each planned
loop node as one governed execution unit. It does not step every declarative
transition or schedule durable child workflows. Execution adapters supply
candidate-bound results to the relevant parent evidence contract.

The candidate digest covers a canonical manifest of tracked and explicitly
included untracked paths, file modes, symlink targets, and submodule commits.
The runner rechecks it when evidence is recorded and a gate completes.
Principal IDs and capabilities come from the content-addressed authority policy;
they are not free-text executor claims.

Creating a card and appending authorization, attempt, evidence, and completion
events uses a narrow runner-mediated control-plane grant in the active binding.
Read-only reviewers cannot change candidate files; the runner may append their
governance receipts.

### 5. Atlas

`concordloom atlas` generates one self-contained, offline HTML file from the
accepted binding and optional run card. It provides:

- one-level-at-a-time recursive navigation with breadcrumbs and browser
  history;
- a visible distinction between containment and local feedback flow;
- planned, actual, verified, and drift states;
- evidence, authority, budget, and terminal-outcome inspection;
- keyboard navigation, reduced-motion behavior, readable focus, and a useful
  narrow viewport.

The Atlas is a generated projection, not an execution authority or trace
database.

### 6. Evolution

`concordloom evolve` reduces repeated, content-addressed signals into a proposed
graph diff. It never changes the active binding. Acceptance requires an
explicit decision under the currently bound authority.

### 7. Codex distribution

The repository contains a valid Codex plugin with a `design-project-loops`
skill. The skill:

- analyzes the current repository and Git history;
- asks only high-information product questions;
- presents graph deltas before acceptance;
- compiles and validates loop contracts;
- maintains the Atlas and evolution signals;
- fails closed when authority or evidence is missing.

## Reference example

The shipped example contains a small generic software service with an outer
delivery loop and nested requirements, implementation, testing, release, and
operation loops. Testing contains a runtime-scenario child loop. It demonstrates
containment, bounded retry, escalation, and parent evidence evaluation without
depending on a game engine or cloud service.

## Verification

v0.1 is acceptable only when all of the following pass:

- unit and integration tests on Python 3.11+;
- deterministic repeated inspection and Atlas generation;
- JSON Schema validation for every public artifact;
- malicious path, malformed Git output, ancestor containment, unbounded retry,
  authority escalation, self-review, evidence mismatch, and self-authorizing
  evolution tests;
- Codex skill and plugin validators;
- installed-package CLI smoke test in a clean virtual environment;
- independent reference review against this specification;
- independent Atlas review at desktop and narrow viewports;
- independent quality review;
- public GitHub release smoke test.

Canonical digests cover a documented payload envelope and exclude wall-clock
display metadata. Identical inputs therefore produce identical digests.

## Explicit non-claims

v0.1 does not claim to invent iterative development, nested workflows,
statecharts, provenance, code graphs, or continuous improvement. It also does
not claim measured productivity gains or ship a durable workflow runtime. Its
testable contribution is the governed, repository-grounded composition of
these ideas into one versioned loop system.
