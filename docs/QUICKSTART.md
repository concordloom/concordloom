# Concord Loom quickstart

This walkthrough separates two useful first experiences:

1. inspect your own repository without executing it; and
2. exercise the complete governed chain with the shipped generic SDLC model.

After installation, Concord Loom commands use only local files. They do not
contact a model provider or hosted service.

## 1. Install and verify

```bash
python3 -m pip install \
  "concordloom @ git+https://github.com/PullDakar/concordloom@v0.1.0"
concordloom --version
```

When working from a clone instead:

```bash
python3 -m pip install -e .
./tools/check.sh
```

## 2. Inspect your repository

Run this from a clean Git repository you want to understand. Governance
artifacts stay outside the target, so they cannot contaminate its candidate
inventory:

```bash
TARGET_REPOSITORY="$(git rev-parse --show-toplevel)"
WORK_DIR="$(mktemp -d /tmp/concordloom-quickstart-XXXXXX)"

concordloom inspect "$TARGET_REPOSITORY" \
  --output $WORK_DIR/observed-project-graph.json
concordloom questions \
  --graph $WORK_DIR/observed-project-graph.json \
  --output $WORK_DIR/questions.json
```

Review the coverage and truncation fields before trusting the graph. An
`observed` edge comes directly from repository or Git evidence. An `inferred`
edge is a hypothesis. Confidence ranks questions; it does not grant authority.

```bash
jq '.coverage, .hypotheses' \
  $WORK_DIR/observed-project-graph.json
jq '.questions[] | {id, prompt, why_it_matters, options}' \
  $WORK_DIR/questions.json
```

Use `--include-untracked` only when those bytes are intentionally in scope.
File, history, subprocess, and co-change budgets are configurable; truncation
stays visible in the output.

## 3. Record operator decisions

Start with a policy that names real principals, roles, capabilities, evidence
rules, budgets, and evolution authority. The tagged source repository contains
an executable generic example:

```bash
git clone --quiet --depth 1 --branch v0.1.0 \
  https://github.com/PullDakar/concordloom.git \
  "$WORK_DIR/concordloom-source"
cp "$WORK_DIR/concordloom-source/framework/generic-sdlc/policy.json" \
  "$WORK_DIR/policy.json"
```

Edit the copied policy deliberately before production use. For a local
walkthrough, its `example-operator` principal can answer the first generated
question:

```bash
QUESTION_ID="$(jq -r '.questions[0].id' \
  $WORK_DIR/questions.json)"

concordloom decide \
  --questions $WORK_DIR/questions.json \
  --question "$QUESTION_ID" \
  --verdict confirmed \
  --actor-id example-operator \
  --actor-kind operator \
  --authority-ref operator \
  --rationale "The operator confirms this proposed project intent." \
  --decided-at 2026-07-24T12:00:00Z \
  --output $WORK_DIR/decision-1.json
```

Repeat `decide` for every blocking question. A correction may provide a
replacement `--graph-delta` JSON array. Rejection remains visible; it is not
deleted from history.

Accept the resulting decision set. Add one repeated `--decision` argument for
each decision file; the one-question form is:

```bash
concordloom accept \
  --graph $WORK_DIR/observed-project-graph.json \
  --policy $WORK_DIR/policy.json \
  --decision $WORK_DIR/decision-1.json \
  --actor-id example-operator \
  --actor-kind operator \
  --authority-ref operator \
  --accepted-at 2026-07-24T12:05:00Z \
  --decision-log-output $WORK_DIR/decision-log.json \
  --output $WORK_DIR/accepted-project-graph.json
```

Acceptance fails while a blocking question lacks a valid decision.

## 4. Propose and separately accept the loop design

```bash
concordloom propose \
  --graph $WORK_DIR/accepted-project-graph.json \
  --decisions $WORK_DIR/decision-log.json \
  --policy $WORK_DIR/policy.json \
  --output $WORK_DIR/loop-design-proposal.json
```

Inspect the proposal. It exposes containment, local flow, budgets, evidence,
authority, and terminal outcomes. It still has no execution authority.

```bash
concordloom accept \
  --proposal $WORK_DIR/loop-design-proposal.json \
  --accepted-graph $WORK_DIR/accepted-project-graph.json \
  --decisions $WORK_DIR/decision-log.json \
  --policy $WORK_DIR/policy.json \
  --decision-id accept-loop-design-1 \
  --rationale "The operator accepts this exact loop-design proposal." \
  --actor-id example-operator \
  --actor-kind operator \
  --authority-ref operator \
  --accepted-at 2026-07-24T12:10:00Z \
  --output $WORK_DIR/loop-design.json
```

This is the first deliberate acceptance seam. `propose` cannot accept its own
output.

## 5. Compile and separately activate a binding

Compilation emits a registry and a binding proposal:

```bash
concordloom compile \
  --graph $WORK_DIR/accepted-project-graph.json \
  --decisions $WORK_DIR/decision-log.json \
  --design-proposal $WORK_DIR/loop-design-proposal.json \
  --design $WORK_DIR/loop-design.json \
  --policy $WORK_DIR/policy.json \
  --created-at 2026-07-24T12:15:00Z \
  --artifact-root "$WORK_DIR" \
  --registry-output $WORK_DIR/cycle-registry.json \
  --proposal-output $WORK_DIR/binding-proposal.json
```

Activation is a second decision over the exact proposal:

```bash
concordloom activate \
  --proposal $WORK_DIR/binding-proposal.json \
  --graph $WORK_DIR/accepted-project-graph.json \
  --decisions $WORK_DIR/decision-log.json \
  --design-proposal $WORK_DIR/loop-design-proposal.json \
  --design $WORK_DIR/loop-design.json \
  --registry $WORK_DIR/cycle-registry.json \
  --policy $WORK_DIR/policy.json \
  --binding-id project-binding-v1 \
  --decision-id activate-binding-v1 \
  --actor-id example-operator \
  --actor-kind operator \
  --authority-ref operator \
  --accepted-at 2026-07-24T12:20:00Z \
  --rationale "Activate this exact compiled proposal." \
  --output $WORK_DIR/binding.json
```

Append it to a catalog:

```bash
concordloom catalog \
  --binding $WORK_DIR/binding.json \
  --artifact-root "$WORK_DIR" \
  --output $WORK_DIR/catalog.json
```

Neither compilation nor catalog creation can silently replace an active
binding.

## 6. Pin a candidate and create a run

Create a manifest from tracked files. Explicitly name any untracked path that
belongs to the candidate:

```bash
concordloom candidate "$TARGET_REPOSITORY" \
  --generated-at 2026-07-24T12:25:00Z \
  --output $WORK_DIR/candidate.json
```

Then create a run against a root loop defined by your compiled registry:

```bash
ROOT_LOOP="$(jq -r '.containment_graph.roots[0]' \
  $WORK_DIR/cycle-registry.json)"

concordloom run new \
  --binding $WORK_DIR/binding.json \
  --registry $WORK_DIR/cycle-registry.json \
  --policy $WORK_DIR/policy.json \
  --candidate $WORK_DIR/candidate.json \
  --run-id first-governed-run \
  --root-loop "$ROOT_LOOP" \
  --candidate-author example-executor \
  --output $WORK_DIR/run-card.json
```

Use `concordloom run authorize`, `attempt`, `guard`, `evidence`, and `complete`
to advance it. Each subcommand requires the current card plus the exact
binding, registry, policy, candidate, repository, actor, and evidence inputs
appropriate to that transition:

```bash
concordloom run authorize --help
concordloom run attempt --help
concordloom run evidence --help
concordloom run complete --help
```

The explicit files are intentional. Planned routing does not become factual
until an attempt records the effective principal, agent, model, skill,
subagents, tools, network, data egress, mutations, elapsed time, and cost.
Evidence must bind to that attempt and to actual payload bytes.

## 7. Generate the offline Atlas

```bash
concordloom atlas \
  --binding $WORK_DIR/binding.json \
  --registry $WORK_DIR/cycle-registry.json \
  --policy $WORK_DIR/policy.json \
  --run-card $WORK_DIR/run-card.json \
  --output $WORK_DIR/atlas.html
```

Open `atlas.html` directly in a browser. It has no network dependencies. Use
`--check` in automation to reject stale generated output.

## 8. Propose evolution

Repeated, content-addressed signals can support a successor proposal:

```bash
concordloom evolve --help
```

The command requires the active binding, policy, one or more signal files,
explicit operations, risk, proposer, existing decision authority, and
generation time. Its output always has `activation_allowed: false`. Accepting
and activating a successor uses the authority bound by the current version.

## 9. Validate the bundled complete example

The tagged source checkout contains every generic artifact in a coherent,
exact-digest chain:

```bash
cd "$WORK_DIR/concordloom-source"
concordloom validate \
  --input framework/generic-sdlc/catalog.json \
  --artifact-root .

python3 tools/generate_generic_example.py --check
```

Study that directory when building your first policy and run inputs. Replace
its example identities and project assumptions; do not treat them as defaults.
