# Help build Concord Loom

Language: **English** | [Русский](ru/HOW_TO_HELP.md)

Concord Loom is an Apache-2.0 open-source project at a very early stage. The
most useful contribution today is not promotion. It is evidence from real
repositories: where setup is confusing, where the Atlas misunderstands a
project, and where the promised safety boundary is hard to verify.

You do not need to understand the schemas or runtime before helping.

## Choose the smallest useful contribution

### Ten minutes: report friction

Open a [repository trial report](https://github.com/concordloom/concordloom/issues/new?template=repository-trial.yml)
after trying the Quickstart, or report one confusing sentence, missing step, or
unexpected result. A useful report names what you tried, what happened, and
what you expected.

### Thirty to sixty minutes: test a repository

Use a disposable or non-sensitive repository and follow the
[repository trial guide](REPOSITORY_TRIAL.md). Record the time to the first
Atlas, incorrect assumptions, unnecessary questions, unexpected writes, and
the point where you stopped. A failed attempt is useful evidence when the
failure is reproducible.

### One focused change: fix a known problem

Pick a [good first issue](https://github.com/concordloom/concordloom/issues?q=is%3Aissue%20state%3Aopen%20label%3A%22good%20first%20issue%22)
or an issue marked [help wanted](https://github.com/concordloom/concordloom/issues?q=is%3Aissue%20state%3Aopen%20label%3A%22help%20wanted%22).
Documentation, error messages, test fixtures, adapters, and small usability
fixes all count. The issue should describe the boundary and expected evidence.

### Deeper work: challenge the model

The project needs people who can test whether its graph, authority, and
evidence model holds outside its own repository. Useful areas include:

- adapters for AI coding agents and developer tools;
- counterexamples from research, operations, creative work, and governance;
- simpler onboarding and recovery from partial or failed runs;
- independent review of specifications, threat assumptions, and release gates;
- accessible, bilingual documentation and public-site improvements.

Start a [Discussion](https://github.com/concordloom/concordloom/discussions)
when the problem is still exploratory. Open an issue when the outcome is
concrete enough to test.

## How repository changes are developed

Concord Loom uses itself and AI coding agents for repository changes. A change
must have an authorized run card, stay inside its declared scope, and preserve
the difference between authored work, independent review, and publication.
The agent may prepare evidence; it cannot grant itself release authority.

Read [CONTRIBUTING.md](../.github/CONTRIBUTING.md) before changing files. If
that workflow is too heavy for your first contact, submit a trial report or
Discussion instead. A maintainer can turn the evidence into a bounded task.

## What a strong contribution contains

- one concrete problem rather than a broad request;
- reproducible evidence with secrets and private data removed;
- the exact version or commit tested;
- a clear boundary: what may change and what must not;
- remaining uncertainty stated plainly.

Concord Loom is experimental. Finding that a workflow is awkward, unsafe, or
not useful is a valid result. Please report it instead of polishing the result
into a success story.
