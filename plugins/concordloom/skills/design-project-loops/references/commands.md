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
| Preview route | `concordloom route preview` | Exact proposed route with no execution authority |
| Execute | `concordloom run` | Governed run-card lifecycle |
| Visualize | `concordloom atlas` | Deterministic offline HTML projection |
| Evolve | `concordloom evolve` | Proposed successor diff, never activation |

The Atlas renderer supports `--locale en` and `--locale ru`. Pass the
operator's explicit onboarding choice on both generation and `--check`; do not
rely on the default locale. This changes human-readable presentation, not
canonical binding or run data.

## Preview before execution

Route Preview is an unreleased `main` feature and is not present in v0.1.5.
First run `concordloom route preview --help`. If it fails, do not fabricate the
artifact or silently install `main`; explain the version gap and ask separately
before testing unreleased code.

Keep the person's request in a temporary UTF-8 file. Select the smallest target
loops that can establish the requested outcome, then create a preview:

```bash
python3 scripts/concordloom_cli.py route preview \
  --binding "$BINDING" \
  --registry "$REGISTRY" \
  --policy "$POLICY" \
  --candidate "$CANDIDATE" \
  --repository "$REPOSITORY" \
  --development-model "$DEVELOPMENT_MODEL" \
  --preview-id "$PREVIEW_ID" \
  --request-file "$REQUEST_FILE" \
  --target-loop "$TARGET_LOOP" \
  --created-at "$CREATED_AT" \
  --output "$PREVIEW"
```

The artifact stores only the request digest and an opaque reference, never the
request text. Show the area breadcrumb separately from the ordered executable
and verification actions, then ask one plain-language question: whether to use
this exact route. To correct it, create a successor preview with
`--replaces-preview`; never edit the old preview. After confirmation, pass the
exact artifact to `run new --route-preview`. Confirmation creates a draft; a
separate authorization is still required before any work starts. If the confirmed preview is a
correction, also pass its exact predecessor with `--replaced-route-preview`.
A v0.1 preview can verify one correction hop. If that correction is still
wrong, create a new base preview rather than attaching unchecked deeper history.
A preview never runs code, writes the repository, contacts the network, or
grants authority.

The output is create-only: the command refuses to overwrite any existing file.
Keep it outside the repository, or under `.concord/runs/` only when Git really
ignores that exact path. For a preview-backed run, `run guard` must receive the
exact binding, registry, candidate, repository, development model, preview, and
its predecessor when the preview is a correction. The guard rechecks all of
them before any task file may be read or changed.

The `run` family covers `new`, `authorize`, `attempt`, `evidence`, `guard`, and
`complete`. Always inspect the nested help before use. Run `guard` before
task-scoped inspection or mutation and include every intended path. Attempt
records include factual model/provider, data egress, network/external mutation,
elapsed time, and cost. Evidence and completion require `--payload-root` so the
declared payload digest can be checked against real bytes.

If `--help` differs from this map, stop and report a version mismatch. Do not
fall back to hand-editing canonical artifacts.
