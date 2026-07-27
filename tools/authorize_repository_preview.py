#!/usr/bin/env python3
"""Evolve the self-binding to authorize the requested repository preview."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from concordloom.canonical import digest, load, save
from concordloom.catalog import append_binding
from concordloom.compiler import (
    accept_loop_design,
    activate_binding,
    compile_registry,
    create_binding_proposal,
    propose_loop_design,
)
from concordloom.evolution import propose_evolution
from concordloom.loops import validate_policy, validate_registry


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "framework" / "concordloom"
TARGET = SOURCE / "v3"
STAMP = "2026-07-27T09:00:00Z"
OPERATOR = {
    "id": "example-operator",
    "kind": "operator",
    "display_name": "Operator",
}


def main() -> None:
    graph = load(SOURCE / "accepted-project-graph.json")
    decisions = load(SOURCE / "decision-log.json")
    old_design = load(SOURCE / "loop-design.json")
    old_policy = load(SOURCE / "policy.json")
    predecessor = load(SOURCE / "binding.json")

    policy = deepcopy(old_policy)
    policy["id"] = "concordloom-self-policy-v3"
    policy["execution"]["default_scope"]["external_mutations"] = [
        "github-pages",
        "github-repository-social-preview",
    ]
    validate_policy(policy)

    loop_specs = [
        {
            "id": loop["id"],
            "purpose": loop["purpose"],
            "input_outcome": loop["input_outcome"],
            "output_outcome": loop["output_outcome"],
            "basis": loop["basis"],
            "decision_ids": loop["decision_ids"],
        }
        for loop in old_design["loops"]
    ]
    containment = [
        {
            "id": edge["id"],
            "parent_loop_id": edge["parent_loop_id"],
            "child_loop_id": edge["child_loop_id"],
            "decision_id": edge["decision_id"],
        }
        for edge in old_design["containment"]
    ]
    design_proposal = propose_loop_design(
        graph,
        decisions,
        policy,
        proposal_id="concordloom-self-loop-design-v3-proposal",
        loop_specs=loop_specs,
        containment=containment,
    )
    design = accept_loop_design(
        design_proposal,
        decisions,
        policy,
        accepted_graph=graph,
        decision_id="accept-concordloom-self-loop-design-v3",
        actor=OPERATOR,
        accepted_at=STAMP,
        authority_ref="operator",
        rationale=(
            "Preserve the accepted universal loop semantics while extending only "
            "the publication policy for the requested repository social preview."
        ),
    )
    registry = compile_registry(
        graph,
        decisions,
        design,
        policy,
        loop_design_proposal=design_proposal,
        registry_id="concordloom-self-cycle-registry-v3",
    )
    local_scope = deepcopy(policy["execution"]["default_scope"])
    local_scope["network"] = "none"
    local_scope["external_mutations"] = []
    read_only_scope = deepcopy(local_scope)
    read_only_scope["write_paths"] = []
    publication_scope = {
        "read_paths": ["."],
        "write_paths": [],
        "network": "write",
        "external_mutations": [
            "github-pages",
            "github-repository-social-preview",
        ],
    }
    for edge in registry["containment_graph"]["edges"]:
        child_id = edge["child_loop_id"]
        if child_id == "publish":
            edge["grant"]["scope"] = deepcopy(publication_scope)
        elif child_id == "execute":
            edge["grant"]["scope"] = deepcopy(local_scope)
        else:
            edge["grant"]["scope"] = deepcopy(read_only_scope)
    validate_registry(registry, policy)

    publication_route = [
        {
            "node_id": "concord-change",
            "loop_id": "concord-change",
            "role": "executor",
            "skill_intent": "coordinate the pinned publication without external effects",
            "model_intent": "none",
            "reasoning_intent": "verify exact publisher handoff",
            "subagent_intent": [],
            "scope": deepcopy(read_only_scope),
        },
        {
            "node_id": "publish",
            "loop_id": "publish",
            "role": "publisher",
            "skill_intent": "publish the pinned candidate and exact preview asset",
            "model_intent": "none",
            "reasoning_intent": "perform only the authorized external effects",
            "subagent_intent": [],
            "scope": deepcopy(publication_scope),
        },
    ]

    base_digest = predecessor["binding_digest"]
    signals = [
        {
            "kind": "concordloom.evolution-signal",
            "schema_version": "0.1",
            "id": "operator-requested-repository-preview",
            "base_binding_digest": base_digest,
            "category": "coverage",
            "severity": "warning",
            "occurrences": 1,
            "summary": "The operator requested a branded social preview for the repository.",
            "source_digest": digest(
                {"source": "conversation:2026-07-27:repository-image-request"}
            ),
            "provenance": [{"kind": "evidence", "ref": "repository-image-request"}],
        },
        {
            "kind": "concordloom.evolution-signal",
            "schema_version": "0.1",
            "id": "preview-asset-exists-without-publication-authority",
            "base_binding_digest": base_digest,
            "category": "friction",
            "severity": "warning",
            "occurrences": 1,
            "summary": (
                "The exact 1280x640 preview exists, but the active publication "
                "scope only authorizes GitHub Pages."
            ),
            "source_digest": digest(
                {"source": "docs/assets/concordloom-social-preview.png"}
            ),
            "provenance": [
                {"kind": "file", "ref": "docs/assets/concordloom-social-preview.png"}
            ],
        },
    ]
    evolution = propose_evolution(
        base_digest,
        signals,
        [
            {
                "op": "add",
                "target_kind": "policy",
                "target_id": "github-repository-social-preview",
                "value": {
                    "external_mutation": "github-repository-social-preview",
                    "publisher_only": True,
                },
            }
        ],
        proposed_by={"id": "example-orchestrator", "kind": "orchestrator"},
        decision_authority_ref="operator",
        expected_effect=(
            "Allow the publisher node to set the exact prepared repository social "
            "preview without broadening executor or reviewer effects."
        ),
        risk={
            "level": "low",
            "failure_modes": [
                "The repository image could diverge from the candidate asset."
            ],
            "rollback": (
                "Restore the prior repository preview and reactivate the predecessor "
                "binding if publication evidence does not match the candidate bytes."
            ),
        },
        generated_at=STAMP,
        policy=old_policy,
        proposal_id="authorize-repository-social-preview",
    )

    paths = {
        "accepted_project_graph": "framework/concordloom/v3/accepted-project-graph.json",
        "decision_log": "framework/concordloom/v3/decision-log.json",
        "loop_design_proposal": "framework/concordloom/v3/loop-design-proposal.json",
        "accepted_loop_design": "framework/concordloom/v3/loop-design.json",
        "cycle_registry": "framework/concordloom/v3/cycle-registry.json",
        "policy": "framework/concordloom/v3/policy.json",
    }
    proposal = create_binding_proposal(
        graph,
        decisions,
        design,
        registry,
        policy,
        loop_design_proposal=design_proposal,
        artifact_paths=paths,
        proposal_id="concordloom-self-binding-v3-proposal",
        created_at=STAMP,
        predecessor_binding_digest=base_digest,
        extra_artifacts={
            "evolution_history": (
                "framework/concordloom/v3/evolution-proposal.json",
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
            "decision_id": "activate-concordloom-self-binding-v3",
            "actor": OPERATOR,
            "authority_ref": "operator",
            "accepted_at": "2026-07-27T09:01:00Z",
            "rationale": (
                "Activate the exact publication-scope successor after the operator's "
                "repository-image request; evolution did not activate itself."
            ),
        },
        binding_id="concordloom-self-binding-v3",
        extra_artifacts={
            "evolution_history": (
                "framework/concordloom/v3/evolution-proposal.json",
                evolution,
            )
        },
    )
    current_catalog = load(SOURCE / "catalog.json")
    predecessor_index = next(
        index
        for index, entry in enumerate(current_catalog["entries"])
        if entry["binding_digest"] == base_digest
    )
    base_catalog = deepcopy(current_catalog)
    base_catalog["entries"] = base_catalog["entries"][: predecessor_index + 1]
    base_catalog["active_binding_digest"] = base_digest
    catalog = append_binding(
        base_catalog,
        binding,
        path="framework/concordloom/v3/binding.json",
    )

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
        "publication-route.json": publication_route,
    }
    for name, document in documents.items():
        save(TARGET / name, document)
    save(SOURCE / "catalog.json", catalog)
    print(f"REPOSITORY_PREVIEW_AUTHORIZED {binding['binding_digest']}")


if __name__ == "__main__":
    main()
