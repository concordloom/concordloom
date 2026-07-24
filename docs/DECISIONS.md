# Product decisions

This file records operator-approved outcomes. Implementation choices may refine
them, but may not silently change them.

## D-001 — Product identity

**Status:** accepted  
**Date:** 2026-07-24

The framework is named **Concord Loom**. Its repository, Python distribution,
CLI, and default plugin identifier use `concordloom`.

The name joins two ideas: concord with the human operator, and a loom that
weaves evidence, decisions, and nested cycles into one inspectable Atlas.

## D-002 — Complete v0.1, not a concept demo

**Status:** accepted  
**Date:** 2026-07-24

v0.1 must cover the whole framework path:

```text
repository evidence
  → observed and inferred project graph
  → high-information operator questions
  → accepted decisions
  → proposed loop design and operator acceptance
  → compiled loop system and policies
  → governed run cards
  → generated Atlas
  → bounded evolution proposal
```

The release also includes a Codex plugin/skill, tests, an example, and a public
article. A static diagram without executable contracts does not satisfy v0.1.

## D-003 — Nested loops are first-class

**Status:** accepted  
**Date:** 2026-07-24

An SDLC is a cycle of cycles. Requirements, design, implementation, testing,
deployment, and operation are not atomic boxes; each may own a bounded feedback
loop and invoke deeper loops.

The implementation must distinguish:

- an acyclic, finite **containment graph** describing which loop refines a
  composite step; and
- a **local control-flow graph** whose feedback transitions have explicit
  budgets, evidence, authority, and terminal outcomes.

“Recursive” describes how the contract pattern and Atlas navigation apply at
multiple levels. A concrete containment graph cannot contain an ancestor cycle.

## D-004 — Operator authority

**Status:** accepted  
**Date:** 2026-07-24

History and static analysis may propose architecture, ownership, and loop
boundaries. Only an explicit operator decision can accept or reject inferred
intent. The tool asks about outcomes and contested relationships, not about
files, models, reviewers, or internal routing.

The evolution loop may prepare a graph diff. It cannot activate its own
proposal. The authority of version `vN` governs acceptance of `vN+1`.

The same boundary applies to initial compilation: heuristics may propose a loop
design, but only an actor with bound product-intent authority can accept it.

## D-005 — Evidence and execution truth

**Status:** accepted  
**Date:** 2026-07-24

Observed, inferred, accepted, planned, actual, and verified information remain
separate. Runtime claims bind to candidate content, policy content, the
effective executor/model/skill/tool route, and structured evidence.

Passing an inner loop is necessary but not sufficient to accept its parent.
Authorship, independent review, release readiness, and publication authority
remain separate capabilities.

## D-006 — Portable core and adapter boundary

**Status:** accepted  
**Date:** 2026-07-24

The portable core is engine-agnostic, local-first, Python 3.11+, standard
library only, and deterministic for identical repository bytes and Git
history. Git is the built-in v0.1 history source. Rich semantic indexes and
durable workflow engines are optional future adapters.

The first release excludes hosted control planes, arbitrary remote code
execution, multi-repository identity, automatic source mutation, and automatic
activation of governance changes.

## D-007 — Public release boundary

**Status:** accepted  
**Date:** 2026-07-24

The release is a new public GitHub repository under Apache-2.0, tagged
`v0.1.0`. Publication occurs only after independent reference, visual, quality,
and release reviews of a pinned candidate. The published release is then
smoke-tested before the run is complete.
