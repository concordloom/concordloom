# Concord Loom quickstart

This guide gives you a useful result before it explains the full governance
chain. Start by inspecting one repository. Continue into a governed run only
when you need execution, independent review, or publication.

## What you will get

In about 5 minutes you will:

1. install the command-line tool;
2. inspect a repository without changing it;
3. see which relationships are observed facts and which are hypotheses; and
4. open the interactive Atlas.

The later sections explain how to turn that observation into an accepted,
executable loop system.

## Recommended: let the Codex skill onboard the repository

If you use Codex, install the plugin as described in the
[Codex plugin guide](CODEX_PLUGIN.md), open the target repository, and ask:

```text
Use $design-project-loops to onboard this repository safely, inspect it
read-only, and show me the highest-impact unresolved loop decision.
```

The skill runs preflight, presents one safe installation plan if the CLI is
missing, and asks for approval before changing the user environment. Continue
below only for a manual or headless CLI setup.

## 1. Install the CLI

```bash
pipx install \
  "concordloom @ git+https://github.com/concordloom/concordloom@v0.1.5"
concordloom --version
```

If `pipx` is unavailable and you already use `uv`, run:

```bash
uv tool install \
  "concordloom @ git+https://github.com/concordloom/concordloom@v0.1.5"
```

Do not pass `--break-system-packages` or install into an
externally-managed system Python.

When working from a clone:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
./tools/check.sh
```

Expected result: the version command prints `concordloom 0.1.5`. The check
script ends with `CHECK_OK`.

## 2. Inspect a repository

Run these commands from a clean Git repository:

```bash
TARGET_REPOSITORY="$(git rev-parse --show-toplevel)"
WORK_DIR="$(mktemp -d /tmp/concordloom-quickstart-XXXXXX)"

concordloom inspect "$TARGET_REPOSITORY" \
  --output "$WORK_DIR/observed-project-graph.json"
concordloom questions \
  --graph "$WORK_DIR/observed-project-graph.json" \
  --output "$WORK_DIR/questions.json"
```

Expected result: `observed-project-graph.json` contains the discovered files and
relationships. `questions.json` contains decisions that cannot be inferred
safely.

Inspect the summary:

```bash
jq '.coverage, .hypotheses' "$WORK_DIR/observed-project-graph.json"
jq '.questions[] | {prompt, why_it_matters, options}' "$WORK_DIR/questions.json"
```

An `observed` relationship comes from repository evidence. An `inferred`
relationship is a hypothesis. Neither one becomes accepted intent until an
operator decides.

## 3. Open the Atlas

The [public Atlas](https://concordloom.github.io/concordloom/#atlas/steward-concordloom)
shows the complete development system used by this repository. It is a
read-only projection: it can explain accepted rules and recorded runs, but
cannot grant authority or change them.

From a source checkout:

```bash
PYTHONPATH=src python3 tools/build_site.py --check
python3 -m http.server --directory site 8000
```

Open `http://localhost:8000/?lang=en#atlas/steward-concordloom`.

The page distinguishes the product release from the internal revision of its
development rules:

```text
Concord Loom 0.1.5
Development rules: revision 8
```

## 4. Decide what the observation means

The inspection result is evidence, not permission. A governed setup names:

- the operator who accepts intent;
- the executor who may create a candidate;
- the reviewer who checks exact candidate bytes;
- the publisher who may perform an external effect; and
- the budgets and terminal outcomes for every feedback edge.

Use `concordloom decide` for each blocking question, then
`concordloom accept` to create an accepted project graph. Run
`concordloom decide --help` and `concordloom accept --help` for the exact input
files. The commands fail closed when a required decision is missing.

An operator decision identifies its authority explicitly:

```bash
concordloom decide \
  --questions "$WORK_DIR/questions.json" \
  --question question-id \
  --verdict confirmed \
  --actor-id project-operator \
  --actor-kind operator \
  --authority-ref operator \
  --rationale "Confirmed by the responsible operator." \
  --decided-at 2026-07-24T12:00:00Z \
  --output "$WORK_DIR/decision.json"
```

## 5. Build an executable loop system

The remaining artifact chain is deliberate:

```text
accepted project graph
  → proposed loop design
  → operator-accepted loop design
  → compiled registry and configuration proposal
  → separately activated configuration
```

Create it with:

```bash
concordloom propose --help
concordloom accept --help
concordloom compile --help
concordloom activate --help
concordloom catalog --help
```

The repository includes a complete software-delivery example under
`framework/generic-sdlc/`. It is a worked example, not Concord Loom's universal
process.

## 6. Run one governed change

Create a manifest for the exact candidate bytes, then create and authorize a
run:

```bash
concordloom candidate "$TARGET_REPOSITORY" \
  --generated-at 2026-07-24T12:25:00Z \
  --output "$WORK_DIR/candidate.json"

concordloom run new \
  --binding "$WORK_DIR/binding.json" \
  --registry "$WORK_DIR/cycle-registry.json" \
  --policy "$WORK_DIR/policy.json" \
  --candidate "$WORK_DIR/candidate.json" \
  --run-id first-governed-run \
  --root-loop project-root \
  --target-loop chosen-leaf-loop \
  --candidate-author project-executor \
  --output "$WORK_DIR/run-card.json"
```

Your accepted configuration supplies the real root loop and principal IDs.
`--target-loop` routes only that responsibility and its ancestors; unrelated
release and evolution branches stay out of the run. Omitting it creates a
coordination-only root run. Use `--portfolio` only for an intentional audit of
the complete reachable system.
Advance the card with:

```bash
concordloom run authorize --help
concordloom run attempt --help
concordloom run evidence --help
concordloom run complete --help
```

A planned route becomes factual only after an attempt records the effective
principal, model, instructions, tools, network use, external effects, elapsed
time, and result. A run is finished only when `run complete` succeeds.

## 7. Understand evolution

Repeated, content-addressed signals may support a successor proposal:

```bash
concordloom evolve --help
```

The proposal always has `activation_allowed: false`. The active configuration
decides who may review and activate its successor. Evolution can propose its
replacement; it cannot authorize itself.

## Where to go next

- [Core concepts](CONCEPTS.md) explains the two graphs and fact states.
- [Trust model](TRUST_MODEL.md) explains authority and independent evidence.
- [Atlas guide](ATLAS.md) explains the interactive and portable views.
- [Architecture](ARCHITECTURE.md) describes the kernel and adapters.
