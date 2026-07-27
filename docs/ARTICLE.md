# Cycles of Cycles: A General Grammar for Governed Change

*How finite containment, bounded feedback, evidence, and authority turn nested
iteration into an inspectable system*

## Abstract

Research, incident response, creative production, governance, and software
delivery look different, but each repeatedly turns an input into a result,
checks that result, and decides what happens next. Each also contains smaller
cycles. An experiment contains calibration and analysis; an incident contains
diagnosis and recovery; a film contains editorial and sound-review loops; a
policy process contains consultation and ratification. A consequential system
of work is often a cycle composed of cycles.

Nesting and iteration are established ideas. The open engineering problem is
their governed composition. A loop needs a typed contract, terminal outcomes,
bounded feedback, explicit evidence, named authority, and a precise rule for
how a child result affects its parent. The system needs a finite containment
graph separate from each loop's local control-flow graph. Its records must also
keep observed, proposed, accepted, planned, actual, and verified facts distinct.

Concord Loom provides that general grammar without prescribing a domain,
runtime, model provider, hosting platform, or repository layout. It discovers
evidence, asks an operator to resolve consequential intent, binds accepted
decisions to finite loop contracts, records governed attempts, projects the
result in an Atlas, and may propose a successor binding. Evolution can propose;
it cannot authorize itself.

## Consequential work already contains loops

A flat process diagram makes each stage look atomic. Practice reveals another
structure.

In research, a program moves from question to hypothesis, experiment,
interpretation, and revision. The experiment may contain calibration,
recruitment, data-quality, and analysis loops. A successful calibration does
not validate the hypothesis. It produces evidence that the experiment parent
must evaluate.

In incident response, a signal starts triage, containment, diagnosis, recovery,
and learning. Diagnosis may invoke log collection, reproduction, or vendor
coordination. A recovered dependency does not close the incident. The incident
commander still decides whether the service is stable, customers were notified,
and follow-up work has an owner.

In creative production, a brief leads to exploration, selection, production,
critique, and delivery. A film, exhibition, or campaign may contain writing,
visual-development, editing, sound, legal-clearance, and accessibility loops.
One approved shot does not authorize publication of the whole work.

In governance, observation leads to a proposal, consultation, decision,
implementation, and review. Consultation can contain expert, community, legal,
and financial review loops. A consultation receipt informs the decision
authority; it does not vote on the proposal by itself.

Software delivery is one more binding of this pattern. Requirements,
implementation, testing, release, and operations each contain feedback and may
invoke smaller loops. A passing test reports what it observed about one
candidate. It neither accepts the product nor grants permission to publish.

The common problem is not iteration. It is deciding:

- which activities are children of which parent;
- which feedback stays local to one loop;
- what each boundary accepts and returns;
- what evidence supports a result;
- who may execute, verify, accept, publish, or escalate;
- what budgets force a terminal outcome; and
- how the active system may be replaced.

## The historical claim should stay honest

Concord Loom does not claim to invent loops, hierarchy, or iterative work.
Software-process research supplies one well-documented lineage. Winston Royce's
[1970 paper on large software systems](https://cse.msu.edu/~cse435/Homework/HW3/royce1970.pdf)
described feedback between successive phases, warned about discovering major
problems at test time, and recommended an early pilot, documentation, and
customer review. Barry Boehm's
[spiral model](https://doi.org/10.1109/2.59) made repeated, risk-driven cycles
central to development and enhancement.

The public description of the
[IEEE/ISO/IEC 12207-2026 life-cycle standard](https://standards.ieee.org/ieee/12207/11416/)
says that processes may be applied concurrently, iteratively, and recursively
to a software system and its elements. Deming's
[Plan-Do-Study-Act model](https://deming.org/explore/pdsa/) treats improvement
as repeated, evidence-producing learning. David Harel's
[statecharts](https://doi.org/10.1016/0167-6423%2887%2990035-9) extended state
machines with hierarchy, concurrency, and communication in 1987.

Modern guidance also composes concerns rather than imposing one universal
process. NIST's
[Secure Software Development Framework](https://csrc.nist.gov/pubs/sp/800/218/final)
defines outcome-oriented security practices that organizations integrate into
their chosen life cycles. Security crosses requirements, design,
implementation, verification, release, and response.

These precedents support a narrow claim:

> The contribution is not nested loops. It is a portable boundary for governing
> their composition, evidence, authority, execution facts, and evolution as a
> versioned artifact chain.

“Executable” does not mean hiding arbitrary code in a diagram. It means that a
validator can reject invalid declarative structures, an adapter can execute
within a bound contract, and a consequential claim can point to exact candidate,
policy, attempt, and evidence identities.

## One grammar, many bindings

Concord Loom treats a domain process as a binding of a general change grammar:

```text
observe
  → negotiate
  → bind
  → execute
  → verify
  → publish an authorized effect, or record none
  → evolve by proposing a successor
```

**Observe.** Record facts with provenance and limits. Observation may include
files, measurements, interviews, sensor readings, prior decisions, or runtime
events. It can also produce explicit hypotheses, but it cannot accept them.

**Negotiate.** Ask the questions whose answers would change the proposed
system. An accountable operator confirms, rejects, or corrects consequential
intent. Confidence can rank a question; it cannot answer it.

**Bind.** Compile accepted intent into exact loop contracts, policy, scope, and
authority. Binding fails on cyclic containment, unbounded feedback,
unreachable terminal outcomes, or unauthorized capability expansion.

**Execute.** Produce one scoped candidate or effect under the active binding.
A candidate may be a dataset, recovery action, creative master, policy package,
or software tree. The binding, not the framework, defines its meaning.

**Verify.** Evaluate the pinned candidate against an evidence contract.
Verification records what the evidence supports. It does not inherit authority
from execution, and independent review may require a different principal.

**Publish.** Perform an explicitly authorized external effect. Publication
might release a dataset, restore traffic, deliver a master, enact a rule, deploy
software, or intentionally do nothing. A passed verification gate is evidence,
not publication authority.

**Evolve.** Reduce repeated, content-addressed signals into a reviewable
successor proposal. The active binding states who may accept and activate that
proposal.

This sequence is a grammar, not a mandatory workflow engine. A binding may omit
irrelevant detail, specialize labels, or delegate execution to laboratory
systems, incident tooling, production software, committee procedure, CI, local
processes, or agent graphs.

## Two graphs, not one recursive tangle

Calling the whole system a recursive graph collapses two different
relationships.

The **containment graph** says that a composite state in one loop invokes
another loop. An experiment can invoke calibration; an incident can invoke
recovery; a production can invoke legal review. Containment explains
refinement, scope, and parent-child ownership. It must be finite and acyclic. A
loop cannot contain itself, directly or through descendants.

The **local control-flow graph** describes progress inside one loop. It may
contain feedback. An experiment can return from analysis to measurement; a
recovery loop can return from validation to mitigation; an edit can return from
critique to revision. Each feedback cycle must consume a finite budget and
retain a path to a terminal or escalation outcome.

```text
Containment (finite DAG)              Local flow (bounded)

program                               prepare → act → evaluate → ACCEPT
├── workstream                                  ▲       │
│   └── review                                  └ retry┘
└── publication                                     │
                                             budget exhausted
                                                    ▼
                                                ESCALATE
```

This separation gives recursive navigation a precise, safe meaning. An Atlas
may descend through several containment levels, but ancestry has a finite
maximum depth. Local repetition has a finite maximum number of traversals.
Containment never disguises a retry, and feedback never creates a hidden child.

Continuous operations use the same discipline. A research program, service, or
governance regime may last for years, but one run covers a bounded question,
incident, observation window, or change. A later signal starts another run.
This makes an ongoing system distinguishable from an execution that cannot
terminate.

## A minimal formal model

Let a governed system be:

```text
K = (H, {Lᵢ}, Π, V)
```

`H` is the containment graph, `{Lᵢ}` is the set of loop contracts, `Π` is the
policy that maps child receipts into parent decisions, and `V` is the versioned
binding over the exact contracts and policy.

Each loop is:

```text
Lᵢ = (I, O, S, s₀, Δ, C, E, A, B, X)
```

- `I` and `O` define input and output contracts.
- `S` and `s₀` define states and the single entry.
- `Δ` defines declarative local transitions.
- `C` defines child invocations attached to composite states.
- `E` defines evidence predicates.
- `A` defines capabilities and separation-of-duty rules.
- `B` defines attempt, time, cost, and tool budgets.
- `X` defines terminal outcomes such as `ACCEPTED`, `REVISE`, `ESCALATED`,
  and `CANCELLED`.

A containment edge records more than “parent calls child”:

```text
h = (parent, state, child, map_in, map_out, deadline, receipt_predicate)
```

The maps prevent hidden shared state from becoming the real contract. The
deadline and cancellation or escalation path bound the invocation. The receipt
predicate states what the parent may learn from the child.

A child receipt should bind at least:

```text
r = digest(
  child_contract,
  run_id,
  input_digest,
  output_digest,
  candidate_digest,
  policy_digest,
  producer,
  result,
  evidence_refs
)
```

The parent evaluates `receipt_predicate(r)` and its own evidence predicates. It
does not copy the child's terminal state. Acceptance is contextual: only the
parent knows whether the child was mandatory, the evidence set is complete, the
producer was independent, and another child invalidated the candidate.

Three structural conditions make execution finite:

1. `H` is a finite directed acyclic graph, so child nesting has bounded depth.
2. Every cyclic strongly connected component in a local `Δ` has a ranking
   function over a well-founded budget. Each feedback traversal strictly
   decreases that ranking; no transition in the component restores it.
3. Budget exhaustion, timeout, and cancellation each lead to a terminal or
   escalation state, while every reachable nonterminal state retains such a
   path.

These conditions establish structural termination, not correctness. A
validator cannot prove that an experiment answers a valuable question, a
recovery restored customer trust, a creative judgment was good, a policy was
just, or a test oracle was complete.

## Truth needs more than green and red

A governed system preserves distinct truth states:

| State | Meaning |
|---|---|
| **Observed** | A sourced fact or measurement was recorded |
| **Proposed** | Someone or something suggested an interpretation or change |
| **Accepted** | An authorized operator accepted exact intent or structure |
| **Planned** | A route, role, budget, or tool use was declared for a run |
| **Actual** | An attempt recorded what principal, agent, tools, scope, and result actually occurred |
| **Verified** | Evidence bound to exact bytes and policy met a declared contract |

These states do not promote themselves. Repository history, sensor data, and
interviews are evidence, not product intent. A proposal is not an accepted
binding. A plan is not an attempt. An attempt is not verification. Verification
is not permission to publish.

Repository analysis illustrates the boundary. [PyDriller](https://pydriller.readthedocs.io/en/latest/processmetrics.html)
exposes commit-derived process metrics, while
[CodeScene's change-coupling model](https://codescene.io/docs/guides/technical/change-coupling.html)
uses co-change to reveal logical dependencies. The
[SCIP protocol](https://github.com/scip-code/scip) provides
language-agnostic symbol indexing, and
[Aider's repository map](https://aider.chat/docs/repomap.html) ranks symbols for
bounded context. Each can ground an observation. None can decide that an
observed structure is intended or authorized.

An Atlas must therefore display accepted structure, plans, attempts, evidence
references, and drift as separate layers. Missing runtime evidence means “not
recorded,” not “failed” or “passed.”

## Evidence and authority cross every domain

Evidence answers “what supports this claim?” Authority answers “who may make
this decision or effect?” They interact, but neither substitutes for the other.

A research instrument may produce calibrated measurements, while the principal
investigator accepts the interpretation. A monitoring system may show stable
latency, while an incident commander authorizes traffic restoration. A legal
review may clear a soundtrack, while a producer approves the final master. A
public consultation may record responses, while a named body enacts policy. A
test suite may pass, while a release authority decides whether to deploy.

A useful evidence contract names:

- required claims and accepted results;
- candidate and policy binding requirements;
- payload identity and producer;
- reviewer capability and independence when required; and
- the parent decision that may consume the receipt.

A useful authority policy names:

- principals, roles, and capabilities;
- permitted read, write, network, and external-mutation scope;
- separation between authorship, review, acceptance, and publication; and
- the existing authority that may activate a successor.

`PASSED` means that a node met its declared evidence contract for its pinned
candidate. It does not grant release, enactment, publication, or product
authority.

## Worked bindings

### Research

A clinical methods program contains a sample-preparation loop and an analysis
loop. Preparation reports temperature, reagent lot, operator, and quality
controls for specimen set `S4`. Analysis reports a result for `S4` under
protocol `P2`. The program parent rejects an analysis receipt for `S3`, even if
that receipt passed. It also requires an independent statistical review before
accepting the conclusion. A later protocol change makes old receipts stale
unless an explicit policy defines a narrower reuse rule.

### Incident response

An incident parent invokes containment and recovery. Containment blocks a
faulty dependency and reports the exact services and time window affected.
Recovery restores traffic in two bounded stages, then reports health evidence.
Neither child may declare the incident closed. The incident commander evaluates
customer impact, residual risk, and communication obligations. If the recovery
budget expires, the loop escalates instead of retrying indefinitely.

### Creative production

A campaign parent invokes copy, visual, accessibility, and legal-clearance
loops. Each child returns a receipt for the same master revision. If the copy
changes after accessibility review, that receipt no longer verifies the current
master. The producer may accept the creative package only after every mandatory
receipt matches the pinned revision; a separate principal may hold publication
authority.

### Governance

A rulemaking parent invokes impact analysis, consultation, and legal review.
The consultation loop records coverage, responses, and unresolved objections.
It does not decide the rule. The authorized body evaluates the combined
evidence, records its rationale, and either accepts, revises, or rejects the
proposal. The adopted rule cannot silently broaden the mechanism that governs
its own successor.

### Software delivery

Consider service candidate `C7` under policy `P3`. A testing parent requires API
contract, database migration, authorization, and performance children, plus an
independent producer and complete candidate-bound receipts.

The migration child receives an immutable database image and `C7`:

```text
prepare → migrate → verify → rollback → verify_restore → report
             ▲         │
             └ diagnose┘
```

The first attempt fails because the isolated fixture lacks an extension.
Diagnosis classifies environment drift, preparation repairs the fixture, and
the second attempt succeeds. The child emits a `PASS` receipt for `C7/P3` with
logs, snapshots, rollback observations, attempt count, and producer identity.
Its retry budget is exhausted; a third attempt would escalate.

An authorization child reports that an endpoint accepts an expired token. Its
`REVISE` receipt also binds to `C7/P3`, so the testing parent returns `REVISE`
despite other green children. Implementation produces `C8`, which makes every
receipt bound only to `C7` stale. Once all mandatory children return valid
receipts for `C8/P3`, the testing parent may emit its own `PASS` receipt.

The delivery parent still requires a release build, independent review, and
publication decision. The test receipt supplies evidence; it does not grant
release authority.

## Concord Loom as its own worked binding

Concord Loom can govern changes to Concord Loom without defining software
delivery as the framework's boundary. Its accepted self-binding uses one root,
`concord-change`, with domain-neutral child loops:

```text
concord-change
├── observe
├── negotiate
├── bind
├── execute
├── verify
├── publish
└── evolve
```

This binding is evidence that the general grammar can describe the repository's
own change path. It is not universal intent inferred from repository history:
an operator corrected and accepted that intent, then separately accepted the
loop design and activated the exact binding.

Self-application does not give the framework special authority. The active
binding scopes execution, independent verification remains separate, publish
performs only an explicitly authorized effect, and evolution emits a successor
proposal with `activation_allowed: false`. The current binding decides who may
activate the next one.

The self-binding is also not mandatory for adopters. A laboratory, studio,
operations team, public body, or software project defines its own policy,
artifacts, identities, evidence, and loop topology.

## Runtime and generated-view boundaries

Concord Loom v0.1 validates containment, local state contracts, candidate
identity, authority, and evidence boundaries. Its portable runner treats each
planned loop node as one governed execution unit. It does not step every local
transition, schedule durable child workflows, stream live execution, or
synthesize child receipts into parent acceptance.

Dedicated systems can provide execution. Temporal defines
[Child Workflows](https://docs.temporal.io/child-workflows) with their own
histories and parent-close behavior. LangGraph defines
[subgraphs](https://docs.langchain.com/oss/python/langgraph/use-subgraphs) with
state-mapping and persistence choices. Laboratory systems, incident platforms,
production suites, committee processes, CI, and local executors can play the
same adapter role.

Execution capability does not establish governed intent, evidence validity, or
authority. Concord Loom binds adapter attempts and receipts to accepted
contracts; it does not replace the adapters.

The Atlas is a generated projection of accepted artifacts and recorded run
facts. It can explain the system and expose drift. It cannot change a binding,
authorize a transition, revalidate referenced payload bytes, or become a source
of truth by being edited.

## The evolution loop

No initial binding remains correct forever. Repeated timeouts, unused evidence,
ambiguous questions, failed handoffs, or unnecessary gates are signals about
the system itself.

```text
observe bounded signals
  → diagnose contract or routing friction
  → propose a graph or policy delta
  → assess risk and compatibility
  → accept or reject under existing authority
  → activate a successor binding
  → observe again
```

The active version `Vₙ` defines who may accept `Vₙ₊₁`. The proposal cannot grant
itself that capability. Activation appends a successor to a catalog and keeps
prior bindings addressable. In-flight runs continue to point to their original
binding.

This rule blocks a seductive failure mode: treating repeated friction as
permission to remove the gate that reports the friction. Evolution may propose
new budgets, evidence, authority, or loop boundaries. Existing authority
decides whether to accept the exact successor bytes.

## Related work and explicit non-claims

Concord Loom composes established ideas:

- iterative and recursive process models;
- risk-driven iteration from spiral development;
- learning cycles from PDSA;
- hierarchy and concurrency from statecharts;
- outcome-oriented practices such as SSDF;
- parent-child execution from durable workflow systems;
- subgraph composition from graph runtimes; and
- evidence discovery from domain tools, semantic indexes, and history mining.

It does **not** claim to invent any item in that list. It does not claim that
every activity deserves a loop, every organization should share a topology, or
a containment DAG models every relationship. Communication, dependency, and
shared-resource graphs may contain other structures; only execution containment
must remain acyclic.

It makes no productivity, quality, safety, artistic, scientific, or governance
claim without comparative evidence. Validation can establish schema
conformance, digest integrity, bounded control flow, and some authority
invariants. It cannot establish that evidence is truthful at its physical
source or an authorized decision was wise.

Concord Loom is not a game engine, hosting platform, model provider, workflow
runtime, operating-system sandbox, credential authority, or repository layout.
Portable principal identifiers support accountability and separation checks;
deployments that need adversarial identity assurance must add platform
enforcement and signed attestations.

The testable contribution is an integration boundary: represent a bounded
system of loops, its evidence rules, authority, execution facts, and evolution
as one content-addressed artifact chain; validate that chain; and make each
claim traceable to a candidate and policy.

## A research and evaluation agenda

Evaluation should compare a governed loop system with the same work expressed
in conventional workflow and prose forms. Useful measures include:

- detection of stale-candidate and wrong-policy evidence;
- time required to explain why a parent remains open;
- frequency and cause of budget exhaustion or escalation;
- divergence between planned and actual execution;
- operator effort per accepted change;
- false-positive rates in inferred loop boundaries; and
- comprehension across domain and containment levels.

Domain studies should test whether the grammar transfers without erasing local
meaning. Research users may need protocol and data lineage; incident teams,
real-time authority and rollback; creative teams, revision and rights lineage;
governance users, consultation and decision records; software teams, candidate
and release identity.

Adversarial tests matter as much as usability tests. A system should fail
closed when evidence names another candidate, a child broadens parent scope, an
author occupies an independent-review role, feedback lacks a decreasing budget,
an inferred relationship seeks authority, or an evolution proposal activates
itself.

The Atlas needs separate study. A valid graph can still be unreadable.
Operators must distinguish containment from feedback, move between levels,
inspect evidence and authority at a boundary, and understand which facts remain
unverified.

## Conclusion

Many consequential systems are cycles of cycles. Their domains differ, but the
governance problem repeats: make boundaries, evidence, authority, budgets,
terminal outcomes, and succession explicit.

Concord Loom supplies a general grammar for that problem. It keeps containment
finite, feedback bounded, truth states distinct, child receipts subordinate to
parent decisions, and evolution unable to authorize itself. A domain binding
then gives those rules concrete meaning without turning one worked case into
the product boundary.
