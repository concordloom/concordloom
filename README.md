<p align="right">
  <strong>English</strong> · <a href="README.ru.md">Русский</a>
</p>

<p align="center">
  <img
    src="docs/assets/concordloom-hero.webp"
    width="1774"
    alt="A dark circular map connects the cycles that make up a project."
  >
</p>

# Concord Loom

## Systems that can change themselves — without granting themselves permission.

[![CI](https://github.com/concordloom/concordloom/actions/workflows/ci.yml/badge.svg)](https://github.com/concordloom/concordloom/actions/workflows/ci.yml)
[![Pages](https://github.com/concordloom/concordloom/actions/workflows/pages.yml/badge.svg)](https://github.com/concordloom/concordloom/actions/workflows/pages.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-c8ff00.svg)](LICENSE)

**Concord Loom is a domain-neutral framework for discovering, negotiating,
binding, executing, verifying, visualizing, and evolving finite systems of
loops.**

```text
OBSERVE  →  NEGOTIATE  →  BIND  →  EXECUTE  →  VERIFY  →  PUBLISH?  →  EVOLVE
 facts       intent       rules      effect      proof      authority    proposal
```

The question is not whether your work contains loops. It does.

The question is whether anyone can tell:

- what was observed and what was merely inferred;
- who accepted the intent;
- which exact policy and candidate ran;
- what evidence met the declared contract;
- where retries terminate;
- and who may authorize the next version of the system.

Concord Loom makes those boundaries explicit and content-addressed.

> **This is not an SDLC framework.** Software delivery is one example binding,
> beside research, incident response, creative production, governance, and
> any other bounded process an operator chooses to accept.

## One grammar, many systems

| Domain | One possible binding |
|---|---|
| Research | hypothesis → experiment → evidence → revision |
| Incident response | signal → containment → recovery → learning |
| Creative production | brief → exploration → critique → delivery |
| Governance | observation → proposal → decision → effect |
| Software delivery | requirements → implementation → testing → release |

The vocabulary changes. The invariants do not: finite containment, explicit
authority, bounded feedback, candidate-bound evidence, and terminal outcomes.

## The two-graph model

Concord Loom refuses to hide two different structures inside one “workflow”
diagram:

1. The **containment graph** states which loop refines a composite step. It is
   finite and acyclic.
2. A loop's **local control-flow graph** may contain feedback, but every cycle
   has an explicit retry budget and a path to success, failure, or escalation.

A child loop reports what it established. Its parent decides what that result
means. A green child receipt never becomes parent authority by accident.

## Try it

Python 3.11+ and Git are enough. The portable core uses only the standard
library.

With Codex, install one skill:

```text
Use $skill-installer to install
https://github.com/concordloom/concordloom/tree/v0.1.5/plugins/concordloom/skills/design-project-loops
```

Start a new conversation in the repository, then ask:

```text
Use $design-project-loops to analyse this repository and build its first Atlas.
Do not change the repository until I approve the map.
```

The skill asks which language to use and what to call you. It then analyses the
repository without changing it and shows a draft Atlas. Correct the map in
ordinary language. The skill asks separately before installing the CLI,
writing the first accepted configuration, or activating a later evolution.

For a CLI-only installation:

```bash
pipx install "concordloom @ git+https://github.com/concordloom/concordloom@v0.1.5"
concordloom --version
```

Continue with the [quickstart](docs/QUICKSTART.md), or open the
[interactive Concord Loom site](https://concordloom.github.io/concordloom/).

## Artifact chain

```text
repository evidence
  ↓
observed graph ──→ ranked questions
  ↓                    ↓
operator decisions ──→ accepted graph
  ↓
loop-design proposal ──→ explicit design acceptance
  ↓
registry + binding proposal ──→ explicit binding activation
  ↓
candidate + run + evidence ──→ generated Atlas
  ↓
repeated signals ──→ successor proposal ──→ separate operator decision
```

Each arrow produces a new artifact. Later stages cite exact digests; they do
not rewrite earlier evidence.

## Concord Loom governs Concord Loom

The active self-binding starts at `steward-concordloom` and expands into ten
responsibility areas: product direction, research, protocol, runtime, trust,
adapters, knowledge, release, adoption, and system evolution. Each area expands
again into concrete capability cycles.

Documentation now has an independent comprehension-review cycle. Site
development and site publication are separate. Evolution is visible as five
different responsibilities: collect signals, propose a successor, review it,
activate it, and observe the migration.

`propose-successor` may draft exact new rules. Another participant reviews
them. Only a separately authorized operator can activate the successor.

## Commands

| Command | Produces |
|---|---|
| `inspect` | observed and inferred repository graph |
| `questions` | ranked unresolved intent questions |
| `decide` | one explicit operator decision |
| `accept` | accepted intent or accepted loop design |
| `propose` | reviewable loop-design proposal |
| `compile` | cycle registry and binding proposal |
| `activate` | binding accepted by a separate decision |
| `catalog` | append-only active-binding chain |
| `candidate` | content-addressed candidate manifest |
| `run` | governed run lifecycle |
| `atlas` | deterministic offline projection |
| `evolve` | successor proposal — never activation |
| `validate` | schema and cross-artifact validation |

## Documentation

Every public guide is maintained in English and Russian.

| English | Русский |
|---|---|
| [Quickstart](docs/QUICKSTART.md) | [Быстрый старт](docs/ru/QUICKSTART.md) |
| [Core concepts](docs/CONCEPTS.md) | [Основные понятия](docs/ru/CONCEPTS.md) |
| [Architecture](docs/ARCHITECTURE.md) | [Архитектура](docs/ru/ARCHITECTURE.md) |
| [Product specification](docs/SPEC_V0.1.md) | [Спецификация](docs/ru/SPEC_V0.1.md) |
| [Trust model](docs/TRUST_MODEL.md) | [Модель доверия](docs/ru/TRUST_MODEL.md) |
| [Codex plugin](docs/CODEX_PLUGIN.md) | [Плагин Codex](docs/ru/CODEX_PLUGIN.md) |
| [Release verification](docs/RELEASE.md) | [Проверка релиза](docs/ru/RELEASE.md) |
| [Cycles of Cycles](docs/ARTICLE.md) | [Циклы циклов](docs/ru/ARTICLE.md) |
| [Atlas guide](docs/ATLAS.md) | [Руководство Atlas](docs/ru/ATLAS.md) |
| [Writing standard](docs/WRITING.md) | [Стандарт текста](docs/ru/WRITING.md) |
| [Design system](docs/DESIGN_SYSTEM.md) | [Дизайн-система](docs/ru/DESIGN_SYSTEM.md) |
| [Product decisions](docs/DECISIONS.md) | [Решения по продукту](docs/ru/DECISIONS.md) |
| [Observed landscape](docs/research/OBSERVED_LANDSCAPE.md) | [Наблюдаемый ландшафт](docs/ru/research/OBSERVED_LANDSCAPE.md) |

## Codex plugin

```text
Use $skill-installer to install
https://github.com/concordloom/concordloom/tree/v0.1.5/plugins/concordloom/skills/design-project-loops
```

Ask Codex to use `$design-project-loops`. The skill begins with bounded,
read-only discovery and refuses to promote repository history into intent
without an operator decision. The [plugin guide](docs/CODEX_PLUGIN.md) also
documents the optional GitHub Marketplace installation.

## Trust boundary

Concord Loom validates declarative artifacts, graph invariants, scopes,
evidence contracts, and authority separation. It is not an OS sandbox,
credential provider, durable workflow engine, or cryptographic identity
service. High-impact deployments must add platform enforcement and signed
attestations appropriate to their threat model.

Read the [trust model](docs/TRUST_MODEL.md) before governing consequential
effects.

## Development

```bash
./tools/check.sh
```

A green local gate is development evidence, not release authority.

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
