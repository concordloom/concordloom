# Concord Loom v0.1 architecture

[Русская версия](ru/ARCHITECTURE.md)

## 1. System boundary

Concord Loom is a domain-neutral compiler and governance harness for bounded
systems of loops. It binds accepted intent, finite loop contracts, policy,
execution facts, and evidence into a content-addressed chain. It does not
replace a domain engine, workflow runtime, model provider, hosting platform,
identity service, or operator authority.

The portable kernel has five boundaries:

```text
evidence sources → observation adapters → accepted loop model
                                             │
                                             ▼
                                   compiler and policy kernel
                                             │
                       ┌─────────────────────┼─────────────────────┐
                       ▼                     ▼                     ▼
               execution adapters        Atlas             evolution proposals
```

Git inspection, the local file-backed runner, and the generic SDLC model are
shipped adapters and examples. They demonstrate the kernel; they do not define
its product boundary.

Every transformation persists a new artifact. Later artifacts cite exact
digests instead of rewriting earlier evidence.

## 2. Knowledge and authority

Concord Loom separates what the system knows from what an operator authorizes:

| State | Meaning | May authorize execution? |
|---|---|---|
| `observed` | Direct evidence from a declared source | No |
| `inferred` | A deterministic or model-assisted hypothesis | No |
| `confirmed` | An operator accepted the proposed meaning | After compilation |
| `rejected` | An operator rejected the proposal | No |
| `runtime_verified` | Bound evidence met a declared predicate | Only within that predicate |

Observations retain provenance. Inferences retain confidence and their source
references. Acceptance overlays append-only decisions; it never rewrites an
inference as an observation. Confidence helps rank questions, but grants no
capability.

The artifact chain is one-way:

```text
observations → questions → decisions → accepted intent
             → loop-design proposal → design acceptance
             → registry and binding proposal → binding activation
             → run facts and evidence → successor proposal
```

## 3. Two graphs define a loop system

### 3.1 Containment

`contains(parent_loop, child_loop)` means a composite parent state invokes a
child through a typed contract. The containment graph must be finite and
acyclic. A child cannot contain an ancestor.

Containment supports recursive navigation and repeated use of the loop
contract pattern. It never authorizes unbounded runtime recursion.

### 3.2 Local control flow

Each loop has a directed state graph. Forward and feedback transitions are
allowed. Every cyclic strongly connected component must consume a finite,
monotonic budget; exhaustion must lead to a terminal or escalation outcome.

```text
prepare → act → inspect → decide ──accept──► ACCEPTED
            ▲       │          │
            └─retry─┘          └──────────► ESCALATED
```

Continuous activity becomes a sequence of bounded runs. One run ends; a later
signal may start another.

### 3.3 Loop contract

A loop is:

```text
L = (I, O, S, δ, C, E, A, B, X)
```

- `I`, `O`: typed input and output descriptions;
- `S`, `δ`: states and declarative local transitions;
- `C`: child invocations and their mappings;
- `E`: evidence predicates;
- `A`: capabilities and independence rules;
- `B`: attempt, time, cost, and tool budgets;
- `X`: terminal outcomes.

The validator checks one entry, reachability, terminal paths, finite child
deadlines, bounded feedback, scope containment, and authority separation.
Predicates use a finite declarative grammar; they contain no executable code.

## 4. Adapters

### 4.1 Observation adapters

An observation adapter turns bounded source evidence into provenance-rich
facts and hypotheses. The v0.1 built-in adapter reads one local Git repository.
It records:

- tracked files, sizes, extensions, and language categories;
- conventional build, test, CI, decision, documentation, and agent surfaces;
- lightweight local Python import edges;
- commit identity, timestamps, churn, authors, renames, and co-change; and
- coverage, truncation, and stable source references.

The v0.1 inspector does not parse JavaScript or TypeScript imports, synthesize
directory nodes, check out historical revisions, import target code, or run
repository hooks. It caps history depth, file count, bytes, subprocess time,
paths per commit, and co-change pairs.

Future adapters may observe other repositories, artifact stores, services, or
physical-process receipts. They must preserve the same fact/inference and
authority boundaries.

### 4.2 Execution adapters

The kernel validates contracts and records governed facts. An execution
adapter may use a workflow engine, CI, an agent graph, a local process, or a
mixed runtime. It must return candidate- and policy-bound evidence.

Concord Loom v0.1 validates local state machines and containment but does not
step every transition, schedule durable children, or derive parent acceptance
from a child status.

### 4.3 Projections

The Atlas is a deterministic, self-contained HTML projection of accepted
artifacts and optional run data. It shows containment separately from feedback
and keeps planned, actual, verified, and drift layers distinct. It is not a
source of truth or execution authority.

## 5. Negotiation and acceptance

Questions rank unresolved hypotheses by downstream impact and uncertainty.
Each question identifies its evidence, why the answer matters, and the graph
delta for each option.

An accepted model requires decisions for every blocking question. The actor
and capability resolve through content-addressed policy. A correction creates
a decision-backed replacement; it does not mutate the observation.

Loop design and binding activation have separate acceptance seams. The
compiler can reject an unsafe proposal, but it cannot approve one.

## 6. Compilation and binding

The binder consumes accepted intent, an accepted loop design, registry,
authority and routing policy, compute policy, and evolution policy. It
validates schemas and cross-artifact invariants, computes canonical SHA-256
digests, and emits a binding over those exact inputs.

Runs pin a binding digest. The catalog appends successor bindings and preserves
their predecessors. No component may resolve authority from an unpinned
“current workflow.”

Canonical JSON is deterministic UTF-8 with a trailing newline. Digest
envelopes exclude declared mutable display metadata.

## 7. Governed execution

A run card is the execution record for one objective:

```text
PENDING → AUTHORIZED → RUNNING → PASSED
                          ├────► REVISE
                          ├────► BLOCKED
                          └────► CANCELLED
```

Authorization checks dependencies, capabilities, budgets, and scope. `guard`
compares intended reads and writes with the node grant. It is a policy check,
not an operating-system sandbox.

An actual attempt records the effective principal, model and reasoning when
used, skill, subagents, tools, policy digest, candidate digest, times, and
terminal result. Evidence records its producer, predicate scope, candidate,
policy, provenance, checks, and payload digest.

Parent contracts choose which child receipts matter. A passing child never
closes its parent automatically. Independent gates reject a principal that
authored candidate content when policy requires separation. A passed gate
proves its evidence contract; it does not grant publication authority.

## 8. Concord Loom's development system

The active, operator-accepted configuration has root
`steward-concordloom`, ten responsibility areas, and 65 cycles in total. The
interactive Atlas projects that complete containment graph.

Ordinary run cards do not execute all 65 cycles. By default they contain only
the root coordinator. A task selects one or more leaves with `--target-loop`;
the route adds only their ancestors. `--portfolio` is an explicit full-system
audit mode.

Every governed run still uses seven phases:

| Stage | Contract outcome |
|---|---|
| Observe | Provenance-rich facts, hypotheses, and coverage |
| Negotiate | Accepted intent and append-only decisions |
| Bind | Separately activated loops, policy, and scope |
| Execute | A scoped candidate and factual attempt evidence |
| Verify | An independent receipt for the pinned candidate |
| Publish | An authorized effect, no-op receipt, or escalation |
| Evolve | A non-activating successor proposal |

The development configuration succeeded the earlier seven-loop example through
explicit operator decisions recorded in the append-only catalog. It governs
Concord Loom itself; other projects may accept different topologies.

## 9. Evolution

Signals are append-only observations about repeated friction, drift, failure,
or cadence. A reducer may deduplicate them and propose a graph or policy delta.
Every proposal identifies its base binding, source signals, preconditions,
risk, and required authority.

```text
binding vN → runs → signals → proposal
       └──────── defines who may decide ────────┘
```

The reducer cannot edit the catalog. The proposal cannot authorize or activate
itself. A separate decision under `vN` must accept the proposal before the
binder can create and activate `vN+1`; stale preconditions fail closed.

## 10. Modules

```text
src/concordloom/
  canonical.py       deterministic JSON and digests
  schema.py          public schema validation
  graph.py           observations and decision overlays
  inspect_repo.py    built-in Git observation adapter
  interview.py       question ranking and decisions
  loops.py           containment and control-flow invariants
  compiler.py        accepted model to binding
  run.py             governed execution lifecycle
  atlas.py           offline projection
  evolution.py       signal reduction and proposals
  cli.py             stable command surface
```

Python 3.11 and the standard library form the portable core. The built-in
schema validator implements the deliberately small JSON Schema subset used by
the shipped schemas and rejects unsupported keywords.

## 11. Security and v0.1 limits

The Git adapter normalizes paths beneath its root, observes but does not follow
external symlinks, disables interactive and executable Git features, and
exposes dirty or truncated coverage. Model-assisted output remains untrusted
until schema and invariant checks pass. The portable core performs no implicit
network egress.

The first public release remains a complete local vertical slice: one local
Git observation adapter, one accepted binding at a time, deterministic JSON,
an offline Atlas, and file-backed runs. These are v0.1 implementation limits,
not universal ontology.

The first release used a separate bootstrap trust-seed protocol under
`concord/`. Public projects use `schemas/run-card.schema.json` and an accepted
binding. Bootstrap cards must never be represented as public v0.1 run cards.
