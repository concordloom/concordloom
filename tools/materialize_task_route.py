#!/usr/bin/env python3
"""Materialize the accepted v10 task-route successor without activating it."""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any

from concordloom.canonical import canonical_bytes, digest, document_digest, load, save
from concordloom.compiler import (
    accept_loop_design,
    compile_registry,
    create_binding_proposal,
)
from concordloom.evolution import validate_evolution_proposal
from concordloom.loops import (
    require_actor_capability,
    validate_policy,
    validate_registry,
)
from concordloom.schema import SchemaStore


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
EVOLUTION_PROPOSAL_DIGEST = (
    "sha256:2b6baf9e3d8b917224c29c28ca753acd06f4617e9a11ad0a5b6c776c10914dbc"
)
LOOP_DESIGN_PROPOSAL_DIGEST = (
    "sha256:c95d7f5eae7eb408c1a73bd309d92d5412471ceaeb8ee34b5f61b7f07f81a410"
)
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


def _raw_digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _load_canonical_receipt(path: Path, *, label: str) -> dict[str, Any]:
    raw = path.read_bytes()
    document = json.loads(raw.decode("utf-8"))
    if not isinstance(document, dict) or raw != canonical_bytes(document) + b"\n":
        raise ValueError(f"{label} receipt bytes are not exact canonical JSON")
    return document


def _receipt_payload(receipt: dict[str, Any], *, label: str) -> dict[str, Any]:
    payload = deepcopy(receipt)
    claimed = payload.pop("receipt_digest", None)
    if claimed is None or claimed != digest(payload):
        raise ValueError(f"{label} receipt digest does not match its canonical payload")
    return payload


def _require_exact_keys(
    document: dict[str, Any], expected: set[str], *, label: str
) -> None:
    if set(document) != expected:
        missing = sorted(expected - set(document))
        extra = sorted(set(document) - expected)
        raise ValueError(
            f"{label} fields changed (missing={missing!r}, extra={extra!r})"
        )


def _require_lifecycle_state(target: Path, catalog: dict[str, Any]) -> None:
    """Accept only the historical v9 head or the exact completed v10 activation."""

    present = {name for name in ACTIVATION_OUTPUTS if (target / name).exists()}
    if present and present != ACTIVATION_OUTPUTS:
        raise ValueError("v10 has an incomplete activation lifecycle")

    tail = catalog["entries"][-1]
    if catalog["active_binding_digest"] == BASE_BINDING_DIGEST:
        if present:
            raise ValueError("v10 authority artifacts exist before catalog activation")
        if (
            tail.get("binding_digest") != BASE_BINDING_DIGEST
            or tail.get("binding_id") != "concordloom-self-binding-v9"
            or tail.get("path") != "framework/concordloom/v9/binding.json"
        ):
            raise ValueError("catalog tail does not match the pinned v9 base")
        return

    if catalog["active_binding_digest"] != ACTIVE_BINDING_DIGEST:
        raise ValueError("catalog head is neither the v9 base nor exact v10 successor")
    if present != ACTIVATION_OUTPUTS:
        raise ValueError("catalog activates v10 without both authority artifacts")
    if (
        tail.get("binding_digest") != ACTIVE_BINDING_DIGEST
        or tail.get("binding_id") != "concordloom-self-binding-v10"
        or tail.get("path") != "framework/concordloom/v10/binding.json"
        or tail.get("previous_binding_digest") != BASE_BINDING_DIGEST
    ):
        raise ValueError("catalog tail does not match the exact v10 successor")

    active_binding = load(target / "binding.json")
    if (
        active_binding.get("id") != "concordloom-self-binding-v10"
        or active_binding.get("binding_digest") != ACTIVE_BINDING_DIGEST
        or active_binding.get("predecessor_binding_digest") != BASE_BINDING_DIGEST
        or active_binding.get("accepted_by", {}).get("proposal_digest")
        != BINDING_PROPOSAL_DIGEST
        or active_binding.get("accepted_by", {}).get("decision_id")
        != "activate-v10-task-route"
    ):
        raise ValueError("v10 binding is not the exact activated successor")
    if active_binding["binding_digest"] != document_digest(
        active_binding,
        excluded_fields=active_binding["digest_contract"]["excluded_fields"],
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


def _validate_publication_route(
    route: list[dict[str, Any]],
    registry: dict[str, Any],
    policy: dict[str, Any],
) -> None:
    """Validate the preserved publication projection outside binding roles."""

    if not route:
        raise ValueError("publication route must not be empty")
    loop_ids = {loop["id"] for loop in registry["loops"]}
    role_ids = {role["id"] for role in policy["authority"]["roles"]}
    allowed_effects = set(
        policy["execution"]["default_scope"]["external_mutations"]
    )
    seen: set[str] = set()
    for index, node in enumerate(route):
        label = f"publication route node {index}"
        loop_id = node.get("loop_id")
        if loop_id not in loop_ids or loop_id in seen:
            raise ValueError(f"{label} has unknown or duplicate loop_id")
        seen.add(loop_id)
        if node.get("node_id") != loop_id:
            raise ValueError(f"{label} node_id does not match loop_id")
        if node.get("role") not in role_ids:
            raise ValueError(f"{label} has an unknown role")
        scope = node.get("scope")
        if not isinstance(scope, dict) or set(scope) != {
            "external_mutations",
            "network",
            "read_paths",
            "write_paths",
        }:
            raise ValueError(f"{label} has an invalid scope")
        if scope["write_paths"]:
            raise ValueError(f"{label} may not mutate repository candidate bytes")
        effects = scope["external_mutations"]
        if not set(effects) <= allowed_effects:
            raise ValueError(f"{label} has an unaccepted external effect")
        if scope["network"] == "none" and effects:
            raise ValueError(f"{label} has an external effect without network write")
        if scope["network"] == "write" and not effects:
            raise ValueError(f"{label} has network write without an exact effect")
        if scope["network"] not in {"none", "write"}:
            raise ValueError(f"{label} has invalid network scope")


def _verify_pinned_input_files(
    root: Path,
    candidate_manifest: dict[str, Any],
) -> None:
    """Verify materializer inputs against the operator-accepted manifest.

    The output files and this materializer are later governed mutations, so a
    whole-worktree comparison would incorrectly treat the expected successor
    materialization as drift. The immutable proposal and predecessor inputs
    themselves must still match the operator-pinned candidate exactly. The
    catalog is deliberately excluded because activation appends to that mutable
    commit point; its exact lifecycle state is validated separately.
    """

    entries = {item["path"]: item for item in candidate_manifest["files"]}
    required_paths = [
        "framework/concordloom/v3/accepted-project-graph.json",
        "framework/concordloom/v3/decision-log.json",
        "framework/concordloom/v9/binding.json",
        "framework/concordloom/v9/cycle-registry.json",
        "framework/concordloom/v9/development-model.json",
        "framework/concordloom/v9/loop-design-proposal.json",
        "framework/concordloom/v9/loop-design.json",
        "framework/concordloom/v9/policy.json",
        "framework/concordloom/v9/publication-route.json",
        "framework/concordloom/v10/evolution-proposal.json",
        "framework/concordloom/v10/loop-design-proposal.json",
    ]
    for relative in required_paths:
        if relative not in entries:
            raise ValueError(f"accepted candidate does not contain {relative}")
        path = root / relative
        if not path.is_file() or _raw_digest(path) != entries[relative]["digest"]:
            raise ValueError(f"accepted materialization input changed: {relative}")


def _validate_decisions(
    *,
    policy: dict[str, Any],
    evolution: dict[str, Any],
    design_proposal: dict[str, Any],
    binding: dict[str, Any],
    candidate_manifest: dict[str, Any],
    design_decision: dict[str, Any],
    evolution_decision: dict[str, Any],
) -> None:
    store = SchemaStore()
    store.validate(candidate_manifest, "candidate-manifest.schema.json")
    candidate_manifest_digest = digest(candidate_manifest)
    candidate_tree_digest = candidate_manifest["tree_digest"]

    _require_exact_keys(
        design_decision,
        {
            "activation_allowed",
            "authority_ref",
            "base_binding_digest",
            "candidate_manifest_digest",
            "candidate_tree_digest",
            "capability",
            "decided_at",
            "evolution_proposal_digest",
            "id",
            "kind",
            "principal",
            "proposal_digest",
            "rationale",
            "receipt_digest",
            "schema_version",
            "verdict",
        },
        label="design decision",
    )
    _receipt_payload(design_decision, label="design decision")
    expected_design = {
        "kind": "concordloom.task-route-design-decision",
        "schema_version": "0.1",
        "proposal_digest": LOOP_DESIGN_PROPOSAL_DIGEST,
        "evolution_proposal_digest": EVOLUTION_PROPOSAL_DIGEST,
        "base_binding_digest": BASE_BINDING_DIGEST,
        "candidate_manifest_digest": candidate_manifest_digest,
        "candidate_tree_digest": candidate_tree_digest,
        "capability": "accept-loop-design",
        "verdict": "accepted",
        "activation_allowed": False,
        "authority_ref": "operator",
    }
    for key, value in expected_design.items():
        if design_decision.get(key) != value:
            raise ValueError(f"design decision does not bind exact {key}")

    _require_exact_keys(
        evolution_decision,
        {
            "activation_allowed",
            "authority_ref",
            "base_binding_digest",
            "candidate_manifest_digest",
            "candidate_tree_digest",
            "capability",
            "decided_at",
            "evolution_proposal_digest",
            "id",
            "kind",
            "principal",
            "rationale",
            "receipt_digest",
            "schema_version",
            "verdict",
        },
        label="evolution decision",
    )
    _receipt_payload(evolution_decision, label="evolution decision")
    expected_evolution = {
        "kind": "concordloom.evolution-decision",
        "schema_version": "0.1",
        "evolution_proposal_digest": EVOLUTION_PROPOSAL_DIGEST,
        "base_binding_digest": BASE_BINDING_DIGEST,
        "candidate_manifest_digest": candidate_manifest_digest,
        "candidate_tree_digest": candidate_tree_digest,
        "capability": "decide-evolution",
        "verdict": "accepted",
        "activation_allowed": False,
        "authority_ref": "operator",
    }
    for key, value in expected_evolution.items():
        if evolution_decision.get(key) != value:
            raise ValueError(f"evolution decision does not bind exact {key}")

    if design_decision["id"] == evolution_decision["id"]:
        raise ValueError("design and evolution decisions need distinct ids")
    if not design_decision["rationale"].strip() or not evolution_decision[
        "rationale"
    ].strip():
        raise ValueError("both decisions require a rationale")
    for decision in (design_decision, evolution_decision):
        principal = decision["principal"]
        require_actor_capability(
            policy,
            principal,
            decision["capability"],
            authority_ref=decision["authority_ref"],
        )
        if principal["id"] == evolution["proposed_by"]["id"]:
            raise ValueError("the evolution proposer cannot accept its own proposal")

    if digest(evolution) != EVOLUTION_PROPOSAL_DIGEST:
        raise ValueError("evolution proposal changed after operator acceptance")
    if digest(design_proposal) != LOOP_DESIGN_PROPOSAL_DIGEST:
        raise ValueError("loop-design proposal changed after operator acceptance")
    if binding["binding_digest"] != BASE_BINDING_DIGEST:
        raise ValueError("accepted decisions do not target the exact v9 binding")


def _runtime_parent_with_route(previous: dict[str, Any]) -> dict[str, Any]:
    parent = deepcopy(previous)
    states = parent["local_control_flow"]["states"]
    if any(state["id"] == "invoke-runtime-tooling.plan-task-route" for state in states):
        raise ValueError("runtime parent already contains the task-route child")
    compiler_state_index = next(
        index
        for index, state in enumerate(states)
        if state["id"] == "invoke-runtime-tooling.maintain-compiler-core"
    )
    states.insert(
        compiler_state_index + 1,
        {
            "id": "invoke-runtime-tooling.plan-task-route",
            "invocation_id": "runtime-tooling.plan-task-route",
            "kind": "child",
            "label": "Invoke plan-task-route",
        },
    )

    transitions = parent["local_control_flow"]["transitions"]
    compiler_success = next(
        transition
        for transition in transitions
        if transition["id"] == "runtime-tooling.maintain-compiler-core-success"
    )
    compiler_success["to"] = "invoke-runtime-tooling.plan-task-route"
    compiler_failure_index = next(
        index
        for index, transition in enumerate(transitions)
        if transition["id"] == "runtime-tooling.maintain-compiler-core-failure"
    )
    transitions[compiler_failure_index + 1 : compiler_failure_index + 1] = [
        {
            "evidence_contract_ids": ["plan-task-route-acceptance"],
            "from": "invoke-runtime-tooling.plan-task-route",
            "guard": "child receipt accepted by parent contract",
            "id": "runtime-tooling.plan-task-route-success",
            "kind": "success",
            "to": "invoke-runtime-tooling.operate-run-lifecycle",
        },
        {
            "evidence_contract_ids": [],
            "from": "invoke-runtime-tooling.plan-task-route",
            "guard": "child failed, timed out, or escalated",
            "id": "runtime-tooling.plan-task-route-failure",
            "kind": "failure",
            "to": "escalated",
        },
    ]
    return parent


def _build_registry(
    *,
    graph: dict[str, Any],
    decisions: dict[str, Any],
    accepted_design: dict[str, Any],
    design_proposal: dict[str, Any],
    policy: dict[str, Any],
    predecessor: dict[str, Any],
    evolution: dict[str, Any],
) -> dict[str, Any]:
    compiled = compile_registry(
        graph,
        decisions,
        accepted_design,
        policy,
        loop_design_proposal=design_proposal,
        registry_id="concordloom-development-registry-v10",
    )
    previous_loops = {loop["id"]: loop for loop in predecessor["loops"]}
    compiled_loops = {loop["id"]: loop for loop in compiled["loops"]}
    if set(compiled_loops) - set(previous_loops) != {"plan-task-route"}:
        raise ValueError("compiled v10 does not add exactly plan-task-route")

    route_loop = deepcopy(compiled_loops["plan-task-route"])
    route_loop["authority"] = {
        "execute_capability": "route-run",
        "accept_capability": "accept-parent",
        "escalate_capability": "escalate",
    }
    loops = deepcopy(previous_loops)
    loops["runtime-tooling"] = _runtime_parent_with_route(
        previous_loops["runtime-tooling"]
    )
    loops["plan-task-route"] = route_loop

    previous_contracts = {
        contract["id"]: contract for contract in predecessor["evidence_contracts"]
    }
    new_contract = deepcopy(
        next(
            contract
            for contract in compiled["evidence_contracts"]
            if contract["id"] == "plan-task-route-acceptance"
        )
    )
    new_contract["producer_capability"] = "route-run"
    new_contract["required_claims"] = [
        "plan-task-route-outcome",
        "route-preview-candidate-bound",
        "route-preview-execution-forbidden",
        "route-preview-full-local-flow",
        "route-preview-proposed",
    ]
    contracts = deepcopy(previous_contracts)
    contracts[new_contract["id"]] = new_contract

    compiled_new_edge = deepcopy(
        next(
            edge
            for edge in compiled["containment_graph"]["edges"]
            if edge["id"] == "runtime-tooling.plan-task-route"
        )
    )
    compiled_new_edge["grant"]["capabilities"] = [
        "accept-parent",
        "escalate",
        "route-run",
    ]
    compiled_new_edge["grant"]["scope"] = {
        "read_paths": [
            "AGENTS.md",
            "framework/concordloom/catalog.json",
            "schemas",
            "src/concordloom/route.py",
            "src/concordloom/run.py",
            "src/concordloom/schema.py",
        ],
        "write_paths": [],
        "network": "none",
        "external_mutations": [],
    }

    replacement_operation = next(
        operation
        for operation in evolution["operations"]
        if operation["op"] == "replace"
        and operation["target_id"] == "runtime-tooling.operate-run-lifecycle"
    )
    old_lifecycle_edge = next(
        edge
        for edge in predecessor["containment_graph"]["edges"]
        if edge["id"] == "runtime-tooling.operate-run-lifecycle"
    )
    if replacement_operation["precondition_digest"] != digest(old_lifecycle_edge):
        raise ValueError("run-lifecycle scope replacement has a stale precondition")
    parent_replacement_operation = next(
        operation
        for operation in evolution["operations"]
        if operation["op"] == "replace"
        and operation["target_id"] == "steward-concordloom.runtime-tooling"
    )
    old_parent_edge = next(
        edge
        for edge in predecessor["containment_graph"]["edges"]
        if edge["id"] == "steward-concordloom.runtime-tooling"
    )
    if parent_replacement_operation["precondition_digest"] != digest(old_parent_edge):
        raise ValueError("runtime-tooling parent replacement has a stale precondition")

    edges: list[dict[str, Any]] = []
    for previous_edge in predecessor["containment_graph"]["edges"]:
        edge = deepcopy(previous_edge)
        if edge["id"] == "steward-concordloom.runtime-tooling":
            edges.append(deepcopy(parent_replacement_operation["value"]))
            continue
        if edge["id"] == "runtime-tooling.maintain-compiler-core":
            edge["success_state"] = "invoke-runtime-tooling.plan-task-route"
            edges.append(edge)
            edges.append(compiled_new_edge)
            continue
        if edge["id"] == "runtime-tooling.operate-run-lifecycle":
            edges.append(deepcopy(replacement_operation["value"]))
            continue
        edges.append(edge)

    registry = {
        "kind": predecessor["kind"],
        "schema_version": predecessor["schema_version"],
        "id": "concordloom-development-registry-v10",
        "source_graph_digest": predecessor["source_graph_digest"],
        "source_decisions_digest": predecessor["source_decisions_digest"],
        "source_loop_design_digest": digest(accepted_design),
        "policy_digest": digest(policy),
        "evidence_contracts": [contracts[key] for key in sorted(contracts)],
        "loops": [loops[key] for key in sorted(loops)],
        "containment_graph": {
            "roots": deepcopy(predecessor["containment_graph"]["roots"]),
            "edges": edges,
        },
    }
    validate_registry(registry, policy)
    return registry


def _build_development_model(
    predecessor: dict[str, Any], evolution: dict[str, Any]
) -> dict[str, Any]:
    model = deepcopy(predecessor)
    model["id"] = "concordloom-development-system-v10"
    model["base_binding_digest"] = BASE_BINDING_DIGEST
    parent = next(node for node in model["nodes"] if node["id"] == "runtime-tooling")
    if "plan-task-route" in parent["children"]:
        raise ValueError("development model already contains plan-task-route")
    compiler_index = parent["children"].index("maintain-compiler-core")
    parent["children"].insert(compiler_index + 1, "plan-task-route")

    route_contract = deepcopy(
        next(
            operation["value"]["proposed_runtime_contract"]
            for operation in evolution["operations"]
            if operation["target_kind"] == "loop"
            and operation["target_id"] == "plan-task-route"
        )
    )
    deterministic = deepcopy(route_contract["routes"]["exact_route_compiler"])
    deterministic.pop("required")
    deterministic["tool_capabilities"] = ["route-compiler"]
    semantic = deepcopy(route_contract["routes"]["semantic_target_selection"])
    if "route-planning" in model["profiles"]:
        raise ValueError("development model already contains route-planning profile")
    model["profiles"]["route-planning"] = {
        "mcp": {
            "source": "active binding",
            "status": "not-declared",
        },
        "model_intent": {
            "en": "deterministic accepted-route compilation",
            "ru": "детерминированная сборка принятого пути",
        },
        "route_materialization": deepcopy(deterministic),
        "skills": [],
        "tools": ["route-compiler"],
        "truth_layer": "planned",
    }
    insertion_index = next(
        index
        for index, node in enumerate(model["nodes"])
        if node["id"] == "maintain-compiler-core"
    )
    model["nodes"].insert(
        insertion_index + 1,
        {
            "id": "plan-task-route",
            "parent_id": "runtime-tooling",
            "children": [],
            "copy": {
                "en": {
                    "label": "Preview Task Route",
                    "purpose": (
                        "Show the complete accepted work path before a run is "
                        "authorized."
                    ),
                },
                "ru": {
                    "label": "Показать путь задачи",
                    "purpose": (
                        "Показывать весь принятый путь работы до разрешения "
                        "запуска."
                    ),
                },
            },
            "responsible_role": {
                "en": "orchestrator",
                "ru": "координатор",
            },
            "execution_profile": "route-planning",
            "contract": {
                "en": {
                    "input": (
                        "A task request, active binding, accepted registry and "
                        "exact candidate."
                    ),
                    "output": (
                        "A candidate-bound proposed route that cannot execute "
                        "or authorize work."
                    ),
                },
                "ru": {
                    "input": (
                        "Запрос, действующая версия правил, принятая карта "
                        "циклов и точная версия файлов."
                    ),
                    "output": (
                        "Предлагаемый путь, привязанный к точной версии файлов "
                        "и не способный запустить или разрешить работу."
                    ),
                },
            },
            "artifacts": [
                "task-request",
                "candidate-manifest",
                "route-preview",
            ],
            "route_materialization": deterministic,
            "route_variants": {
                "semantic_target_selection": semantic,
            },
            "route_contract": route_contract,
        },
    )
    return model


def build(
    root: Path,
    *,
    design_decision_path: Path,
    evolution_decision_path: Path,
    candidate_manifest_path: Path,
) -> dict[str, dict[str, Any]]:
    source = root / "framework" / "concordloom"
    predecessor = source / "v9"
    target = source / "v10"

    graph = load(source / "v3" / "accepted-project-graph.json")
    decisions = load(source / "v3" / "decision-log.json")
    catalog = load(source / "catalog.json")
    binding = load(predecessor / "binding.json")
    previous_registry = load(predecessor / "cycle-registry.json")
    previous_model = load(predecessor / "development-model.json")
    policy = load(predecessor / "policy.json")
    publication_route = load(predecessor / "publication-route.json")
    design_proposal = load(target / "loop-design-proposal.json")
    evolution = load(target / "evolution-proposal.json")
    design_decision = _load_canonical_receipt(
        design_decision_path, label="design decision"
    )
    evolution_decision = _load_canonical_receipt(
        evolution_decision_path, label="evolution decision"
    )
    candidate_manifest = load(candidate_manifest_path)
    _require_lifecycle_state(target, catalog)

    if binding["binding_digest"] != document_digest(
        binding, excluded_fields=binding["digest_contract"]["excluded_fields"]
    ):
        raise ValueError("v9 binding digest contract failed")
    if binding["binding_digest"] != BASE_BINDING_DIGEST:
        raise ValueError("v9 binding is not the accepted materialization base")
    validate_policy(policy)
    _verify_pinned_input_files(root, candidate_manifest)
    _validate_decisions(
        policy=policy,
        evolution=evolution,
        design_proposal=design_proposal,
        binding=binding,
        candidate_manifest=candidate_manifest,
        design_decision=design_decision,
        evolution_decision=evolution_decision,
    )

    old_lifecycle_edge = next(
        edge
        for edge in previous_registry["containment_graph"]["edges"]
        if edge["id"] == "runtime-tooling.operate-run-lifecycle"
    )
    old_runtime_parent_edge = next(
        edge
        for edge in previous_registry["containment_graph"]["edges"]
        if edge["id"] == "steward-concordloom.runtime-tooling"
    )
    validate_evolution_proposal(
        evolution,
        policy,
        base_binding=binding,
        base_targets={
            "containment": {
                "runtime-tooling.operate-run-lifecycle": old_lifecycle_edge,
                "steward-concordloom.runtime-tooling": old_runtime_parent_edge,
            }
        },
    )

    accepted_design = accept_loop_design(
        design_proposal,
        decisions,
        policy,
        accepted_graph=graph,
        decision_id=design_decision["id"],
        actor={
            "id": design_decision["principal"]["id"],
            "kind": "operator",
        },
        accepted_at=design_decision["decided_at"],
        authority_ref=design_decision["authority_ref"],
        rationale=design_decision["rationale"],
    )
    registry = _build_registry(
        graph=graph,
        decisions=decisions,
        accepted_design=accepted_design,
        design_proposal=design_proposal,
        policy=policy,
        predecessor=previous_registry,
        evolution=evolution,
    )
    _validate_publication_route(publication_route, registry, policy)
    model = _build_development_model(previous_model, evolution)
    history = {
        "kind": "concordloom.evolution-history",
        "schema_version": "0.1",
        "id": "task-route-v10-evolution-history",
        "base_binding_digest": BASE_BINDING_DIGEST,
        "candidate_manifest_digest": digest(candidate_manifest),
        "candidate_tree_digest": candidate_manifest["tree_digest"],
        "evolution_proposal": {
            "id": evolution["id"],
            "digest": EVOLUTION_PROPOSAL_DIGEST,
        },
        "loop_design_proposal": {
            "id": design_proposal["id"],
            "digest": LOOP_DESIGN_PROPOSAL_DIGEST,
        },
        "publication_route": {
            "path": "framework/concordloom/v10/publication-route.json",
            "digest": digest(publication_route),
        },
        "decisions": [
            {
                "kind": "decide-evolution",
                "id": evolution_decision["id"],
                "receipt_digest": evolution_decision["receipt_digest"],
            },
            {
                "kind": "accept-loop-design",
                "id": design_decision["id"],
                "receipt_digest": design_decision["receipt_digest"],
            },
        ],
        "activation_allowed": False,
    }
    paths = {
        "accepted_project_graph": (
            "framework/concordloom/v3/accepted-project-graph.json"
        ),
        "decision_log": "framework/concordloom/v3/decision-log.json",
        "loop_design_proposal": (
            "framework/concordloom/v10/loop-design-proposal.json"
        ),
        "accepted_loop_design": "framework/concordloom/v10/loop-design.json",
        "cycle_registry": "framework/concordloom/v10/cycle-registry.json",
        "policy": "framework/concordloom/v10/policy.json",
    }
    extras = {
        "atlas_input": (
            "framework/concordloom/v10/development-model.json",
            model,
        ),
        "evolution_history": (
            "framework/concordloom/v10/evolution-history.json",
            history,
        ),
    }
    proposal = create_binding_proposal(
        graph,
        decisions,
        accepted_design,
        registry,
        policy,
        loop_design_proposal=design_proposal,
        artifact_paths=paths,
        proposal_id="concordloom-self-binding-v10-proposal",
        created_at=evolution_decision["decided_at"],
        predecessor_binding_digest=BASE_BINDING_DIGEST,
        extra_artifacts=extras,
    )
    if proposal["status"] != "proposed" or proposal["activation_required"] is not True:
        raise ValueError("v10 binding proposal crossed the activation boundary")

    return {
        "loop-design.json": accepted_design,
        "cycle-registry.json": registry,
        "policy.json": policy,
        "development-model.json": model,
        "evolution-history.json": history,
        "binding-proposal.json": proposal,
        "publication-route.json": publication_route,
    }


def _resolve_under_root(root: Path, value: Path) -> Path:
    return value if value.is_absolute() else root / value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument(
        "--design-decision",
        type=Path,
        default=Path(".concord/runs/route-preview-v10/design-decision-r2.json"),
    )
    parser.add_argument(
        "--evolution-decision",
        type=Path,
        default=Path(".concord/runs/route-preview-v10/evolution-decision-r2.json"),
    )
    parser.add_argument(
        "--candidate-manifest",
        type=Path,
        default=Path(".concord/runs/route-preview-v10/revision-candidate.json"),
    )
    args = parser.parse_args()
    root = args.root.resolve()
    target = root / "framework" / "concordloom" / "v10"
    documents = build(
        root,
        design_decision_path=_resolve_under_root(root, args.design_decision),
        evolution_decision_path=_resolve_under_root(root, args.evolution_decision),
        candidate_manifest_path=_resolve_under_root(root, args.candidate_manifest),
    )
    if set(documents) != MATERIALIZED_OUTPUTS:
        raise SystemExit("materializer output set changed")
    if args.check:
        stale = [
            name
            for name, document in documents.items()
            if not (target / name).is_file()
            or (target / name).read_bytes() != _pretty_bytes(document)
        ]
        if stale:
            raise SystemExit("STALE_TASK_ROUTE_MATERIALIZATION " + " ".join(stale))
        print("TASK_ROUTE_MATERIALIZATION_CHECK_OK")
        return

    for name, document in documents.items():
        save(target / name, document)
    _require_lifecycle_state(target, load(root / "framework" / "concordloom" / "catalog.json"))
    print(
        "TASK_ROUTE_MATERIALIZATION_OK "
        f"proposal={documents['binding-proposal.json']['proposal_digest']}"
    )


if __name__ == "__main__":
    main()
