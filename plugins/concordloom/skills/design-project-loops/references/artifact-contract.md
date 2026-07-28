# Concord Loom artifact and authority contract

Use this reference when accepting intent, compiling a binding, governing a run,
or proposing evolution.

## Artifact chain

Keep the chain directional and content-addressed:

```text
repository snapshot
  -> observed project graph
  -> ranked questions
  -> append-only decisions
  -> accepted project graph
  -> proposed loop-design delta
  -> loop-design acceptance
  -> compiled registry and binding proposal
  -> separate activation decision
  -> active binding and append-only catalog entry
  -> run cards and Atlas
  -> evolution signals
  -> successor proposal
```

Do not overwrite an earlier artifact to make a later conclusion appear
observed. Store mutable display metadata outside canonical digest payloads.

Communication and presentation locale are display metadata. Keep them outside
canonical graph, policy, binding, candidate, and evidence payloads unless an
accepted schema explicitly makes locale part of that artifact. A translated
projection must preserve machine identifiers, exact values, and digests.

## Epistemic states

| State | Basis | Grants authority |
|---|---|---|
| `observed` | Repository bytes or Git records | No |
| `inferred` | Deterministic heuristic | No |
| `confirmed` | Explicit, capable operator decision | Only after binding |
| `rejected` | Explicit operator decision | No |
| `runtime_verified` | Candidate-bound evidence contract | Only for its scope |

Confidence ranks questions. It cannot promote `inferred` to `confirmed`.

## Graph delta presentation

Before requesting a decision, present each answer as operations such as:

```json
{
  "answer_id": "confirm-test-ownership",
  "operations": [
    {
      "op": "confirm_edge",
      "edge_id": "owns:quality:tests"
    },
    {
      "op": "add_loop_candidate",
      "loop_id": "verification"
    }
  ]
}
```

State which nodes or edges are added, removed, corrected, or left unresolved.
Name the source references and the expected downstream loops or authority
grants affected. Record actor and rationale with the decision.

## Two graph types

Containment describes a finite hierarchy of loop contracts. It must be a DAG:
a child cannot contain an ancestor.

Local control flow describes states and transitions within one loop. Feedback
edges are allowed only when every cyclic strongly connected component consumes
a finite monotonic budget and exhaustion reaches a terminal or escalation.

Never use “recursive” to imply unbounded runtime recursion. It means that the
same loop-contract pattern and Atlas navigation apply at multiple levels.

## Planned, actual, and verified

- Planned route: intent recorded before execution.
- Actual route: effective principal, model/reasoning, skill, subagents, tools,
  and policy used.
- Verified result: structured evidence matching the candidate and policy
  digests and the gate's evidence predicate.
- Drift: a visible difference between planned and actual facts.

Do not merge these states. A child receipt is input to a parent's decision; it
does not automatically accept the parent.

## Authority boundaries

Resolve capabilities through the bound policy rather than accepting free-text
claims. Keep at least these decisions distinct:

- accept project intent;
- accept a proposed loop design;
- authorize execution;
- author candidate content;
- independently review a pinned candidate;
- declare release readiness;
- publish externally;
- accept and activate a successor binding.

The runner may have a narrow control-plane capability to append run events
while the candidate remains read-only. This does not grant candidate write or
publication authority.

## Evolution

An evolution reducer may aggregate repeated, content-addressed signals into a
proposal. The proposal must include:

- exact base binding digest;
- contributing signal digests;
- graph operations;
- per-operation precondition digests;
- a decision requirement under the base binding.

Never let the proposer accept or activate its own change. Reject stale
preconditions and preserve historical bindings.
