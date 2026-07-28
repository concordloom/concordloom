# Concord Loom v0.1 command map

Use this reference only after checking the bundled launcher and relevant
subcommand help. Command flags are versioned contracts; never invent an option.

## Supported CLI dependency path

From this skill directory, invoke every command as:

```bash
python3 scripts/concordloom_cli.py <command> ...
```

The launcher first uses the exact same-repository v0.1 source distribution.
When the plugin is installed without that source tree, it uses an installed
`concordloom` command. Resolve the route without executing a project command:

```bash
python3 scripts/concordloom_cli.py --resolve
```

If the dependency is absent, the launcher and preflight emit an `install_plan`
for the matching v0.1 release. The plan prefers `pipx`, then `uv tool`, then a
dedicated virtual environment managed outside the target repository. Show the
plan to the operator and obtain approval before executing every command. Then
rerun `--resolve`.

Never use system `pip`, `--break-system-packages`, an unpinned package, or
source copied into the target repository. `install_argv` remains as a
compatibility field containing the first command; use the complete
`install_plan`.

## Fresh repository

An absent binding is not a CLI error. Preflight reports
`mode=bootstrap-discovery`. Keep outputs in a temporary directory and use only
`inspect` and `questions` until presenting the bootstrap packet. Repository
mutation, authority claims, network access, external mutations, run-card
authorization, and binding activation remain forbidden until the operator
accepts the exact first-binding writes.

| Stage | Command family | Required result |
|---|---|---|
| Observe | `concordloom inspect` | Revision-bound observed/inferred graph |
| Interview | `concordloom questions` | Ranked questions with answer deltas |
| Decide | `concordloom decide` | Append-only actor decision and rationale |
| Accept | `concordloom accept` | Accepted graph or a blocking failure |
| Propose | `concordloom propose` | Reviewable loop-design delta |
| Compile | `concordloom compile` | Registry plus non-authoritative binding proposal |
| Activate | `concordloom activate` | Binding accepted from that exact proposal digest |
| Validate | `concordloom validate` | Schema and cross-artifact checks |
| Identify | `concordloom candidate` | Canonical candidate manifest and digest |
| Catalog | `concordloom catalog` | New append-only active-binding chain value |
| Execute | `concordloom run` | Governed run-card lifecycle |
| Visualize | `concordloom atlas` | Deterministic offline HTML projection |
| Evolve | `concordloom evolve` | Proposed successor diff, never activation |

The Atlas renderer supports `--locale en` and `--locale ru`. Pass the
operator's explicit onboarding choice on both generation and `--check`; do not
rely on the default locale. This changes human-readable presentation, not
canonical binding or run data.

The `run` family covers `new`, `authorize`, `attempt`, `evidence`, `guard`, and
`complete`. Always inspect the nested help before use. Run `guard` before
task-scoped inspection or mutation and include every intended path. Attempt
records include factual model/provider, data egress, network/external mutation,
elapsed time, and cost. Evidence and completion require `--payload-root` so the
declared payload digest can be checked against real bytes.

If `--help` differs from this map, stop and report a version mismatch. Do not
fall back to hand-editing canonical artifacts.
