# Concord Loom repository rules

Concord Loom is an engine-agnostic framework for discovering, negotiating,
executing, visualizing, and evolving bounded systems of development loops.

## Product boundary

- Do not make a game engine, hosting platform, model provider, or repository
  layout mandatory.
- Repository history is evidence, not product intent. An inferred graph cannot
  become accepted without an operator decision.
- Keep observed, proposed, accepted, planned, actual, and verified facts
  distinct.
- The containment graph is finite and acyclic. Local control flow may contain
  feedback edges only when retry budgets and terminal outcomes are explicit.
- Evolution may propose a successor binding; it cannot authorize itself.

## Governance

The first commit is the transparent trust seed: repository rules, license,
packaging metadata, the bootstrap cycle, its runner, and tests. This one-time
bootstrap is the only mutation exempt from a run card.

After that commit, every mutation requires a run card under
`.concord/runs/<run-id>/run-card.json`. Before reading task-scoped files, run:

```bash
python3 tools/concord_run.py guard --card <card> --node <node>
```

Before writing, also pass every intended path with `--write-path`. Executors
must stay within the scope recorded for their node. Review and release nodes are
read-only and cannot certify work authored by the same agent.

`PASSED` means the node's declared evidence contract was met for its pinned
candidate. It is not release authority. A run is complete only when:

```bash
python3 tools/concord_run.py complete --card <card>
```

The first release uses the explicitly separate
`concord/bootstrap-run-card.schema.json` trust-seed protocol. Bootstrap run
cards and post-release signals are mutable receipts under ignored
`.concord/runs/` and `.concord/signals/`; they are not source-candidate bytes.
Public projects use `schemas/run-card.schema.json`, which is bound to an
accepted registry, policy, binding, and candidate manifest. Never represent a
bootstrap card as a public v0.1 run card.

## Engineering

- Python 3.11+ and the standard library are the portable core.
- Keep durable graph and policy rules separate from CLI presentation.
- JSON files are canonical, deterministic, UTF-8, and newline terminated.
- Add tests for graph invariants, authority boundaries, candidate binding, and
  every bug fixed.
- Generated Atlas output is a projection of accepted/run data, never an
  independent source of truth.
