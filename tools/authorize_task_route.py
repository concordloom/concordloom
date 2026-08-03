#!/usr/bin/env python3
"""Build the proposal-only v10 task-route successor artifacts.

This tool deliberately owns only the two reviewable proposals. A separate
materializer may add non-activating successor artifacts after exact operator
decisions, but neither stage may activate a binding or append the public
catalog.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path

from concordloom.canonical import digest, document_digest, load, save
from concordloom.compiler import propose_loop_design
from concordloom.evolution import propose_evolution, validate_evolution_proposal
from concordloom.loops import validate_policy


DEFAULT_ROOT = Path(__file__).resolve().parents[1]
BASE_BINDING_DIGEST = (
    "sha256:1940a57ca917d6136c5742048dfccc68d0434c530da2ad3ef3b2ba486f866597"
)
ACTIVE_BINDING_DIGEST = (
    "sha256:7ab2f2e59e3f08a914bb9af266165f5ef9868489d43e4eb841f23fb52b9b04c4"
)
BINDING_PROPOSAL_DIGEST = (
    "sha256:e19ebf34082aaff8f6a52d8f7b9420b60db146ca8b0acb22d2ec7fa7dd3d84bd"
)
RUNTIME_TOOLING_PARENT_EDGE_DIGEST = (
    "sha256:8d72161e7a22c9609cade5f9bb73b8e847673eecc41c3707d1bbacd2fb5e6c4a"
)
STAMP = "2026-08-02T00:00:00Z"
ALLOWED_OUTPUTS = {
    "evolution-proposal.json",
    "loop-design-proposal.json",
}
MATERIALIZED_OUTPUTS = {
    "binding-proposal.json",
    "cycle-registry.json",
    "development-model.json",
    "evolution-history.json",
    "loop-design.json",
    "policy.json",
    "publication-route.json",
}
ACTIVATION_OUTPUTS = {
    "activation-receipt.json",
    "binding.json",
}


def _pretty_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _require_lifecycle_state(target: Path, catalog: dict) -> None:
    """Accept an exact historical or fully activated v10 lifecycle state."""

    present = {path.name for path in target.iterdir()} if target.exists() else set()
    unexpected = sorted(
        present - ALLOWED_OUTPUTS - MATERIALIZED_OUTPUTS - ACTIVATION_OUTPUTS
    )
    if unexpected:
        raise ValueError(
            "v10 contains artifacts outside its governed lifecycle: "
            + ", ".join(unexpected)
        )
    activation_present = present & ACTIVATION_OUTPUTS
    if activation_present and activation_present != ACTIVATION_OUTPUTS:
        raise ValueError("v10 has an incomplete activation lifecycle")

    tail = catalog["entries"][-1]
    if catalog["active_binding_digest"] == BASE_BINDING_DIGEST:
        if activation_present:
            raise ValueError("v10 authority artifacts exist before catalog activation")
        if (
            tail.get("binding_digest") != BASE_BINDING_DIGEST
            or tail.get("binding_id") != "concordloom-self-binding-v9"
            or tail.get("path") != "framework/concordloom/v9/binding.json"
        ):
            raise ValueError("catalog tail does not match the pinned v9 base")
        return

    if activation_present != ACTIVATION_OUTPUTS:
        raise ValueError("catalog contains v10 without both authority artifacts")
    v10_entry = next(
        (
            entry
            for entry in catalog["entries"]
            if entry.get("binding_digest") == ACTIVE_BINDING_DIGEST
        ),
        None,
    )
    if (
        v10_entry is None
        or v10_entry.get("binding_id") != "concordloom-self-binding-v10"
        or v10_entry.get("path") != "framework/concordloom/v10/binding.json"
        or v10_entry.get("previous_binding_digest") != BASE_BINDING_DIGEST
    ):
        raise ValueError("catalog does not contain the exact v10 successor")

    binding = load(target / "binding.json")
    if (
        binding.get("id") != "concordloom-self-binding-v10"
        or binding.get("binding_digest") != ACTIVE_BINDING_DIGEST
        or binding.get("predecessor_binding_digest") != BASE_BINDING_DIGEST
        or binding.get("accepted_by", {}).get("proposal_digest")
        != BINDING_PROPOSAL_DIGEST
        or binding.get("accepted_by", {}).get("decision_id")
        != "activate-v10-task-route"
    ):
        raise ValueError("v10 binding is not the exact activated successor")
    if binding["binding_digest"] != document_digest(
        binding,
        excluded_fields=binding["digest_contract"]["excluded_fields"],
    ):
        raise ValueError("v10 binding digest contract failed")

    receipt = load(target / "activation-receipt.json")
    if (
        receipt.get("kind") != "concordloom.activation-receipt"
        or receipt.get("binding_digest") != ACTIVE_BINDING_DIGEST
        or receipt.get("binding_proposal_digest") != BINDING_PROPOSAL_DIGEST
        or receipt.get("activation_decision_id") != "activate-v10-task-route"
    ):
        raise ValueError("v10 activation receipt does not bind the exact successor")


def _insert_after(
    values: list[dict],
    *,
    key: str,
    anchor: str,
    addition: dict,
) -> list[dict]:
    identifiers = [value[key] for value in values]
    if addition[key] in identifiers:
        raise ValueError(f"proposed identifier already exists: {addition[key]}")
    try:
        index = identifiers.index(anchor)
    except ValueError as exc:
        raise ValueError(f"proposal anchor is missing: {anchor}") from exc
    result = deepcopy(values)
    result.insert(index + 1, deepcopy(addition))
    return result


def _route(
    *,
    model_provider: str,
    model: str,
    reasoning: str,
    skills: list[dict] | None = None,
) -> dict:
    return {
        "model_provider": model_provider,
        "model": model,
        "reasoning": reasoning,
        "skills": deepcopy(skills or []),
        "mcp_servers": [],
        "resources": [],
        "tool_capabilities": [],
        "subagent_identities": [],
    }


def build(root: Path) -> dict[str, dict]:
    source = root / "framework" / "concordloom"
    predecessor = source / "v9"
    target = source / "v10"

    catalog = load(source / "catalog.json")
    _require_lifecycle_state(target, catalog)
    binding = load(predecessor / "binding.json")
    policy = load(predecessor / "policy.json")
    registry = load(predecessor / "cycle-registry.json")
    previous_proposal = load(predecessor / "loop-design-proposal.json")
    accepted_graph = load(source / "v3" / "accepted-project-graph.json")
    decision_log = load(source / "v3" / "decision-log.json")

    if binding["binding_digest"] != BASE_BINDING_DIGEST:
        raise ValueError("v9 binding bytes do not match the pinned proposal base")
    validate_policy(policy)
    if previous_proposal["authority_policy_digest"] != digest(policy):
        raise ValueError("v9 loop proposal and policy digest disagree")
    if len(previous_proposal["loops"]) != 65:
        raise ValueError("v9 loop count changed; review the proposal delta")
    if len(previous_proposal["containment"]) != 64:
        raise ValueError("v9 containment count changed; review the proposal delta")

    lifecycle_edge = next(
        (
            edge
            for edge in registry["containment_graph"]["edges"]
            if edge["id"] == "runtime-tooling.operate-run-lifecycle"
        ),
        None,
    )
    if lifecycle_edge is None:
        raise ValueError("v9 lifecycle containment edge is missing")
    lifecycle_edge = deepcopy(lifecycle_edge)
    expected_lifecycle_reads = [
        "AGENTS.md",
        "framework/concordloom/catalog.json",
        "schemas",
        "src/concordloom/run.py",
        "tests",
    ]
    expected_lifecycle_writes = [
        "schemas",
        "src/concordloom/run.py",
        "tests",
    ]
    if lifecycle_edge["grant"]["scope"]["read_paths"] != expected_lifecycle_reads:
        raise ValueError("v9 lifecycle read scope changed; review the proposal delta")
    if lifecycle_edge["grant"]["scope"]["write_paths"] != expected_lifecycle_writes:
        raise ValueError("v9 lifecycle write scope changed; review the proposal delta")
    lifecycle_edge_with_route = deepcopy(lifecycle_edge)
    lifecycle_edge_with_route["grant"]["scope"]["read_paths"] = [
        *expected_lifecycle_reads[:-1],
        "src/concordloom/route.py",
        "src/concordloom/schema.py",
        expected_lifecycle_reads[-1],
    ]
    lifecycle_edge_with_route["grant"]["scope"]["write_paths"] = [
        "schemas",
        "src/concordloom/route.py",
        "src/concordloom/run.py",
        "src/concordloom/schema.py",
        "tests",
    ]
    runtime_parent_edge = next(
        edge
        for edge in registry["containment_graph"]["edges"]
        if edge["id"] == "steward-concordloom.runtime-tooling"
    )
    runtime_parent_edge = deepcopy(runtime_parent_edge)
    if digest(runtime_parent_edge) != RUNTIME_TOOLING_PARENT_EDGE_DIGEST:
        raise ValueError("v9 runtime-tooling parent edge changed")
    runtime_parent_with_route = deepcopy(runtime_parent_edge)
    for mode in ("read_paths", "write_paths"):
        runtime_parent_with_route["grant"]["scope"][mode] = sorted(
            runtime_parent_edge["grant"]["scope"][mode]
            + ["src/concordloom/route.py", "src/concordloom/schema.py"]
        )

    loop = {
        "id": "plan-task-route",
        "purpose": (
            "Compile an exact, immutable proposed route preview from the "
            "accepted local control flow before any run card exists."
        ),
        "input_outcome": (
            "A task request, the active binding, its accepted loop registry, "
            "and an exact candidate manifest."
        ),
        "output_outcome": (
            "An immutable candidate-bound proposed route preview that keeps "
            "the task area separate from every accepted execution, "
            "verification, and review action; confirmation is required and "
            "execution is forbidden."
        ),
        "basis": [{"kind": "decision", "ref": "accepted-project-graph"}],
        "decision_ids": ["accept-universal-loop-system"],
    }
    edge = {
        "id": "runtime-tooling.plan-task-route",
        "parent_loop_id": "runtime-tooling",
        "child_loop_id": "plan-task-route",
        "decision_id": "accept-universal-loop-system",
    }
    loops = _insert_after(
        previous_proposal["loops"],
        key="id",
        anchor="maintain-compiler-core",
        addition=loop,
    )
    containment = _insert_after(
        previous_proposal["containment"],
        key="id",
        anchor="runtime-tooling.maintain-compiler-core",
        addition=edge,
    )
    loop_design = propose_loop_design(
        accepted_graph,
        decision_log,
        policy,
        proposal_id="concordloom-development-system-v10-proposal",
        loop_specs=loops,
        containment=containment,
    )

    route_contract = {
        "authority": {
            "execute_capability": "route-run",
            "accept_capability": "accept-parent",
            "escalate_capability": "escalate",
        },
        "candidate_effects": {
            "repository_candidate_write_paths": [],
            "network": "none",
            "external_mutations": [],
        },
        "preview_artifact": {
            "state": "proposed",
            "immutable": True,
            "candidate_bound": True,
            "area_path_separated": True,
            "execution_route_source": "accepted-local-control-flow",
            "verification_steps_included": True,
            "confirmation_required": True,
            "execution_allowed": False,
            "run_card_creation": "after-explicit-confirmation-only",
        },
        "routes": {
            "exact_route_compiler": {
                "required": True,
                **_route(
                    model_provider="",
                    model="none",
                    reasoning="deterministic",
                ),
            },
            "semantic_target_selection": {
                "optional": True,
                "fallback": "require-explicit-target-loop",
                **_route(
                    model_provider="openai",
                    model="gpt-5.6-luna",
                    reasoning="low",
                    skills=[
                        {"id": "design-project-loops", "version": "0.1.0"}
                    ],
                ),
            },
        },
    }
    loop_operation_value = {
        "parent_loop_id": "runtime-tooling",
        "after_child_loop_id": "maintain-compiler-core",
        "before_child_loop_id": "operate-run-lifecycle",
        "purpose": loop["purpose"],
        "input_outcome": loop["input_outcome"],
        "output_outcome": loop["output_outcome"],
        "proposed_runtime_contract": route_contract,
    }
    operations = [
        {
            "op": "add",
            "target_kind": "loop",
            "target_id": "plan-task-route",
            "value": loop_operation_value,
        },
        {
            "op": "add",
            "target_kind": "containment",
            "target_id": "runtime-tooling.plan-task-route",
            "value": {
                "id": "runtime-tooling.plan-task-route",
                "parent_loop_id": "runtime-tooling",
                "child_loop_id": "plan-task-route",
                "after_child_loop_id": "maintain-compiler-core",
                "before_child_loop_id": "operate-run-lifecycle",
            },
        },
        {
            "op": "replace",
            "target_kind": "containment",
            "target_id": "runtime-tooling.operate-run-lifecycle",
            "precondition_digest": digest(lifecycle_edge),
            "value": lifecycle_edge_with_route,
        },
        {
            "op": "replace",
            "target_kind": "containment",
            "target_id": "steward-concordloom.runtime-tooling",
            "precondition_digest": RUNTIME_TOOLING_PARENT_EDGE_DIGEST,
            "value": runtime_parent_with_route,
        },
    ]
    signals = [
        {
            "kind": "concordloom.evolution-signal",
            "schema_version": "0.1",
            "id": "task-routes-are-invisible-before-execution",
            "base_binding_digest": BASE_BINDING_DIGEST,
            "source_digest": digest(
                {"source": "self-use:v9:route-not-visible-before-run"}
            ),
            "category": "friction",
            "severity": "warning",
            "occurrences": 3,
            "summary": (
                "Operators cannot inspect which accepted loops a task will "
                "traverse before authorizing the run."
            ),
            "provenance": [
                {"kind": "evidence", "ref": "operator-route-preview-feedback"}
            ],
        },
        {
            "kind": "concordloom.evolution-signal",
            "schema_version": "0.1",
            "id": "task-target-selection-lacks-a-native-preview",
            "base_binding_digest": BASE_BINDING_DIGEST,
            "source_digest": digest(
                {"source": "self-use:v9:task-target-selection-gap"}
            ),
            "category": "coverage",
            "severity": "warning",
            "occurrences": 2,
            "summary": (
                "The runtime can compile an explicit target closure but has no "
                "bounded user-facing step that separates its area breadcrumb "
                "from every accepted execution, verification, and review "
                "action."
            ),
            "provenance": [
                {"kind": "evidence", "ref": "task-route-runtime-audit"}
            ],
        },
    ]
    evolution = propose_evolution(
        BASE_BINDING_DIGEST,
        signals,
        operations,
        proposed_by={"id": "example-orchestrator", "kind": "orchestrator"},
        decision_authority_ref="operator",
        expected_effect=(
            "Add one proposal-only route-planning child and grant the existing "
            "run-lifecycle child exact ownership of src/concordloom/route.py "
            "and src/concordloom/schema.py. Raise only the exact "
            "steward-to-runtime-tooling delegation ceiling required for "
            "those two paths. "
            "The preview keeps the task area separate from the full accepted "
            "local execution flow, including verification and review, may use "
            "Luna at low reasoning to suggest a target, and requires separate "
            "explicit confirmation before run new may create a draft run card. "
            "It cannot write candidate bytes, use task network access, mutate "
            "external systems, authorize execution, or activate a successor."
        ),
        risk={
            "level": "medium",
            "failure_modes": [
                "Semantic target selection may suggest the wrong loop.",
                (
                    "An ancestry-only preview may hide mandatory execution, "
                    "verification, or review actions."
                ),
                "A preview may become stale when its binding or candidate changes.",
            ],
            "rollback": "Reject v10 and retain the active v9 binding unchanged.",
        },
        generated_at=STAMP,
        policy=policy,
        proposal_id="add-task-route-preview-cycle",
        base_targets={
            "containment": {
                "runtime-tooling.operate-run-lifecycle": lifecycle_edge,
                "steward-concordloom.runtime-tooling": runtime_parent_edge,
            }
        },
    )
    validate_evolution_proposal(
        evolution,
        policy,
        base_binding=binding,
        base_targets={
            "containment": {
                "runtime-tooling.operate-run-lifecycle": lifecycle_edge,
                "steward-concordloom.runtime-tooling": runtime_parent_edge,
            }
        },
    )
    return {
        "loop-design-proposal.json": loop_design,
        "evolution-proposal.json": evolution,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    target = root / "framework" / "concordloom" / "v10"
    documents = build(root)
    if args.check:
        stale = [
            name
            for name, document in documents.items()
            if not (target / name).is_file()
            or (target / name).read_bytes() != _pretty_bytes(document)
        ]
        if stale:
            raise SystemExit("STALE_TASK_ROUTE_PROPOSAL " + " ".join(stale))
        print("TASK_ROUTE_PROPOSAL_CHECK_OK")
        return

    for name, document in documents.items():
        save(target / name, document)
    print("TASK_ROUTE_PROPOSAL_OK")


if __name__ == "__main__":
    main()
