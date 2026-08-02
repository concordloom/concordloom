"""Immutable, non-authorizing previews of exact task routes.

A route preview describes the route a later run card could request.  It never
contains the human request, grants no authority, and cannot execute any part of
the route it displays.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

from .canonical import digest, document_digest
from .run import (
    RunStateError,
    materialize_route,
    target_ancestor_closure,
    validate_binding,
    validate_planned_route_metadata,
)
from .schema import SchemaStore


class RoutePreviewError(ValueError):
    """A route preview is stale, non-exact, or attempts to grant authority."""


_DIGEST_EXCLUSIONS = ("/preview_digest",)
_PREVIEW_SCOPE = {
    "read_paths": [],
    "write_paths": [],
    "network": "none",
    "external_mutations": [],
}
_CORRECTION_BASE_FIELDS = (
    "request_digest",
    "request_ref",
    "binding_digest",
    "registry_digest",
    "policy_digest",
    "development_model_digest",
    "candidate_tree_digest",
    "candidate_manifest_digest",
    "root_loop_id",
)


def _artifact(binding: Mapping[str, Any], role: str) -> Mapping[str, Any]:
    matches = [
        artifact
        for artifact in binding["artifacts"]
        if artifact["role"] == role
    ]
    if len(matches) != 1:
        raise RoutePreviewError(
            f"binding must contain exactly one {role!r} artifact"
        )
    return matches[0]


def _validate_development_model(
    development_model: Mapping[str, Any],
    binding: Mapping[str, Any],
    registry: Mapping[str, Any],
) -> None:
    if not isinstance(development_model, Mapping):
        raise RoutePreviewError("development model is required")
    if development_model.get("kind") != "concordloom.development-model":
        raise RoutePreviewError("development model has an unexpected kind")
    if development_model.get("schema_version") != "0.1":
        raise RoutePreviewError(
            "development model has an unsupported schema version"
        )
    expected_digest = _artifact(binding, "atlas_input")["digest"]
    actual_digest = digest(development_model)
    if actual_digest != expected_digest:
        raise RoutePreviewError(
            "development model is not the binding's exact atlas input"
        )

    raw_nodes = development_model.get("nodes")
    if not isinstance(raw_nodes, list):
        raise RoutePreviewError("development model nodes must be an array")
    node_ids: list[str] = []
    for node in raw_nodes:
        if not isinstance(node, Mapping) or not isinstance(node.get("id"), str):
            raise RoutePreviewError(
                "development model nodes must have explicit string ids"
            )
        node_ids.append(node["id"])
    if len(node_ids) != len(set(node_ids)):
        raise RoutePreviewError("development model node ids must be unique")
    registry_ids = {str(loop["id"]) for loop in registry["loops"]}
    if set(node_ids) != registry_ids:
        raise RoutePreviewError(
            "development model must describe every registry loop exactly once"
        )
    if development_model.get("root_loop_id") not in registry[
        "containment_graph"
    ]["roots"]:
        raise RoutePreviewError(
            "development model root is not a registry root"
        )
    semantics = development_model.get("resource_semantics")
    if not isinstance(semantics, Mapping) or not isinstance(
        semantics.get("route_materialization"), str
    ):
        raise RoutePreviewError(
            "development model does not declare exact route materialization"
        )


def _supports_target_plans(registry: Mapping[str, Any]) -> bool:
    return any(loop.get("id") == "plan-task-route" for loop in registry["loops"])


def _branch_choice_map(
    choices: Mapping[str, str] | None,
) -> dict[str, str]:
    if choices is None:
        return {}
    if not isinstance(choices, Mapping):
        raise RoutePreviewError("branch choices must be an explicit object")
    result: dict[str, str] = {}
    for key, transition_id in choices.items():
        if (
            not isinstance(key, str)
            or ":" not in key
            or not all(key.split(":", 1))
            or not isinstance(transition_id, str)
            or not transition_id
        ):
            raise RoutePreviewError(
                "branch choices must map LOOP:STATE to a transition id"
            )
        result[key] = transition_id
    return result


def _retry_choice_map(
    choices: Mapping[str, int] | None,
) -> dict[str, int]:
    if choices is None:
        return {}
    if not isinstance(choices, Mapping):
        raise RoutePreviewError("retry choices must be an explicit object")
    result: dict[str, int] = {}
    for key, traversals in choices.items():
        if (
            not isinstance(key, str)
            or ":" not in key
            or not all(key.split(":", 1))
            or not isinstance(traversals, int)
            or isinstance(traversals, bool)
            or traversals < 0
        ):
            raise RoutePreviewError(
                "retry choices must map LOOP:TRANSITION to a non-negative integer"
            )
        result[key] = traversals
    return result


def _merge_choice(
    choices: dict[str, Any], key: str, value: Any, *, label: str
) -> None:
    previous = choices.get(key)
    if previous is not None and previous != value:
        raise RoutePreviewError(
            f"target plans contain conflicting {label} choice {key!r}"
        )
    choices[key] = value


def _choices_from_target_plans(
    target_plans: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, str], dict[str, int]]:
    branches: dict[str, str] = {}
    retries: dict[str, int] = {}
    for plan in target_plans:
        for choice in plan["branch_choices"]:
            key = f"{choice['loop_id']}:{choice['state_id']}"
            _merge_choice(
                branches,
                key,
                choice["transition_id"],
                label="branch",
            )
        for choice in plan["retry_choices"]:
            key = f"{choice['loop_id']}:{choice['transition_id']}"
            _merge_choice(
                retries,
                key,
                choice["traversals"],
                label="retry",
            )
    return branches, retries


def _compile_target_plans(
    registry: Mapping[str, Any],
    target_loop_ids: Sequence[str],
    *,
    branch_choices: Mapping[str, str] | None,
    retry_choices: Mapping[str, int] | None,
) -> list[dict[str, Any]]:
    """Expand targets through accepted successful local control flow only."""

    branches = _branch_choice_map(branch_choices)
    retries = _retry_choice_map(retry_choices)
    loops = {str(loop["id"]): loop for loop in registry["loops"]}
    containment = {
        str(edge["id"]): edge
        for edge in registry["containment_graph"]["edges"]
    }
    used_branches: set[str] = set()
    used_retries: set[str] = set()

    def expand(
        loop_id: str,
        stack: tuple[str, ...],
    ) -> tuple[list[str], list[dict[str, str]], list[dict[str, Any]]]:
        if loop_id in stack:
            raise RoutePreviewError(
                f"target expansion encountered containment cycle at {loop_id!r}"
            )
        loop = loops[loop_id]
        flow = loop["local_control_flow"]
        states = {str(state["id"]): state for state in flow["states"]}
        outgoing: dict[str, list[Mapping[str, Any]]] = {}
        for transition in flow["transitions"]:
            outgoing.setdefault(str(transition["from"]), []).append(transition)

        actions = [loop_id]
        action_ids = {loop_id}
        branch_records: list[dict[str, str]] = []
        retry_records: list[dict[str, Any]] = []
        recorded_branches: set[str] = set()
        recorded_retries: set[str] = set()
        remaining_retries = {
            key: traversals
            for key, traversals in retries.items()
            if key.split(":", 1)[0] == loop_id
        }
        retry_total = sum(remaining_retries.values())
        max_steps = len(states) * (retry_total + 2) + len(flow["transitions"])
        current = str(flow["entry_state"])
        steps = 0

        while True:
            steps += 1
            if steps > max_steps:
                raise RoutePreviewError(
                    f"successful route for loop {loop_id!r} did not terminate"
                )
            try:
                state = states[current]
            except KeyError as exc:
                raise RoutePreviewError(
                    f"loop {loop_id!r} entered unknown state {current!r}"
                ) from exc

            if state["kind"] == "terminal":
                if state.get("outcome") != "succeeded":
                    raise RoutePreviewError(
                        f"target plan for loop {loop_id!r} does not end in success"
                    )
                break

            if state["kind"] == "child":
                invocation_id = str(state.get("invocation_id", ""))
                edge = containment.get(invocation_id)
                if edge is None or edge["parent_loop_id"] != loop_id:
                    raise RoutePreviewError(
                        f"loop {loop_id!r} has unknown child invocation "
                        f"{invocation_id!r}"
                    )
                child_id = str(edge["child_loop_id"])
                child_actions, child_branches, child_retries = expand(
                    child_id,
                    (*stack, loop_id),
                )
                for action_id in child_actions:
                    if action_id not in action_ids:
                        action_ids.add(action_id)
                        actions.append(action_id)
                for record in child_branches:
                    record_key = f"{record['loop_id']}:{record['state_id']}"
                    if record_key not in recorded_branches:
                        recorded_branches.add(record_key)
                        branch_records.append(record)
                for record in child_retries:
                    record_key = f"{record['loop_id']}:{record['transition_id']}"
                    if record_key not in recorded_retries:
                        recorded_retries.add(record_key)
                        retry_records.append(record)

            transitions = outgoing.get(current, [])
            feedback = [
                transition
                for transition in transitions
                if transition["kind"] == "feedback"
            ]
            positive_feedback: list[tuple[Mapping[str, Any], str]] = []
            for transition in feedback:
                retry_key = f"{loop_id}:{transition['id']}"
                if retry_key not in retries:
                    continue
                budget = transition.get("feedback_budget")
                if not isinstance(budget, Mapping):
                    raise RoutePreviewError(
                        f"retry transition {transition['id']!r} has no budget"
                    )
                traversals = retries[retry_key]
                if traversals > budget["max_traversals"]:
                    raise RoutePreviewError(
                        f"retry choice {retry_key!r} exceeds max_traversals"
                    )
                used_retries.add(retry_key)
                if retry_key not in recorded_retries:
                    recorded_retries.add(retry_key)
                    retry_records.append(
                        {
                            "loop_id": loop_id,
                            "transition_id": str(transition["id"]),
                            "traversals": traversals,
                        }
                    )
                if remaining_retries[retry_key] > 0:
                    positive_feedback.append((transition, retry_key))

            if len(positive_feedback) > 1:
                raise RoutePreviewError(
                    f"loop {loop_id!r} has multiple requested retries from "
                    f"state {current!r}"
                )
            if positive_feedback:
                chosen, retry_key = positive_feedback[0]
                remaining_retries[retry_key] -= 1
                current = str(chosen["to"])
                continue

            forward = [
                transition
                for transition in transitions
                if transition["kind"] in {"progress", "success"}
            ]
            branch_key = f"{loop_id}:{current}"
            if len(forward) > 1:
                transition_id = branches.get(branch_key)
                if transition_id is None:
                    raise RoutePreviewError(
                        f"successful route for {branch_key!r} requires an "
                        "explicit branch choice"
                    )
                matches = [
                    transition
                    for transition in forward
                    if transition["id"] == transition_id
                ]
                if len(matches) != 1:
                    raise RoutePreviewError(
                        f"branch choice {branch_key!r} does not name an "
                        "accepted successful transition"
                    )
                used_branches.add(branch_key)
                if branch_key not in recorded_branches:
                    recorded_branches.add(branch_key)
                    branch_records.append(
                        {
                            "loop_id": loop_id,
                            "state_id": current,
                            "transition_id": transition_id,
                        }
                    )
                chosen = matches[0]
            elif len(forward) == 1:
                chosen = forward[0]
            else:
                raise RoutePreviewError(
                    f"loop {loop_id!r} has no accepted successful transition "
                    f"from state {current!r}"
                )
            current = str(chosen["to"])

        return actions, branch_records, retry_records

    plans: list[dict[str, Any]] = []
    for target_id in target_loop_ids:
        actions, plan_branches, plan_retries = expand(target_id, ())
        plans.append(
            {
                "target_loop_id": target_id,
                "action_loop_ids": actions,
                "branch_choices": plan_branches,
                "retry_choices": plan_retries,
            }
        )

    unused_branches = sorted(set(branches) - used_branches)
    if unused_branches:
        raise RoutePreviewError(
            f"unused or non-ambiguous branch choices {unused_branches!r}"
        )
    unused_retries = sorted(set(retries) - used_retries)
    if unused_retries:
        raise RoutePreviewError(
            f"unknown or unreachable retry choices {unused_retries!r}"
        )
    return plans


def _exact_route(
    binding: dict[str, Any],
    registry: dict[str, Any],
    policy: dict[str, Any],
    candidate_manifest: dict[str, Any],
    development_model: Mapping[str, Any],
    *,
    root_loop_id: str,
    target_loop_ids: Sequence[str],
    branch_choices: Mapping[str, str] | None = None,
    retry_choices: Mapping[str, int] | None = None,
    schema_store: SchemaStore,
) -> tuple[list[str], list[dict[str, Any]] | None, list[dict[str, Any]]]:
    validate_binding(binding, registry, policy, schema_store=schema_store)
    schema_store.validate(candidate_manifest, "candidate-manifest.schema.json")
    _validate_development_model(development_model, binding, registry)

    if root_loop_id not in binding["active_root_loop_ids"]:
        raise RoutePreviewError("route preview root is not active in the binding")
    if root_loop_id not in registry["containment_graph"]["roots"]:
        raise RoutePreviewError("route preview root is not a registry root")

    if isinstance(target_loop_ids, (str, bytes)) or not isinstance(
        target_loop_ids, Sequence
    ):
        raise RoutePreviewError("route preview targets must be an explicit array")
    targets = list(target_loop_ids)
    if not targets:
        raise RoutePreviewError(
            "route preview needs at least one explicit target loop"
        )
    if not all(isinstance(target, str) and target for target in targets):
        raise RoutePreviewError(
            "route preview target loops must be non-empty string ids"
        )
    if len(targets) != len(set(targets)):
        raise RoutePreviewError("route preview target loops must be unique")
    canonical_targets = sorted(targets)
    known_loop_ids = {str(loop["id"]) for loop in registry["loops"]}
    unknown_targets = sorted(set(canonical_targets) - known_loop_ids)
    if unknown_targets:
        raise RoutePreviewError(
            f"unknown target loops {unknown_targets!r}"
        )

    try:
        target_plans = None
        expanded_targets = canonical_targets
        if _supports_target_plans(registry):
            target_plans = _compile_target_plans(
                registry,
                canonical_targets,
                branch_choices=branch_choices,
                retry_choices=retry_choices,
            )
            expanded_targets = [
                loop_id
                for plan in target_plans
                for loop_id in plan["action_loop_ids"]
            ]
        elif branch_choices or retry_choices:
            raise RoutePreviewError(
                "route choices require a binding with target plan support"
            )
        selected = target_ancestor_closure(
            registry,
            root_loop_id,
            expanded_targets,
        )
        route = materialize_route(
            registry,
            policy,
            root_loop_id,
            selected,
            development_model,
        )
        for planned in route:
            validate_planned_route_metadata(planned, policy, candidate_manifest)
    except RunStateError as exc:
        raise RoutePreviewError(str(exc)) from exc
    return canonical_targets, target_plans, route


def _validate_preview_core(
    preview: Mapping[str, Any],
    binding: dict[str, Any],
    registry: dict[str, Any],
    policy: dict[str, Any],
    candidate_manifest: dict[str, Any],
    development_model: Mapping[str, Any],
    *,
    schema_store: SchemaStore,
) -> dict[str, Any]:
    value = _validate_preview_document(preview, schema_store=schema_store)
    if value["binding_digest"] != binding["binding_digest"]:
        raise RoutePreviewError("route preview is pinned to a different binding")
    if value["registry_digest"] != digest(registry):
        raise RoutePreviewError("route preview is pinned to a different registry")
    if value["policy_digest"] != digest(policy):
        raise RoutePreviewError("route preview is pinned to a different policy")
    if value["development_model_digest"] != digest(development_model):
        raise RoutePreviewError(
            "route preview is pinned to a different development model"
        )
    if value["candidate_tree_digest"] != candidate_manifest["tree_digest"]:
        raise RoutePreviewError(
            "route preview is pinned to a different candidate tree"
        )
    if value["candidate_manifest_digest"] != digest(candidate_manifest):
        raise RoutePreviewError(
            "route preview is pinned to a different candidate manifest"
        )
    target_plans = value.get("target_plans")
    branch_choices: Mapping[str, str] | None = None
    retry_choices: Mapping[str, int] | None = None
    if value["schema_version"] == "0.2":
        branch_choices, retry_choices = _choices_from_target_plans(target_plans)
    if _supports_target_plans(registry) != (value["schema_version"] == "0.2"):
        raise RoutePreviewError(
            "route preview schema version does not match the active binding"
        )
    canonical_targets, expected_plans, expected_route = _exact_route(
        binding,
        registry,
        policy,
        candidate_manifest,
        development_model,
        root_loop_id=value["root_loop_id"],
        target_loop_ids=value["target_loop_ids"],
        branch_choices=branch_choices,
        retry_choices=retry_choices,
        schema_store=schema_store,
    )
    if value["target_loop_ids"] != canonical_targets:
        raise RoutePreviewError(
            "route preview target loops are not canonically ordered"
        )
    if value.get("target_plans") != expected_plans:
        raise RoutePreviewError(
            "route preview does not contain the exact deterministic target plans"
        )
    if value["proposed_route"] != expected_route:
        raise RoutePreviewError(
            "route preview does not contain the exact deterministic route"
        )
    return value


def _validate_preview_document(
    preview: Mapping[str, Any],
    *,
    schema_store: SchemaStore,
) -> dict[str, Any]:
    value = deepcopy(dict(preview))
    schema_name = (
        "route-preview-v0.2.schema.json"
        if value.get("schema_version") == "0.2"
        else "route-preview.schema.json"
    )
    schema_store.validate(value, schema_name)
    expected_preview_digest = document_digest(
        value,
        excluded_fields=value["digest_contract"]["excluded_fields"],
    )
    if value["preview_digest"] != expected_preview_digest:
        raise RoutePreviewError("route preview digest contract mismatch")
    if value["preview_scope"] != _PREVIEW_SCOPE:
        raise RoutePreviewError("route preview itself must be effect-free")
    return value


def validate_route_preview_reference(
    preview: Mapping[str, Any],
    *,
    replaced_preview: Mapping[str, Any] | None = None,
    schema_store: SchemaStore | None = None,
) -> dict[str, Any]:
    """Validate immutable preview bytes and an optional correction link."""

    store = schema_store or SchemaStore()
    value = _validate_preview_document(preview, schema_store=store)
    replaces_digest = value.get("replaces_preview_digest")
    if replaces_digest is None:
        if replaced_preview is not None:
            raise RoutePreviewError(
                "a base preview cannot be validated with a replaced preview"
            )
        return value
    if replaced_preview is None:
        raise RoutePreviewError(
            "a correction requires the exact preview it replaces"
        )
    previous = _validate_preview_document(replaced_preview, schema_store=store)
    if previous["schema_version"] != value["schema_version"]:
        raise RoutePreviewError(
            "a correction cannot change the route preview schema version"
        )
    if "replaces_preview_digest" in previous:
        raise RoutePreviewError(
            "a correction cannot replace another correction"
        )
    if replaces_digest != previous["preview_digest"]:
        raise RoutePreviewError("route preview correction link digest mismatch")
    for field in _CORRECTION_BASE_FIELDS:
        if value[field] != previous[field]:
            raise RoutePreviewError(
                f"a correction cannot change route preview {field}"
            )
    if (
        value["target_loop_ids"] == previous["target_loop_ids"]
        and value.get("target_plans") == previous.get("target_plans")
    ):
        raise RoutePreviewError("a correction must replace the target plan")
    return value


def create_route_preview(
    binding: dict[str, Any],
    registry: dict[str, Any],
    policy: dict[str, Any],
    candidate_manifest: dict[str, Any],
    development_model: Mapping[str, Any],
    *,
    preview_id: str,
    request_digest: str,
    request_ref: str,
    root_loop_id: str,
    target_loop_ids: Sequence[str],
    created_at: str,
    branch_choices: Mapping[str, str] | None = None,
    retry_choices: Mapping[str, int] | None = None,
    replaces_preview: Mapping[str, Any] | None = None,
    schema_store: SchemaStore | None = None,
) -> dict[str, Any]:
    """Create a pinned proposal without retaining request text or authority."""

    store = schema_store or SchemaStore()
    canonical_targets, target_plans, proposed_route = _exact_route(
        binding,
        registry,
        policy,
        candidate_manifest,
        development_model,
        root_loop_id=root_loop_id,
        target_loop_ids=target_loop_ids,
        branch_choices=branch_choices,
        retry_choices=retry_choices,
        schema_store=store,
    )
    schema_version = "0.2" if target_plans is not None else "0.1"
    preview: dict[str, Any] = {
        "kind": "concordloom.route-preview",
        "schema_version": schema_version,
        "id": preview_id,
        "status": "proposed",
        "created_at": created_at,
        "preview_digest": "sha256:" + ("0" * 64),
        "digest_contract": {
            "algorithm": "sha256",
            "canonicalization": "rfc8785",
            "excluded_fields": list(_DIGEST_EXCLUSIONS),
        },
        "request_digest": request_digest,
        "request_ref": request_ref,
        "binding_digest": binding["binding_digest"],
        "registry_digest": digest(registry),
        "policy_digest": digest(policy),
        "development_model_digest": digest(development_model),
        "candidate_tree_digest": candidate_manifest["tree_digest"],
        "candidate_manifest_digest": digest(candidate_manifest),
        "root_loop_id": root_loop_id,
        "target_loop_ids": canonical_targets,
        "proposed_route": proposed_route,
        "preview_scope": deepcopy(_PREVIEW_SCOPE),
        "confirmation_required": True,
        "execution_allowed": False,
    }
    if target_plans is not None:
        preview["target_plans"] = target_plans

    if replaces_preview is not None:
        previous_document = _validate_preview_document(
            replaces_preview,
            schema_store=store,
        )
        if "replaces_preview_digest" in previous_document:
            raise RoutePreviewError(
                "a correction cannot replace another correction"
            )
        previous = _validate_preview_core(
            previous_document,
            binding,
            registry,
            policy,
            candidate_manifest,
            development_model,
            schema_store=store,
        )
        for field in _CORRECTION_BASE_FIELDS:
            if preview[field] != previous[field]:
                raise RoutePreviewError(
                    f"a correction cannot change route preview {field}"
                )
        if (
            preview["target_loop_ids"] == previous["target_loop_ids"]
            and preview.get("target_plans") == previous.get("target_plans")
        ):
            raise RoutePreviewError("a correction must replace the target plan")
        preview["replaces_preview_digest"] = previous["preview_digest"]

    preview["preview_digest"] = document_digest(
        preview,
        excluded_fields=_DIGEST_EXCLUSIONS,
    )
    return validate_route_preview(
        preview,
        binding,
        registry,
        policy,
        candidate_manifest,
        development_model,
        replaced_preview=replaces_preview,
        schema_store=store,
    )


def validate_route_preview(
    preview: Mapping[str, Any],
    binding: dict[str, Any],
    registry: dict[str, Any],
    policy: dict[str, Any],
    candidate_manifest: dict[str, Any],
    development_model: Mapping[str, Any],
    *,
    replaced_preview: Mapping[str, Any] | None = None,
    schema_store: SchemaStore | None = None,
) -> dict[str, Any]:
    """Validate exact pins, route bytes, and an optional correction link."""

    store = schema_store or SchemaStore()
    referenced = validate_route_preview_reference(
        preview,
        replaced_preview=replaced_preview,
        schema_store=store,
    )
    value = _validate_preview_core(
        referenced,
        binding,
        registry,
        policy,
        candidate_manifest,
        development_model,
        schema_store=store,
    )
    if replaced_preview is not None:
        _validate_preview_core(
            replaced_preview,
            binding,
            registry,
            policy,
            candidate_manifest,
            development_model,
            schema_store=store,
        )
    return value
