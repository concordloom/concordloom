# Model routing contract

Use this contract for the first binding and every route-changing successor.
The binding proposes routes; run evidence proves what happened.

## Inputs

For each leaf loop, record:

- whether the work is deterministic, model-assisted, or a human decision;
- consequence of a wrong result and whether independent review can catch it;
- ambiguity, context size, tool complexity, volume, latency target, and budget;
- required modalities, skills, tools, MCP resources, and data policy;
- prior candidate-bound tokens, cost, latency, retries, drift, and outcomes.

Do not infer model availability from a name. Use the provider and models allowed
by the accepted policy.

## Selection

1. Use `none` for deterministic transforms, validators, publication mechanics,
   and operator decisions.
2. Start model-assisted work on the least costly eligible route.
3. Use low or medium reasoning by default. Use high or xhigh only when risk,
   ambiguity, or measured quality warrants it. Reserve max for an explicit
   quality-first escalation.
4. Use the flagship tier for architecture, protocol invariants, evolution,
   threat analysis, or critical independent review when a weaker tier has not
   met the evidence contract.
5. Keep author and reviewer routes independent. A stronger model does not
   replace authority separation.

Every planned node must state an exact provider, model, reasoning effort,
versioned skills, tool capabilities, declared MCP servers, resource digests and
access modes, or explicitly state that none apply.

## Runtime proof

Record planned, actual, and verified routes separately. Fail closed on an
undeclared provider, model, reasoning increase, skill, MCP server, resource,
tool capability, or subagent. Record input and output tokens, latency, cost,
retries, terminal result, and the evidence digest.

Do not call a cheaper route successful merely because it used fewer tokens. It
must satisfy the same evidence contract.

## Evolution

Compare routes only on representative, candidate-bound runs. Separate model
failure from missing context, wrong scope, missing tools, unavailable
resources, and invalid inputs.

Propose one bounded change at a time:

- demote when a cheaper route repeatedly meets the same contract;
- promote when the current route repeatedly fails for model-capability reasons;
- lower reasoning when quality holds;
- increase reasoning only when measured quality improves enough to justify it;
- remove a model when deterministic code can replace it.

Pin the base binding, affected profile, telemetry digests, old route, proposed
route, budget delta, and rollback condition. The proposal cannot accept or
activate itself.
