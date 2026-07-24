# Core concepts

## A cycle of cycles

An SDLC is an outer feedback loop whose apparent phases are themselves loops.
Requirements revises hypotheses. Design evaluates alternatives.
Implementation edits and repairs. Testing plans and interprets scenario runs.
Release builds and smokes exact artifacts. Operations observes bounded windows
and turns findings into new intent.

Testing can contain contract, migration, security, and performance loops. A
scenario can contain setup or diagnosis loops. Concord Loom applies one
contract pattern at every level while keeping concrete nesting finite.

## Containment is not feedback

Concord Loom stores two different graphs:

- `contains(parent, child)` is a finite, acyclic refinement relation. It gives
  nested execution a maximum depth.
- A loop's local state graph may contain feedback. Each cyclic strongly
  connected component must decrease a finite attempt, time, cost, or tool
  budget and retain a path to termination or escalation.

Calling both relationships “recursion” hides the safety property. The Atlas
renders them differently.

## A loop contract

A loop defines:

- typed input and output descriptions;
- a single entry, states, declarative transitions, and terminal outcomes;
- child invocations with input/output mapping, deadline, and cancellation;
- evidence predicates;
- required capabilities and independence rules;
- attempt, time, cost, and tool budgets; and
- escalation when the loop cannot finish safely.

The validator rejects cyclic containment, unreachable states, nonterminal dead
ends, unbudgeted feedback, budget exhaustion without an exit, child authority
broader than its parent, and author self-certification where independence is
required.

## A child receipt is not a parent decision

The contract model requires a child to report a result scoped to its input,
candidate, policy, producer, and evidence. Its parent evaluates that receipt
against the parent's own contract.

A migration scenario can pass while a testing campaign remains open. A testing
campaign can pass while release remains unauthorized. This rule prevents a
green inner status from silently expanding its meaning.

The v0.1 runner records attempts and evidence per planned loop node. It does
not synthesize child receipts, traverse every local transition, or launch a
durable child workflow. An execution adapter must supply the relevant
candidate-bound evidence to the parent; the parent's own completion check
remains authoritative.

## Epistemic states

Concord Loom keeps these states distinct:

| State | Meaning |
|---|---|
| Observed | Derived from repository bytes or Git records |
| Inferred | A heuristic hypothesis with provenance and confidence |
| Accepted | Explicit operator intent |
| Planned | Intended route, scope, model, skill, or reviewer |
| Actual | What a runtime attempt recorded |
| Verified | Evidence satisfied a bound contract |
| Drift | Planned and actual facts differ |

Confidence helps rank a question. It never grants authority.

## Three acceptance seams

The operator accepts three different meanings:

1. **Project intent:** decisions overlay an observed graph.
2. **Loop design:** an exact proposal digest becomes an accepted design.
3. **Binding activation:** an exact compiled proposal becomes active.

Collapsing these seams would let an inference or compiler output authorize
itself.

## Candidate and evidence identity

A candidate manifest covers tracked and explicitly selected untracked paths,
content, modes, symlink targets, submodule commits, repository revision, and
inventory. The runner rechecks the candidate at evidence and completion
boundaries.

Evidence names the candidate, policy, factual attempt, producer, result,
payload digest, provenance, and checks. Identical evidence IDs do not permit
substituting different bytes.

## Binding and catalog

A binding names exact accepted graph, decision log, design proposal, accepted
design, registry, and policy digests. A run pins a binding digest, not the word
“current.”

The catalog is append-only. Activating a successor preserves prior bindings so
historical runs keep their original meaning.

## Evolution is another governed loop

Runs produce bounded signals about friction, failures, drift, or cadence.
Signals can reduce into an evolution proposal with preconditions and risk.
They cannot edit the active catalog.

The active version defines who may accept its successor. An evolution proposal
cannot grant itself that capability or activate itself.
