"""Project-graph invariants and operator-authorized decision overlays.

The functions in this module deliberately do not infer authority from graph
confidence.  An observed graph becomes an accepted graph only through a
content-bound decision log and an authority policy that resolves every actor
and role.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import re
from typing import Any, Iterable, Mapping

from .canonical import document_digest


_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_ACCEPT_INTENT_CAPABILITIES = {"accept-intent", "accept_intent"}
_PROJECT_TARGET_KINDS = {"node", "edge", "hypothesis"}


class GraphError(ValueError):
    """The project graph is structurally invalid."""


class DecisionError(GraphError):
    """A decision log is inconsistent with its source graph."""


class AuthorityError(DecisionError):
    """A decision actor does not have the bound authority."""


class BlockingDecisionError(DecisionError):
    """A blocking question has not received an authorized decision."""


def validate_project_graph(graph: Mapping[str, Any]) -> None:
    """Validate cross-object invariants not expressible in JSON Schema."""

    if graph.get("kind") != "concordloom.project-graph":
        raise GraphError("kind must be concordloom.project-graph")
    if graph.get("schema_version") != "0.1":
        raise GraphError("schema_version must be 0.1")
    if graph.get("phase") not in {"observed", "accepted"}:
        raise GraphError("phase must be observed or accepted")

    repository = graph.get("repository")
    if not isinstance(repository, Mapping):
        raise GraphError("repository must be an object")
    if not _DIGEST_RE.fullmatch(str(repository.get("tree_digest", ""))):
        raise GraphError("repository.tree_digest must be a sha256 digest")

    nodes = _indexed(graph.get("nodes"), "node")
    edges = _indexed(graph.get("edges"), "edge")
    hypotheses = _indexed(graph.get("hypotheses"), "hypothesis")

    for edge in edges.values():
        if edge.get("source") not in nodes:
            raise GraphError(
                f"edge {edge['id']!r} references missing source {edge.get('source')!r}"
            )
        if edge.get("target") not in nodes:
            raise GraphError(
                f"edge {edge['id']!r} references missing target {edge.get('target')!r}"
            )

    valid_targets = {
        "node": set(nodes),
        "edge": set(edges),
        "hypothesis": set(hypotheses),
    }
    for hypothesis in hypotheses.values():
        operations = hypothesis.get("graph_delta")
        if not isinstance(operations, list) or not operations:
            raise GraphError(
                f"hypothesis {hypothesis['id']!r} must have a non-empty graph_delta"
            )
        for operation in operations:
            _validate_project_operation(
                operation,
                valid_targets,
                allow_new_targets=True,
                context=f"hypothesis {hypothesis['id']}",
            )


def apply_decisions(
    observed_graph: Mapping[str, Any],
    decision_log: Mapping[str, Any],
    authority_policy: Mapping[str, Any],
) -> dict[str, Any]:
    """Overlay an immutable decision log and return an accepted graph.

    The function fails closed when source digests, authority, blocking
    decisions, or operation targets are inconsistent.  Observations are never
    deleted: a rejection marks an inferred object rejected, while a correction
    preserves the original and adds a provenance-bound replacement.
    """

    validate_project_graph(observed_graph)
    if observed_graph.get("phase") != "observed":
        raise DecisionError("decisions can only be applied to an observed graph")
    _validate_decision_log_header(observed_graph, decision_log, authority_policy)

    accepted = deepcopy(dict(observed_graph))
    node_index = _indexed(accepted["nodes"], "node")
    edge_index = _indexed(accepted["edges"], "edge")
    hypothesis_index = _indexed(accepted["hypotheses"], "hypothesis")
    indexes: dict[str, dict[str, dict[str, Any]]] = {
        "node": node_index,
        "edge": edge_index,
        "hypothesis": hypothesis_index,
    }

    decisions = decision_log.get("decisions")
    if not isinstance(decisions, list):
        raise DecisionError("decisions must be an array")

    latest_by_subject: dict[str, Mapping[str, Any]] = {}
    decision_ids: set[str] = set()
    for decision in decisions:
        if not isinstance(decision, Mapping):
            raise DecisionError("every decision must be an object")
        decision_id = str(decision.get("id", ""))
        if not decision_id or decision_id in decision_ids:
            raise DecisionError(f"duplicate or empty decision id: {decision_id!r}")
        decision_ids.add(decision_id)
        _require_authorized_actor(decision, authority_policy, "accept intent")

        subject_id = str(decision.get("subject_id", ""))
        if subject_id not in hypothesis_index:
            raise DecisionError(
                f"decision {decision_id!r} references unknown hypothesis {subject_id!r}"
            )
        verdict = decision.get("verdict")
        if verdict not in {"confirmed", "rejected", "corrected"}:
            raise DecisionError(f"decision {decision_id!r} has invalid verdict")
        rationale = decision.get("rationale")
        if not isinstance(rationale, str) or not rationale.strip():
            raise DecisionError(f"decision {decision_id!r} requires a rationale")
        if verdict == "corrected" and not str(decision.get("correction", "")).strip():
            raise DecisionError(
                f"corrected decision {decision_id!r} requires correction text"
            )

        operations = decision.get("graph_delta")
        if not isinstance(operations, list):
            raise DecisionError(
                f"decision {decision_id!r} graph_delta must be an array"
            )
        if not operations:
            operations = [
                {
                    "op": "confirm" if verdict == "confirmed" else "reject",
                    "target_kind": "hypothesis",
                    "target_id": subject_id,
                }
            ]
        for operation in operations:
            _apply_operation(
                accepted,
                indexes,
                operation,
                decision_id=decision_id,
                verdict=str(verdict),
            )

        # The subject state follows the latest append-only decision even when
        # the explicit graph delta only describes corrected nodes or edges.
        subject = hypothesis_index[subject_id]
        subject["status"] = str(verdict)
        latest_by_subject[subject_id] = decision

    unresolved = sorted(
        hypothesis_id
        for hypothesis_id, hypothesis in hypothesis_index.items()
        if bool(hypothesis.get("blocking")) and hypothesis_id not in latest_by_subject
    )
    declared_unresolved = decision_log.get("unresolved_blocking_question_ids")
    if not isinstance(declared_unresolved, list):
        raise DecisionError("unresolved_blocking_question_ids must be an array")
    if sorted(set(map(str, declared_unresolved))) != unresolved:
        raise DecisionError(
            "unresolved_blocking_question_ids does not match blocking hypotheses"
        )

    acceptance = decision_log.get("acceptance")
    if not isinstance(acceptance, Mapping):
        raise DecisionError("acceptance must be an object")
    state = acceptance.get("state")
    if state != "complete":
        raise BlockingDecisionError("decision log acceptance is not complete")
    if unresolved:
        raise BlockingDecisionError(
            "unresolved blocking questions: " + ", ".join(unresolved)
        )
    _require_authorized_actor(acceptance, authority_policy, "accept intent")

    # Rejected blocking intent is an explicit refusal to compile, not a
    # successful resolution that can silently grant execution authority.
    rejected_blocking = sorted(
        hypothesis_id
        for hypothesis_id, decision in latest_by_subject.items()
        if bool(hypothesis_index[hypothesis_id].get("blocking"))
        and decision.get("verdict") == "rejected"
    )
    if rejected_blocking:
        raise BlockingDecisionError(
            "blocking intent was rejected: " + ", ".join(rejected_blocking)
        )

    accepted["phase"] = "accepted"
    accepted["id"] = _accepted_id(str(observed_graph.get("id", "project")))
    accepted["generated_at"] = _latest_timestamp(decision_log, observed_graph)
    accepted["decision_log_digest"] = document_digest(decision_log)
    accepted["nodes"] = sorted(node_index.values(), key=lambda item: item["id"])
    accepted["edges"] = sorted(edge_index.values(), key=lambda item: item["id"])
    accepted["hypotheses"] = sorted(
        hypothesis_index.values(), key=lambda item: item["id"]
    )
    validate_project_graph(accepted)
    return accepted


def actor_capabilities(
    actor_id: str, authority_policy: Mapping[str, Any]
) -> frozenset[str]:
    """Resolve an actor's capabilities through policy roles."""

    authority = authority_policy.get("authority")
    if not isinstance(authority, Mapping):
        raise AuthorityError("policy.authority must be an object")
    roles_value = authority.get("roles")
    principals_value = authority.get("principals")
    if not isinstance(roles_value, list) or not isinstance(principals_value, list):
        raise AuthorityError("policy authority roles and principals must be arrays")

    roles: dict[str, Mapping[str, Any]] = {}
    for role in roles_value:
        if not isinstance(role, Mapping) or not role.get("id"):
            raise AuthorityError("every authority role must have an id")
        role_id = str(role["id"])
        if role_id in roles:
            raise AuthorityError(f"duplicate authority role {role_id!r}")
        roles[role_id] = role

    principal: Mapping[str, Any] | None = None
    for candidate in principals_value:
        if isinstance(candidate, Mapping) and candidate.get("id") == actor_id:
            if principal is not None:
                raise AuthorityError(f"duplicate principal {actor_id!r}")
            principal = candidate
    if principal is None:
        raise AuthorityError(f"actor {actor_id!r} is not a policy principal")

    capabilities: set[str] = set()
    principal_roles = principal.get("roles")
    if not isinstance(principal_roles, list) or not principal_roles:
        raise AuthorityError(f"principal {actor_id!r} has no roles")
    for role_id_value in principal_roles:
        role_id = str(role_id_value)
        role = roles.get(role_id)
        if role is None:
            raise AuthorityError(
                f"principal {actor_id!r} references unknown role {role_id!r}"
            )
        role_capabilities = role.get("capabilities")
        if not isinstance(role_capabilities, list):
            raise AuthorityError(f"role {role_id!r} capabilities must be an array")
        capabilities.update(map(str, role_capabilities))
    return frozenset(capabilities)


def _validate_decision_log_header(
    graph: Mapping[str, Any],
    decision_log: Mapping[str, Any],
    authority_policy: Mapping[str, Any],
) -> None:
    if decision_log.get("kind") != "concordloom.decision-log":
        raise DecisionError("kind must be concordloom.decision-log")
    if decision_log.get("schema_version") != "0.1":
        raise DecisionError("decision log schema_version must be 0.1")
    expected_graph_digest = document_digest(graph)
    if decision_log.get("source_graph_digest") != expected_graph_digest:
        raise DecisionError(
            "decision log source_graph_digest does not match the observed graph"
        )
    expected_policy_digest = document_digest(authority_policy)
    if decision_log.get("authority_policy_digest") != expected_policy_digest:
        raise AuthorityError(
            "decision log authority_policy_digest does not match the policy"
        )


def _require_authorized_actor(
    record: Mapping[str, Any],
    authority_policy: Mapping[str, Any],
    action: str,
) -> None:
    actor = record.get("actor")
    if not isinstance(actor, Mapping) or not str(actor.get("id", "")):
        raise AuthorityError(f"{action} record requires an actor")
    actor_id = str(actor["id"])
    authority_ref = str(record.get("authority_ref", ""))
    if not authority_ref:
        raise AuthorityError(f"{action} record requires authority_ref")

    authority = authority_policy.get("authority")
    if not isinstance(authority, Mapping):
        raise AuthorityError("policy.authority must be an object")
    principal = next(
        (
            item
            for item in authority.get("principals", [])
            if isinstance(item, Mapping) and item.get("id") == actor_id
        ),
        None,
    )
    if not isinstance(principal, Mapping):
        raise AuthorityError(f"actor {actor_id!r} is not a policy principal")
    principal_roles = {str(role) for role in principal.get("roles", [])}
    if authority_ref not in principal_roles:
        raise AuthorityError(
            f"authority_ref {authority_ref!r} is not a role of actor {actor_id!r}"
        )
    capabilities = actor_capabilities(actor_id, authority_policy)
    if not capabilities.intersection(_ACCEPT_INTENT_CAPABILITIES):
        raise AuthorityError(
            f"actor {actor_id!r} lacks the accept-intent capability"
        )


def _apply_operation(
    graph: dict[str, Any],
    indexes: dict[str, dict[str, dict[str, Any]]],
    operation: Any,
    *,
    decision_id: str,
    verdict: str,
) -> None:
    valid_targets = {kind: set(index) for kind, index in indexes.items()}
    _validate_project_operation(
        operation,
        valid_targets,
        allow_new_targets=True,
        context=f"decision {decision_id}",
    )
    if not isinstance(operation, Mapping):  # narrowed by validator
        raise DecisionError("operation must be an object")
    op = str(operation["op"])
    target_kind = str(operation["target_kind"])
    target_id = str(operation["target_id"])
    index = indexes[target_kind]

    if op in {"confirm", "reject"}:
        target = index.get(target_id)
        if target is None:
            raise DecisionError(
                f"{op} target {target_kind} {target_id!r} does not exist"
            )
        if op == "reject" and target.get("status") == "observed":
            raise DecisionError(
                f"observed {target_kind} {target_id!r} cannot be rejected"
            )
        target["status"] = "confirmed" if op == "confirm" else "rejected"
        if target_kind != "hypothesis":
            target["operator_decision_id"] = decision_id
            if op == "confirm":
                target["confidence"] = 1
        return

    if op == "remove":
        target = index.get(target_id)
        if target is None:
            raise DecisionError(
                f"remove target {target_kind} {target_id!r} does not exist"
            )
        if target.get("status") == "observed":
            raise DecisionError(
                f"observed {target_kind} {target_id!r} cannot be removed"
            )
        target["status"] = "rejected"
        if target_kind != "hypothesis":
            target["operator_decision_id"] = decision_id
        return

    value = operation.get("value")
    if not isinstance(value, Mapping):
        raise DecisionError(f"{op} operation requires an object value")
    replacement = deepcopy(dict(value))
    replacement_id = str(replacement.get("id", ""))
    if not replacement_id:
        raise DecisionError(f"{op} operation value requires an id")

    if op == "add":
        if replacement_id in index:
            raise DecisionError(
                f"add target {target_kind} {replacement_id!r} already exists"
            )
    elif op == "replace":
        original = index.get(target_id)
        if original is None:
            raise DecisionError(
                f"replace target {target_kind} {target_id!r} does not exist"
            )
        if replacement_id == target_id:
            raise DecisionError(
                "a correction must add a replacement id and preserve the original"
            )
        if replacement_id in index:
            raise DecisionError(
                f"replacement {target_kind} {replacement_id!r} already exists"
            )
        if original.get("status") != "observed":
            original["status"] = "corrected"
            if target_kind != "hypothesis":
                original["operator_decision_id"] = decision_id
    else:
        raise DecisionError(f"unsupported project operation {op!r}")

    replacement["status"] = "corrected" if verdict == "corrected" else "confirmed"
    if target_kind != "hypothesis":
        replacement["operator_decision_id"] = decision_id
        replacement["confidence"] = 1
        provenance_key = "provenance" if target_kind == "node" else "source_refs"
        provenance = replacement.get(provenance_key)
        if not isinstance(provenance, list):
            provenance = []
            replacement[provenance_key] = provenance
        provenance.append({"kind": "decision", "ref": decision_id})
    index[replacement_id] = replacement

    collection = {
        "node": graph["nodes"],
        "edge": graph["edges"],
        "hypothesis": graph["hypotheses"],
    }[target_kind]
    collection.append(replacement)


def _validate_project_operation(
    operation: Any,
    valid_targets: Mapping[str, set[str]],
    *,
    allow_new_targets: bool,
    context: str,
) -> None:
    if not isinstance(operation, Mapping):
        raise DecisionError(f"{context}: graph operation must be an object")
    op = operation.get("op")
    if op not in {"add", "remove", "replace", "confirm", "reject"}:
        raise DecisionError(f"{context}: invalid graph operation {op!r}")
    target_kind = operation.get("target_kind")
    if target_kind not in _PROJECT_TARGET_KINDS:
        raise AuthorityError(
            f"{context}: project acceptance cannot change {target_kind!r}"
        )
    target_id = str(operation.get("target_id", ""))
    if not target_id:
        raise DecisionError(f"{context}: graph operation requires target_id")
    if (
        op in {"remove", "replace", "confirm", "reject"}
        and target_id not in valid_targets[target_kind]
    ):
        raise DecisionError(
            f"{context}: {target_kind} target {target_id!r} does not exist"
        )
    if op == "add" and not allow_new_targets:
        raise DecisionError(f"{context}: add is not allowed")


def _indexed(values: Any, label: str) -> dict[str, dict[str, Any]]:
    if not isinstance(values, list):
        raise GraphError(f"{label}s must be an array")
    result: dict[str, dict[str, Any]] = {}
    for value in values:
        if not isinstance(value, dict):
            raise GraphError(f"every {label} must be an object")
        identifier = str(value.get("id", ""))
        if not identifier or identifier in result:
            raise GraphError(f"duplicate or empty {label} id: {identifier!r}")
        result[identifier] = value
    return result


def _accepted_id(source_id: str) -> str:
    suffix = "-accepted"
    return source_id if source_id.endswith(suffix) else f"{source_id}{suffix}"


def _latest_timestamp(
    decision_log: Mapping[str, Any], observed_graph: Mapping[str, Any]
) -> str:
    candidates: list[str] = [str(observed_graph.get("generated_at", ""))]
    acceptance = decision_log.get("acceptance")
    if isinstance(acceptance, Mapping):
        candidates.append(str(acceptance.get("decided_at", "")))
    for decision in decision_log.get("decisions", []):
        if isinstance(decision, Mapping):
            candidates.append(str(decision.get("decided_at", "")))
    valid: list[tuple[datetime, str]] = []
    for value in candidates:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            continue
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        normalized = parsed.astimezone(timezone.utc).isoformat().replace(
            "+00:00", "Z"
        )
        valid.append((parsed.astimezone(timezone.utc), normalized))
    if not valid:
        raise DecisionError("no valid decision or graph timestamp")
    return max(valid)[1]


def unresolved_blocking_ids(
    graph: Mapping[str, Any], decisions: Iterable[Mapping[str, Any]]
) -> list[str]:
    """Return stable unresolved blocking hypothesis IDs."""

    decided = {
        str(decision.get("subject_id", ""))
        for decision in decisions
        if isinstance(decision, Mapping)
    }
    return sorted(
        str(hypothesis["id"])
        for hypothesis in graph.get("hypotheses", [])
        if isinstance(hypothesis, Mapping)
        and bool(hypothesis.get("blocking"))
        and str(hypothesis.get("id", "")) not in decided
    )


# Conversationally useful alias.
accept_project_graph = apply_decisions
