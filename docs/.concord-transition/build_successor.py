#!/usr/bin/env python3
"""Build the operator-approved universal Concord Loom self-binding."""

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
from concordloom.loops import validate_policy


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / ".concord-transition"
STAMP = "2026-07-27T08:30:00Z"
OPERATOR = {
    "id": "example-operator",
    "kind": "operator",
    "display_name": "Operator",
}


def successor_policy() -> dict:
    policy = deepcopy(load(ROOT / "framework/generic-sdlc/policy.json"))
    policy["id"] = "concordloom-self-policy"
    policy["authority"]["roles"] = [
        {
            "id": "operator",
            "description": "Accepts intent, loop design, evolution, and bindings.",
            "capabilities": [
                "accept-intent",
                "accept-loop-design",
                "authorize-run",
                "decide-evolution",
                "activate-binding",
                "escalate",
            ],
        },
        {
            "id": "orchestrator",
            "description": "Routes accepted outcomes without changing their authority.",
            "capabilities": ["route-run", "accept-parent", "escalate"],
        },
        {
            "id": "executor",
            "description": "Produces scoped candidates and factual evidence.",
            "capabilities": ["execute-work", "produce-evidence", "escalate"],
        },
        {
            "id": "reviewer",
            "description": "Independently evaluates a pinned candidate.",
            "capabilities": [
                "review-candidate",
                "accept-gate",
                "produce-evidence",
                "escalate",
            ],
        },
        {
            "id": "publisher",
            "description": "Performs one explicitly authorized external effect.",
            "capabilities": [
                "execute-work",
                "publish-release",
                "produce-evidence",
                "escalate",
            ],
        },
    ]
    policy["authority"]["separation_rules"] = [
        {
            "id": "author-verification-separation",
            "subject_capability": "execute-work",
            "review_capability": "review-candidate",
            "disallow_same_principal": True,
            "applies_to_loop_ids": ["verify"],
        }
    ]
    policy["execution"]["default_scope"] = {
        "read_paths": ["."],
        "write_paths": [
            ".github",
            "README.md",
            "README.ru.md",
            "docs",
            "framework",
            "plugins",
            "schemas",
            "site",
            "src",
            "tests",
            "tools",
        ],
        "network": "write",
        "external_mutations": ["github-pages"],
    }
    policy["execution"]["allowed_tools"] = [
        "git",
        "github",
        "imagegen",
        "orca",
        "python",
        "web",
    ]
    policy["execution"]["model_policy"] = {
        "allowed_providers": ["openai"],
        "privacy": "public_data_only",
        "allowed_path_prefixes": ["."],
        "allowed_content_classes": [
            "metadata",
            "history",
            "source",
            "tests",
            "documentation",
            "configuration",
            "evidence",
        ],
        "public_content_classes": [
            "metadata",
            "history",
            "source",
            "tests",
            "documentation",
            "configuration",
            "evidence",
        ],
        "allowed_models": [
            {"provider": "", "model": "none"},
            {"provider": "openai", "model": "gpt-5"},
        ],
        "max_cost_units": 10,
        "record_effective_model": True,
    }
    validate_policy(policy)
    return policy


def main() -> None:
    old_binding = load(ROOT / "framework/generic-sdlc/binding.json")
    old_policy = load(ROOT / "framework/generic-sdlc/policy.json")
    graph = load(OUT / "accepted-project-graph.json")
    decisions = load(OUT / "decision-log.json")
    policy = successor_policy()

    loop_specs = [
        {
            "id": "concord-change",
            "purpose": "Govern one bounded change without assuming a domain.",
            "input_outcome": "An operator-accepted outcome.",
            "output_outcome": "A verified effect or explicit escalation.",
        },
        {
            "id": "observe",
            "purpose": "Separate observed facts from inferred intent.",
            "input_outcome": "A bounded subject and evidence sources.",
            "output_outcome": "An observed graph with provenance.",
        },
        {
            "id": "negotiate",
            "purpose": "Resolve consequential intent through operator decisions.",
            "input_outcome": "Observed facts and ranked questions.",
            "output_outcome": "Accepted intent and an append-only decision log.",
        },
        {
            "id": "bind",
            "purpose": "Compile accepted intent into finite loops, policy, and scope.",
            "input_outcome": "Accepted intent and an unaccepted design proposal.",
            "output_outcome": "One separately activated, content-addressed binding.",
        },
        {
            "id": "execute",
            "purpose": "Produce one scoped candidate within the active binding.",
            "input_outcome": "An authorized run card and exact scope.",
            "output_outcome": "A pinned candidate and factual execution evidence.",
        },
        {
            "id": "verify",
            "purpose": "Independently evaluate the pinned candidate.",
            "input_outcome": "A candidate manifest and evidence contract.",
            "output_outcome": "An independent verification receipt.",
        },
        {
            "id": "publish",
            "purpose": "Perform an explicitly authorized external effect, or record none.",
            "input_outcome": "A verified candidate and publication authority.",
            "output_outcome": "A publication receipt, a no-op receipt, or escalation.",
        },
        {
            "id": "evolve",
            "purpose": "Reduce repeated signals into a non-activating successor proposal.",
            "input_outcome": "Pinned signals from the active binding.",
            "output_outcome": "A successor proposal requiring a separate operator decision.",
        },
    ]
    containment = [
        {
            "id": f"concord-change-{loop_id}",
            "parent_loop_id": "concord-change",
            "child_loop_id": loop_id,
        }
        for loop_id in (
            "observe",
            "negotiate",
            "bind",
            "execute",
            "verify",
            "publish",
            "evolve",
        )
    ]
    design_proposal = propose_loop_design(
        graph,
        decisions,
        policy,
        proposal_id="concordloom-self-loop-design-proposal",
        loop_specs=loop_specs,
        containment=containment,
    )
    design = accept_loop_design(
        design_proposal,
        decisions,
        policy,
        accepted_graph=graph,
        decision_id="accept-concordloom-self-loop-design",
        actor=OPERATOR,
        accepted_at=STAMP,
        authority_ref="operator",
        rationale=(
            "Accept the domain-neutral Observe, Negotiate, Bind, Execute, Verify, "
            "Publish, Evolve containment sequence for Concord Loom itself."
        ),
    )
    registry = compile_registry(
        graph,
        decisions,
        design,
        policy,
        loop_design_proposal=design_proposal,
        registry_id="concordloom-self-cycle-registry",
    )

    base_digest = old_binding["binding_digest"]
    signal_scope = {
        "kind": "concordloom.evolution-signal",
        "schema_version": "0.1",
        "id": "self-evolution-scope-deadlock",
        "base_binding_digest": base_digest,
        "category": "recurring-failure",
        "severity": "critical",
        "occurrences": 1,
        "summary": (
            "The active binding cannot write a successor outside src, tests, or docs."
        ),
        "source_digest": digest(
            {"source": "generic-service-policy.execution.default_scope.write_paths"}
        ),
        "provenance": [{"kind": "evidence", "ref": "guard-scope-audit-2026-07-27"}],
    }
    signal_publish = {
        "kind": "concordloom.evolution-signal",
        "schema_version": "0.1",
        "id": "self-evolution-publication-deadlock",
        "base_binding_digest": base_digest,
        "category": "recurring-failure",
        "severity": "critical",
        "occurrences": 1,
        "summary": (
            "The active binding forbids every network and external publication effect."
        ),
        "source_digest": digest(
            {
                "source": (
                    "generic-service-policy.execution.default_scope."
                    "network+external_mutations"
                )
            }
        ),
        "provenance": [{"kind": "evidence", "ref": "pages-scope-audit-2026-07-27"}],
    }
    evolution = propose_evolution(
        base_digest,
        [signal_scope, signal_publish],
        [
            {
                "op": "add",
                "target_kind": "loop",
                "target_id": "concord-change",
                "value": {"successor_registry_id": registry["id"]},
            },
            {
                "op": "add",
                "target_kind": "policy",
                "target_id": "concordloom-self-policy",
                "value": {
                    "scoped_external_mutation": "github-pages",
                    "allow_self_activation": False,
                },
            },
        ],
        proposed_by={"id": "example-orchestrator", "kind": "orchestrator"},
        decision_authority_ref="operator",
        expected_effect=(
            "Replace the SDLC-shaped self-binding with a domain-neutral cycle and "
            "make successor proposal plus scoped publication possible."
        ),
        risk={
            "level": "high",
            "failure_modes": [
                "An overly broad run route could grant publishing to a non-publisher.",
                "A successor could be mistaken for self-authorized evolution.",
            ],
            "rollback": (
                "Keep the generic-service binding active and reject the successor "
                "proposal before catalog activation."
            ),
        },
        generated_at=STAMP,
        policy=old_policy,
        proposal_id="concordloom-universal-self-evolution",
    )

    paths = {
        "accepted_project_graph": "docs/.concord-transition/accepted-project-graph.json",
        "decision_log": "docs/.concord-transition/decision-log.json",
        "loop_design_proposal": "docs/.concord-transition/loop-design-proposal.json",
        "accepted_loop_design": "docs/.concord-transition/loop-design.json",
        "cycle_registry": "docs/.concord-transition/cycle-registry.json",
        "policy": "docs/.concord-transition/policy.json",
    }
    binding_proposal = create_binding_proposal(
        graph,
        decisions,
        design,
        registry,
        policy,
        loop_design_proposal=design_proposal,
        artifact_paths=paths,
        proposal_id="concordloom-self-binding-proposal",
        created_at=STAMP,
        extra_artifacts={
            "evolution_history": (
                "docs/.concord-transition/evolution-proposal.json",
                evolution,
            )
        },
        predecessor_binding_digest=base_digest,
    )
    binding = activate_binding(
        binding_proposal,
        graph,
        decisions,
        design_proposal,
        design,
        registry,
        policy,
        activation_decision={
            "decision_id": "activate-concordloom-self-binding",
            "actor": OPERATOR,
            "authority_ref": "operator",
            "accepted_at": "2026-07-27T08:31:00Z",
            "rationale": (
                "Activate the exact successor after separate operator acceptance; "
                "the evolution proposal itself remains non-authoritative."
            ),
        },
        binding_id="concordloom-self-binding",
        extra_artifacts={
            "evolution_history": (
                "docs/.concord-transition/evolution-proposal.json",
                evolution,
            )
        },
    )
    catalog = append_binding(
        load(ROOT / "framework/generic-sdlc/catalog.json"),
        binding,
        path="docs/.concord-transition/binding.json",
        catalog_id="concordloom-binding-catalog",
    )

    outputs = {
        "policy.json": policy,
        "loop-design-proposal.json": design_proposal,
        "loop-design.json": design,
        "cycle-registry.json": registry,
        "evolution-signal-scope.json": signal_scope,
        "evolution-signal-publish.json": signal_publish,
        "evolution-proposal.json": evolution,
        "binding-proposal.json": binding_proposal,
        "binding.json": binding,
        "catalog.json": catalog,
    }
    for name, document in outputs.items():
        save(OUT / name, document)


if __name__ == "__main__":
    main()
