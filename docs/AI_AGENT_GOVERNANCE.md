# How to govern AI coding agents without giving them release authority

Language: **English** | [Русский](ru/AI_AGENT_GOVERNANCE.md)

An instruction file can tell an AI coding agent how to work. It cannot prove
which candidate the agent tested, stop credentials from granting broader
access, or decide that a change may be released. Governing AI agents requires
separate records for intent, execution, evidence, and authority.

Concord Loom is an early-stage attempt to make those boundaries inspectable.
It does not replace an operating-system sandbox, CI permissions, signed
attestations, or human review.

## Instructions are not authority

Files such as `AGENTS.md` are useful because they make repository rules visible
to people and agents. They still depend on the surrounding platform. An agent
with a broad token may be technically able to push even when its instructions
say not to.

Treat instructions as one input to a control system, not as the control system
itself. The effective boundary also includes filesystem scope, network access,
credentials, branch protection, required checks, and the person or service
allowed to publish.

## Keep six facts separate

Many agent workflows collapse different claims into one green status. Keep
these states distinct:

1. **Observed:** repository bytes or history show something.
2. **Proposed:** an agent suggests an interpretation or change.
3. **Accepted:** a capable operator confirms intent.
4. **Planned:** a route and candidate are fixed before execution.
5. **Actual:** tools, models, files, and external effects used in the run.
6. **Verified:** evidence satisfies the declared contract for that candidate.

Verification is not publication. A passing test says something about exact
bytes under exact rules. It does not grant the right to merge, deploy, send a
message, or activate new governance.

## Bind evidence to the exact candidate

Store the candidate digest, policy digest, command, environment, and result
together. Otherwise a green check can be reused for bytes it never tested.
When a candidate changes, evidence for the previous candidate becomes stale.

The same rule applies to review. A review of a description is not a review of
the resulting commit. A generated Atlas is a projection of accepted and actual
records; it is not an independent source of truth.

## Bound retries and escalation

Agentic workflows often say “fix until green.” That hides an unbounded loop.
Each feedback cycle needs a retry budget, terminal outcomes, and an escalation
path. When the budget is exhausted, stop or ask for a decision instead of
quietly widening scope.

## Separate author, reviewer, and publisher

For consequential changes, the same effective principal should not author the
candidate, certify its own work, and publish it. Platform controls should
enforce the separation that repository policy describes.

Concord Loom represents these responsibilities as explicit capabilities and
run nodes. A node receives only the read, write, network, and external-effect
scope it needs. Publication remains a separate authorized action.

## A practical starting point

For one repository:

1. document the repository rules;
2. inspect the project without writing to it;
3. let a person correct and accept the project map;
4. preview the route for a task before execution;
5. authorize narrowly scoped work against one candidate;
6. run independent checks against the same candidate;
7. publish only through a separate, protected decision.

This is a target architecture, not a claim that every Concord Loom adapter
already enforces every layer. The current public onboarding is centered on the
Codex skill. Support for Claude and other agents needs adapters, trials, and
review.

## Help test the boundary

If you operate AI coding agents on real repositories, Concord Loom needs your
counterexamples more than a success story. Follow the
[repository trial guide](REPOSITORY_TRIAL.md), report where the boundary is
unclear, or help build an adapter through
[the contribution paths](HOW_TO_HELP.md).
