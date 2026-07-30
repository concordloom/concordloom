---
name: design-project-loops
description: Discover, negotiate, compile, execute, visualize, and evolve a repository-specific system of bounded development loops with Concord Loom. Use when Codex needs to analyze a Git repository and its history, distinguish observed evidence from inferred or operator-accepted intent, ask high-impact architecture or workflow questions, create or update a loop-system binding and offline Atlas, govern a run card, compare planned and actual routes, or propose evidence-backed process evolution without self-authorizing it.
---

# Design Project Loops

Treat repository history as evidence, never as product intent. Move through
persisted, digest-linked artifacts and stop whenever the required operator
authority, decision, scope, candidate identity, or evidence is absent.

Make this skill the conversational onboarding entrypoint. Do not ask a new
user to install the CLI, create temporary directories, or choose artifact
commands before preflight establishes what is needed.

## 0. Learn how to address the person

Before reading repository files or running preflight, ask which language to
use. After the answer, ask what name to use in the conversation and Atlas.
Ask these two short questions one at a time.

> Which language should I use for our conversation and generated
> human-readable materials: English or Russian?

Do not infer the answer from the user's operating system, location, repository
content, or first message. Wait for an explicit choice. Keep it as
`communication_locale` for the onboarding session:

- `en`: communicate in English and generate the Atlas with `--locale en`;
- `ru`: communicate in Russian and generate the Atlas with `--locale ru`.

Use the chosen language for questions, explanations, summaries, decision
rationales drafted for the operator, Atlas UI, and other human-readable
projections. Keep commands, paths, JSON keys, schema values, loop IDs, model
IDs, digests, and exact evidence in their original machine spelling.

Keep the supplied name as display-only session metadata. Derive a machine
identifier internally if an artifact needs one. Never show placeholders such
as `current-operator`, `example-operator`, or an authority reference as the
person's name.

Language is presentation metadata. It does not accept product intent, grant
authority, change canonical digests, or create a second machine contract.
Keep the choice outside canonical candidate bytes unless an accepted project
policy explicitly defines a default presentation language. If the requested
language is not supported by the Atlas renderer, explain that limitation and
ask the operator to choose `en` or `ru` for generated Atlas output.

### Russian editorial dependency

When `communication_locale=ru`, load the companion `ru-text` skill before the
first Russian operator-facing message. Use the pinned upstream release
`talkstream/ru-text@v1.10.1`.

- Apply its typography rules to every Russian message.
- Apply `ux-writing.md`, `anti-patterns.md`, and `addenda.md` to onboarding,
  Atlas copy, errors, hints, buttons, and generated summaries.
- Apply `info-style.md`, `anti-patterns.md`, and `addenda.md` to documentation
  and long explanations.
- Use `scoring.md` for the final contextual review of public Russian prose.
- Keep exact commands, paths, JSON keys, schema values, loop IDs, model IDs,
  digests, and evidence spellings in code formatting.

If `ru-text` is unavailable, explain that Russian editorial quality depends on
an external skill and ask before installing the exact pinned release. Never
download or install it silently. Until it is available, do not claim that the
Russian editorial gate passed.

For governed model-assisted work, declare `ru-text@v1.10.1` in the planned and
effective skill route whenever Russian human-facing text is produced or
reviewed. A surface linter does not replace the contextual editorial review.

## Speak plainly and keep the conversation moving

Write for an operator who has never seen Concord Loom. Lead with the practical
meaning, not the framework term. Never mix untranslated English prose into a
Russian sentence or untranslated Russian prose into an English sentence.

Keep machine spellings only when the operator needs an exact command, path,
JSON key, status value, digest, or identifier. Put optional implementation
details after the plain explanation under a short “Technical details” or
“Технические детали” label. Do not make the operator decode terms such as
`governed delivery boundary`, `epistemic state`, `graph delta`, `raw impact`,
`nodes/edges`, or `project intent`.

Translate their meaning in context:

- `governed delivery boundary`: which work shares one set of development,
  verification, and release rules;
- `inferred`: a system hypothesis that the operator has not confirmed;
- `confidence`: how strong the available evidence is, not probability of
  truth;
- `raw impact`: how much of the proposed project map this answer may change;
- `nodes/edges`: project parts and the relationships between them;
- `epistemic state`: whether a claim is observed, proposed, accepted, actual,
  or verified;
- `project intent`: the operator-accepted understanding of the project.

After every step, ask exactly one next question or offer one concrete next
action. Do not end onboarding with a status report, artifact list, digest, or
“completed” message while a blocking operator decision remains. State what
needs deciding, why it matters, and provide plain answer choices. Preserve
exact machine values only as supporting detail.

Before sending any operator-facing message, apply the comprehension gate in
[operator-conversation.md](references/operator-conversation.md) or its
[Russian peer](references/operator-conversation.ru.md), according to the
chosen language. This gate applies to installation, discovery, negotiation,
design, activation, Atlas, execution, failures, completion, and evolution.
For Russian, apply the `ru-text` register rules after this comprehension gate
and before sending the message.
Do not paste CLI JSON or technical reference prose into the conversation.
Translate its meaning, then offer technical details only on request.

Read [artifact-contract.md](references/artifact-contract.md) before accepting a
graph, compiling a binding, recording evidence, or proposing evolution. Read
[commands.md](references/commands.md) before invoking the v0.1 CLI.
Read [model-routing.md](references/model-routing.md) before proposing the first
binding, creating a run card, or changing a route through evolution.
Read the matching operator-conversation reference before the first
operator-facing report or question.

## 1. Build the first Atlas without interviewing the person

1. Read repository instructions. Do not assume that a fresh repository already
   has a Concord Loom binding.
2. Run `python3 scripts/preflight.py --repo <repository>` from this skill
   directory. Report the resolved Git root, exact revision, dirty state, and
   CLI route. Treat a dirty or truncated snapshot as an explicit
   acceptance concern.
3. If preflight reports `ready=false`, present its `install_plan` in ordinary
   language. State that installation changes the user's environment and needs
   network access. Obtain explicit approval before executing every command in
   the plan. The launcher selects `pipx`, then `uv tool`, then an isolated
   managed virtual environment. Never use a system `pip`, never pass
   `--break-system-packages`, and never silently install the dependency.
4. Rerun preflight after installation. Use
   `python3 scripts/concordloom_cli.py` as the CLI entrypoint. It prefers the
   matching same-repository source, then an installed command, then the
   launcher's managed environment. Inspect `--help` and relevant subcommand
   help. Never guess flags or edit canonical JSON to imitate success.
5. Do not ask the person to assign roles, authority references, graph
   boundaries, artifact paths, or temporary storage. Existing repository rules
   remain evidence. If none exist, keep the first Atlas explicitly provisional.

### Fresh repository bootstrap lane

When preflight reports `mode=bootstrap-discovery`, use this explicit
zero-authority, read-only lane instead of failing circularly on a missing
binding:

1. Keep all generated observations, questions, policy drafts, and design drafts
   outside the repository, in an operating-system temporary directory.
2. Stay within the preflight caps: three 15-second Git identity/status calls,
   1 MiB per Git stream, at most 10,000 status entries, zero repository writes,
   zero network calls, and zero external mutations.
3. Run only read-only inspection and draft-Atlas generation. Never run
   repository code, authorize a run, mutate a catalog, claim a capability, or
   treat an inference as accepted intent.
4. Run one deterministic onboarding command:

   `python3 scripts/onboard.py --repo <repository> --locale <en|ru>
   --person-name <name> --output <temporary-atlas.html>
   --model-output <temporary-model.json>`

   It inspects tracked files, languages, repository areas, imports, bounded Git
   history, and co-change evidence. It writes only to the operating-system
   temporary directory. The result is a draft, not an active binding.
5. Give the person the Atlas and ask only whether the map describes the project
   correctly. Do not show a bootstrap packet, terminal transcript, artifact
   list, or technical questionnaire.
6. If the person corrects the map, update the temporary model and rerender with
   `--model`. Any participant may suggest a correction. Do not ask about roles.
7. After the person accepts the map, record the required machine decisions
   internally and ask separately before activation. Never debug actor kinds,
   authority references, schemas, or shell quoting in the user conversation.
8. Rerun preflight with `--binding <exact-path>`, validate the first binding,
   and use normal bound governance for every later mutation.

If the person does not accept the Atlas, leave the repository byte-for-byte
unchanged. A first binding cannot approve its own creation retroactively.

## 2. Review the Atlas

Open or link the generated Atlas. It must let the person click a cycle and
descend into nested cycles. Show recognizable project language first. Keep
source paths as supporting evidence inside the Atlas.

Keep each claim in its emitted state:

- `observed`: directly derived from repository bytes or Git records;
- `inferred`: a heuristic interpretation awaiting a decision;
- `confirmed` or `rejected`: an operator decision with provenance;
- `runtime_verified`: evidence valid only for its recorded scope and candidate.

Never relabel confidence as authority. Never execute repository code merely to
inspect it. Never demand answers about internal mechanics before showing the
map.

## 3. Negotiate intent

Generate machine questions only after the person reviews the Atlas. Do not
present them as an onboarding questionnaire. Convert a correction or approval
given in ordinary language into the corresponding internal record.

After plain approval, use `scripts/record_answer.py` for each machine question
already represented by the Atlas. Never assemble `decide` arguments by hand.
If a correction does not map unambiguously, update the visible Atlas and ask
whether the revised map is correct before recording anything.

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
Assign each model-assisted loop an exact provider, model, reasoning effort,
skills, tools, and declared MCP resources. Use no model for deterministic or
human-authority work. Start with the least costly eligible route and record the
reason for every higher tier. Treat the route as proposed until the operator
accepts the binding.
Require a separate operator decision over the proposed design digest.

Run the launcher's `compile` command only with the accepted graph, the exact
loop-design proposal, its separately accepted manifest, and explicit policies.
Compilation emits a registry and non-authoritative binding proposal. Present
that proposal digest, then run `activate` only as a separate capable operator
decision with rationale. Let the compiler reject ancestor containment,
unbounded feedback, dead ends, authority escalation, missing child deadlines,
or self-review. Do not weaken a contract just to make compilation pass.

## 5. Generate and inspect the Atlas

Generate the offline Atlas with the launcher's `atlas` command from the exact
accepted binding and, when applicable, a run card. Always pass the session's
explicit `--locale en` or `--locale ru`; never rely on a renderer default.
Verify its deterministic check mode with the same locale.
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
Reject undeclared model substitutions and reasoning increases. Escalate to a
more capable or more expensive route only through the bound budget and record
the failed or insufficient lower-tier attempt.

Do not infer parent acceptance from child success. Do not let an author certify
an independent gate. Do not call a run complete while any required gate,
candidate match, or publication authority is missing.

## 7. Propose evolution

Append content-addressed friction, drift, cadence, and failure signals. Run the
launcher's `evolve` command only to produce a proposed diff against an exact base
binding. Show contributing signals, graph operations, and stale-precondition
checks.

Aggregate candidate-bound route telemetry: input and output tokens, reasoning
effort, latency, cost, retries, drift, terminal result, reviewer findings, and
escalations. Propose the smallest route change that meets the evidence
contract. Do not promote a model from preference or one successful run. Do not
demote it after a failure caused by missing tools, bad scope, or bad input.

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
- a route names an unavailable model, undeclared skill, or unbound MCP
  resource;
- a more expensive route lacks a bound reason, budget, or comparison evidence;
- an evolution proposal is stale or lacks separate acceptance;
- release readiness is mistaken for publication authority.

End with the operator outcome and the one next action. If work is genuinely
complete, say what is now usable and how to use or inspect it. If work is
blocked, ask the one decision needed to continue. Put artifact paths, digests,
exact checks, candidate identity, and authority boundaries in an optional
technical appendix. Avoid claiming that a generated file, passing child loop,
or confidence score proves acceptance.
