# Observed landscape

Date: 2026-07-24

This note records the evidence used to set Concord Loom's v0.1 boundary. It is
an observation, not a claim that inferred project intent is correct.

## What existing tools already do

The problem has strong neighboring solutions:

- [SCIP](https://github.com/scip-code/scip) is a language-agnostic interchange
  format for definitions, references, and implementations.
- [CodeQL](https://codeql.github.com/docs/codeql-overview/about-codeql/)
  extracts language-specific relational databases with syntax, name binding,
  data-flow, and control-flow information.
- [Aider's repository map](https://aider.chat/docs/repomap.html) ranks code
  symbols to fit useful repository context into a token budget.
- [Temporal child
  workflows](https://docs.temporal.io/child-workflows) and [LangGraph
  subgraphs](https://docs.langchain.com/oss/python/langgraph/use-subgraphs)
  compose executable workflows.
- Change-coupling and repository-archaeology tools derive relationships from
  co-change, churn, ownership, and time.

Concord Loom must not compete by inventing another universal parser, graph
database, or durable workflow runtime. Those are adapters or execution targets.

## The missing governed chain

The v0.1 hypothesis is a chain of distinct, provenance-preserving artifacts:

1. An **observed project graph** records structural and historical facts.
2. An **inferred graph** records hypotheses with sources and confidence.
3. A minimal operator interview accepts, rejects, or corrects high-impact
   hypotheses.
4. An **accepted project graph** records the resulting decisions.
5. A compiler derives bounded loop contracts, routing policy, and Atlas data.
6. Run cards separate planned routing from hash-bound actual execution.
7. Execution signals may propose a successor graph, but cannot activate it.

The defensible contribution is not nested loops by themselves. It is governing
their composition, evidence, authority, and evolution as a repository-bound,
versioned artifact.

## Clean extraction decisions

- Start a new history and Apache-2.0 codebase.
- Reimplement only generic invariants; do not copy product-specific catalogs,
  paths, node names, generated snapshots, or skills.
- Use Python 3.11+ and the standard library for the portable core.
- Treat Git as the v0.1 observation source. Make richer semantic indexes
  optional adapters.
- Store canonical artifacts as deterministic JSON.
- Render the Atlas offline from the same accepted graph and run-card data that
  the harness validates.
- Keep the first release single-repository and local-first. Exclude hosted
  services, multi-repository identity, and arbitrary model-provider APIs.

## Risks found before implementation

- A containment hierarchy is not enough to model a cycle. The schema needs an
  acyclic `contains` relation and separate bounded feedback transitions.
- Passing child evidence cannot automatically close a parent gate.
- Evidence and review must bind to candidate bytes, not only a policy version.
- Review independence must be enforced rather than described.
- A path guard is a fail-closed authorization check, not a filesystem sandbox.
- Repository history is a fossil record. Co-change is evidence of a
  relationship, not proof of desired architecture.
- Generated HTML can drift unless generation and validation share canonical
  input.

## Brand observation

`Concord Loom` describes operator concord and the weaving of evidence,
decisions, and nested loops. Exact-name checks found no obvious GitHub, PyPI, or
npm collision on 2026-07-24. This is an engineering name check, not legal
clearance.

