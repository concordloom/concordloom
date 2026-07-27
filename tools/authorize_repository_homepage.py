#!/usr/bin/env python3
"""Evolve the self-binding to publish the Pages URL in repository metadata."""

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
PREDECESSOR_DIR = SOURCE / "v3"
TARGET = SOURCE / "v4"
STAMP = "2026-07-27T09:40:00Z"
OPERATOR = {
    "id": "example-operator",
    "kind": "operator",
    "display_name": "Operator",
}
EXTERNAL_MUTATIONS = [
    "github-pages",
    "github-repository-homepage",
    "github-repository-social-preview",
]


def main() -> None:
    graph = load(PREDECESSOR_DIR / "accepted-project-graph.json")
    decisions = load(PREDECESSOR_DIR / "decision-log.json")
    old_design = load(PREDECESSOR_DIR / "loop-design.json")
    old_policy = load(PREDECESSOR_DIR / "policy.json")
    predecessor = load(PREDECESSOR_DIR / "binding.json")

    policy = deepcopy(old_policy)
    policy["id"] = "concordloom-self-policy-v4"
    policy["execution"]["default_scope"]["external_mutations"] = EXTERNAL_MUTATIONS
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
        proposal_id="concordloom-self-loop-design-v4-proposal",
        loop_specs=loop_specs,
        containment=containment,
    )
    design = accept_loop_design(
        design_proposal,
        decisions,
        policy,
        accepted_graph=graph,
        decision_id="accept-concordloom-self-loop-design-v4",
        actor=OPERATOR,
        accepted_at=STAMP,
        authority_ref="operator",
        rationale=(
            "Preserve the accepted loop structure and grant the requested "
            "repository homepage effect only through the publisher route."
        ),
    )
    registry = compile_registry(
        graph,
        decisions,
        design,
        policy,
        loop_design_proposal=design_proposal,
        registry_id="concordloom-self-cycle-registry-v4",
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
        "external_mutations": EXTERNAL_MUTATIONS,
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
            "skill_intent": "publish the pinned candidate and repository metadata",
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
            "id": "operator-requested-repository-homepage",
            "base_binding_digest": base_digest,
            "category": "coverage",
            "severity": "warning",
            "occurrences": 1,
            "summary": "The operator requested the Pages URL in GitHub About.",
            "source_digest": digest(
                {"source": "conversation:2026-07-27:repository-homepage-request"}
            ),
            "provenance": [{"kind": "evidence", "ref": "repository-homepage-request"}],
        },
        {
            "kind": "concordloom.evolution-signal",
            "schema_version": "0.1",
            "id": "pages-url-exists-without-homepage-authority",
            "base_binding_digest": base_digest,
            "category": "friction",
            "severity": "warning",
            "occurrences": 1,
            "summary": (
                "The Pages URL exists, but the active scope cannot mutate the "
                "repository homepage field."
            ),
            "source_digest": digest(
                {"source": "https://concordloom.github.io/concordloom/"}
            ),
            "provenance": [
                {
                    "kind": "evidence",
                    "ref": "https://concordloom.github.io/concordloom/",
                }
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
                "target_id": "github-repository-homepage",
                "value": {
                    "external_mutation": "github-repository-homepage",
                    "publisher_only": True,
                },
            }
        ],
        proposed_by={"id": "example-orchestrator", "kind": "orchestrator"},
        decision_authority_ref="operator",
        expected_effect=(
            "Allow Publish to set the live Pages URL in GitHub About without "
            "broadening any non-publisher node."
        ),
        risk={
            "level": "low",
            "failure_modes": ["The homepage could point to a non-live URL."],
            "rollback": (
                "Clear the repository homepage and reactivate the predecessor "
                "binding if live verification fails."
            ),
        },
        generated_at=STAMP,
        policy=old_policy,
        proposal_id="authorize-repository-homepage",
    )

    paths = {
        "accepted_project_graph": (
            "framework/concordloom/v3/accepted-project-graph.json"
        ),
        "decision_log": "framework/concordloom/v3/decision-log.json",
        "loop_design_proposal": (
            "framework/concordloom/v4/loop-design-proposal.json"
        ),
        "accepted_loop_design": "framework/concordloom/v4/loop-design.json",
        "cycle_registry": "framework/concordloom/v4/cycle-registry.json",
        "policy": "framework/concordloom/v4/policy.json",
    }
    proposal = create_binding_proposal(
        graph,
        decisions,
        design,
        registry,
        policy,
        loop_design_proposal=design_proposal,
        artifact_paths=paths,
        proposal_id="concordloom-self-binding-v4-proposal",
        created_at=STAMP,
        predecessor_binding_digest=base_digest,
        extra_artifacts={
            "evolution_history": (
                "framework/concordloom/v4/evolution-proposal.json",
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
            "decision_id": "activate-concordloom-self-binding-v4",
            "actor": OPERATOR,
            "authority_ref": "operator",
            "accepted_at": "2026-07-27T09:41:00Z",
            "rationale": (
                "Activate the exact publisher-only homepage successor after the "
                "operator request; evolution did not activate itself."
            ),
        },
        binding_id="concordloom-self-binding-v4",
        extra_artifacts={
            "evolution_history": (
                "framework/concordloom/v4/evolution-proposal.json",
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
        path="framework/concordloom/v4/binding.json",
    )

    documents = {
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
    print(f"REPOSITORY_HOMEPAGE_AUTHORIZED {binding['binding_digest']}")


if __name__ == "__main__":
    main()
