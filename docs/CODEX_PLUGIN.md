# Codex plugin

Concord Loom ships a Codex plugin containing the `design-project-loops` skill.
The plugin provides a conversational layer over the deterministic CLI and
artifact contracts. It is not limited to software delivery: it can describe
any finite system of nested loops whose outcomes, evidence, authority, scope,
budgets, and terminal states can be made explicit.

The generic SDLC is an example binding, not the product boundary. Concord
Loom's repository uses the separately accepted 58-cycle development
configuration rooted at `steward-concordloom`. Observe, negotiate, bind,
execute, verify, publish, and evolve are the phases of each governed run.

## Install from the GitHub marketplace

Pin the marketplace to the release tag, then install the plugin:

```bash
codex plugin marketplace add concordloom/concordloom --ref v0.1.2
codex plugin add concordloom@concordloom
```

The marketplace entry resolves the repository-local
`plugins/concordloom` bundle. Inspect
`.agents/plugins/marketplace.json` and
`plugins/concordloom/.codex-plugin/plugin.json` before installing if your
environment requires a manual trust review.

For local plugin development, add the checkout as a marketplace source and
install the same `concordloom@concordloom` identity according to the current
Codex plugin CLI help.

## Use

You do not need to install the Concord Loom CLI first. Open the target
repository and ask Codex:

```text
Use $design-project-loops to onboard this repository safely, inspect it
read-only, and show me the highest-impact unresolved loop decision.
```

The skill:

1. runs bounded, read-only preflight;
2. if the CLI is missing, selects `pipx`, `uv tool`, or an isolated virtual
   environment and presents the exact pinned installation plan;
3. asks before changing the user environment or using the network;
4. reruns preflight and inspects the repository without executing its code;
5. presents observations, inferences, coverage, and high-impact questions;
6. records the operator's accepted, rejected, or corrected intent;
7. proposes a loop system and waits for exact acceptance;
8. compiles and validates the accepted contracts;
9. routes governed execution through run cards;
10. maintains the offline Atlas; and
11. records evidence-backed evolution proposals without activating them.

The skill never uses system `pip`, never passes `--break-system-packages`, and
never installs silently.

The same sequence applies outside software repositories. Adapters may provide
different evidence or executors, but they do not replace operator acceptance,
finite containment, bounded feedback, or candidate-bound verification.

## Fresh repositories

A repository with no Concord Loom binding enters a bounded read-only bootstrap:

- no product authority is inferred;
- no candidate or source mutation is authorized;
- discovery budgets remain explicit;
- the skill shows the proposed graph and required decisions; and
- mutation remains blocked until the operator establishes the first accepted
  binding.

The bundled launcher reports an exact installation plan when the `concordloom`
CLI is unavailable. It prefers `pipx`, then `uv tool`, then a dedicated virtual
environment outside the repository. It does not silently download a package or
execute a repository-provided replacement.

## Authority boundary

The skill is not project execution authority by itself. Repository rules,
accepted artifacts, the active binding, and each run card remain controlling.
The operator chooses outcomes and disputed intent. The orchestrator chooses
files, tests, tools, models, and reviewers within those accepted boundaries.

Model output is a proposal until deterministic validation and required
authority accept it.

The active binding also governs Concord Loom's public surfaces. The bilingual
Pages site and its social-preview artwork are projections and communication
assets: they may explain accepted artifacts, but cannot create or change
authority. A Pages workflow is publication machinery, and a green build is not
proof of a live deployment without the separately authorized publication
receipt and deployed URL.

## Data and network policy

The core inspector is local and does not execute target code. A Codex session
may use model or connector services according to the user's environment.
Bind allowed content classes, providers, network access, and data egress in
policy; record the effective route in each attempt.

## Languages

English documents are canonical peers of the Russian files under `docs/ru/`.
The plugin's two operator references also have `.ru.md` siblings, and the
generic SDLC example includes `README.ru.md`. Translation must preserve command
names, identifiers, digests, epistemic states, and authority boundaries; it
must not turn a proposal or planned publication into an accepted or verified
fact.
