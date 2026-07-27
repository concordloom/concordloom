# Trust model

[Русская версия](ru/TRUST_MODEL.md)

Concord Loom is a domain-neutral, declarative governance framework. It makes
declared claims mechanically checkable, but it cannot turn an untrusted
machine, source, identity provider, model, or operator into a trusted one.
The shipped generic SDLC binding is one example governed by this trust model;
it does not narrow the model to software delivery.

## Protected invariants

The portable core fails closed on:

- inferred intent used as accepted authority;
- unaccepted loop designs passed to compilation;
- cyclic containment or unbounded local feedback;
- child scope, budget, or authority broader than its parent;
- stale binding, policy, candidate, attempt, or evidence digests;
- candidate inventory, content, mode, link, or revision drift;
- evidence claims that do not match recorded payload bytes;
- planned routes represented as factual attempts;
- author/reviewer overlap where separation is required;
- append-only catalog predecessor or active-head mismatch; and
- evolution proposals that try to accept or activate themselves.

Canonical JSON and explicit digest envelopes make these checks reproducible.
They prove internal consistency, not truth outside the recorded boundary.

## Observation adapters

Every observation adapter must treat its subject as data, expose coverage and
truncation, preserve provenance, and distinguish facts from hypotheses.

The v0.1 Git adapter disables hooks, fsmonitor, external diff and text
conversion, pagers, prompts, replace objects, lazy fetch, and optional locks
where applicable. It does not check out history, import repository code, or
execute the target. File, history, path, byte, time, and co-change limits are
explicit. Untracked files require opt-in before entering a candidate.

These controls describe the shipped adapter. Other domains need their own
source-specific isolation and provenance rules.

## What `guard` means

`guard` checks requested paths and effects against a run-card capability. It is
a policy gate, not an operating-system sandbox. A process that bypasses the
runner can still use every permission granted to its operating-system account.

Use restricted users, containers, virtual machines, network policy, secret
brokers, protected storage, and platform authorization when hostile-code
isolation is required. Those controls complement Concord Loom.

## Identity and independence

Policy resolves principal IDs, roles, and capabilities from content-addressed
artifacts. The runner records the effective principal, agent, model, skill,
subagents, and tools. It rejects author/reviewer overlap when the binding
requires independence.

In the portable local deployment, identities are logical assertions rather
than cryptographic authentication. They support accountability and consistency
checks, but cannot stop one malicious local actor from assuming two names or
editing all local state.

Deployments that require adversarial identity assurance should bind receipts to
signed workload identities or platform attestations and protect policy,
candidate, catalog, and run storage from candidate authors.

## Evidence is scoped

Evidence can establish only its declared predicate for its exact subject,
candidate, policy, attempt, producer, and payload. It cannot establish:

- that the chosen outcome is valuable;
- that an oracle or measurement is complete;
- that a physical observation was honest before digitization;
- that an authorized decision was wise;
- that one child result satisfies the full parent contract; or
- that verification grants publication authority.

Parent loops own parent acceptance. External effects require their own
capability and scope.

## Models, runtimes, and external services

Python and the standard library form the portable core. The core has no model
provider dependency or implicit network egress. Model-assisted plugins and
external runtimes are adapters; their outputs remain untrusted until schemas,
policy, and invariants accept them.

A run policy should name allowed providers, models, data classes, egress,
tools, network access, external mutations, cost, and elapsed-time budgets.
Actual attempts record what happened, including drift from the plan.

Concord Loom validates declared execution facts. It does not prove that an
external runtime enforced a transition or that a remote service returned
honest data.

## Publication boundary

A verified candidate is not a published effect. Publication requires a
publisher capability, an exact candidate, and scope naming the permitted
external mutation. The publish node records the effect, a deliberate no-op, or
escalation.

This boundary keeps `PASSED` factual: it means a node met its evidence
contract. It never means “release authorized” unless a separate policy and
authority explicitly say so.

## Self-binding and evolution

Concord Loom's accepted repository binding is:

```text
Observe → Negotiate → Bind → Execute → Verify → Publish → Evolve
```

It separates observation from intent, compilation from activation, execution
from independent verification, and verification from publication. The final
stage may only propose a successor.

The active binding defines the authority that may decide on its replacement.
An evolution proposal names its base binding, signals, preconditions, risk,
and required decision. It cannot edit the catalog, grant itself capability, or
activate itself. A separate operator decision and activation are required.

## Bootstrap receipts

The first release used an explicitly separate trust-seed protocol under
`concord/`. Mutable bootstrap cards and signals live under ignored
`.concord/runs/` and `.concord/signals/`; they are not source-candidate bytes.

The bootstrap runner can export a deterministic receipt bundle containing the
final card, cycle, policy, candidate digest, and review evidence. A published
SHA-256 gains meaning only when an independently referenced release or
attestation anchors it.

Bootstrap cards must never be represented as public `concordloom.run-card`
artifacts. Public runs use `schemas/run-card.schema.json` and bind an accepted
registry, policy, binding, candidate manifest, route, evidence, and authority.

## Residual risks

- A compromised operating-system account can bypass a policy-only guard.
- A malicious authority can approve a harmful but structurally valid model.
- Logical identities can be impersonated without external authentication.
- An adapter can produce plausible but wrong observations.
- Digest integrity does not imply semantic or physical truth.
- A correct child receipt can still be irrelevant to parent acceptance.
- Availability, secrets, and remote-runtime isolation remain deployment
  responsibilities.

Treat a passing validator as evidence about declared invariants, never as a
universal safety certificate.
