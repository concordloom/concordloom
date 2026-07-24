---
name: design-project-loops
description: Discover, negotiate, compile, execute, visualize, and evolve a repository-specific system of bounded development loops with Concord Loom. Use when Codex needs to analyze a Git repository and its history, distinguish observed evidence from inferred or operator-accepted intent, ask high-impact architecture or workflow questions, create or update a loop-system binding and offline Atlas, govern a run card, compare planned and actual routes, or propose evidence-backed process evolution without self-authorizing it.
---

# Design Project Loops

Treat repository history as evidence, never as product intent. Move through
persisted, digest-linked artifacts and stop whenever the required operator
authority, decision, scope, candidate identity, or evidence is absent.

Read [artifact-contract.md](references/artifact-contract.md) before accepting a
graph, compiling a binding, recording evidence, or proposing evolution. Read
[commands.md](references/commands.md) before invoking the v0.1 CLI.

## 1. Establish the boundary

1. Read repository instructions. Do not assume that a fresh repository already
   has a Concord Loom binding.
2. Run `python3 scripts/preflight.py --repo <repository>` from this skill
   directory. Report the resolved Git root, exact revision, dirty state, and
   CLI route. Treat a dirty or truncated snapshot as an explicit
   acceptance concern.
3. Use `python3 scripts/concordloom_cli.py` as the CLI entrypoint. It prefers
   the matching same-repository source and otherwise uses an installed command.
   If neither exists, use its emitted `install_argv` for this plugin's matching
   release, rerun preflight, then inspect `--help` and subcommand help. Never
   guess flags or edit canonical JSON to imitate success.
4. Determine who may accept intent, authorize runs, review candidates, activate
   bindings, and publish releases. The skill itself grants none of these
   capabilities.

### Fresh repository bootstrap lane

When preflight reports `mode=bootstrap-discovery`, use this explicit
zero-authority, read-only lane instead of failing circularly on a missing
binding:

1. Keep all generated observations, questions, policy drafts, and design drafts
   outside the repository, in an operating-system temporary directory.
2. Stay within the preflight caps: three 15-second Git identity/status calls,
   1 MiB per Git stream, at most 10,000 status entries, zero repository writes,
   zero network calls, and zero external mutations.
3. Run only read-only inspection and question generation. Never run repository
   code, authorize a run, mutate a catalog, claim a capability, or treat an
   inference as accepted intent.
4. Present one bootstrap packet: revision and coverage, observed graph digest,
   unresolved questions, proposed policy/loop deltas, exact first-binding
   outputs, and the authority that the first binding would grant.
5. Stop for explicit operator acceptance. The lane grants no authority. A
   directly accepted, recorded bootstrap decision authorizes only the stated
   first-binding writes; creating that binding ends bootstrap.
6. Rerun preflight with `--binding <exact-path>`, validate the first binding,
   and use normal bound governance for every later mutation.

If the operator does not accept the packet, leave the repository byte-for-byte
unchanged. A first binding cannot approve its own creation retroactively.

## 2. Discover the project graph

Run the launcher's `inspect` command against the selected repository and
preserve its output as the observed project graph. In bootstrap discovery,
write it only to the temporary directory. Verify the pinned revision, coverage,
limits, ignored/untracked handling, and truncation markers before interpreting
it.

Keep each claim in its emitted state:

- `observed`: directly derived from repository bytes or Git records;
- `inferred`: a heuristic interpretation awaiting a decision;
- `confirmed` or `rejected`: an operator decision with provenance;
- `runtime_verified`: evidence valid only for its recorded scope and candidate.

Never relabel confidence as authority. Never execute repository code merely to
inspect it.

## 3. Negotiate intent

Generate ranked questions with the launcher's `questions` command. Ask one blocking,
high-information question at a time. Phrase it in product outcomes, ownership,
or evidence expectations; do not ask the operator to choose files, models,
tools, reviewers, or internal routing.

For every question show:

- the hypothesis and whether it is observed or inferred;
- source references, confidence, and coverage caveats;
- why the decision matters;
- the exact graph operations for every answer;
- the resulting added, removed, or corrected nodes and edges;
- whether the unresolved decision blocks acceptance.

Record the chosen answer with the launcher's `decide` command, including actor and
rationale. If a free-form answer does not map unambiguously to one delta, show
the proposed mapping and obtain confirmation before recording it.

Run the launcher's `accept` command only after all blocking questions have decisions and
the acting principal has the required intent capability. Preserve rejected
hypotheses and correction provenance; do not rewrite history.

## 4. Design and bind the loop system

Run the launcher's `propose` command from the accepted project graph. Present its loop
design as another explicit delta before acceptance. Distinguish:

- finite, acyclic containment between parent and child loops; and
- local feedback control flow with explicit retry, time, cost, or tool budgets.

Require every loop to state inputs, outputs, states, transitions, child
contracts, evidence, authority, budgets, escalation, and terminal outcomes.
Require a separate operator decision over the proposed design digest.

Run the launcher's `compile` command only with the accepted graph, the exact
loop-design proposal, its separately accepted manifest, and explicit policies.
Compilation emits a registry and non-authoritative binding proposal. Present
that proposal digest, then run `activate` only as a separate capable operator
decision with rationale. Let the compiler reject ancestor containment,
unbounded feedback, dead ends, authority escalation, missing child deadlines,
or self-review. Do not weaken a contract just to make compilation pass.

## 5. Generate and inspect the Atlas

Generate the offline Atlas with the launcher's `atlas` command from the exact accepted
binding and, when applicable, a run card. Verify its deterministic check mode.
Inspect recursive navigation, breadcrumbs, containment versus feedback flow,
authority, budgets, evidence, terminal outcomes, and
planned/actual/verified/drift distinctions. Treat the Atlas as a projection,
never as authority or a trace database.

## 6. Govern execution

Create and mutate run cards only through the launcher's `run` commands. Pin the
binding and candidate manifest. Before task inspection or mutation, authorize
the node and run its scope guard for every read and write path.

Record the effective route, not only routing intent: principal/agent, model and
provider, reasoning when used, skill, subagents, tools, egress, network and
external mutations, elapsed time, cost, policy digest, candidate digest, and
terminal result. Attach structured, candidate-bound evidence and verify its
payload against real bytes through the declared payload root. Keep
`planned`, `actual`, and `verified` separate and display drift explicitly.

Do not infer parent acceptance from child success. Do not let an author certify
an independent gate. Do not call a run complete while any required gate,
candidate match, or publication authority is missing.

## 7. Propose evolution

Append content-addressed friction, drift, cadence, and failure signals. Run the
launcher's `evolve` command only to produce a proposed diff against an exact base
binding. Show contributing signals, graph operations, and stale-precondition
checks.

Never activate an evolution proposal automatically. Require an explicit
decision from authority bound by the base version, then compile and activate a
successor through the normal governed path. Preserve all prior bindings and
run identities.

## Fail closed

Stop with a concrete missing requirement instead of improvising when:

- repository instructions cannot be resolved, or a claimed binding cannot be
  validated (a genuinely absent binding enters the bounded bootstrap lane);
- inspection coverage is insufficient and unacknowledged;
- an inferred edge lacks an operator decision;
- the acting principal lacks a required capability;
- a path is outside the run-card scope;
- containment, budget, escalation, or independence invariants fail;
- effective-route or candidate-bound evidence is incomplete;
- an evolution proposal is stale or lacks separate acceptance;
- release readiness is mistaken for publication authority.

End with artifact paths and digests, unresolved decisions, exact checks run,
the candidate identity, and the next authority boundary. Avoid claiming that a
generated file, passing child loop, or confidence score proves acceptance.
