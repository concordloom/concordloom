"""Semantic invariants for bounded systems of development loops."""

from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Iterable, Mapping
from pathlib import PurePosixPath
from typing import Any

from .canonical import digest
from .schema import SchemaStore


class InvariantError(ValueError):
    """A schema-valid artifact violates a cross-field governance invariant."""


def _index(values: Iterable[dict[str, Any]], label: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for value in values:
        identifier = value["id"]
        if identifier in result:
            raise InvariantError(f"duplicate {label} id {identifier!r}")
        result[identifier] = value
    return result


def _safe_parts(raw: str) -> tuple[str, ...]:
    if raw == ".":
        return ()
    path = PurePosixPath(raw)
    if path.is_absolute() or ".." in path.parts or "\\" in raw:
        raise InvariantError(f"unsafe relative path {raw!r}")
    return tuple(part for part in path.parts if part not in ("", "."))


def path_within(path: str, prefix: str) -> bool:
    child = _safe_parts(path)
    parent = _safe_parts(prefix)
    return child[: len(parent)] == parent


def _paths_subset(children: Iterable[str], parents: Iterable[str]) -> bool:
    allowed = tuple(parents)
    return all(any(path_within(child, parent) for parent in allowed) for child in children)


def scope_subset(child: Mapping[str, Any], parent: Mapping[str, Any]) -> bool:
    """Return whether a child grant is no broader than a parent grant."""

    network_order = {"none": 0, "read": 1, "write": 2}
    return (
        _paths_subset(child["read_paths"], parent["read_paths"])
        and _paths_subset(child["write_paths"], parent["write_paths"])
        and network_order[child["network"]] <= network_order[parent["network"]]
        and set(child["external_mutations"]) <= set(parent["external_mutations"])
    )


def budget_subset(child: Mapping[str, Any], parent: Mapping[str, Any]) -> bool:
    return (
        child["max_attempts"] <= parent["max_attempts"]
        and child["max_elapsed_seconds"] <= parent["max_elapsed_seconds"]
        and child["max_cost_units"] <= parent["max_cost_units"]
    )


def policy_roles(policy: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return _index(policy["authority"]["roles"], "role")


def policy_principals(policy: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return _index(policy["authority"]["principals"], "principal")


def all_capabilities(policy: Mapping[str, Any]) -> set[str]:
    return {
        capability
        for role in policy["authority"]["roles"]
        for capability in role["capabilities"]
    }


def principal_capabilities(policy: Mapping[str, Any], principal_id: str) -> set[str]:
    roles = policy_roles(policy)
    principals = policy_principals(policy)
    try:
        principal = principals[principal_id]
    except KeyError as exc:
        raise InvariantError(f"unknown principal {principal_id!r}") from exc
    return {
        capability
        for role_id in principal["roles"]
        for capability in roles[role_id]["capabilities"]
    }


def require_actor_capability(
    policy: Mapping[str, Any],
    actor: Mapping[str, Any],
    capability: str,
    *,
    authority_ref: str | None = None,
) -> None:
    """Resolve an actor through the bound policy and require a capability."""

    principal_id = actor.get("id")
    principals = policy_principals(policy)
    if principal_id not in principals:
        raise InvariantError(f"actor {principal_id!r} is not a bound principal")
    principal = principals[principal_id]
    if authority_ref is not None and authority_ref not in principal["roles"]:
        raise InvariantError(
            f"principal {principal_id!r} does not hold authority role {authority_ref!r}"
        )
    if capability not in principal_capabilities(policy, principal_id):
        raise InvariantError(
            f"principal {principal_id!r} lacks capability {capability!r}"
        )


def validate_policy(
    policy: dict[str, Any], *, schema_store: SchemaStore | None = None
) -> dict[str, Any]:
    store = schema_store or SchemaStore()
    store.validate(policy, "policy.schema.json")
    roles = policy_roles(policy)
    principals = policy_principals(policy)
    capabilities = all_capabilities(policy)
    for principal in principals.values():
        unknown = set(principal["roles"]) - set(roles)
        if unknown:
            raise InvariantError(
                f"principal {principal['id']!r} has unknown roles {sorted(unknown)!r}"
            )
    runner_id = policy["execution"]["control_plane"]["runner_principal_id"]
    if runner_id not in principals:
        raise InvariantError(f"control-plane runner {runner_id!r} is not a principal")
    separation_ids: set[str] = set()
    for rule in policy["authority"]["separation_rules"]:
        if rule["id"] in separation_ids:
            raise InvariantError(f"duplicate separation rule {rule['id']!r}")
        separation_ids.add(rule["id"])
        for key in ("subject_capability", "review_capability"):
            if rule[key] not in capabilities:
                raise InvariantError(
                    f"separation rule {rule['id']!r} uses unknown capability "
                    f"{rule[key]!r}"
                )
    evolution = policy["evolution"]
    for key in ("proposal_capability", "decision_capability", "activation_capability"):
        if evolution[key] not in capabilities:
            raise InvariantError(f"evolution policy uses unknown capability {evolution[key]!r}")
    model_policy = policy["execution"]["model_policy"]
    allowed_providers = set(model_policy["allowed_providers"])
    model_pairs: set[tuple[str, str]] = set()
    for model in model_policy["allowed_models"]:
        pair = (model["provider"], model["model"])
        if pair in model_pairs:
            raise InvariantError(f"duplicate allowed model route {pair!r}")
        model_pairs.add(pair)
        if model["provider"] and model["provider"] not in allowed_providers:
            raise InvariantError(
                f"allowed model {model['model']!r} uses an unapproved provider"
            )
        if model["provider"] == "" and model["model"] != "none":
            raise InvariantError("providerless model routes must use model 'none'")
    public_classes = set(model_policy["public_content_classes"])
    if public_classes - set(model_policy["allowed_content_classes"]):
        raise InvariantError(
            "public content classes must be a subset of allowed content classes"
        )
    return policy


def _reachable(entry: str, adjacency: Mapping[str, set[str]]) -> set[str]:
    seen: set[str] = set()
    pending = [entry]
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        pending.extend(sorted(adjacency.get(current, ()), reverse=True))
    return seen


def _acyclic(nodes: Iterable[str], adjacency: Mapping[str, set[str]], label: str) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            raise InvariantError(f"{label} contains a cycle through {node!r}")
        if node in visited:
            return
        visiting.add(node)
        for target in sorted(adjacency.get(node, ())):
            visit(target)
        visiting.remove(node)
        visited.add(node)

    for node in sorted(nodes):
        visit(node)


def strongly_connected_components(
    nodes: Iterable[str], adjacency: Mapping[str, set[str]]
) -> list[set[str]]:
    """Return deterministic Tarjan SCCs, primarily for diagnostics and tests."""

    index = 0
    indices: dict[str, int] = {}
    low: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    result: list[set[str]] = []

    def visit(node: str) -> None:
        nonlocal index
        indices[node] = low[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)
        for target in sorted(adjacency.get(node, ())):
            if target not in indices:
                visit(target)
                low[node] = min(low[node], low[target])
            elif target in on_stack:
                low[node] = min(low[node], indices[target])
        if low[node] == indices[node]:
            component: set[str] = set()
            while True:
                member = stack.pop()
                on_stack.remove(member)
                component.add(member)
                if member == node:
                    break
            result.append(component)

    for node in sorted(nodes):
        if node not in indices:
            visit(node)
    return result


def _validate_control_flow(
    loop: dict[str, Any],
    contracts: Mapping[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    flow = loop["local_control_flow"]
    states = _index(flow["states"], f"state in loop {loop['id']}")
    transitions = _index(flow["transitions"], f"transition in loop {loop['id']}")
    entry = flow["entry_state"]
    if entry not in states:
        raise InvariantError(f"loop {loop['id']!r} entry state does not exist")
    start_states = [state["id"] for state in states.values() if state["kind"] == "start"]
    if start_states != [entry]:
        raise InvariantError(
            f"loop {loop['id']!r} must have exactly one start state equal to entry"
        )
    declared_terminals = set(flow["terminal_state_ids"])
    actual_terminals = {
        state["id"] for state in states.values() if state["kind"] == "terminal"
    }
    if declared_terminals != actual_terminals:
        raise InvariantError(
            f"loop {loop['id']!r} terminal_state_ids must list exactly terminal states"
        )

    adjacency: dict[str, set[str]] = defaultdict(set)
    reverse: dict[str, set[str]] = defaultdict(set)
    non_feedback: dict[str, set[str]] = defaultdict(set)
    outgoing: dict[str, int] = defaultdict(int)
    for transition in transitions.values():
        source, target = transition["from"], transition["to"]
        if source not in states or target not in states:
            raise InvariantError(
                f"loop {loop['id']!r} transition {transition['id']!r} "
                "references an unknown state"
            )
        if source in declared_terminals:
            raise InvariantError(
                f"terminal state {source!r} in loop {loop['id']!r} has an outgoing edge"
            )
        adjacency[source].add(target)
        reverse[target].add(source)
        outgoing[source] += 1
        unknown_contracts = set(transition["evidence_contract_ids"]) - set(contracts)
        if unknown_contracts:
            raise InvariantError(
                f"transition {transition['id']!r} uses unknown evidence contracts "
                f"{sorted(unknown_contracts)!r}"
            )
        if transition["kind"] == "feedback":
            budget = transition["feedback_budget"]
            exhaustion = budget["on_exhaustion_state"]
            if exhaustion not in states:
                raise InvariantError(
                    f"feedback transition {transition['id']!r} has unknown "
                    "exhaustion state"
                )
            exhaustion_state = states[exhaustion]
            if (
                exhaustion_state["kind"] != "terminal"
                or exhaustion_state["outcome"] != budget["on_exhaustion_outcome"]
            ):
                raise InvariantError(
                    f"feedback transition {transition['id']!r} exhaustion must point "
                    "to a matching terminal outcome"
                )
            if budget["max_traversals"] > loop["budgets"]["max_attempts"]:
                raise InvariantError(
                    f"feedback transition {transition['id']!r} exceeds loop attempts"
                )
        else:
            non_feedback[source].add(target)

    reachable = _reachable(entry, adjacency)
    if reachable != set(states):
        raise InvariantError(
            f"loop {loop['id']!r} has unreachable states "
            f"{sorted(set(states) - reachable)!r}"
        )
    for state_id in set(states) - declared_terminals:
        if not outgoing[state_id]:
            raise InvariantError(
                f"loop {loop['id']!r} has nonterminal dead end {state_id!r}"
            )
    terminal_reachable: set[str] = set()
    pending = list(declared_terminals)
    while pending:
        current = pending.pop()
        if current in terminal_reachable:
            continue
        terminal_reachable.add(current)
        pending.extend(reverse.get(current, ()))
    missing_terminal_path = reachable - terminal_reachable
    if missing_terminal_path:
        raise InvariantError(
            f"loop {loop['id']!r} states cannot reach a terminal: "
            f"{sorted(missing_terminal_path)!r}"
        )

    # If removing all budget-consuming feedback edges leaves a cycle, at least
    # one runtime cycle can repeat without consuming a finite budget.
    _acyclic(states, non_feedback, f"unbudgeted control flow in loop {loop['id']!r}")
    for component in strongly_connected_components(states, adjacency):
        cyclic = len(component) > 1 or any(
            node in adjacency.get(node, ()) for node in component
        )
        if cyclic and not any(
            transition["kind"] == "feedback"
            and transition["from"] in component
            and transition["to"] in component
            for transition in transitions.values()
        ):
            raise InvariantError(
                f"cyclic SCC in loop {loop['id']!r} has no bounded feedback edge"
            )
    return states


def validate_loop_design(
    design: dict[str, Any],
    decision_log: dict[str, Any],
    policy: dict[str, Any],
    *,
    proposal: dict[str, Any],
    accepted_graph: dict[str, Any] | None = None,
    schema_store: SchemaStore | None = None,
) -> dict[str, Any]:
    store = schema_store or SchemaStore()
    validate_policy(policy, schema_store=store)
    store.validate(decision_log, "decision-log.schema.json")
    store.validate(design, "loop-design-manifest.schema.json")
    store.validate(proposal, "loop-design-proposal.schema.json")
    if design["proposal_digest"] != digest(proposal):
        raise InvariantError("loop design is not bound to the supplied proposal")
    for field in (
        "source_graph_digest",
        "decision_log_digest",
        "authority_policy_digest",
        "loops",
        "containment",
    ):
        if design[field] != proposal[field]:
            raise InvariantError(
                f"accepted loop design changes proposed field {field!r}"
            )
    if decision_log["acceptance"]["state"] != "complete":
        raise InvariantError("decision log is not operator-accepted")
    if decision_log["unresolved_blocking_question_ids"]:
        raise InvariantError("blocking operator questions remain unresolved")
    require_actor_capability(
        policy,
        decision_log["acceptance"]["actor"],
        "accept-intent",
        authority_ref=decision_log["acceptance"]["authority_ref"],
    )
    require_actor_capability(
        policy,
        design["accepted_by"]["actor"],
        "accept-loop-design",
        authority_ref=design["accepted_by"]["authority_ref"],
    )
    policy_digest = digest(policy)
    if design["authority_policy_digest"] != policy_digest:
        raise InvariantError("loop design is not bound to the supplied policy")
    if design["decision_log_digest"] != digest(decision_log):
        raise InvariantError("loop design is not bound to the supplied decision log")
    if accepted_graph is not None:
        store.validate(accepted_graph, "project-graph.schema.json")
        if accepted_graph["phase"] != "accepted":
            raise InvariantError("compiler input project graph is not accepted")
        if design["source_graph_digest"] != digest(accepted_graph):
            raise InvariantError("loop design is not bound to the accepted project graph")
        if accepted_graph.get("decision_log_digest") != digest(decision_log):
            raise InvariantError("accepted graph is not bound to the decision log")

    decisions = _index(decision_log["decisions"], "decision")
    allowed_verdicts = {"confirmed", "corrected"}
    loops = _index(design["loops"], "loop design")
    adjacency: dict[str, set[str]] = defaultdict(set)
    for loop in loops.values():
        for decision_id in loop["decision_ids"]:
            if decision_id not in decisions:
                raise InvariantError(
                    f"loop {loop['id']!r} cites unknown decision {decision_id!r}"
                )
            if decisions[decision_id]["verdict"] not in allowed_verdicts:
                raise InvariantError(
                    f"loop {loop['id']!r} cites rejected decision {decision_id!r}"
                )
    containment_ids: set[str] = set()
    for edge in design["containment"]:
        if edge["id"] in containment_ids:
            raise InvariantError(f"duplicate containment design {edge['id']!r}")
        containment_ids.add(edge["id"])
        parent, child = edge["parent_loop_id"], edge["child_loop_id"]
        if parent not in loops or child not in loops:
            raise InvariantError(
                f"containment design {edge['id']!r} references an unknown loop"
            )
        decision_id = edge["decision_id"]
        if (
            decision_id not in decisions
            or decisions[decision_id]["verdict"] not in allowed_verdicts
        ):
            raise InvariantError(
                f"containment design {edge['id']!r} lacks an accepted decision"
            )
        adjacency[parent].add(child)
    _acyclic(loops, adjacency, "accepted containment design")
    return design


def _separation_applies(
    policy: Mapping[str, Any],
    *,
    subject: str,
    reviewer: str,
    loop_id: str,
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


def validate_registry(
    registry: dict[str, Any],
    policy: dict[str, Any],
    *,
    schema_store: SchemaStore | None = None,
) -> dict[str, Any]:
    store = schema_store or SchemaStore()
    validate_policy(policy, schema_store=store)
    store.validate(registry, "cycle-registry.schema.json")
    if registry["policy_digest"] != digest(policy):
        raise InvariantError("cycle registry policy digest mismatch")
    capabilities = all_capabilities(policy)
    contracts = _index(registry["evidence_contracts"], "evidence contract")
    for contract in contracts.values():
        referenced = {
            contract["producer_capability"],
            contract.get("reviewer_capability"),
            contract.get("independent_from_capability"),
        } - {None}
        unknown = referenced - capabilities
        if unknown:
            raise InvariantError(
                f"evidence contract {contract['id']!r} uses unknown capabilities "
                f"{sorted(unknown)!r}"
            )

    loops = _index(registry["loops"], "loop")
    states_by_loop: dict[str, dict[str, dict[str, Any]]] = {}
    for loop in loops.values():
        for capability in loop["authority"].values():
            if capability not in capabilities:
                raise InvariantError(
                    f"loop {loop['id']!r} uses unknown capability {capability!r}"
                )
        states_by_loop[loop["id"]] = _validate_control_flow(loop, contracts)
        used_contracts = {
            contract_id
            for transition in loop["local_control_flow"]["transitions"]
            for contract_id in transition["evidence_contract_ids"]
        }
        for contract_id in used_contracts:
            contract = contracts[contract_id]
            subject = contract.get("independent_from_capability")
            reviewer = contract.get("reviewer_capability")
            if subject and reviewer and not _separation_applies(
                policy, subject=subject, reviewer=reviewer, loop_id=loop["id"]
            ):
                raise InvariantError(
                    f"loop {loop['id']!r} uses independent contract {contract_id!r} "
                    "without a matching separation rule"
                )

    containment = registry["containment_graph"]
    edges = _index(containment["edges"], "containment edge")
    adjacency: dict[str, set[str]] = defaultdict(set)
    indegree = {loop_id: 0 for loop_id in loops}
    incoming: dict[str, list[dict[str, Any]]] = defaultdict(list)
    invocation_edges: dict[tuple[str, str], str] = {}
    for edge in edges.values():
        parent, child = edge["parent_loop_id"], edge["child_loop_id"]
        if parent not in loops or child not in loops:
            raise InvariantError(
                f"containment edge {edge['id']!r} references an unknown loop"
            )
        adjacency[parent].add(child)
        indegree[child] += 1
        incoming[child].append(edge)
        states = states_by_loop[parent]
        at_state = edge["at_state"]
        if at_state not in states or states[at_state]["kind"] != "child":
            raise InvariantError(
                f"containment edge {edge['id']!r} is not attached to a child state"
            )
        if states[at_state].get("invocation_id") != edge["id"]:
            raise InvariantError(
                f"child state {at_state!r} does not name invocation {edge['id']!r}"
            )
        for target_key in ("success_state", "failure_state"):
            if edge[target_key] not in states:
                raise InvariantError(
                    f"containment edge {edge['id']!r} has unknown {target_key}"
                )
        key = (parent, at_state)
        if key in invocation_edges:
            raise InvariantError(f"child state {at_state!r} has multiple invocations")
        invocation_edges[key] = edge["id"]
        unknown = set(edge["grant"]["capabilities"]) - capabilities
        if unknown:
            raise InvariantError(
                f"containment edge {edge['id']!r} grants unknown capabilities "
                f"{sorted(unknown)!r}"
            )
        child_authority = set(loops[child]["authority"].values())
        if not child_authority <= set(edge["grant"]["capabilities"]):
            raise InvariantError(
                f"containment edge {edge['id']!r} does not grant child authority"
            )

    _acyclic(loops, adjacency, "containment graph")
    roots = set(containment["roots"])
    expected_roots = {loop_id for loop_id, degree in indegree.items() if degree == 0}
    if roots != expected_roots:
        raise InvariantError(
            f"containment roots must be exactly {sorted(expected_roots)!r}"
        )
    covered: set[str] = set()
    for root in roots:
        covered |= _reachable(root, adjacency)
    if covered != set(loops):
        raise InvariantError("not every loop is reachable from a containment root")
    for loop_id, states in states_by_loop.items():
        child_states = {
            state_id for state_id, state in states.items() if state["kind"] == "child"
        }
        referenced_states = {
            state_id for parent, state_id in invocation_edges if parent == loop_id
        }
        if child_states != referenced_states:
            raise InvariantError(
                f"loop {loop_id!r} child states and containment edges differ"
            )

    default_scope = policy["execution"]["default_scope"]
    default_budget = policy["execution"]["default_budgets"]
    for loop_id, loop in loops.items():
        parents = incoming.get(loop_id)
        if not parents:
            if not budget_subset(loop["budgets"], default_budget):
                raise InvariantError(f"root loop {loop_id!r} exceeds policy budget")
        else:
            for edge in parents:
                if not budget_subset(loop["budgets"], edge["grant"]["budgets"]):
                    raise InvariantError(
                        f"loop {loop_id!r} exceeds inbound grant budget"
                    )
        for edge in (
            value for value in edges.values() if value["parent_loop_id"] == loop_id
        ):
            parent_limits = parents or [
                {"grant": {"scope": default_scope, "budgets": default_budget}}
            ]
            for parent_limit in parent_limits:
                if not scope_subset(
                    edge["grant"]["scope"], parent_limit["grant"]["scope"]
                ):
                    raise InvariantError(
                        f"child grant {edge['id']!r} broadens parent scope"
                    )
                if not budget_subset(
                    edge["grant"]["budgets"], parent_limit["grant"]["budgets"]
                ):
                    raise InvariantError(
                        f"child grant {edge['id']!r} broadens parent budget"
                    )
    return registry
