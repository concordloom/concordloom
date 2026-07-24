# Trust model

Concord Loom is a local, declarative governance framework. It makes important
claims mechanically checkable, but it does not turn an untrusted computer or
identity provider into a trusted one.

## Protected invariants

The portable core fails closed on:

- inferred project intent used as accepted authority;
- unaccepted loop designs passed to compilation;
- cyclic containment or unbounded local feedback;
- child scope or budget broader than its parent;
- stale binding, policy, candidate, attempt, or evidence digests;
- candidate inventory, content, mode, symlink, or revision drift;
- evidence payload claims that do not match real bytes;
- planned routes represented as factual attempts;
- reviewers that match recorded candidate authors where separation is bound;
- append-only catalog predecessor or active-head mismatch; and
- evolution proposals that try to activate themselves.

Canonical JSON and explicit digest envelopes make these checks reproducible.

## Repository inspection

Inspection treats the target repository as data. Git calls disable hooks,
fsmonitor, external diff and text conversion, pagers, prompts, replace objects,
lazy fetch, and optional locks where applicable. It does not check out history
or import repository code.

File, history, path, byte, time, and co-change limits are explicit. Coverage
and truncation remain visible. Untracked files require opt-in before they enter
a candidate.

## What `guard` means

`guard` checks declared paths against a run-card capability. It is a policy
gate, not an operating-system sandbox. A process that ignores the runner can
still write anywhere its operating-system account permits.

Use containers, virtual machines, restricted users, network policy, secret
brokers, and filesystem permissions when hostile-code isolation is required.
Those controls complement Concord Loom; the framework does not simulate them.

## Identity and independence

The public policy model resolves principal IDs, roles, and capabilities from
content-addressed artifacts. The runner records the effective principal,
agent, model, skill, subagents, and tools and rejects recorded author/reviewer
identity overlap when a gate requires independence.

In the portable local deployment these identities are logical assertions, not
cryptographic authentication. They improve accountability and detect internal
inconsistency. They do not stop one malicious local actor from claiming two
names or editing every local file.

Deployments requiring adversarial identity assurance should bind receipts to
signed workload identities or platform attestations and protect policy,
candidate, and run storage outside the writer's authority.

## Evidence is scoped

Evidence can establish only its declared predicate for its exact candidate,
policy, attempt, producer, and payload. It does not prove:

- that a product requirement is valuable;
- that a test oracle is complete;
- that physical observations were honest before digitization;
- that an authorized decision was wise; or
- that one child result satisfies a parent's complete acceptance contract.

Parent loops own parent acceptance.

## Models and external services

The standard-library core has no model-provider dependency or implicit network
egress. Model-assisted plugins are routing layers. Their outputs remain
untrusted until schemas and invariants pass.

A run policy should state allowed providers, models, content classes, data
egress, network access, mutations, cost, and elapsed-time budgets. Actual
attempts record what happened, even when it differs from the plan.

## Bootstrap receipts

The first release uses an explicitly separate trust-seed protocol under
`concord/`. Mutable bootstrap run cards and signals live in ignored
`.concord/runs/` and `.concord/signals/`; they are not source-candidate bytes.

After completion, the runner exports a deterministic receipt bundle embedding
the final card, cycle, policy, candidate digest, and review evidence. Its
published SHA-256 must be attached to the exact Git release. A self-digest is
tamper-evidence only when an independently referenced release or attestation
anchors it.

Bootstrap cards must never be represented as public
`concordloom.run-card` artifacts. Public runs use
`schemas/run-card.schema.json` and bind an accepted registry, policy, binding,
candidate manifest, route, evidence, and authority.

## Residual risks

- A compromised operating-system account can bypass a policy-only guard.
- A malicious authority can approve a harmful but structurally valid model.
- Logical identities can be impersonated without external authentication.
- Repository mining can produce plausible but wrong hypotheses.
- Digest integrity does not imply semantic truth.
- Availability, secret handling, and remote-runtime isolation are deployment
  responsibilities.

Treat a passing validator as evidence about declared invariants, not as a
universal safety certificate.
