#!/usr/bin/env python3
"""Regenerate the public generic SDLC example with a real digest chain."""

from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from concordloom.canonical import digest, load, save  # noqa: E402
from concordloom.catalog import append_binding  # noqa: E402
from concordloom.compiler import (  # noqa: E402
    accept_loop_design,
    activate_binding,
    compile_registry,
    create_binding_proposal,
    propose_loop_design,
)
from concordloom.graph import apply_decisions  # noqa: E402
from concordloom.interview import (  # noqa: E402
    generate_questions,
    make_decision,
    make_decision_log,
)
from concordloom.evolution import propose_evolution  # noqa: E402


EXAMPLE = ROOT / "framework" / "generic-sdlc"
EXAMPLE_INPUTS = ROOT / "examples" / "generic-sdlc"
STAMP = "2026-07-24T00:00:00Z"


def observed_graph() -> dict:
    graph = deepcopy(load(EXAMPLE / "accepted-project-graph.json"))
    graph["id"] = "generic-service"
    graph["phase"] = "observed"
    graph.pop("decision_log_digest", None)
    for node in graph["nodes"]:
        node["status"] = "observed"
        node.pop("operator_decision_id", None)
    for edge in graph["edges"]:
        edge["status"] = "observed"
        edge.pop("operator_decision_id", None)
    hypothesis = graph["hypotheses"][0]
    hypothesis["status"] = "unresolved"
    hypothesis["graph_delta"] = [
        {
            "op": "confirm",
            "target_kind": "node",
            "target_id": node["id"],
        }
        for node in graph["nodes"]
    ] + [
        {
            "op": "confirm",
            "target_kind": "edge",
            "target_id": edge["id"],
        }
        for edge in graph["edges"]
    ] + [
        {
            "op": "confirm",
            "target_kind": "hypothesis",
            "target_id": hypothesis["id"],
        }
    ]
    return graph


def main(*, check: bool = False) -> int:
    policy = load(EXAMPLE / "policy.json")
    old_design = load(EXAMPLE / "loop-design.json")
    observed = observed_graph()
    questions = generate_questions(observed)
    decision = make_decision(
        questions["questions"][0],
        "confirmed",
        actor={
            "id": "example-operator",
            "kind": "operator",
            "display_name": "Example operator",
        },
        authority_ref="operator",
        rationale=(
            "The service uses one delivery system whose SDLC stages are "
            "bounded child loops."
        ),
        decided_at="2026-07-24T00:05:00Z",
        decision_id="accept-nested-sdlc",
    )
    decisions = make_decision_log(
        observed,
        policy,
        [decision],
        log_id="generic-service-decisions",
        acceptance_actor={
            "id": "example-operator",
            "kind": "operator",
            "display_name": "Example operator",
        },
        acceptance_authority_ref="operator",
        accepted_at="2026-07-24T00:06:00Z",
    )
    accepted = apply_decisions(observed, decisions, policy)
    loop_specs = [
        {
            "id": loop["id"],
            "purpose": loop["purpose"],
            "input_outcome": loop["input_outcome"],
            "output_outcome": loop["output_outcome"],
            "basis": loop["basis"],
            "decision_ids": ["accept-nested-sdlc"],
        }
        for loop in old_design["loops"]
    ]
    containment = [
        {
            "id": edge["id"],
            "parent_loop_id": edge["parent_loop_id"],
            "child_loop_id": edge["child_loop_id"],
            "decision_id": "accept-nested-sdlc",
        }
        for edge in old_design["containment"]
    ]
    design_proposal = propose_loop_design(
        accepted,
        decisions,
        policy,
        proposal_id="generic-service-loop-design-proposal",
        loop_specs=loop_specs,
        containment=containment,
    )
    design = accept_loop_design(
        design_proposal,
        decisions,
        policy,
        accepted_graph=accepted,
        decision_id="accept-generic-loop-system",
        actor={
            "id": "example-operator",
            "kind": "operator",
            "display_name": "Example operator",
        },
        accepted_at="2026-07-24T00:07:00Z",
        authority_ref="operator",
        rationale=(
            "Accept the exact nested SDLC design, including the testing "
            "runtime-scenario child loop."
        ),
    )
    registry = compile_registry(
        accepted,
        decisions,
        design,
        policy,
        loop_design_proposal=design_proposal,
        registry_id="generic-service-cycle-registry",
    )
    paths = {
        "accepted_project_graph": "framework/generic-sdlc/accepted-project-graph.json",
        "decision_log": "framework/generic-sdlc/decision-log.json",
        "loop_design_proposal": "framework/generic-sdlc/loop-design-proposal.json",
        "accepted_loop_design": "framework/generic-sdlc/loop-design.json",
        "cycle_registry": "framework/generic-sdlc/cycle-registry.json",
        "policy": "framework/generic-sdlc/policy.json",
    }
    binding_proposal = create_binding_proposal(
        accepted,
        decisions,
        design,
        registry,
        policy,
        loop_design_proposal=design_proposal,
        artifact_paths=paths,
        proposal_id="generic-service-binding-proposal",
        created_at="2026-07-24T00:08:00Z",
    )
    binding = activate_binding(
        binding_proposal,
        accepted,
        decisions,
        design_proposal,
        design,
        registry,
        policy,
        activation_decision={
            "decision_id": "activate-generic-binding",
            "actor": {
                "id": "example-operator",
                "kind": "operator",
                "display_name": "Example operator",
            },
            "authority_ref": "operator",
            "accepted_at": "2026-07-24T00:09:00Z",
            "rationale": "Activate this exact digest chain for the example run.",
        },
        binding_id="generic-service-binding",
    )
    catalog = append_binding(
        None,
        binding,
        path="framework/generic-sdlc/binding.json",
        catalog_id="generic-service-catalog",
    )
    signals = [
        {
            "kind": "concordloom.evolution-signal",
            "schema_version": "0.1",
            "id": f"repeated-review-friction-{index}",
            "base_binding_digest": binding["binding_digest"],
            "source_digest": digest({"review_observation": index}),
            "category": "friction",
            "severity": "warning",
            "occurrences": 1,
            "summary": "Independent review repeatedly needs an explicit threat-model input.",
            "provenance": [
                {
                    "kind": "evidence",
                    "ref": f"review-observation-{index}",
                }
            ],
        }
        for index in (1, 2)
    ]
    evolution_operations = [
        {
            "op": "add",
            "target_kind": "loop",
            "target_id": "threat-model-review",
            "value": {
                "purpose": "Propose a bounded threat-model review child loop."
            },
        }
    ]
    evolution_risk = {
        "level": "medium",
        "failure_modes": ["The additional gate may delay low-risk changes."],
        "rollback": "Reject the proposal and retain the active binding.",
    }
    evolution_proposal = propose_evolution(
        binding["binding_digest"],
        signals,
        evolution_operations,
        proposed_by={"id": "example-orchestrator", "kind": "orchestrator"},
        decision_authority_ref="operator",
        expected_effect="Make recurring threat-model review friction explicit.",
        risk=evolution_risk,
        generated_at="2026-07-24T00:10:00Z",
        policy=policy,
        proposal_id="generic-service-evolution-proposal",
    )

    documents = {
        "observed-project-graph.json": observed,
        "questions.json": questions,
        "decision-log.json": decisions,
        "accepted-project-graph.json": accepted,
        "loop-design-proposal.json": design_proposal,
        "loop-design.json": design,
        "cycle-registry.json": registry,
        "binding-proposal.json": binding_proposal,
        "binding.json": binding,
        "catalog.json": catalog,
        "evolution-signal-1.json": signals[0],
        "evolution-signal-2.json": signals[1],
        "evolution-proposal.json": evolution_proposal,
    }
    for name, document in documents.items():
        path = EXAMPLE / name
        if check:
            if not path.is_file() or load(path) != document:
                raise RuntimeError(f"generated example is stale: {path}")
        else:
            save(path, document)
    inputs = {
        "evolution-operations.json": evolution_operations,
        "evolution-risk.json": evolution_risk,
    }
    for name, document in inputs.items():
        path = EXAMPLE_INPUTS / name
        if check:
            if not path.is_file() or load(path) != document:
                raise RuntimeError(f"generated example input is stale: {path}")
        else:
            save(path, document)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    raise SystemExit(main(check=arguments.check))
