# Generic nested SDLC example

This example is deliberately small and product-neutral. It models an outer
delivery loop containing requirements, implementation, testing, release, and
operation loops. Testing invokes a runtime-scenario loop.

The directories are produced at different stages:

- `inspection/` contains observed graph, questions, decisions, and accepted
  graph examples.
- `runtime/` contains the accepted loop registry, binding, candidate manifest,
  run card, and evidence examples.

The important distinction is visible in both data and Atlas:

- containment is a finite DAG;
- local state transitions may feed back only through a finite budget and a
  terminal exhaustion path.

