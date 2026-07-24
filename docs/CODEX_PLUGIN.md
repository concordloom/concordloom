# Codex plugin

Concord Loom ships a Codex plugin containing the `design-project-loops` skill.
The plugin provides a conversational layer over the deterministic CLI and
artifact contracts.

## Install from the GitHub marketplace

Pin the marketplace to the release tag, then install the plugin:

```bash
codex plugin marketplace add PullDakar/concordloom --ref v0.1.0
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

In the target repository, ask Codex explicitly:

```text
Use $design-project-loops to inspect this repository and show me the
highest-impact unresolved loop decision. Do not mutate the repository until I
accept the graph delta.
```

The skill:

1. runs bounded, read-only preflight and repository inspection;
2. presents observations, inferences, coverage, and high-impact questions;
3. records the operator's accepted, rejected, or corrected intent;
4. proposes a loop system and waits for exact acceptance;
5. compiles and validates the accepted contracts;
6. routes governed execution through run cards;
7. maintains the offline Atlas; and
8. records evidence-backed evolution proposals without activating them.

## Fresh repositories

A repository with no Concord Loom binding enters a bounded read-only bootstrap:

- no product authority is inferred;
- no candidate or source mutation is authorized;
- discovery budgets remain explicit;
- the skill shows the proposed graph and required decisions; and
- mutation remains blocked until the operator establishes the first accepted
  binding.

The bundled launcher reports an exact installation command when the
`concordloom` CLI is unavailable. It does not silently download a package or
execute a repository-provided replacement.

## Authority boundary

The skill is not project execution authority by itself. Repository rules,
accepted artifacts, the active binding, and each run card remain controlling.
The operator chooses outcomes and disputed intent. The orchestrator chooses
files, tests, tools, models, and reviewers within those accepted boundaries.

Model output is a proposal until deterministic validation and required
authority accept it.

## Data and network policy

The core inspector is local and does not execute target code. A Codex session
may use model or connector services according to the user's environment.
Bind allowed content classes, providers, network access, and data egress in
policy; record the effective route in each attempt.
