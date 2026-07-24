# Cycles of Cycles: From Loop Engineering to Governed Software Delivery Systems

*Why an SDLC is a hierarchy of bounded feedback loops—and how to make that
hierarchy executable, verifiable, and evolvable*

## Abstract

Software delivery is often drawn as one loop: learn, build, verify, release,
observe, repeat. That picture hides the machinery inside each step.
Requirements work revisits hypotheses. Design compares alternatives.
Implementation compiles and repairs. Testing launches many scenario-level
experiments. Release and operations have their own feedback paths. A software
development life cycle is therefore better understood as a cycle composed of
cycles.

The nesting itself is not new. Iterative life-cycle models, spiral development,
hierarchical state machines, continual-improvement cycles, child workflows, and
subgraphs all precede this article. The useful next step is to govern their
composition. Each loop needs a typed contract, explicit evidence, bounded
feedback, named decision authority, terminal outcomes, and a precise rule for
how a child result affects its parent. The whole arrangement should be a
versioned, machine-validated artifact rather than a diagram whose meaning lives
in meetings.

This article calls that practice **loop engineering** and describes its system
form: a **governed software delivery system**. It separates a finite acyclic
containment graph from bounded local feedback graphs; keeps observation,
inference, acceptance, plans, execution, and verification distinct; and treats
process evolution as another governed loop. The aim is modest but concrete:
make the delivery system inspectable, executable, and falsifiable without
pretending that automation can replace product judgment.

## The SDLC was never one loop

A familiar SDLC drawing places requirements, design, implementation, testing,
release, and operations around a circle. The arrow from operations back to
requirements correctly says that delivered software changes what the team
knows. The boxes, however, suggest that each phase is atomic. None is.

A requirements team proposes behavior, checks it against constraints, resolves
conflicts, and revises the proposal. A design team models alternatives,
prototypes the riskiest parts, reviews the result, and either selects or
reworks an option. An implementation task moves through edit, build, diagnose,
and repair. A testing task plans coverage, prepares an environment, executes
scenarios, interprets observations, and decides whether to retest. Release
work packages, signs, approves, publishes, and smoke-tests the exact artifact.
Operations observes a bounded window, triages anomalies, mitigates incidents,
and turns learning into new intent.

The outer delivery loop therefore contains child loops:

```text
delivery
├── requirements
├── design
├── implementation
├── testing
│   ├── contract scenarios
│   ├── migration scenarios
│   ├── security scenarios
│   └── performance scenarios
├── release
└── operations
```

Testing makes the nesting easiest to see. “Run the tests” is not one action.
Each runtime scenario has its own setup, stimulus, observation, oracle,
cleanup, and disposition. A failed scenario can invoke a diagnosis loop. A
flaky environment can invoke a bounded recovery loop. The testing parent then
evaluates a set of scenario receipts against its own coverage and independence
rules. A passing scenario does not pass the testing campaign, just as a passing
testing campaign does not authorize a release.

This view also avoids a false choice between linear and iterative development.
Ordering and feedback coexist. A release must use a built candidate, so some
edges are directional. A test result can force implementation revision, so
other edges carry feedback. The engineering problem is to state which
relationship applies, who may traverse it, what evidence the traversal
requires, and when it must stop.

## The historical claim should stay honest

Nesting and iteration have a long lineage. Winston Royce's
[1970 paper on large software systems](https://cse.msu.edu/~cse435/Homework/HW3/royce1970.pdf)
did not simply prescribe a one-pass sequence. It described feedback between
successive phases, warned about discovering major problems at test time, and
recommended deliberate measures such as an early pilot, documentation, and
customer review. Barry Boehm's
[spiral model](https://doi.org/10.1109/2.59) made repeated,
risk-driven cycles central to development and enhancement.

The current [IEEE/ISO/IEC 12207-2026 life-cycle standard](https://standards.ieee.org/ieee/12207/11416/)
goes further than a stage diagram: its public description says that processes
may be applied concurrently, iteratively, and recursively to a software system
and its elements. Deming's
[Plan-Do-Study-Act model](https://deming.org/explore/pdsa/) treats improvement
as repeated, evidence-producing learning. David Harel's
[statecharts](https://doi.org/10.1016/0167-6423%2887%2990035-9) extended state
machines with hierarchy, concurrency, and communication in 1987. These are
substantial precedents, not footnotes to erase.

Modern delivery guidance also composes concerns rather than replacing one
universal process with another. NIST's
[Secure Software Development Framework](https://csrc.nist.gov/pubs/sp/800/218/final)
defines outcome-oriented security practices that organizations integrate into
their chosen SDLC implementations. Security work cuts through requirements,
design, implementation, verification, release, and response; it does not fit
honestly into one late “security” box.

The claim here is therefore narrower:

> The novelty is not nesting loops. It is governing their composition,
> evidence, authority, and evolution as one versioned executable artifact.

“Executable” does not mean embedding arbitrary code in a process diagram. It
means that a conforming execution adapter can interpret finite declarative
contracts, a validator can reject unsafe structures, and every consequential
transition can point to content-addressed evidence and policy.

## Two graphs, not one recursive tangle

Calling everything a recursive graph collapses two different relationships.
A governed system needs both, and must display them differently.

The **containment graph** says that a composite state in one loop invokes
another loop. Testing contains a migration-scenario loop; the migration
scenario may contain a bounded environment-preparation loop. Containment
explains refinement and ownership. It must be finite and acyclic. A loop cannot
contain itself, directly or through descendants.

The **local control-flow graph** describes progress within one loop. It may
contain feedback. A testing loop can move from interpretation back to execution
after a repair; an implementation loop can move from a failed build back to
editing. These cycles are useful only when they consume a finite budget and
retain a path to a terminal or escalation outcome.

```text
Containment (finite DAG)             Local testing flow (bounded)

delivery                             plan → execute → interpret → decide → PASS
└── testing                                    ▲          │
    └── scenario                               └─ retry ──┘
                                                   │
                                           budget exhausted
                                                   ▼
                                               ESCALATE
```

This separation gives “recursive navigation” a safe meaning. The same loop
contract can appear at every level, and an Atlas can descend from parent to
child. Runtime ancestry, however, has a finite maximum depth. Local repetition
has a finite maximum number of traversals. We get compositional structure
without unbounded recursion.

Continuous work needs the same discipline. Operations may continue for years,
but an individual operations run can cover one incident or one observation
window and then end. A later signal starts a new run. This produces durable
history and makes “still running” distinguishable from “unable to terminate.”

## A minimal formal model

Let a governed delivery system be:

```text
K = (H, {Lᵢ}, Π, V)
```

Here, `H` is the containment graph, `{Lᵢ}` is the set of loop contracts, `Π`
is the policy that maps child receipts into parent decisions, and `V` is the
versioned binding over the exact contracts and policy.

Each loop is:

```text
Lᵢ = (I, O, S, s₀, Δ, C, E, A, B, X)
```

- `I` and `O` define its input and output contracts.
- `S` and `s₀` define its states and single entry.
- `Δ` defines declarative local transitions.
- `C` defines child invocations attached to composite states.
- `E` defines evidence predicates.
- `A` defines required capabilities and separation-of-duty rules.
- `B` defines attempt, time, cost, and tool budgets.
- `X` defines terminal outcomes such as `ACCEPTED`, `REVISE`, `ESCALATED`,
  and `CANCELLED`.

A containment edge records more than “parent calls child”:

```text
h = (parent, state, child, map_in, map_out, deadline, receipt_predicate)
```

The input and output maps prevent hidden shared state from becoming the real
contract. The deadline and cancellation or escalation path bound the
invocation. The receipt predicate tells the parent exactly what it may learn
from the child.

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

The parent evaluates `receipt_predicate(r)` and its own evidence predicates.
It does not copy the child's terminal state. This rule matters because
acceptance is contextual. A scenario can truthfully report that one behavior
passed on one candidate under one policy. Only its parent knows whether that
scenario was mandatory, whether the full set is complete, whether the producer
was independent, and whether another child invalidated the candidate.

Three structural conditions make execution finite:

1. `H` is a finite directed acyclic graph, so child nesting has bounded depth.
2. Every cyclic strongly connected component in a local `Δ` has a ranking
   function over a well-founded budget. Each feedback traversal strictly
   decreases that ranking; no transition inside the component restores it.
3. Budget exhaustion, timeout, and cancellation each lead to a terminal or
   escalation state, while every reachable nonterminal state retains such a
   path.

These conditions establish contract-level structural termination, not business
correctness. They ensure that a conforming runtime has a finite containment
depth and explicit bounded exits. A validator cannot prove that an adapter
enforced the contract or that a reviewer made a wise product decision.
Governance must preserve that boundary instead of laundering judgment into a
green machine status.

### Model and v0.1 execution boundary

The formal model describes the semantics that a governed delivery system and
its execution adapters should preserve. Concord Loom v0.1 compiles and
validates containment, local flow, budgets, evidence, and authority; its run
harness pins candidates and records factual attempts and evidence for planned
loop nodes. It does not step every transition, schedule durable child
workflows, or synthesize a child receipt into parent evidence. CI systems,
workflow engines, agent graphs, and local executors perform that work.

The harness therefore refuses the unsafe shortcut—one child's green status
never closes its parent—but a v0.1 adapter must explicitly deliver the
candidate-bound child result that the parent's own evidence contract consumes.
The worked example below specifies the intended composition semantics, not a
claim that the portable CLI simulates the scenario state machine.

## Worked example: a testing loop inside a delivery loop

Consider a service candidate `C7`. The outer delivery run pins `C7`, policy
`P3`, and a testing contract. The testing parent requires four child classes:
API contract, database migration, authorization, and performance. It also
requires an independent testing producer, one receipt for every mandatory
scenario, matching candidate and policy digests, and a parent-level review of
coverage.

The migration child receives an immutable database image and `C7`. Its local
states are:

```text
prepare → migrate → verify → rollback → verify_restore → report
             ▲         │
             └ diagnose┘
```

The child has two execution attempts and a 20-minute deadline. A first
migration attempt fails because the test environment lacks an expected
extension. Diagnosis classifies this as environment drift, preparation repairs
the isolated fixture, and the second attempt succeeds. The child emits a
`PASS` receipt for `C7/P3` with logs, schema snapshots, rollback observations,
attempt count, and producer identity. The retry budget is now exhausted; a
third attempt would escalate rather than silently loop.

Meanwhile, an authorization scenario finds that a privileged endpoint accepts
an expired token. Its `REVISE` receipt also binds to `C7/P3`. The testing
parent must return `REVISE`, even though the migration child passed and most
other scenarios did too. Counting green children cannot override a mandatory
failure.

Implementation produces candidate `C8`. This change makes every receipt bound
to `C7` stale. Reusing the successful migration receipt would be convenient,
but it would assert something never observed about `C8`. The next testing run
must execute the required scenarios against `C8`, or an explicit policy must
define a sound, narrower reuse rule.

Suppose all mandatory children now return valid receipts for `C8/P3`. The
testing parent performs its own checks: every required scenario is present,
the evidence set covers the accepted test model, the producer satisfies the
independence rule, no receipt reports truncation, and all digests agree. Only
then does the testing loop emit its own `PASS` receipt.

The outer delivery loop still remains open. Its contract also requires a clean
release build, a release-readiness review, and an authorized publication
decision. The test receipt supplies evidence; it does not grant release
authority. After publication, a smoke-test child verifies the published bytes,
and an operations child observes a defined window. Each level closes only by
its own contract.

This example exposes five failure modes that a flat pipeline hides:

- a child passes a different candidate;
- a retry succeeds after exceeding the agreed budget;
- a required scenario never ran;
- an author certifies work that requires independent review;
- a valid test result is mistaken for permission to publish.

Typed receipts and parent predicates make each error detectable.

## From loop engineering to a governed delivery system

Loop engineering starts with a local question: what feedback mechanism does
this activity need? A useful loop contract states the objective, input,
terminal output, evidence, authority, budgets, and escalation path. It avoids
the vague instruction “iterate until good.”

A governed delivery system adds composition and provenance. A practical
construction path looks like this:

```text
repository evidence
  → observed and inferred project graph
  → high-impact operator questions
  → accepted project graph
  → proposed loop design
  → explicit acceptance of the proposal digest
  → compiled registry and binding proposal
  → explicit binding activation
  → governed runs and evidence
  → evolution proposal
```

The distinctions along this path are more important than the arrows.

**Observation is not intent.** Source imports, build files, CI definitions,
ownership files, commit churn, and co-change can reveal how a repository
behaves. They cannot declare why the organization wants that behavior.
Repository-mining tools already provide useful inputs:
[PyDriller](https://pydriller.readthedocs.io/en/latest/processmetrics.html)
exposes commit-derived process metrics, while
[CodeScene's change-coupling model](https://codescene.io/docs/guides/technical/change-coupling.html)
uses co-change to reveal logical dependencies. Both are evidence. A co-change
edge may indicate a real boundary, generated files, or an unhealthy coupling.
It remains an inference until an accountable operator decides.

**A code graph is not a project graph.** The
[SCIP protocol](https://github.com/scip-code/scip) provides
language-agnostic symbol indexing for definitions and references.
[Aider's repository map](https://aider.chat/docs/repomap.html) ranks code
symbols to fit relevant repository context into a token budget. Such
techniques can ground structural observations. A project graph must also
represent decisions, ownership, runtime evidence, release boundaries, and
uncertainty. The framework should preserve source references and confidence,
then ask the operator only questions whose answers materially change the
proposed loop system.

**Acceptance is not compilation.** A model can propose a loop boundary, but an
explicit actor must accept the exact proposal digest. Compilation can then
reject unreachable states, cyclic containment, unbounded feedback, authority
escalation, and missing terminal paths. The resulting binding identifies an
exact registry and policy. “Use the current workflow” is not reproducible;
“use binding digest `B`” is.

**A plan is not an attempt, and an attempt is not verification.** A run card
may plan an executor, model, skill, tool set, budget, and reviewer. Runtime
records must state what actually executed. Verification needs evidence bound
to those facts and to the exact candidate. An Atlas should show planned,
actual, verified, and drift as separate layers.

**Completion is not authority expansion.** Passing a technical gate does not
grant product acceptance, release approval, or publication permission.
Capabilities should be explicit and separable. The author of a candidate may
run local checks; a bound policy may still require a different principal for
independent review and another authority for publication.

## Why hierarchy alone is insufficient

Workflow systems already execute nested work. Temporal defines
[Child Workflows](https://docs.temporal.io/child-workflows) with their own
execution histories and explicit parent-close behavior. LangGraph defines
[subgraphs](https://docs.langchain.com/oss/python/langgraph/use-subgraphs) as
graphs used as nodes in parent graphs, with documented state-mapping and
persistence choices. These systems demonstrate that parent-child execution is
practical and useful.

They also help clarify the additional governance layer. A durable child
workflow tells us that execution occurred and how its lifecycle relates to the
parent. A subgraph interface tells us how state moves across a boundary.
Neither fact alone says that:

- the operator accepted this decomposition as project intent;
- the child ran against the candidate now under review;
- its producer held the required capability;
- its result satisfies the parent's evidence predicate;
- the active policy permits the parent to close; or
- the process may rewrite its own governing policy.

A governed loop model can execute on a dedicated workflow engine, an agent
graph, CI jobs, local processes, or a mixed adapter layer. It should not
pretend to replace those runtimes. Its job is to bind their attempts and
receipts to accepted contracts.

## The meta-loop: evolving the delivery system

No first process model remains correct forever. A testing loop accumulates
repeated timeouts. A release gate produces evidence no parent consumes. A
question repeatedly requires manual correction. These are signals about the
delivery system itself.

The response is a meta-loop:

```text
observe runs
  → aggregate bounded signals
  → diagnose contract or routing friction
  → propose a graph/policy delta
  → assess risk and compatibility
  → accept or reject under existing authority
  → activate a successor binding
  → observe again
```

This loop must not self-authorize. The active version `Vₙ` defines who may
accept a proposal for `Vₙ₊₁`; the proposal cannot grant itself that capability.
Activation appends a successor to a catalog and leaves prior bindings
addressable. In-flight runs continue to point to their original version.

This rule turns “continuous process improvement” into an auditable transition.
It also protects against a seductive failure mode in adaptive agent systems:
interpreting repeated friction as permission to remove the gate that reports
the friction. Evolution may propose fewer checks, different budgets, or a new
loop boundary. Existing authority decides whether the evidence justifies the
change.

## Related work and explicit non-claims

This proposal composes established ideas:

- iterative and recursive life-cycle processes from software-engineering
  standards and process models;
- risk-driven iteration from spiral development;
- learning cycles from PDSA;
- hierarchy and concurrency from statecharts;
- outcome-oriented secure-development practices from SSDF;
- parent-child execution from durable workflow systems;
- subgraph composition from graph runtimes; and
- repository structure and history from semantic indexes and mining tools.

It does **not** claim to invent any item in that list. It does not claim that
every activity deserves its own loop, that all organizations should share one
loop topology, or that a containment DAG models every organizational
relationship. Communication, dependencies, and shared resources can form
other graphs; only execution containment needs the acyclic restriction
described here.

It also makes no productivity, quality, or safety claim without comparative
evidence. Machine validation can establish schema conformance, digest
integrity, bounded control flow, and some authority invariants. It cannot
establish that requirements are valuable, a test oracle is complete, evidence
is truthful at its physical source, or an authorized human chose well.
Operating-system isolation, credential assurance, and tamper-resistant
identity remain deployment concerns beyond a portable declarative core.

The testable contribution is an integration boundary: represent nested
delivery loops, their evidence rules, authority, budgets, and evolution in one
content-addressed artifact chain; compile and validate that chain; and make
every runtime claim traceable to its candidate and policy.

## A research and evaluation agenda

The idea becomes useful only if evaluation can falsify it. Early studies should
compare a governed loop system with the same delivery process expressed in
conventional pipeline and prose forms. Useful measures include:

- how often reviewers detect stale-candidate or wrong-policy evidence;
- time required to explain why a parent gate remains open;
- frequency and cause of budget exhaustion or escalation;
- divergence between planned and actual execution routes;
- operator effort per accepted graph change;
- false-positive rates in repository-derived loop hypotheses; and
- stability of accepted loop boundaries across project revisions.

Adversarial tests matter as much as usability tests. A candidate should fail
closed when evidence names another candidate, an inferred edge seeks execution
authority, a child broadens its parent's scope, an author occupies an
independent-review role, a feedback SCC lacks a decreasing budget, or an
evolution proposal tries to activate itself.

Finally, the Atlas deserves separate study. A mathematically valid hierarchy
can still be unusable. Operators must be able to descend one level at a time,
distinguish containment from feedback, inspect the evidence and authority at a
boundary, and return to the parent without losing context. Comprehension is a
runtime quality, not a schema property.

## Conclusion

Software delivery is a cycle of cycles. Requirements, design,
implementation, testing, release, and operations each learn through feedback,
and each can invoke smaller loops. Treating those loops as boxes hides the
contracts that make them safe.

Loop engineering makes the contracts explicit. A governed software delivery
system then binds their composition, evidence, authority, budgets, execution,
and evolution to exact versions. Its central law is simple: a child reports
what it proved; the parent decides what that proof means. With finite
containment, bounded local feedback, and non-self-authorizing evolution, a
recursive-looking delivery system can remain understandable, terminable, and
accountable.
