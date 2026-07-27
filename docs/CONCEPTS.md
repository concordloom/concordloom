# Core concepts

[Русская версия](ru/CONCEPTS.md)

Concord Loom models a bounded system as loops that contain other loops. It
does not prescribe a domain, engine, runtime, provider, or repository layout.
A software development life cycle (SDLC) is one possible binding of the model,
not the identity of the framework.

## A system of bounded loops

A loop turns a declared input into a terminal outcome under evidence,
authority, scope, and budget constraints. A parent loop may refine one of its
states through a child loop. The same contract pattern applies at every level,
but the resulting system remains finite.

The shipped generic SDLC binding illustrates this pattern with requirements,
implementation, testing, release, and operations. Another binding could govern
research, content production, hardware qualification, incident response, or a
mixed human-and-machine process without changing the core model.

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

A child reports a result scoped to its input, candidate, policy, producer, and
evidence. Its parent evaluates that receipt against the parent's own contract.

A scenario can pass while its campaign remains open. A campaign can pass
while publication remains unauthorized. A valid child receipt supplies
evidence; it never expands authority or closes its parent automatically.

The v0.1 runner records attempts and evidence per planned loop node. It does
not synthesize child receipts, traverse every local transition, or launch a
durable child workflow. An execution adapter supplies candidate-bound evidence
to the parent, whose completion check remains authoritative.

## Epistemic states

Concord Loom keeps these states distinct:

| State | Meaning |
|---|---|
| Observed | Derived directly from declared evidence sources |
| Inferred | A hypothesis with provenance and confidence |
| Accepted | Intent approved by an authorized operator |
| Planned | Intended route, scope, model, tool, or reviewer |
| Actual | What an attempt recorded |
| Verified | Evidence satisfied a bound contract |
| Drift | Planned and actual facts differ |

Observation adapters may read a Git repository, an artifact store, a service
API, or another bounded source. Confidence ranks questions; it never grants
authority.

## Acceptance seams

Three decisions carry different meanings:

1. **Intent acceptance:** decisions resolve consequential hypotheses.
2. **Loop-design acceptance:** an exact proposal digest becomes an accepted
   design.
3. **Binding activation:** an exact compiled proposal becomes active.

Collapsing these seams would let an inference, generator, or compiler authorize
its own output.

## Candidate and evidence identity

A candidate is the exact subject of a run. The built-in repository adapter
represents it as a canonical manifest of selected paths, content, modes,
symlink targets, submodule commits, revision, and inventory. Other adapters
must provide an equally stable identity contract.

Evidence names the candidate, policy, factual attempt, producer, result,
payload digest, provenance, and checks. Matching evidence IDs cannot justify
substituting different bytes or a different subject.

## Binding and catalog

A binding names exact accepted intent, decision log, accepted loop design,
registry, and policy digests. A run pins a binding digest, never the word
“current.”

The catalog is append-only. Activating a successor preserves prior bindings so
historical runs retain their original meaning.

## Concord Loom's self-binding

Concord Loom governs its own bounded changes with an operator-accepted
self-binding:

```text
Observe → Negotiate → Bind → Execute → Verify → Publish → Evolve
```

- **Observe** separates facts from inferred intent.
- **Negotiate** records operator decisions.
- **Bind** compiles and separately activates exact loops, policy, and scope.
- **Execute** produces a scoped candidate and factual attempt evidence.
- **Verify** independently evaluates the pinned candidate.
- **Publish** performs only an explicitly authorized external effect, or
  records that no effect occurred.
- **Evolve** reduces pinned signals into a successor proposal.

This sequence is Concord Loom's accepted binding for its own repository. It is
not a mandatory topology for every project.

## Evolution cannot authorize itself

Runs produce bounded signals about friction, failure, drift, or cadence.
Signals may reduce into a proposal with explicit preconditions and risk. The
proposal cannot edit the active catalog or grant itself activation authority.

The active binding defines who may decide on its successor. A separately
authorized decision and activation create the next binding; otherwise the
current binding remains active.
