"""Reduce repeated evidence into non-activating evolution proposals.

Evolution is deliberately a proposal boundary.  This module can describe a
successor to a binding, but it cannot accept that description, update a
catalog, or activate a binding.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
import re
from typing import Any

from .canonical import canonical_bytes, digest
from .loops import (
    policy_principals,
    policy_roles,
    require_actor_capability,
    validate_policy,
)
from .schema import validate_named


class EvolutionError(ValueError):
    """Evolution evidence or a proposed compare-and-swap is invalid."""


def _deduplicate_signals(
    signals: Sequence[Mapping[str, Any]],
    base_binding_digest: str,
) -> list[dict[str, Any]]:
    """Validate and deduplicate signals by their content-addressed source."""

    unique: dict[str, dict[str, Any]] = {}
    encoded: dict[str, bytes] = {}
    for raw_signal in signals:
        if not isinstance(raw_signal, Mapping):
            raise EvolutionError("every evolution signal must be an object")
        signal = deepcopy(dict(raw_signal))
        validate_named(signal)
        if signal["base_binding_digest"] != base_binding_digest:
            raise EvolutionError(
                f"signal {signal['id']!r} is pinned to a different base binding"
            )

        source_digest = signal["source_digest"]
        payload = canonical_bytes(signal)
        if source_digest in unique:
            if encoded[source_digest] != payload:
                raise EvolutionError(
                    "conflicting evolution signals share source_digest "
                    f"{source_digest!r}"
                )
            continue
        unique[source_digest] = signal
        encoded[source_digest] = payload

    return [
        unique[source_digest]
        for source_digest in sorted(unique)
    ]


def _require_decision_authority(
    policy: Mapping[str, Any],
    authority_ref: str,
) -> None:
    """Require a bound, assigned role capable of deciding this proposal."""

    roles = policy_roles(policy)
    try:
        role = roles[authority_ref]
    except KeyError as exc:
        raise EvolutionError(
            f"unknown evolution decision authority role {authority_ref!r}"
        ) from exc

    capability = policy["evolution"]["decision_capability"]
    if capability not in role["capabilities"]:
        raise EvolutionError(
            f"authority role {authority_ref!r} lacks evolution decision "
            f"capability {capability!r}"
        )
    if not any(
        authority_ref in principal["roles"]
        for principal in policy_principals(policy).values()
    ):
        raise EvolutionError(
            f"evolution decision authority role {authority_ref!r} has no "
            "bound principal"
        )


def _target_value(
    base_targets: Mapping[str, Any],
    target_kind: str,
    target_id: str,
) -> Any:
    """Resolve one base target without silently choosing an ambiguous shape.

    The portable JSON form is ``{"loop:testing": {...}}``.  Nested
    ``{"loop": {"testing": {...}}}`` and unambiguous ID-keyed maps are also
    accepted so callers can feed an already-indexed artifact directly.
    """

    candidates: list[Any] = []
    composite = f"{target_kind}:{target_id}"
    if composite in base_targets:
        candidates.append(base_targets[composite])

    by_kind = base_targets.get(target_kind)
    if isinstance(by_kind, Mapping) and target_id in by_kind:
        candidates.append(by_kind[target_id])

    if target_id in base_targets:
        candidates.append(base_targets[target_id])

    if not candidates:
        raise EvolutionError(
            f"base target {target_kind}:{target_id} is unavailable for "
            "precondition verification"
        )
    first_digest = digest(candidates[0])
    if any(digest(candidate) != first_digest for candidate in candidates[1:]):
        raise EvolutionError(
            f"base target {target_kind}:{target_id} resolves ambiguously"
        )
    return candidates[0]


_INVALID_POINTER_ESCAPE = re.compile(r"~(?:[^01]|$)")


def _pointer_value(document: Any, pointer: str | None) -> Any:
    """Resolve an RFC 6901 JSON pointer for compare-and-swap verification."""

    if pointer is None:
        return document
    if not pointer.startswith("/"):
        raise EvolutionError(f"precondition path is not a JSON pointer: {pointer!r}")

    current = document
    for encoded in pointer[1:].split("/"):
        if _INVALID_POINTER_ESCAPE.search(encoded):
            raise EvolutionError(f"invalid JSON pointer escape in {pointer!r}")
        token = encoded.replace("~1", "/").replace("~0", "~")
        if isinstance(current, Mapping):
            if token not in current:
                raise EvolutionError(
                    f"precondition path {pointer!r} does not exist"
                )
            current = current[token]
        elif isinstance(current, list):
            if not token.isdigit() or (len(token) > 1 and token.startswith("0")):
                raise EvolutionError(
                    f"precondition path {pointer!r} has an invalid array index"
                )
            index = int(token)
            if index >= len(current):
                raise EvolutionError(
                    f"precondition path {pointer!r} does not exist"
                )
            current = current[index]
        else:
            raise EvolutionError(
                f"precondition path {pointer!r} descends through a scalar"
            )
    return current


def _verify_preconditions(
    operations: Sequence[Mapping[str, Any]],
    base_targets: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    """Require and verify CAS preconditions for every mutating existing target."""

    copied: list[dict[str, Any]] = []
    for index, raw_operation in enumerate(operations):
        if not isinstance(raw_operation, Mapping):
            raise EvolutionError(f"evolution operation {index} must be an object")
        operation = deepcopy(dict(raw_operation))
        copied.append(operation)
        if operation.get("op") == "add":
            continue

        precondition = operation.get("precondition_digest")
        if not isinstance(precondition, str) or not precondition:
            raise EvolutionError(
                f"non-add operation {index} requires precondition_digest"
            )
        if base_targets is None:
            raise EvolutionError(
                f"non-add operation {index} requires base_targets for "
                "compare-and-swap verification"
            )

        try:
            target_kind = str(operation["target_kind"])
            target_id = str(operation["target_id"])
        except KeyError as exc:
            raise EvolutionError(
                f"evolution operation {index} is missing {exc.args[0]}"
            ) from exc
        target = _target_value(base_targets, target_kind, target_id)
        current = _pointer_value(target, operation.get("path"))
        actual = digest(current)
        if actual != precondition:
            raise EvolutionError(
                f"stale precondition for {target_kind}:{target_id}: "
                f"expected {precondition}, found {actual}"
            )
    return copied


def propose_evolution(
    base_binding_digest: str,
    signals: Sequence[Mapping[str, Any]],
    operations: Sequence[Mapping[str, Any]],
    *,
    proposed_by: Mapping[str, Any],
    decision_authority_ref: str,
    expected_effect: str,
    risk: Mapping[str, Any],
    generated_at: str,
    policy: dict[str, Any],
    proposal_id: str | None = None,
    base_targets: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a validated proposal that cannot authorize its own activation."""

    validate_policy(policy)
    evolution_policy = policy["evolution"]
    if evolution_policy["allow_self_activation"] is not False:
        raise EvolutionError("evolution policy must forbid self-activation")

    actor = deepcopy(dict(proposed_by))
    require_actor_capability(
        policy,
        actor,
        evolution_policy["proposal_capability"],
    )
    _require_decision_authority(policy, decision_authority_ref)

    reduced_signals = _deduplicate_signals(signals, base_binding_digest)
    threshold = max(2, int(evolution_policy.get("minimum_repeated_signals", 2)))
    if len(reduced_signals) < threshold:
        raise EvolutionError(
            f"evolution proposal needs at least {threshold} distinct source "
            f"signals; found {len(reduced_signals)}"
        )
    reduced_operations = _verify_preconditions(operations, base_targets)

    proposal: dict[str, Any] = {
        "kind": "concordloom.evolution-proposal",
        "schema_version": "0.1",
        "id": proposal_id or "evolution-proposal",
        "status": "proposed",
        "base_binding_digest": base_binding_digest,
        "generated_at": generated_at,
        "proposed_by": actor,
        "signals": reduced_signals,
        "operations": reduced_operations,
        "expected_effect": expected_effect,
        "risk": deepcopy(dict(risk)),
        "decision_required": True,
        "decision_authority_ref": decision_authority_ref,
        "activation_allowed": False,
    }
    validate_named(proposal)
    return proposal


def validate_evolution_proposal(
    proposal: dict[str, Any],
    policy: dict[str, Any],
    *,
    base_binding: Mapping[str, Any] | None = None,
    base_targets: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Recompute every proposal invariant without granting activation."""

    validate_named(proposal)
    if base_binding is not None and proposal["base_binding_digest"] != base_binding.get(
        "binding_digest"
    ):
        raise EvolutionError("proposal is pinned to a different base binding")
    expected = propose_evolution(
        proposal["base_binding_digest"],
        proposal["signals"],
        proposal["operations"],
        proposed_by=proposal["proposed_by"],
        decision_authority_ref=proposal["decision_authority_ref"],
        expected_effect=proposal["expected_effect"],
        risk=proposal["risk"],
        generated_at=proposal["generated_at"],
        policy=policy,
        proposal_id=proposal["id"],
        base_targets=base_targets,
    )
    if expected != proposal:
        raise EvolutionError("evolution proposal is not in canonical reduced form")
    return proposal
