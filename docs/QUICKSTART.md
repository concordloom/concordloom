# Concord Loom quickstart

You do not need to learn Concord Loom's internal file formats before you can
use it. The normal path has four steps:

1. install one Codex skill;
2. let it inspect the repository without changing it;
3. review a visual Atlas and correct anything it misunderstood;
4. approve the connection only when the map looks right.

The schemas, graph checks, evidence records, and authority rules stay behind
that conversation.

## What you will get

The first session produces a draft Atlas of the repository:

- the work areas the skill found;
- the cycles it thinks connect those areas;
- the evidence behind each conclusion;
- and the uncertain parts that still need your judgment.

The draft is not an accepted configuration and cannot grant itself authority.
Until you approve it, the repository remains unchanged.

## 1. Install the Codex skill

Ask Codex:

```text
Use $skill-installer to install
https://github.com/concordloom/concordloom/tree/v0.1.5/plugins/concordloom/skills/design-project-loops
```

Start a new Codex conversation in the repository after installation. The new
conversation is important: it ensures that Codex loads the installed skill.

## 2. Ask for the first Atlas

Say:

```text
Use $design-project-loops to analyse this repository and build its first Atlas.
Do not change the repository until I approve the map.
```

The skill first asks:

1. which language to use for the conversation and generated material;
2. what name to use when addressing you.

It does not ask you to invent roles, authority identifiers, graph boundaries,
or artifact paths.

Next, the skill checks whether the Concord Loom command is available. If it is
missing, the skill shows one safe installation plan and asks for permission
before changing your environment or using the network. The preferred command
is:

```bash
pipx install \
  "concordloom @ git+https://github.com/concordloom/concordloom@v0.1.5"
```

Do not use `--break-system-packages`. The skill can also use `uv tool` or an
isolated managed environment when `pipx` is unavailable.

## 3. Review the map

The first analysis is read-only. The skill inspects tracked files, repository
areas, imports, bounded Git history, and files that often change together. It
does not run the repository's code.

The draft Atlas is written outside the repository. Open it and click through
the proposed cycles. Each cycle should answer three ordinary questions:

- What part of the project is this?
- What result does this work produce?
- What other work does it depend on?

Then answer one question: **does this map describe the project correctly?**

You can reply in ordinary language:

```text
Yes, this is accurate.
```

or:

```text
No. Release notes belong to the release cycle, not documentation.
```

The skill updates the draft and shows it again. A correction is only a
correction; it does not require a role or a special authority label.

## 4. Connect the repository

When the map is accurate, the skill asks separately whether it may save the
first accepted configuration inside the repository. This is the first
repository write, so approval must be explicit.

After connection:

- the accepted Atlas becomes the shared map of the project;
- later work can target the relevant cycle instead of loading the whole system;
- the Atlas can be regenerated from the accepted configuration;
- repeated problems can produce a reviewable evolution proposal;
- and a person still decides whether a proposed successor becomes active.

Approving the map and activating a future evolution are separate decisions.
The framework may suggest a better version of its rules; it cannot install
that version by itself.

## Everyday use

For normal work, describe the task and ask Codex to use the skill:

```text
Use $design-project-loops for this change. Show me the relevant cycle and keep
the Atlas current when the accepted project map changes.
```

The skill chooses a focused route, records what actually ran, and keeps
technical evidence available on request. You should see the practical next
step first, not an artifact transcript.

## Manual CLI path

The skill is the recommended interface. Use the CLI directly when you are
integrating Concord Loom into automation or developing the framework itself.

Read-only inspection:

```bash
WORK_DIR="$(mktemp -d /tmp/concordloom-quickstart-XXXXXX)"
concordloom inspect . \
  --output "$WORK_DIR/observed-project-graph.json"
concordloom questions \
  --graph "$WORK_DIR/observed-project-graph.json" \
  --output "$WORK_DIR/questions.json"
```

These files contain observations and hypotheses, not an accepted project map.
Run `concordloom --help` for the lower-level proposal, compilation, run, Atlas,
and evolution commands.

## What to read next

- [Atlas guide](ATLAS.md) explains the interactive and portable views.
- [Core concepts](CONCEPTS.md) explains the two graphs and fact states.
- [Trust model](TRUST_MODEL.md) explains why verification and permission are
  separate.
- [Architecture](ARCHITECTURE.md) documents the kernel and adapters.
