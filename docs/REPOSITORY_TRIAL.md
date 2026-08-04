# Test Concord Loom on a repository

Language: **English** | [Русский](ru/REPOSITORY_TRIAL.md)

This trial checks whether a newcomer can obtain and correct a useful Atlas
without surrendering control of the repository. It is a product test, not a
request to prove that Concord Loom works.

Allow 30–60 minutes. Stop earlier if the process becomes unsafe or unclear.

## Before the trial

Use a disposable repository, a public repository you may inspect, or a copy
with secrets and private data removed. Do not use production credentials. Note:

- repository language, size, and approximate age;
- operating system, Python version, agent, and agent version;
- Concord Loom version or full commit SHA;
- whether you already understand the repository.

Read the [Quickstart](QUICKSTART.md). The first inspection should be read-only.
Do not approve repository writes merely to finish the trial.

## Run the scenario

1. Start a new agent conversation in the repository.
2. Ask the `design-project-loops` skill to inspect the repository and build a
   first Atlas without changing repository files.
3. Answer the language and operator-name questions.
4. Review the proposed map. Correct at least one wrong or uncertain conclusion
   in ordinary language.
5. Stop before connecting the repository unless you deliberately want to test
   the write path.

If you test the write path, inspect the proposed paths and authorization before
approving it. Record every file changed. A draft map must not silently become
accepted intent or active authority.

## Record what happened

Capture facts while the trial is fresh:

- minutes to the first readable Atlas;
- commands or prompts that were hard to understand;
- questions that felt unnecessary or arrived too late;
- incorrect repository areas, cycles, or relationships;
- whether evidence and inference were visibly different;
- any unexpected file, network, or external action;
- whether recovery instructions were clear after an error;
- the point where you would have abandoned the process without this test.

Screenshots and short redacted logs help. Do not upload secrets, private source
code, personal data, tokens, or complete proprietary logs.

## Submit the result

Open a [repository trial report](https://github.com/concordloom/concordloom/issues/new?template=repository-trial.yml).
Choose an outcome even when no Atlas appeared:

- completed without repository writes;
- completed and deliberately tested the write path;
- stopped because instructions were unclear;
- stopped because the boundary felt unsafe;
- blocked by an error.

Describe the smallest change that would have helped most. Maintainers will use
the report as evidence; it does not automatically change accepted product
intent.

For a security vulnerability, do not open a public issue. Follow the
[security policy](../.github/SECURITY.md).
