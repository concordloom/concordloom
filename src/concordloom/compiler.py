"""Compile operator-accepted intent into bounded loop contracts and bindings."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

from .canonical import digest, document_digest
from .loops import (
    InvariantError,
    all_capabilities,
    require_actor_capability,
    validate_loop_design,
    validate_policy,
    validate_registry,
)
from .schema import SchemaStore


COMPILER_PROFILE = "bounded-sdlc-v0.1"


def _accepted_decisions(decision_log: Mapping[str, Any]) -> list[str]:
    return sorted(
        decision["id"]
        for decision in decision_log["decisions"]
        if decision["verdict"] in {"confirmed", "corrected"}
    )


def _basis(graph: Mapping[str, Any]) -> list[dict[str, Any]]:
    for node in sorted(graph["nodes"], key=lambda item: item["id"]):
        if node["status"] in {"confirmed", "corrected"} and node["provenance"]:
            return [deepcopy(node["provenance"][0])]
    return [{"kind": "decision", "ref": "accepted-project-graph"}]


def validate_loop_design_proposal(
    proposal: dict[str, Any],
    accepted_graph: dict[str, Any],
    decision_log: dict[str, Any],
    policy: dict[str, Any],
    *,
    schema_store: SchemaStore | None = None,
) -> dict[str, Any]:
    """Validate a proposal's sources, finite containment, and exposed delta."""

    store = schema_store or SchemaStore()
    store.validate(proposal, "loop-design-proposal.schema.json")
    store.validate(accepted_graph, "project-graph.schema.json")
    store.validate(decision_log, "decision-log.schema.json")
    validate_policy(policy, schema_store=store)
    if accepted_graph["phase"] != "accepted":
        raise InvariantError("loop proposal requires an accepted project graph")
    if decision_log["acceptance"]["state"] != "complete":
        raise InvariantError("loop proposal requires accepted project intent")
    if proposal["source_graph_digest"] != digest(accepted_graph):
        raise InvariantError("loop proposal source graph digest mismatch")
    if proposal["decision_log_digest"] != digest(decision_log):
        raise InvariantError("loop proposal decision-log digest mismatch")
    if proposal["authority_policy_digest"] != digest(policy):
        raise InvariantError("loop proposal policy digest mismatch")
    accepted = {
        item["id"]
        for item in decision_log["decisions"]
        if item["verdict"] in {"confirmed", "corrected"}
    }
    loops = {item["id"]: item for item in proposal["loops"]}
    if len(loops) != len(proposal["loops"]):
        raise InvariantError("loop proposal repeats a loop id")
    adjacency: dict[str, set[str]] = defaultdict(set)
    edge_ids: set[str] = set()
    for loop in proposal["loops"]:
        if not set(loop["decision_ids"]) <= accepted:
            raise InvariantError(f"loop {loop['id']!r} cites an unaccepted decision")
    for edge in proposal["containment"]:
        if edge["id"] in edge_ids:
            raise InvariantError(f"duplicate containment proposal {edge['id']!r}")
        edge_ids.add(edge["id"])
        if edge["parent_loop_id"] not in loops or edge["child_loop_id"] not in loops:
            raise InvariantError(
                f"containment proposal {edge['id']!r} references an unknown loop"
            )
        if edge["decision_id"] not in accepted:
            raise InvariantError(
                f"containment proposal {edge['id']!r} cites an unaccepted decision"
            )
        adjacency[edge["parent_loop_id"]].add(edge["child_loop_id"])
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(loop_id: str) -> None:
        if loop_id in visiting:
            raise InvariantError("loop proposal containment graph contains a cycle")
        if loop_id in visited:
            return
        visiting.add(loop_id)
        for child in sorted(adjacency.get(loop_id, ())):
            visit(child)
        visiting.remove(loop_id)
        visited.add(loop_id)

    for loop_id in sorted(loops):
        visit(loop_id)
    expected_delta = [
        {"op": "add", "target_kind": "loop", "target_id": loop["id"], "value": loop}
        for loop in proposal["loops"]
    ] + [
        {
            "op": "add",
            "target_kind": "containment",
            "target_id": edge["id"],
            "value": edge,
        }
        for edge in proposal["containment"]
    ]
    if proposal["graph_delta"] != expected_delta:
        raise InvariantError("loop proposal graph delta does not expose exact design")
    return proposal


def propose_loop_design(
    accepted_graph: dict[str, Any],
    decision_log: dict[str, Any],
    policy: dict[str, Any],
    *,
    proposal_id: str = "loop-design-proposal",
    loop_specs: Sequence[Mapping[str, Any]] | None = None,
    containment: Sequence[Mapping[str, Any]] | None = None,
    schema_store: SchemaStore | None = None,
) -> dict[str, Any]:
    """Create a reviewable proposal; it has no execution authority.

    Callers may provide explicit loop specs.  Otherwise a deliberately small
    heuristic proposes one delivery loop plus stage loops supported by
    confirmed repository categories.  In both cases the output remains
    ``status=proposed`` until :func:`accept_loop_design` is called.
    """

    store = schema_store or SchemaStore()
    validate_policy(policy, schema_store=store)
    store.validate(accepted_graph, "project-graph.schema.json")
    store.validate(decision_log, "decision-log.schema.json")
    if accepted_graph["phase"] != "accepted":
        raise InvariantError("loop proposal requires an accepted project graph")
    if decision_log["acceptance"]["state"] != "complete":
        raise InvariantError("loop proposal requires a complete operator decision log")
    if accepted_graph.get("decision_log_digest") != digest(decision_log):
        raise InvariantError("accepted graph and decision log digest do not match")
    accepted_ids = _accepted_decisions(decision_log)
    if not accepted_ids:
        raise InvariantError("loop proposal needs at least one accepted decision")

    default_basis = _basis(accepted_graph)
    if loop_specs is None:
        categories = {
            node.get("category")
            for node in accepted_graph["nodes"]
            if node["status"] in {"confirmed", "corrected"}
        }
        stages: list[tuple[str, str, str, str]] = []
        if "decision" in categories or "documentation" in categories:
            stages.append(
                (
                    "requirements",
                    "Turn accepted intent into testable requirements.",
                    "Accepted outcome.",
                    "Testable requirements.",
                )
            )
        if "source" in categories:
            stages.append(
                (
                    "implementation",
                    "Produce a scoped candidate.",
                    "Testable requirements.",
                    "Candidate manifest.",
                )
            )
        if "test" in categories:
            stages.append(
                (
                    "testing",
                    "Evaluate the pinned candidate.",
                    "Candidate manifest.",
                    "Verification receipt.",
                )
            )
        if categories & {"build", "ci"}:
            stages.append(
                (
                    "release",
                    "Authorize a verified candidate for publication.",
                    "Verification receipt.",
                    "Release decision.",
                )
            )
        if "operations" in categories:
            stages.append(
                (
                    "operation",
                    "Observe one bounded operating window.",
                    "Release identity.",
                    "Operation observation.",
                )
            )
        loop_specs = [
            {
                "id": "delivery",
                "purpose": "Deliver one operator-accepted project outcome.",
                "input_outcome": "Operator-accepted outcome.",
                "output_outcome": "Verified delivery result or escalation.",
            },
            *(
                {
                    "id": identifier,
                    "purpose": purpose,
                    "input_outcome": input_outcome,
                    "output_outcome": output_outcome,
                }
                for identifier, purpose, input_outcome, output_outcome in stages
            ),
        ]
        containment = [
            {
                "id": f"delivery-{stage[0]}",
                "parent_loop_id": "delivery",
                "child_loop_id": stage[0],
            }
            for stage in stages
        ]
    elif containment is None:
        containment = []

    loops: list[dict[str, Any]] = []
    for spec in loop_specs:
        loops.append(
            {
                "id": spec["id"],
                "purpose": spec["purpose"],
                "input_outcome": spec["input_outcome"],
                "output_outcome": spec["output_outcome"],
                "basis": deepcopy(spec.get("basis", default_basis)),
                "decision_ids": sorted(spec.get("decision_ids", accepted_ids)),
            }
        )
    edges = [
        {
            "id": edge["id"],
            "parent_loop_id": edge["parent_loop_id"],
            "child_loop_id": edge["child_loop_id"],
            "decision_id": edge.get("decision_id", accepted_ids[0]),
        }
        for edge in containment
    ]
    operations = [
        {"op": "add", "target_kind": "loop", "target_id": loop["id"], "value": loop}
        for loop in loops
    ] + [
        {
            "op": "add",
            "target_kind": "containment",
            "target_id": edge["id"],
            "value": edge,
        }
        for edge in edges
    ]
    proposal = {
        "kind": "concordloom.loop-design-proposal",
        "schema_version": "0.1",
        "id": proposal_id,
        "status": "proposed",
        "compiler_profile": COMPILER_PROFILE,
        "source_graph_digest": digest(accepted_graph),
        "decision_log_digest": digest(decision_log),
        "authority_policy_digest": digest(policy),
        "loops": loops,
        "containment": edges,
        "graph_delta": operations,
        "acceptance_required": True,
    }
    validate_loop_design_proposal(
        proposal,
        accepted_graph,
        decision_log,
        policy,
        schema_store=store,
    )
    return proposal


def accept_loop_design(
    proposal: dict[str, Any],
    decision_log: dict[str, Any],
    policy: dict[str, Any],
    *,
    accepted_graph: dict[str, Any],
    decision_id: str,
    actor: Mapping[str, Any],
    accepted_at: str,
    authority_ref: str,
    rationale: str,
    schema_store: SchemaStore | None = None,
) -> dict[str, Any]:
    """Overlay explicit operator acceptance and return the public manifest."""

    store = schema_store or SchemaStore()
    if (
        proposal.get("kind") != "concordloom.loop-design-proposal"
        or proposal.get("status") != "proposed"
        or proposal.get("acceptance_required") is not True
    ):
        raise InvariantError("only an unaccepted loop-design proposal can be accepted")
    if proposal.get("compiler_profile") != COMPILER_PROFILE:
        raise InvariantError("unsupported loop-design compiler profile")
    validate_loop_design_proposal(
        proposal,
        accepted_graph,
        decision_log,
        policy,
        schema_store=store,
    )
    if decision_log["acceptance"]["state"] != "complete":
        raise InvariantError("loop-design acceptance requires accepted project intent")
    require_actor_capability(
        policy, actor, "accept-loop-design", authority_ref=authority_ref
    )
    if decision_id in {
        decision["id"] for decision in decision_log.get("decisions", [])
    }:
        raise InvariantError(
            "loop-design acceptance must be a separate decision, not an intent decision"
        )
    if not rationale.strip():
        raise InvariantError("loop-design acceptance requires a rationale")
    manifest = {
        "kind": "concordloom.loop-design-manifest",
        "schema_version": "0.1",
        "id": proposal["id"].removesuffix("-proposal") + "-manifest",
        "status": "accepted",
        "source_graph_digest": proposal["source_graph_digest"],
        "decision_log_digest": proposal["decision_log_digest"],
        "authority_policy_digest": proposal["authority_policy_digest"],
        "proposal_digest": digest(proposal),
        "loops": deepcopy(proposal["loops"]),
        "containment": deepcopy(proposal["containment"]),
        "accepted_by": {
            "decision_id": decision_id,
            "actor": deepcopy(dict(actor)),
            "accepted_at": accepted_at,
            "authority_ref": authority_ref,
            "rationale": rationale.strip(),
        },
    }
    store.validate(manifest, "loop-design-manifest.schema.json")
    return manifest


def _choose(capabilities: set[str], preferred: Sequence[str], purpose: str) -> str:
    for candidate in preferred:
        if candidate in capabilities:
            return candidate
    raise InvariantError(
        f"policy has no capability suitable for {purpose}; expected one of "
        f"{list(preferred)!r}"
    )


def _independence(
    policy: Mapping[str, Any], loop_id: str, subject: str, reviewer: str
) -> bool:
    for rule in policy["authority"]["separation_rules"]:
        applies = rule.get("applies_to_loop_ids")
        if (
            rule["subject_capability"] == subject
            and rule["review_capability"] == reviewer
            and (not applies or loop_id in applies)
        ):
            return True
    return False


def _contract(
    loop_id: str,
    *,
    producer: str,
    reviewer: str | None,
    subject: str,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": f"{loop_id}-acceptance",
        "description": f"Evidence that {loop_id} reached its accepted outcome.",
        "required_claims": [f"{loop_id}-outcome"],
        "accepted_results": ["pass"],
        "producer_capability": producer,
        "candidate_binding_required": True,
        "policy_binding_required": True,
    }
    if reviewer:
        result["reviewer_capability"] = reviewer
        result["independent_from_capability"] = subject
    return result


def _build_loop(
    design: Mapping[str, Any],
    child_edges: Sequence[Mapping[str, Any]],
    *,
    budget: Mapping[str, Any],
    execute_capability: str,
    accept_capability: str,
    escalate_capability: str,
) -> dict[str, Any]:
    loop_id = design["id"]
    states: list[dict[str, Any]] = [
        {"id": "start", "kind": "start", "label": "Start"},
    ]
    transitions: list[dict[str, Any]] = []
    for edge in child_edges:
        state_id = f"invoke-{edge['id']}"
        states.append(
            {
                "id": state_id,
                "kind": "child",
                "label": f"Invoke {edge['child_loop_id']}",
                "invocation_id": edge["id"],
            }
        )
    states.extend(
        [
            {"id": "work", "kind": "work", "label": "Produce candidate"},
            {"id": "gate", "kind": "gate", "label": "Evaluate evidence"},
            {
                "id": "succeeded",
                "kind": "terminal",
                "label": "Succeeded",
                "outcome": "succeeded",
            },
            {
                "id": "escalated",
                "kind": "terminal",
                "label": "Escalated",
                "outcome": "escalated",
            },
        ]
    )
    if child_edges:
        transitions.append(
            {
                "id": f"enter-{child_edges[0]['id']}",
                "from": "start",
                "to": f"invoke-{child_edges[0]['id']}",
                "kind": "progress",
                "guard": "accepted input is present",
                "evidence_contract_ids": [],
            }
        )
        for index, edge in enumerate(child_edges):
            state_id = f"invoke-{edge['id']}"
            next_state = (
                f"invoke-{child_edges[index + 1]['id']}"
                if index + 1 < len(child_edges)
                else "work"
            )
            transitions.extend(
                [
                    {
                        "id": f"{edge['id']}-success",
                        "from": state_id,
                        "to": next_state,
                        "kind": "success",
                        "guard": "child receipt accepted by parent contract",
                        "evidence_contract_ids": [],
                    },
                    {
                        "id": f"{edge['id']}-failure",
                        "from": state_id,
                        "to": "escalated",
                        "kind": "failure",
                        "guard": "child failed, timed out, or escalated",
                        "evidence_contract_ids": [],
                    },
                ]
            )
    else:
        transitions.append(
            {
                "id": "begin",
                "from": "start",
                "to": "work",
                "kind": "progress",
                "guard": "accepted input is present",
                "evidence_contract_ids": [],
            }
        )
    transitions.extend(
        [
            {
                "id": "evaluate",
                "from": "work",
                "to": "gate",
                "kind": "progress",
                "guard": "candidate and factual evidence are present",
                "evidence_contract_ids": [],
            },
            {
                "id": "accept",
                "from": "gate",
                "to": "succeeded",
                "kind": "success",
                "guard": "parent evaluates required evidence as passing",
                "evidence_contract_ids": [f"{loop_id}-acceptance"],
            },
            {
                "id": "escalate",
                "from": "gate",
                "to": "escalated",
                "kind": "escalation",
                "guard": "terminal failure or explicit escalation",
                "evidence_contract_ids": [],
            },
        ]
    )
    if budget["max_attempts"] > 1:
        transitions.append(
            {
                "id": "retry",
                "from": "gate",
                "to": "work",
                "kind": "feedback",
                "guard": "evidence requests a bounded revision",
                "evidence_contract_ids": [],
                "feedback_budget": {
                    "max_traversals": budget["max_attempts"] - 1,
                    "on_exhaustion_state": "escalated",
                    "on_exhaustion_outcome": "escalated",
                },
            }
        )
    return {
        "id": loop_id,
        "label": loop_id.replace("-", " ").title(),
        "purpose": design["purpose"],
        "inputs": [
            {
                "name": "input",
                "type": "artifact_ref",
                "description": design["input_outcome"],
                "required": True,
            }
        ],
        "outputs": [
            {
                "name": "output",
                "type": "artifact_ref",
                "description": design["output_outcome"],
                "required": True,
            }
        ],
        "budgets": deepcopy(dict(budget)),
        "authority": {
            "execute_capability": execute_capability,
            "accept_capability": accept_capability,
            "escalate_capability": escalate_capability,
        },
        "local_control_flow": {
            "entry_state": "start",
            "terminal_state_ids": ["escalated", "succeeded"],
            "states": states,
            "transitions": transitions,
        },
    }


def compile_registry(
    accepted_graph: dict[str, Any],
    decision_log: dict[str, Any],
    loop_design: dict[str, Any],
    policy: dict[str, Any],
    *,
    loop_design_proposal: dict[str, Any],
    registry_id: str = "compiled-cycle-registry",
    schema_store: SchemaStore | None = None,
) -> dict[str, Any]:
    """Compile an accepted manifest; never accept a proposal implicitly."""

    store = schema_store or SchemaStore()
    validate_loop_design(
        loop_design,
        decision_log,
        policy,
        proposal=loop_design_proposal,
        accepted_graph=accepted_graph,
        schema_store=store,
    )
    capabilities = all_capabilities(policy)
    execute = _choose(capabilities, ("execute-work",), "loop execution")
    accept = _choose(
        capabilities, ("accept-parent", "accept-gate", "accept-intent"), "loop acceptance"
    )
    escalate = _choose(capabilities, ("escalate",), "loop escalation")
    producer = _choose(capabilities, ("produce-evidence",), "evidence production")
    reviewer = (
        _choose(capabilities, ("review-candidate",), "independent review")
        if any(
            rule["disallow_same_principal"]
            for rule in policy["authority"]["separation_rules"]
        )
        else None
    )
    budget = policy["execution"]["default_budgets"]
    scope = policy["execution"]["default_scope"]
    designs = {loop["id"]: loop for loop in loop_design["loops"]}
    edges_by_parent: dict[str, list[dict[str, Any]]] = defaultdict(list)
    # The accepted array order defines the parent's child-invocation sequence.
    # Sorting by identifier here would silently replace an operator decision.
    for edge in loop_design["containment"]:
        edges_by_parent[edge["parent_loop_id"]].append(deepcopy(edge))

    contracts = [
        _contract(
            loop_id,
            producer=producer,
            reviewer=(
                reviewer
                if reviewer
                and _independence(policy, loop_id, execute, reviewer)
                else None
            ),
            subject=execute,
        )
        for loop_id in sorted(designs)
    ]
    loops = [
        _build_loop(
            designs[loop_id],
            edges_by_parent.get(loop_id, []),
            budget=budget,
            execute_capability=execute,
            accept_capability=accept,
            escalate_capability=escalate,
        )
        for loop_id in sorted(designs)
    ]

    loop_needs: dict[str, set[str]] = {}
    for loop in loops:
        contract = next(
            item for item in contracts if item["id"] == f"{loop['id']}-acceptance"
        )
        loop_needs[loop["id"]] = set(loop["authority"].values()) | {
            contract["producer_capability"]
        }
        if "reviewer_capability" in contract:
            loop_needs[loop["id"]].add(contract["reviewer_capability"])

    descendants: dict[str, set[str]] = {}

    def needs(loop_id: str) -> set[str]:
        if loop_id not in descendants:
            result = set(loop_needs[loop_id])
            for edge in edges_by_parent.get(loop_id, []):
                result |= needs(edge["child_loop_id"])
            descendants[loop_id] = result
        return descendants[loop_id]

    containment_edges: list[dict[str, Any]] = []
    for edge in loop_design["containment"]:
        parent_edges = edges_by_parent[edge["parent_loop_id"]]
        index = next(
            position for position, candidate in enumerate(parent_edges) if candidate == edge
        )
        success_state = (
            f"invoke-{parent_edges[index + 1]['id']}"
            if index + 1 < len(parent_edges)
            else "work"
        )
        containment_edges.append(
            {
                "id": edge["id"],
                "parent_loop_id": edge["parent_loop_id"],
                "child_loop_id": edge["child_loop_id"],
                "at_state": f"invoke-{edge['id']}",
                "success_state": success_state,
                "failure_state": "escalated",
                "grant": {
                    "scope": deepcopy(scope),
                    "capabilities": sorted(needs(edge["child_loop_id"])),
                    "budgets": deepcopy(budget),
                },
                "input_mapping": {},
                "output_mapping": {},
                "timeout_seconds": budget["max_elapsed_seconds"],
                "deadline_outcome": "escalated",
            }
        )
    children = {edge["child_loop_id"] for edge in containment_edges}
    roots = sorted(set(designs) - children)
    registry = {
        "kind": "concordloom.cycle-registry",
        "schema_version": "0.1",
        "id": registry_id,
        "source_graph_digest": digest(accepted_graph),
        "source_decisions_digest": digest(decision_log),
        "source_loop_design_digest": digest(loop_design),
        "policy_digest": digest(policy),
        "evidence_contracts": contracts,
        "loops": loops,
        "containment_graph": {"roots": roots, "edges": containment_edges},
    }
    validate_registry(registry, policy, schema_store=store)
    return registry


def _binding_artifacts(
    accepted_graph: dict[str, Any],
    decision_log: dict[str, Any],
    loop_design_proposal: dict[str, Any],
    loop_design: dict[str, Any],
    registry: dict[str, Any],
    policy: dict[str, Any],
    artifact_paths: Mapping[str, str],
    extra_artifacts: Mapping[str, tuple[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    expected = {
        "accepted_project_graph": accepted_graph,
        "decision_log": decision_log,
        "loop_design_proposal": loop_design_proposal,
        "accepted_loop_design": loop_design,
        "cycle_registry": registry,
        "policy": policy,
    }
    missing = set(expected) - set(artifact_paths)
    if missing:
        raise InvariantError(f"binding artifact paths missing roles {sorted(missing)!r}")
    artifacts = [
        {
            "role": role,
            "path": artifact_paths[role],
            "digest": digest(document),
        }
        for role, document in expected.items()
    ]
    for role, (path, document) in sorted((extra_artifacts or {}).items()):
        if role in expected:
            raise InvariantError(f"duplicate binding artifact role {role!r}")
        artifacts.append({"role": role, "path": path, "digest": digest(document)})
    artifacts.sort(key=lambda item: item["role"])
    if len({item["role"] for item in artifacts}) != len(artifacts):
        raise InvariantError("binding artifact roles must be unique")
    return artifacts


def create_binding_proposal(
    accepted_graph: dict[str, Any],
    decision_log: dict[str, Any],
    loop_design: dict[str, Any],
    registry: dict[str, Any],
    policy: dict[str, Any],
    *,
    loop_design_proposal: dict[str, Any],
    artifact_paths: Mapping[str, str],
    proposal_id: str,
    created_at: str,
    extra_artifacts: Mapping[str, tuple[str, Any]] | None = None,
    predecessor_binding_digest: str | None = None,
    schema_store: SchemaStore | None = None,
) -> dict[str, Any]:
    """Compile exact bytes into a non-authoritative activation proposal."""

    store = schema_store or SchemaStore()
    validate_loop_design(
        loop_design,
        decision_log,
        policy,
        proposal=loop_design_proposal,
        accepted_graph=accepted_graph,
        schema_store=store,
    )
    validate_registry(registry, policy, schema_store=store)
    if registry["source_loop_design_digest"] != digest(loop_design):
        raise InvariantError("registry and accepted loop design digest do not match")
    proposal: dict[str, Any] = {
        "kind": "concordloom.binding-proposal",
        "schema_version": "0.1",
        "id": proposal_id,
        "status": "proposed",
        "framework_version": "0.1.0",
        "created_at": created_at,
        "proposal_digest": "sha256:" + ("0" * 64),
        "digest_contract": {
            "algorithm": "sha256",
            "canonicalization": "rfc8785",
            "excluded_fields": ["/proposal_digest"],
        },
        "active_root_loop_ids": deepcopy(registry["containment_graph"]["roots"]),
        "artifacts": _binding_artifacts(
            accepted_graph,
            decision_log,
            loop_design_proposal,
            loop_design,
            registry,
            policy,
            artifact_paths,
            extra_artifacts,
        ),
        "activation_required": True,
    }
    if predecessor_binding_digest is not None:
        proposal["predecessor_binding_digest"] = predecessor_binding_digest
    proposal["proposal_digest"] = document_digest(
        proposal, excluded_fields=proposal["digest_contract"]["excluded_fields"]
    )
    store.validate(proposal, "binding-proposal.schema.json")
    return proposal


def validate_binding_proposal(
    proposal: dict[str, Any],
    accepted_graph: dict[str, Any],
    decision_log: dict[str, Any],
    loop_design_proposal: dict[str, Any],
    loop_design: dict[str, Any],
    registry: dict[str, Any],
    policy: dict[str, Any],
    *,
    extra_artifacts: Mapping[str, tuple[str, Any]] | None = None,
    schema_store: SchemaStore | None = None,
) -> dict[str, Any]:
    """Validate an exact activation proposal and every supplied source digest."""

    store = schema_store or SchemaStore()
    store.validate(proposal, "binding-proposal.schema.json")
    expected_digest = document_digest(
        proposal, excluded_fields=proposal["digest_contract"]["excluded_fields"]
    )
    if proposal["proposal_digest"] != expected_digest:
        raise InvariantError("binding proposal digest does not satisfy its contract")
    if proposal["status"] != "proposed" or proposal["activation_required"] is not True:
        raise InvariantError("binding proposal is not awaiting activation")
    validate_loop_design(
        loop_design,
        decision_log,
        policy,
        proposal=loop_design_proposal,
        accepted_graph=accepted_graph,
        schema_store=store,
    )
    validate_registry(registry, policy, schema_store=store)
    if registry["source_loop_design_digest"] != digest(loop_design):
        raise InvariantError("registry and accepted loop design digest do not match")
    expected_artifacts = _binding_artifacts(
        accepted_graph,
        decision_log,
        loop_design_proposal,
        loop_design,
        registry,
        policy,
        {item["role"]: item["path"] for item in proposal["artifacts"]},
        extra_artifacts,
    )
    if proposal["artifacts"] != expected_artifacts:
        raise InvariantError("binding proposal artifact set or digest changed")
    if proposal["active_root_loop_ids"] != registry["containment_graph"]["roots"]:
        raise InvariantError("binding proposal active roots do not match registry")
    return proposal


def activate_binding(
    proposal: dict[str, Any],
    accepted_graph: dict[str, Any],
    decision_log: dict[str, Any],
    loop_design_proposal: dict[str, Any],
    loop_design: dict[str, Any],
    registry: dict[str, Any],
    policy: dict[str, Any],
    *,
    activation_decision: Mapping[str, Any],
    binding_id: str,
    extra_artifacts: Mapping[str, tuple[str, Any]] | None = None,
    schema_store: SchemaStore | None = None,
) -> dict[str, Any]:
    """Activate one exact proposal through a separate authorized decision."""

    store = schema_store or SchemaStore()
    validate_binding_proposal(
        proposal,
        accepted_graph,
        decision_log,
        loop_design_proposal,
        loop_design,
        registry,
        policy,
        extra_artifacts=extra_artifacts,
        schema_store=store,
    )
    required_decision_fields = {
        "decision_id",
        "actor",
        "authority_ref",
        "accepted_at",
        "rationale",
    }
    missing = required_decision_fields - set(activation_decision)
    if missing:
        raise InvariantError(
            f"activation decision is missing fields {sorted(missing)!r}"
        )
    if not str(activation_decision["rationale"]).strip():
        raise InvariantError("activation decision requires a rationale")
    require_actor_capability(
        policy,
        activation_decision["actor"],
        "activate-binding",
        authority_ref=str(activation_decision["authority_ref"]),
    )
    accepted_by = {
        "decision_id": activation_decision["decision_id"],
        "actor": deepcopy(dict(activation_decision["actor"])),
        "authority_ref": activation_decision["authority_ref"],
        "accepted_at": activation_decision["accepted_at"],
        "proposal_digest": proposal["proposal_digest"],
        "rationale": str(activation_decision["rationale"]).strip(),
    }
    binding: dict[str, Any] = {
        "kind": "concordloom.binding",
        "schema_version": "0.1",
        "id": binding_id,
        "framework_version": "0.1.0",
        "created_at": activation_decision["accepted_at"],
        "binding_digest": "sha256:" + ("0" * 64),
        "digest_contract": {
            "algorithm": "sha256",
            "canonicalization": "rfc8785",
            "excluded_fields": ["/binding_digest"],
        },
        "active_root_loop_ids": deepcopy(proposal["active_root_loop_ids"]),
        "artifacts": deepcopy(proposal["artifacts"]),
        "accepted_by": accepted_by,
    }
    if "predecessor_binding_digest" in proposal:
        binding["predecessor_binding_digest"] = proposal[
            "predecessor_binding_digest"
        ]
    binding["binding_digest"] = document_digest(
        binding, excluded_fields=binding["digest_contract"]["excluded_fields"]
    )
    store.validate(binding, "binding.schema.json")
    if binding["binding_digest"] != document_digest(
        binding, excluded_fields=binding["digest_contract"]["excluded_fields"]
    ):
        raise InvariantError("binding digest does not match its digest contract")
    return binding


# Descriptive aliases used by integrations.
compile_loop_system = compile_registry
bind = activate_binding
