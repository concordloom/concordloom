#!/usr/bin/env python3
"""Propose the non-activating v8 token-aware self-binding successor."""

from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path

from concordloom.canonical import digest, load, save
from concordloom.catalog import append_binding
from concordloom.compiler import activate_binding, create_binding_proposal
from concordloom.evolution import propose_evolution
from concordloom.loops import validate_policy, validate_registry
from authorize_metadata_maintenance import _validate_activation_receipts


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "framework" / "concordloom"
PREDECESSOR = SOURCE / "v7"
TARGET = SOURCE / "v8"
STAMP = "2026-07-28T00:00:00Z"


def route(
    model: str,
    reasoning: str,
    *,
    provider: str = "openai",
    skills: list[dict] | None = None,
    tool_capabilities: list[str] | None = None,
) -> dict:
    if model == "none":
        provider = ""
    return {
        "model_provider": provider,
        "model": model,
        "reasoning": reasoning,
        "skills": deepcopy(skills or []),
        "mcp_servers": [],
        "resources": [],
        "tool_capabilities": sorted(set(tool_capabilities or [])),
        "subagent_identities": [],
    }


PROFILE_ROUTES = {
    "strategy": route("gpt-5.6-sol", "high"),
    "research": route("gpt-5.6-terra", "medium"),
    "protocol": route("gpt-5.6-sol", "high"),
    "engineering": route("gpt-5.6-terra", "medium"),
    "assurance": route("gpt-5.6-sol", "high"),
    "integration": route("gpt-5.6-terra", "medium"),
    "editorial": route("gpt-5.6-terra", "low"),
    "localization": route("gpt-5.6-terra", "medium"),
    "comprehension": route("gpt-5.6-terra", "medium"),
    "experience": route("gpt-5.6-terra", "medium"),
    "release": route("none", "deterministic"),
    "insight": route("gpt-5.6-luna", "low"),
    "evolution-analysis": route("gpt-5.6-sol", "high"),
    "evolution-proposal": route("gpt-5.6-sol", "high"),
    "evolution-review": route("gpt-5.6-sol", "high"),
    "operator": route("none", "human-decision"),
}

LUNA_NODES = {
    "observe-landscape",
    "collect-friction",
    "synthesize-feedback",
    "collect-evolution-signals",
}

DESIGN_PROJECT_LOOPS_SKILL = {
    "id": "design-project-loops",
    "version": "0.1.0",
}

SKILL_GOVERNED_NODES = {
    "discover-product-needs",
    "define-artifact-semantics",
    "design-graphs-policies",
    "evolve-schemas",
    "operate-run-lifecycle",
    "maintain-self-binding",
    "maintain-reference-bindings",
    "collect-evolution-signals",
    "propose-successor",
    "review-successor",
    "observe-migration",
}


def development_model(base_digest: str) -> dict:
    model = deepcopy(load(PREDECESSOR / "development-model.json"))
    model["id"] = "concordloom-development-system-v8"
    model["base_binding_digest"] = base_digest
    model["resource_semantics"].update(
        {
            "route_materialization": (
                "exact binding metadata; actual execution must match"
            ),
            "empty_resources_mean": "no MCP or repository resource was declared",
            "max_reasoning": "explicit escalation only; never a default",
        }
    )
    for profile_id, profile in model["profiles"].items():
        materialization = deepcopy(PROFILE_ROUTES[profile_id])
        materialization["tool_capabilities"] = sorted(set(profile["tools"]))
        profile["route_materialization"] = materialization
    for node in model["nodes"]:
        profile = model["profiles"][node["execution_profile"]]
        materialization = deepcopy(profile["route_materialization"])
        if node["responsible_role"]["en"] in {"operator", "operator only"}:
            materialization = route(
                "none",
                "human-decision",
                tool_capabilities=profile["tools"],
            )
        elif node["id"] in LUNA_NODES:
            materialization = route(
                "gpt-5.6-luna",
                "medium",
                tool_capabilities=profile["tools"],
            )
        if node["id"] in SKILL_GOVERNED_NODES:
            materialization["skills"] = [deepcopy(DESIGN_PROJECT_LOOPS_SKILL)]
        node["route_materialization"] = materialization
    return model


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--activate", action="store_true")
    parser.add_argument("--accepted-proposal-digest")
    parser.add_argument("--review-recommendation", type=Path)
    parser.add_argument("--evolution-decision", type=Path)
    parser.add_argument("--activation-evidence", type=Path)
    args = parser.parse_args()
    if args.activate and (
        not args.accepted_proposal_digest
        or args.review_recommendation is None
        or args.evolution_decision is None
        or args.activation_evidence is None
    ):
        raise SystemExit(
            "activation requires --accepted-proposal-digest, "
            "--review-recommendation, --evolution-decision, and "
            "--activation-evidence"
        )

    graph = load(SOURCE / "v3" / "accepted-project-graph.json")
    decisions = load(SOURCE / "v3" / "decision-log.json")
    design_proposal = deepcopy(load(PREDECESSOR / "loop-design-proposal.json"))
    design = deepcopy(load(PREDECESSOR / "loop-design.json"))
    predecessor = load(PREDECESSOR / "binding.json")
    base_digest = predecessor["binding_digest"]

    policy = deepcopy(load(PREDECESSOR / "policy.json"))
    policy["id"] = "concordloom-self-policy-v8"
    policy["execution"]["model_policy"]["allowed_models"] = [
        {"provider": "", "model": "none"},
        {"provider": "openai", "model": "gpt-5.6-luna"},
        {"provider": "openai", "model": "gpt-5.6-terra"},
        {"provider": "openai", "model": "gpt-5.6-sol"},
    ]
    policy["execution"]["model_policy"]["allowed_providers"] = ["openai"]
    validate_policy(policy)

    design_proposal["id"] = "concordloom-development-system-v8-proposal"
    design_proposal["authority_policy_digest"] = digest(policy)
    design["id"] = "concordloom-development-system-v8-manifest"
    design["authority_policy_digest"] = digest(policy)
    design["proposal_digest"] = digest(design_proposal)
    design["accepted_by"] = {
        "decision_id": "accept-concordloom-development-system-v8",
        "actor": {
            "id": "example-operator",
            "kind": "operator",
            "display_name": "Operator",
        },
        "authority_ref": "operator",
        "accepted_at": STAMP,
        "rationale": (
            "Keep the accepted topology and bind exact token-aware execution "
            "profiles without activating the successor."
        ),
    }
    registry = deepcopy(load(PREDECESSOR / "cycle-registry.json"))
    registry["id"] = "concordloom-development-registry-v8"
    registry["policy_digest"] = digest(policy)
    registry["source_loop_design_digest"] = digest(design)
    validate_registry(registry, policy)

    model = development_model(base_digest)
    signals = [
        {
            "kind": "concordloom.evolution-signal",
            "schema_version": "0.1",
            "id": "unbound-model-intent-cannot-control-token-spend",
            "base_binding_digest": base_digest,
            "category": "coverage",
            "severity": "warning",
            "occurrences": 4,
            "summary": (
                "Execution profiles describe intent but do not bind an exact "
                "provider, model, reasoning level, or empty resource set."
            ),
            "source_digest": digest({"source": "self-use:v7:model-routing-gap"}),
            "provenance": [{"kind": "evidence", "ref": "v7-route-audit"}],
        },
        {
            "kind": "concordloom.evolution-signal",
            "schema_version": "0.1",
            "id": "full-strength-model-default-wastes-bounded-run-budget",
            "base_binding_digest": base_digest,
            "category": "friction",
            "severity": "warning",
            "occurrences": 3,
            "summary": (
                "Bounded triage and deterministic publication do not need the "
                "same model class as protocol and successor review."
            ),
            "source_digest": digest({"source": "self-use:v7:token-budget-audit"}),
            "provenance": [{"kind": "evidence", "ref": "v7-cost-audit"}],
        },
    ]
    evolution = propose_evolution(
        base_digest,
        signals,
        [
            {
                "op": "add",
                "target_kind": "policy",
                "target_id": policy["id"],
                "value": {
                    "unchanged_cycle_count": 58,
                    "unchanged_containment_edge_count": 57,
                    "exact_models": [
                        "none",
                        "gpt-5.6-luna",
                        "gpt-5.6-terra",
                        "gpt-5.6-sol",
                    ],
                    "max_reasoning_default": False,
                },
            }
        ],
        proposed_by={"id": "example-orchestrator", "kind": "orchestrator"},
        decision_authority_ref="operator",
        expected_effect=(
            "Bind each targeted route to the least costly adequate exact model "
            "while materializing accepted tool capabilities, pinning the "
            "repository-owned design skill where it governs the route, and "
            "leaving undeclared MCP resources and subagents empty."
        ),
        risk={
            "level": "medium",
            "failure_modes": [
                "An underpowered route may need explicit escalation.",
                "Declared route metadata may drift from actual execution.",
            ],
            "rollback": "Reject v8 and keep the active v7 binding.",
        },
        generated_at=STAMP,
        policy=load(PREDECESSOR / "policy.json"),
        proposal_id="bind-token-aware-route-materialization",
    )
    paths = {
        "accepted_project_graph": "framework/concordloom/v3/accepted-project-graph.json",
        "decision_log": "framework/concordloom/v3/decision-log.json",
        "loop_design_proposal": "framework/concordloom/v8/loop-design-proposal.json",
        "accepted_loop_design": "framework/concordloom/v8/loop-design.json",
        "cycle_registry": "framework/concordloom/v8/cycle-registry.json",
        "policy": "framework/concordloom/v8/policy.json",
    }
    extras = {
        "atlas_input": (
            "framework/concordloom/v8/development-model.json",
            model,
        ),
        "evolution_history": (
            "framework/concordloom/v8/evolution-proposal.json",
            evolution,
        ),
    }
    proposal = create_binding_proposal(
        graph,
        decisions,
        design,
        registry,
        policy,
        loop_design_proposal=design_proposal,
        artifact_paths=paths,
        proposal_id="concordloom-self-binding-v8-proposal",
        created_at=STAMP,
        predecessor_binding_digest=base_digest,
        extra_artifacts=extras,
    )
    publication_route = deepcopy(load(PREDECESSOR / "publication-route.json"))
    deterministic = route("none", "deterministic")
    for item in publication_route:
        item.update(deepcopy(deterministic))
    documents = {
        "loop-design-proposal.json": design_proposal,
        "loop-design.json": design,
        "cycle-registry.json": registry,
        "policy.json": policy,
        "development-model.json": model,
        "evolution-proposal.json": evolution,
        "binding-proposal.json": proposal,
        "publication-route.json": publication_route,
    }
    if not args.activate:
        for name, document in documents.items():
            save(TARGET / name, document)
        print(
            "TOKEN_ROUTING_V8_PROPOSED "
            f"proposal={proposal['proposal_digest']} "
            f"tree={digest(proposal['artifacts'])}"
        )
        return

    if args.accepted_proposal_digest != proposal["proposal_digest"]:
        raise SystemExit("accepted proposal digest does not match exact v8 proposal")
    predecessor_policy = load(PREDECESSOR / "policy.json")
    receipts = _validate_activation_receipts(
        review_path=args.review_recommendation,
        evolution_path=args.evolution_decision,
        activation_path=args.activation_evidence,
        proposal_digest=proposal["proposal_digest"],
        proposal_tree_digest=digest(proposal["artifacts"]),
        base_binding_digest=base_digest,
        policy=predecessor_policy,
    )
    for name, document in documents.items():
        save(TARGET / name, document)

    binding = activate_binding(
        proposal,
        graph,
        decisions,
        design_proposal,
        design,
        registry,
        policy,
        activation_decision={
            "decision_id": receipts["activation"]["decision_id"],
            "actor": {
                "id": receipts["activation"]["principal"]["id"],
                "kind": "operator",
                "display_name": "Operator",
            },
            "authority_ref": "operator",
            "accepted_at": "2026-07-28T00:05:00Z",
            "rationale": (
                "Activate the exact token-routing successor after independent "
                f"recommendation {receipts['review_digest']}, separate "
                f"evolution decision {receipts['evolution_digest']}, and "
                f"activation evidence {receipts['activation_digest']}."
            ),
        },
        binding_id="concordloom-self-binding-v8",
        extra_artifacts=extras,
    )
    catalog = append_binding(
        load(SOURCE / "catalog.json"),
        binding,
        path="framework/concordloom/v8/binding.json",
    )
    save(TARGET / "binding.json", binding)
    save(
        TARGET / "activation-receipt.json",
        {
            "kind": "concordloom.activation-receipt",
            "schema_version": "0.1",
            "id": "activate-concordloom-self-binding-v8-receipt",
            "binding_digest": binding["binding_digest"],
            "binding_proposal_digest": proposal["proposal_digest"],
            "candidate_tree_digest": receipts["candidate_tree_digest"],
            "proposal_tree_digest": receipts["proposal_tree_digest"],
            "review_recommendation_id": receipts["review"]["id"],
            "review_recommendation_digest": receipts["review_digest"],
            "evolution_decision_id": receipts["evolution"]["decision_id"],
            "evolution_decision_digest": receipts["evolution_digest"],
            "activation_decision_id": receipts["activation"]["decision_id"],
            "activation_evidence_id": receipts["activation"]["id"],
            "activation_evidence_digest": receipts["activation_digest"],
            "activated_at": "2026-07-28T00:05:00Z",
        },
    )
    save(SOURCE / "catalog.json", catalog)
    print(
        "TOKEN_ROUTING_V8_ACTIVATED "
        f"binding={binding['binding_digest']}"
    )


if __name__ == "__main__":
    main()
