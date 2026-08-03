#!/usr/bin/env python3
"""Materialize the accepted v11 community-surface scope without activating it."""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from concordloom.canonical import canonical_bytes, digest, load, save
from concordloom.compiler import (
    accept_loop_design,
    create_binding_proposal,
    validate_binding_proposal,
    validate_loop_design_proposal,
)
from concordloom.evolution import validate_evolution_proposal
from concordloom.loops import require_actor_capability, validate_policy, validate_registry


ROOT = Path(__file__).resolve().parents[1]
BASE_BINDING_DIGEST = (
    "sha256:7ab2f2e59e3f08a914bb9af266165f5ef9868489d43e4eb841f23fb52b9b04c4"
)
EVOLUTION_PROPOSAL_DIGEST = (
    "sha256:9cca4032a0d83773cea0629477b7bafb5e087379dab6661d69881db79f87b37f"
)
OUTPUTS = {
    "binding-proposal.json",
    "cycle-registry.json",
    "development-model.json",
    "evolution-history.json",
    "evolution-proposal.json",
    "loop-design-proposal.json",
    "loop-design.json",
    "policy.json",
    "publication-route.json",
}


def _pretty_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2, sort_keys=True)
        + "\n"
    ).encode("utf-8")


def _receipt(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    value = json.loads(raw.decode("utf-8"))
    if raw != canonical_bytes(value) + b"\n":
        raise ValueError("evolution decision must be canonical JSON")
    payload = deepcopy(value)
    claimed = payload.pop("receipt_digest", None)
    if claimed != digest(payload):
        raise ValueError("evolution decision receipt digest does not match")
    return value


def _targets(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        edge["id"]: edge for edge in registry["containment_graph"]["edges"]
    }


def _set_pointer(document: dict[str, Any], pointer: str, value: Any) -> None:
    current: Any = document
    tokens = pointer[1:].split("/")
    for encoded in tokens[:-1]:
        token = encoded.replace("~1", "/").replace("~0", "~")
        current = current[token]
    token = tokens[-1].replace("~1", "/").replace("~0", "~")
    current[token] = deepcopy(value)


def prepare_design_proposal(root: Path, evolution_path: Path) -> dict[str, Any]:
    source = root / "framework" / "concordloom"
    policy = deepcopy(load(source / "v10" / "policy.json"))
    proposal = deepcopy(load(source / "v10" / "loop-design-proposal.json"))
    evolution = load(evolution_path)
    for operation in evolution["operations"]:
        if operation["target_kind"] == "policy":
            _set_pointer(
                policy["execution"]["default_scope"],
                operation["path"],
                operation["value"],
            )
    validate_policy(policy)
    proposal["id"] = "community-surfaces-v11-loop-design-proposal"
    proposal["authority_policy_digest"] = digest(policy)
    graph = load(source / "v3" / "accepted-project-graph.json")
    decisions = load(source / "v3" / "decision-log.json")
    validate_loop_design_proposal(proposal, graph, decisions, policy)
    return proposal


def _validate_decision(
    decision: dict[str, Any],
    *,
    proposal: dict[str, Any],
    candidate: dict[str, Any],
    policy: dict[str, Any],
) -> None:
    expected = {
        "kind": "concordloom.evolution-decision",
        "schema_version": "0.1",
        "evolution_proposal_digest": EVOLUTION_PROPOSAL_DIGEST,
        "base_binding_digest": BASE_BINDING_DIGEST,
        "candidate_manifest_digest": digest(candidate),
        "candidate_tree_digest": candidate["tree_digest"],
        "capability": "decide-evolution",
        "verdict": "accepted",
        "activation_allowed": False,
        "authority_ref": "operator",
    }
    for key, value in expected.items():
        if decision.get(key) != value:
            raise ValueError(f"evolution decision does not bind exact {key}")
    if decision["principal"]["id"] == proposal["proposed_by"]["id"]:
        raise ValueError("evolution proposer cannot accept its own proposal")
    require_actor_capability(
        policy,
        decision["principal"],
        decision["capability"],
        authority_ref=decision["authority_ref"],
    )


def _validate_design_decision(
    decision: dict[str, Any],
    *,
    proposal: dict[str, Any],
    evolution: dict[str, Any],
    candidate: dict[str, Any],
    policy: dict[str, Any],
) -> None:
    expected = {
        "kind": "concordloom.task-route-design-decision",
        "schema_version": "0.1",
        "proposal_digest": digest(proposal),
        "evolution_proposal_digest": digest(evolution),
        "base_binding_digest": BASE_BINDING_DIGEST,
        "candidate_manifest_digest": digest(candidate),
        "candidate_tree_digest": candidate["tree_digest"],
        "capability": "accept-loop-design",
        "verdict": "accepted",
        "activation_allowed": False,
        "authority_ref": "operator",
    }
    for key, value in expected.items():
        if decision.get(key) != value:
            raise ValueError(f"design decision does not bind exact {key}")
    require_actor_capability(
        policy,
        decision["principal"],
        decision["capability"],
        authority_ref=decision["authority_ref"],
    )


def build(
    root: Path,
    *,
    decision_path: Path,
    design_decision_path: Path,
    design_proposal_path: Path,
    candidate_path: Path,
    proposal_path: Path,
) -> dict[str, dict[str, Any] | list[dict[str, Any]]]:
    source = root / "framework" / "concordloom"
    base = source / "v10"

    binding = load(base / "binding.json")
    policy = load(base / "policy.json")
    registry = load(base / "cycle-registry.json")
    graph = load(source / "v3" / "accepted-project-graph.json")
    decisions = load(source / "v3" / "decision-log.json")
    loop_proposal = load(design_proposal_path)
    model = load(base / "development-model.json")
    publication_route = load(base / "publication-route.json")
    evolution = load(proposal_path)
    decision = _receipt(decision_path)
    design_decision = _receipt(design_decision_path)
    candidate = load(candidate_path)

    if binding["binding_digest"] != BASE_BINDING_DIGEST:
        raise ValueError("v10 binding is not the accepted v11 base")
    if digest(evolution) != EVOLUTION_PROPOSAL_DIGEST:
        raise ValueError("v11 evolution proposal bytes changed")
    validate_policy(policy)
    base_targets = {
        "containment": _targets(registry),
        "policy": {
            "execution-default-scope": policy["execution"]["default_scope"]
        },
    }
    validate_evolution_proposal(
        evolution,
        policy,
        base_binding=binding,
        base_targets=base_targets,
    )
    _validate_decision(
        decision,
        proposal=evolution,
        candidate=candidate,
        policy=policy,
    )

    registry = deepcopy(registry)
    policy = deepcopy(policy)
    edges = _targets(registry)
    for operation in evolution["operations"]:
        if operation["op"] != "replace":
            raise ValueError("v11 materializer accepts replacements only")
        if operation["target_kind"] == "containment":
            target = edges[operation["target_id"]]
        elif (
            operation["target_kind"] == "policy"
            and operation["target_id"] == "execution-default-scope"
        ):
            target = policy["execution"]["default_scope"]
        else:
            raise ValueError("v11 materializer received an unexpected target")
        _set_pointer(target, operation["path"], operation["value"])
    registry["policy_digest"] = digest(policy)
    validate_policy(policy)
    validate_registry(registry, policy)
    _validate_design_decision(
        design_decision,
        proposal=loop_proposal,
        evolution=evolution,
        candidate=candidate,
        policy=policy,
    )
    loop_design = accept_loop_design(
        loop_proposal,
        decisions,
        policy,
        accepted_graph=graph,
        decision_id=design_decision["id"],
        actor={"id": design_decision["principal"]["id"], "kind": "operator"},
        accepted_at=design_decision["decided_at"],
        authority_ref=design_decision["authority_ref"],
        rationale=design_decision["rationale"],
    )
    registry["source_loop_design_digest"] = digest(loop_design)
    validate_registry(registry, policy)

    route_by_node = {item["node_id"]: item for item in publication_route}
    route_by_node["maintain-repository-presence"]["scope"]["external_mutations"] = (
        deepcopy(edges["release-distribution.maintain-repository-presence"]["grant"]["scope"]["external_mutations"])
    )

    history = {
        "kind": "concordloom.evolution-history",
        "schema_version": "0.1",
        "id": "community-surfaces-v11-evolution-history",
        "base_binding_digest": BASE_BINDING_DIGEST,
        "candidate_manifest_digest": digest(candidate),
        "candidate_tree_digest": candidate["tree_digest"],
        "evolution_proposal": {
            "id": evolution["id"],
            "digest": EVOLUTION_PROPOSAL_DIGEST,
        },
        "loop_design_proposal": {
            "id": loop_proposal["id"],
            "digest": digest(loop_proposal),
        },
        "decisions": [
            {
                "kind": "decide-evolution",
                "id": decision["id"],
                "receipt_digest": decision["receipt_digest"],
            },
            {
                "kind": "accept-loop-design",
                "id": design_decision["id"],
                "receipt_digest": design_decision["receipt_digest"],
            }
        ],
        "activation_allowed": False,
    }
    paths = {
        "accepted_project_graph": "framework/concordloom/v3/accepted-project-graph.json",
        "decision_log": "framework/concordloom/v3/decision-log.json",
        "loop_design_proposal": "framework/concordloom/v11/loop-design-proposal.json",
        "accepted_loop_design": "framework/concordloom/v11/loop-design.json",
        "cycle_registry": "framework/concordloom/v11/cycle-registry.json",
        "policy": "framework/concordloom/v11/policy.json",
    }
    extras = {
        "atlas_input": ("framework/concordloom/v11/development-model.json", model),
        "evolution_history": ("framework/concordloom/v11/evolution-history.json", history),
    }
    binding_proposal = create_binding_proposal(
        graph,
        decisions,
        loop_design,
        registry,
        policy,
        loop_design_proposal=loop_proposal,
        artifact_paths=paths,
        proposal_id="concordloom-self-binding-v11-proposal",
        created_at=decision["decided_at"],
        predecessor_binding_digest=BASE_BINDING_DIGEST,
        extra_artifacts=extras,
    )
    validate_binding_proposal(
        binding_proposal,
        graph,
        decisions,
        loop_proposal,
        loop_design,
        registry,
        policy,
        extra_artifacts={
            "atlas_input": ("framework/concordloom/v11/development-model.json", model),
            "evolution_history": ("framework/concordloom/v11/evolution-history.json", history),
        },
    )
    return {
        "binding-proposal.json": binding_proposal,
        "cycle-registry.json": registry,
        "development-model.json": model,
        "evolution-history.json": history,
        "evolution-proposal.json": evolution,
        "loop-design-proposal.json": loop_proposal,
        "loop-design.json": loop_design,
        "policy.json": policy,
        "publication-route.json": publication_route,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--decision", type=Path)
    parser.add_argument("--design-decision", type=Path)
    parser.add_argument("--design-proposal", type=Path)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--proposal", type=Path, required=True)
    parser.add_argument("--prepare-design-proposal", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    resolve = lambda path: path if path.is_absolute() else root / path
    if args.prepare_design_proposal is not None:
        design = prepare_design_proposal(root, resolve(args.proposal))
        save(resolve(args.prepare_design_proposal), design)
        print(f"COMMUNITY_DESIGN_PROPOSED {digest(design)}")
        return
    if (
        args.decision is None
        or args.design_decision is None
        or args.design_proposal is None
        or args.candidate is None
    ):
        parser.error(
            "materialization requires --decision, --design-decision, "
            "--design-proposal, and --candidate"
        )
    documents = build(
        root,
        decision_path=resolve(args.decision),
        design_decision_path=resolve(args.design_decision),
        design_proposal_path=resolve(args.design_proposal),
        candidate_path=resolve(args.candidate),
        proposal_path=resolve(args.proposal),
    )
    if set(documents) != OUTPUTS:
        raise SystemExit("v11 output set changed")
    target = root / "framework" / "concordloom" / "v11"
    if args.check:
        stale = [
            name
            for name, value in documents.items()
            if not (target / name).is_file()
            or (target / name).read_bytes() != _pretty_bytes(value)
        ]
        if stale:
            raise SystemExit("STALE_COMMUNITY_SCOPE " + " ".join(stale))
        print("COMMUNITY_SCOPE_MATERIALIZATION_CHECK_OK")
        return
    for name, value in documents.items():
        save(target / name, value)
    print(f"COMMUNITY_SCOPE_MATERIALIZED {documents['binding-proposal.json']['proposal_digest']}")


if __name__ == "__main__":
    main()
