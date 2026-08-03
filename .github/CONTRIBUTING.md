# Contributing to Concord Loom

Thank you for helping make bounded, evidence-governed work easier to understand and operate.

[Русская версия](CONTRIBUTING.ru.md)

## Before opening an issue

- Use [GitHub Discussions](https://github.com/concordloom/concordloom/discussions) for questions, early ideas, and examples that are not yet actionable defects.
- Use an issue form for a reproducible bug or a concrete proposal.
- For a vulnerability, follow [SECURITY.md](SECURITY.md) and do not open a public issue.

## Development setup

Concord Loom requires Python 3.11 or newer. Its portable core uses the standard library.

```bash
git clone https://github.com/concordloom/concordloom.git
cd concordloom
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
./tools/check.sh
```

## Working on a change

1. Read `AGENTS.md` before task-scoped repository work.
2. Keep observed, proposed, accepted, planned, actual, and verified facts distinct.
3. Make the smallest coherent change and add a regression test for every bug fixed.
4. Preserve deterministic, UTF-8, newline-terminated JSON artifacts.
5. Keep English and Russian documentation semantically aligned when changing public guidance.
6. Run `./tools/check.sh` before submitting the pull request.

The active Concord Loom binding governs this repository. After the trust-seed commit, repository mutations require an authorized run card and a passing guard for every intended path. A successful evidence contract is not release authority, and an evolution proposal cannot activate itself.

## Pull requests

Complete the pull request template. Explain the accepted problem, the exact scope, the evidence produced, and any remaining uncertainty. Do not describe a local build, test result, or generated artifact as deployed or published evidence.

Small, reviewable pull requests are preferred. Maintainers may ask for a proposal to be split when it combines unrelated authority, product, documentation, and release changes.

By contributing, you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md).
