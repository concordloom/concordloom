#!/usr/bin/env python3
"""Materialize the accepted self-binding at its durable framework path."""

from __future__ import annotations

from pathlib import Path

from concordloom.canonical import digest, load, save
from concordloom.catalog import append_binding
from concordloom.compiler import activate_binding, create_binding_proposal
from concordloom.evolution import propose_evolution


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / ".concord-transition"
TARGET = ROOT / "framework" / "concordloom"
STAMP = "2026-07-27T08:45:00Z"
OPERATOR = {
    "id": "example-operator",
    "kind": "operator",
    "display_name": "Operator",
}


def main() -> None:
    graph = load(SOURCE / "accepted-project-graph.json")
    decisions = load(SOURCE / "decision-log.json")
    design_proposal = load(SOURCE / "loop-design-proposal.json")
    design = load(SOURCE / "loop-design.json")
    registry = load(SOURCE / "cycle-registry.json")
    policy = load(SOURCE / "policy.json")
    predecessor = load(SOURCE / "binding.json")

    signals = [
        {
            "kind": "concordloom.evolution-signal",
            "schema_version": "0.1",
            "id": "transition-artifacts-need-durable-path",
            "base_binding_digest": predecessor["binding_digest"],
            "category": "drift",
            "severity": "warning",
            "occurrences": 1,
            "summary": (
                "The accepted bridge binding points at a temporary documentation namespace."
            ),
            "source_digest": digest(
                {"source": "docs/.concord-transition/binding.json:artifacts"}
            ),
            "provenance": [
                {"kind": "evidence", "ref": "transition-binding-path-audit"}
            ],
        },
        {
            "kind": "concordloom.evolution-signal",
            "schema_version": "0.1",
            "id": "active-catalog-retains-example-identity",
            "base_binding_digest": predecessor["binding_digest"],
            "category": "drift",
            "severity": "warning",
            "occurrences": 1,
            "summary": (
                "The active catalog still carries the generic-service example identity."
            ),
            "source_digest": digest(
                {"source": "docs/.concord-transition/catalog.json:id"}
            ),
            "provenance": [{"kind": "evidence", "ref": "catalog-identity-audit"}],
        },
    ]
    evolution = propose_evolution(
        predecessor["binding_digest"],
        signals,
        [
            {
                "op": "add",
                "target_kind": "policy",
                "target_id": "durable-self-binding-location",
                "value": {"path": "framework/concordloom"},
            },
            {
                "op": "add",
                "target_kind": "policy",
                "target_id": "concordloom-binding-catalog",
                "value": {"id": "concordloom-binding-catalog"},
            },
        ],
        proposed_by={"id": "example-orchestrator", "kind": "orchestrator"},
        decision_authority_ref="operator",
        expected_effect=(
            "Preserve the accepted loop semantics while moving their exact source "
            "artifacts into a durable product-level framework namespace."
        ),
        risk={
            "level": "low",
            "failure_modes": [
                "Artifact-path digests could diverge from the accepted transition."
            ],
            "rollback": (
                "Reject the proposal and keep the docs-scoped transition binding active."
            ),
        },
        generated_at=STAMP,
        policy=policy,
        proposal_id="materialize-concordloom-self-binding",
    )

    paths = {
        "accepted_project_graph": "framework/concordloom/accepted-project-graph.json",
        "decision_log": "framework/concordloom/decision-log.json",
        "loop_design_proposal": "framework/concordloom/loop-design-proposal.json",
        "accepted_loop_design": "framework/concordloom/loop-design.json",
        "cycle_registry": "framework/concordloom/cycle-registry.json",
        "policy": "framework/concordloom/policy.json",
    }
    proposal = create_binding_proposal(
        graph,
        decisions,
        design,
        registry,
        policy,
        loop_design_proposal=design_proposal,
        artifact_paths=paths,
        proposal_id="concordloom-self-binding-v2-proposal",
        created_at=STAMP,
        predecessor_binding_digest=predecessor["binding_digest"],
        extra_artifacts={
            "evolution_history": (
                "framework/concordloom/evolution-proposal.json",
                evolution,
            )
        },
    )
    binding = activate_binding(
        proposal,
        graph,
        decisions,
        design_proposal,
        design,
        registry,
        policy,
        activation_decision={
            "decision_id": "activate-durable-concordloom-self-binding",
            "actor": OPERATOR,
            "authority_ref": "operator",
            "accepted_at": "2026-07-27T08:46:00Z",
            "rationale": (
                "Activate the exact path-only successor after a separate operator "
                "decision; cycle semantics remain unchanged."
            ),
        },
        binding_id="concordloom-self-binding-v2",
        extra_artifacts={
            "evolution_history": (
                "framework/concordloom/evolution-proposal.json",
                evolution,
            )
        },
    )
    catalog = append_binding(
        load(SOURCE / "catalog.json"),
        binding,
        path="framework/concordloom/binding.json",
    )
    catalog["id"] = "concordloom-binding-catalog"

    documents = {
        "accepted-project-graph.json": graph,
        "decision-log.json": decisions,
        "loop-design-proposal.json": design_proposal,
        "loop-design.json": design,
        "cycle-registry.json": registry,
        "policy.json": policy,
        "evolution-proposal.json": evolution,
        "binding-proposal.json": proposal,
        "binding.json": binding,
        "catalog.json": catalog,
    }
    for name, document in documents.items():
        save(TARGET / name, document)
    print(f"SELF_BINDING_MATERIALIZED {binding['binding_digest']}")


if __name__ == "__main__":
    main()
