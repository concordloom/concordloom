# Concord Loom v0.1 architecture

## 1. System boundary

Concord Loom is a compiler and governance harness around repository evidence.
It does not replace a compiler, semantic index, workflow runtime, CI system, or
human product authority.

```text
Git repository
    │
    ▼
Inspector ──► observed graph ──► ranked questions
                                      │
                                      ▼
                              decision records
                                      │
                                      ▼
accepted project graph ──► proposed loop design ──► operator acceptance
                                                       │
                                                       ▼
accepted loop design + policies ──► binder ──► content-addressed binding
                                                   │
                         ┌─────────────────────────┼───────────────┐
                         ▼                         ▼               ▼
                     run cards                 Atlas          evolution
```

Every arrow produces a persisted artifact. Later stages refer to exact
digests; they do not overwrite the meaning of earlier evidence.

## 2. Artifact states

Project knowledge uses explicit epistemic states:

| State | Meaning | May authorize execution? |
|---|---|---|
| `observed` | Directly derived from repository bytes or Git records | No |
| `inferred` | A deterministic heuristic proposed a meaning | No |
| `confirmed` | An operator accepted the proposed meaning | Yes, after compile |
| `rejected` | An operator rejected the proposal | No |
| `runtime_verified` | A bound execution produced contract-valid evidence | Only for its evidence scope |

Edges carry `source_refs`, `first_seen`, `last_seen`, `weight`, `confidence`,
and optional `decision_id`. Confidence is a ranking aid, not authority.

The inspector emits observations and hypotheses. `accept` overlays immutable
decision records to produce an accepted view. It never rewrites an inference
as if it had always been observed. Artifact references form a one-way chain:
observed graph → decision log → accepted graph → loop-design decision →
binding. Two content-addressed documents never contain each other's digest.

## 3. Two graphs define a loop system

Calling every hierarchy a “recursive cycle” hides an important distinction.
Concord Loom stores two graphs.

### 3.1 Containment

`contains(parent_cycle, child_cycle)` means a composite state in the parent
invokes the child using a typed contract. The containment graph must be finite
and acyclic. A child cannot directly or indirectly contain an ancestor.

This graph supports recursive navigation and recursive application of the loop
contract pattern. It does not authorize unbounded runtime recursion.

### 3.2 Local control flow

Each cycle has a directed state graph. Forward and feedback transitions are
both allowed. Every cyclic strongly connected component must consume a finite,
monotonic budget. Exhausting that budget must lead to a terminal outcome or an
escalation state.

```text
testing:
  plan → execute → interpret → decide ──pass────► ACCEPTED
                    ▲          │
                    └─retest── diagnose
                                 │
                                 └─budget exhausted──► ESCALATED
```

Continuous activities are modeled as a sequence of bounded runs. An operation
window or incident ends; a later signal can create a new run.

### 3.3 Loop contract

A loop is:

```text
L = (I, O, S, δ, C, E, A, B, X)
```

- `I`, `O`: human-readable typed input and output contracts;
- `S`: states;
- `δ`: local transitions;
- `C`: child-cycle invocations attached to composite states;
- `E`: evidence predicates;
- `A`: actor capabilities and independence requirements;
- `B`: attempt, time, cost, and tool budgets;
- `X`: terminal outcomes such as `ACCEPTED`, `REVISE`, `ESCALATED`, and
  `CANCELLED`.

The validator checks a single entry, state references, reachability, and a path
from every reachable nonterminal state to a terminal or escalation. It rejects
nonterminal dead ends. Every child invocation needs a finite deadline and a
cancellation or escalation path. The validator proves structural invariants;
it cannot prove that a human judgment was wise.

Transitions use a finite declarative grammar: named events, state or terminal
targets, optional child receipts, and receipt requirements over producer
capability, candidate/policy digest equality, allowed result, and minimum count.
No predicate contains executable code.

## 4. Repository inspection

v0.1 uses only Git and repository bytes.

### Structural observations

- tracked files, sizes, extensions, and language categories;
- conventional build, test, CI, decision, documentation, and agent surfaces;
- lightweight import edges between tracked local Python modules; and
- repository-relative paths on file nodes.

JavaScript and TypeScript files receive language categories, but v0.1 does not
parse their imports. It also does not synthesize directory nodes or directory
containment edges. Those are explicit future adapter opportunities rather than
facts in the observed graph.

### Historical observations

- commit identity and timestamps;
- file churn and distinct author counts;
- rename records;
- weighted file co-change edges.

Co-change is computed over commits within configured limits. Generated,
vendored, binary, and oversized files are excluded from semantic hints but
remain visible as files. Every metric records its command-free source
reference, such as a commit and path.

The v0.1 inspector never checks out historical revisions and never executes
repository code. Git calls disable hooks, pagers, prompts, optional locks,
external diff/text conversion, replace objects, and fsmonitor where applicable.
History depth, file count, bytes read, paths per commit, subprocess bytes and
time, and co-change pairs have explicit caps. Coverage and truncation are
visible and must be acknowledged before acceptance.

### Determinism

The revision identity, configuration, stable path ordering, and canonical JSON
encoding define inspector output. A canonical digest envelope contains
`schema_version`, `artifact_kind`, and `payload`. Wall-clock invocation
timestamps and display metadata live outside the payload and are excluded from
its digest.

## 5. Interview and acceptance

Question ranking favors decisions that would change the most downstream loop
or ownership edges. A question contains:

- the hypothesis;
- evidence references and confidence;
- why the answer matters;
- mutually exclusive answer identifiers;
- an explicit graph delta for each answer;
- whether it blocks compilation.

v0.1 ranks by the number of proposed graph operations, then confidence
uncertainty, then stable question ID. Rejected hypotheses stay visible with
their decision reference; unresolved non-blocking hypotheses stay inferred and
cannot grant authority.

The CLI does not impersonate a conversational UI. It emits portable question
JSON and accepts explicit decision arguments or decision files. A Codex skill
provides the conversational layer.

An accepted graph is valid only when all blocking questions have decisions and
their actor/rationale fields are present. Actor IDs and the `accept_intent`
capability resolve through a content-addressed authority policy. A correction
creates a replacement edge with decision provenance; it does not mutate the
observed edge.

## 6. Compilation and binding

The proposal stage consumes an accepted project graph and emits a loop-design
delta. Its confidence supplies no authority. The binder consumes:

- an accepted project graph;
- a loop registry whose digest has an authorized acceptance decision;
- an authority/routing policy;
- a compute-intent policy;
- an evolution policy.

It validates every public artifact against its JSON Schema, checks cross-file
invariants, computes canonical SHA-256 digests, and emits a binding containing
those digests. Runs pin a binding digest, never the word “current.”

A catalog is append-only: a new binding adds a successor entry. Prior entries
and their artifacts remain addressable.

## 7. Execution model

A run card is the source of execution state for one objective.

```text
PENDING → AUTHORIZED → RUNNING → PASSED
                          ├────► REVISE
                          ├────► BLOCKED
                          └────► CANCELLED
```

Authorization checks dependency outcomes and scope. `guard` rejects reads and
writes outside the node grant. It is a policy check, not an operating-system
sandbox; callers that need hostile-code isolation must add one.

The active binding grants the runner a narrow control-plane capability to
create cards and append authorization, attempt, evidence, and completion
events. This is distinct from candidate write scope. A reviewer can be
read-only with respect to candidate files while the runner records the review
receipt. The transparent bootstrap binding grants this lane for the first full
run.

An actual attempt records:

- effective executor and independent-review identity;
- model and reasoning when a model was used;
- skill, subagents, and tool versions;
- policy digest and candidate tree digest;
- start/end and terminal result.

Evidence is structured and content-addressed. It states its producer, candidate
digest, policy digest, scope, result, provenance, and checks. A parent contract
chooses which child receipts are necessary and evaluates its own predicates.

The v0.1 runner treats each planned loop node as a governed execution unit. It
validates the declared local state graph but does not step each transition or
schedule child workflows. A workflow, CI, agent, or local adapter executes the
child and supplies its candidate-bound result to the parent's evidence
contract. The runner never promotes a child status into parent acceptance.

Independent gates reject an executor identity that authored candidate content.
Release readiness and the external authority to publish remain separate.

Candidate identity is a canonical manifest of selected tracked and explicitly
included untracked paths, file modes, symlink targets, and submodule commits.
The runner rechecks the manifest digest when evidence is recorded and a gate
completes. Identity and capability claims resolve through the bound authority
policy; arbitrary strings are not authenticated principals. Protecting policy
and run files from a hostile local writer requires OS or VCS enforcement
outside the portable core.

## 8. Atlas

The Atlas renderer reads accepted binding artifacts and, optionally, one run
card. It emits a self-contained HTML document with no network dependencies.

The primary view shows one containment level. Selecting a composite state
descends into its child cycle; breadcrumbs and browser history preserve
location. Local transitions use a different visual vocabulary from containment.

Plan and fact are never merged:

- **planned** comes from the binding and run card route;
- **actual** comes from recorded attempts;
- **verified** requires candidate-bound evidence;
- **drift** is a visible comparison, not an implicit correction.

The renderer is deterministic and the CLI supports `--check` to detect stale
generated output.

## 9. Evolution

Signals are append-only, source-addressed observations about repeated friction,
drift, failure, or cadence. The reducer deduplicates them and may emit a
proposed graph diff with supporting signal IDs.

```text
binding vN → runs → signals → proposal
       └──────── defines who may accept ────────┘
```

Every proposal names `base_binding_digest`, contributing signal digests, and
per-operation precondition digests. The reducer cannot edit the active catalog.
A decision under `vN` must accept the proposal before a binder can create
`vN+1`; stale preconditions fail closed. Historical runs remain pinned to their
original binding.

## 10. Modules

```text
src/concordloom/
  canonical.py       deterministic JSON and digests
  schema.py          public schema validation
  graph.py           project graph and decision overlays
  inspect_repo.py    safe repository/Git inspection
  interview.py       question ranking and decisions
  loops.py           containment/control-flow invariants
  compiler.py        accepted model to binding
  run.py             governed execution lifecycle
  atlas.py           offline HTML renderer
  evolution.py       signal reduction and proposals
  cli.py             stable command surface
```

The core is standard-library only. JSON Schema validation implements the
deliberately small keyword subset used by shipped schemas; unsupported schema
keywords fail closed. External full-schema validators may be used as an
additional check.

## 11. Security and trust

- Inspection uses argument-vector subprocess calls and does not invoke a shell.
- Paths are normalized beneath the selected repository root.
- Scope prefixes match complete path components, not string prefixes. Paths are
  stored as UTF-8 with explicit rejection metadata for names that cannot be
  represented safely.
- Symbolic links are observed but not followed outside the root.
- No repository code, hooks, build scripts, or CI files are executed by
  inspection.
- Artifact digests exclude mutable filesystem metadata.
- Inspection reports tracked, untracked, ignored, and dirty coverage. Binding a
  dirty or truncated snapshot requires an explicit operator acknowledgement;
  release policy may reject it outright.
- Model-assisted output is untrusted input until schema and invariant checks
  pass.
- Secrets and file contents are not included in the graph by default.
- The portable core has zero network egress. Model-assisted skills obey a bound
  data policy for allowed paths, content classes, providers, and privacy; the
  actual egress route and content scope are recorded.
- The Atlas escapes all repository-controlled text and ships a restrictive
  content-security policy.

## 12. v0.1 constraints

The first release intentionally favors a complete, inspectable vertical slice:
one local Git repository, one accepted binding at a time, deterministic JSON,
an offline Atlas, and file-backed runs. Adapters may later provide deeper
semantic graphs, hosted coordination, or durable workflow execution without
changing the core authority model.
