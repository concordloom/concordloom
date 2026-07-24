"""Portable, high-information operator interviews for project intent."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from .canonical import document_digest
from .graph import DecisionError, unresolved_blocking_ids, validate_project_graph


class InterviewError(ValueError):
    """The graph or supplied interview answer is inconsistent."""


def generate_questions(graph: Mapping[str, Any]) -> dict[str, Any]:
    """Return a deterministic, ranked question document.

    Ranking is deliberately simple and inspectable: the number of proposed
    graph operations, then confidence uncertainty, then the stable question
    ID.  Every mutually exclusive answer exposes the graph delta it records.
    """

    validate_project_graph(graph)
    if graph.get("phase") != "observed":
        raise InterviewError("questions require an observed project graph")

    object_confidence = _confidence_index(graph)
    questions: list[dict[str, Any]] = []
    for hypothesis in graph.get("hypotheses", []):
        if not isinstance(hypothesis, Mapping):
            raise InterviewError("every hypothesis must be an object")
        if hypothesis.get("status") != "unresolved":
            continue
        hypothesis_id = str(hypothesis["id"])
        proposed_delta = deepcopy(list(hypothesis["graph_delta"]))
        confirmation = _with_subject_operation(
            proposed_delta, "confirm", hypothesis_id
        )
        rejection = [
            {
                "op": "reject",
                "target_kind": "hypothesis",
                "target_id": hypothesis_id,
            }
        ]
        correction = [
            {
                "op": "reject",
                "target_kind": "hypothesis",
                "target_id": hypothesis_id,
            }
        ]
        confidence = _hypothesis_confidence(
            hypothesis, proposed_delta, object_confidence
        )
        operation_count = len(proposed_delta)
        uncertainty = round(1.0 - abs(confidence - 0.5) * 2.0, 6)
        question_id = f"question.{hypothesis_id}"
        target_kinds = sorted(
            {
                str(operation.get("target_kind"))
                for operation in proposed_delta
                if isinstance(operation, Mapping)
            }
        )
        questions.append(
            {
                "id": question_id,
                "hypothesis_id": hypothesis_id,
                "prompt": f"Should Concord Loom accept this intent: {hypothesis['claim']}",
                "blocking": bool(hypothesis["blocking"]),
                "confidence": confidence,
                "evidence": deepcopy(list(hypothesis["evidence"])),
                "why_it_matters": _why_it_matters(
                    bool(hypothesis["blocking"]), target_kinds, operation_count
                ),
                "impact_score": float(operation_count),
                "options": [
                    {
                        "id": "confirm",
                        "verdict": "confirmed",
                        "label": "Confirm the proposed intent",
                        "graph_delta": confirmation,
                    },
                    {
                        "id": "reject",
                        "verdict": "rejected",
                        "label": "Reject the proposed intent",
                        "graph_delta": rejection,
                    },
                    {
                        "id": "correct",
                        "verdict": "corrected",
                        "label": "Reject this wording and provide a correction",
                        "graph_delta": correction,
                    },
                ],
                "_sort": (-operation_count, -uncertainty, question_id),
            }
        )

    questions.sort(key=lambda item: item["_sort"])
    for question in questions:
        question.pop("_sort")

    return {
        "kind": "concordloom.question-set",
        "schema_version": "0.1",
        "id": f"{graph['id']}-questions",
        "source_graph_digest": document_digest(graph),
        "questions": questions,
    }


def make_decision(
    question: Mapping[str, Any],
    verdict: str,
    *,
    actor: Mapping[str, Any],
    authority_ref: str,
    rationale: str,
    decided_at: str,
    decision_id: str | None = None,
    correction: str | None = None,
    graph_delta: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create one explicit decision from a generated question."""

    if verdict not in {"confirmed", "rejected", "corrected"}:
        raise InterviewError("verdict must be confirmed, rejected, or corrected")
    if not rationale.strip():
        raise InterviewError("a non-empty rationale is required")
    _parse_timestamp(decided_at)
    if not isinstance(actor, Mapping) or not actor.get("id") or not actor.get("kind"):
        raise InterviewError("actor requires id and kind")
    if not authority_ref:
        raise InterviewError("authority_ref is required")

    hypothesis_id = str(question.get("hypothesis_id", ""))
    if not hypothesis_id:
        raise InterviewError("question requires hypothesis_id")
    selected = next(
        (
            answer
            for answer in question.get("options", [])
            if isinstance(answer, Mapping) and answer.get("verdict") == verdict
        ),
        None,
    )
    if selected is None:
        raise InterviewError(f"question has no {verdict!r} answer")
    selected_delta = (
        deepcopy(list(graph_delta))
        if graph_delta is not None
        else deepcopy(list(selected.get("graph_delta", [])))
    )
    if verdict == "corrected":
        if not correction or not correction.strip():
            raise InterviewError("a corrected decision requires correction text")
        if graph_delta is None:
            raise InterviewError(
                "a corrected decision requires an explicit replacement graph_delta"
            )

    decision: dict[str, Any] = {
        "id": decision_id or f"decision.{hypothesis_id}.{verdict}",
        "subject_id": hypothesis_id,
        "verdict": verdict,
        "actor": deepcopy(dict(actor)),
        "decided_at": _normalize_timestamp(decided_at),
        "authority_ref": authority_ref,
        "rationale": rationale.strip(),
        "graph_delta": selected_delta,
    }
    if verdict == "corrected":
        decision["correction"] = correction.strip()
    return decision


def make_decision_log(
    graph: Mapping[str, Any],
    authority_policy: Mapping[str, Any],
    decisions: Sequence[Mapping[str, Any]],
    *,
    log_id: str | None = None,
    acceptance_actor: Mapping[str, Any] | None = None,
    acceptance_authority_ref: str | None = None,
    accepted_at: str | None = None,
) -> dict[str, Any]:
    """Build a source- and policy-bound append-only decision log.

    Supplying acceptance fields requests ``complete`` acceptance.  The helper
    refuses to construct that claim while blocking questions are unresolved.
    Final authority is still checked by :func:`graph.apply_decisions`.
    """

    validate_project_graph(graph)
    if graph.get("phase") != "observed":
        raise InterviewError("decision logs require an observed graph")
    copied_decisions = [deepcopy(dict(decision)) for decision in decisions]
    unresolved = unresolved_blocking_ids(graph, copied_decisions)
    accepting = any(
        value is not None
        for value in (
            acceptance_actor,
            acceptance_authority_ref,
            accepted_at,
        )
    )
    if accepting and (
        acceptance_actor is None
        or not acceptance_authority_ref
        or accepted_at is None
    ):
        raise InterviewError(
            "complete acceptance requires actor, authority_ref, and timestamp"
        )
    if accepting and unresolved:
        raise InterviewError(
            "cannot accept with unresolved blocking questions: "
            + ", ".join(unresolved)
        )

    acceptance: dict[str, Any] = {"state": "pending"}
    if accepting:
        if not isinstance(acceptance_actor, Mapping):
            raise InterviewError("acceptance_actor must be an object")
        acceptance = {
            "state": "complete",
            "actor": deepcopy(dict(acceptance_actor)),
            "decided_at": _normalize_timestamp(str(accepted_at)),
            "authority_ref": str(acceptance_authority_ref),
        }

    return {
        "kind": "concordloom.decision-log",
        "schema_version": "0.1",
        "id": log_id or f"{graph['id']}-decisions",
        "source_graph_digest": document_digest(graph),
        "authority_policy_digest": document_digest(authority_policy),
        "decisions": copied_decisions,
        "unresolved_blocking_question_ids": unresolved,
        "acceptance": acceptance,
    }


def _confidence_index(graph: Mapping[str, Any]) -> dict[tuple[str, str], float]:
    result: dict[tuple[str, str], float] = {}
    for kind, collection_name in (("node", "nodes"), ("edge", "edges")):
        for item in graph.get(collection_name, []):
            if isinstance(item, Mapping):
                confidence = item.get("confidence")
                if isinstance(confidence, (int, float)):
                    result[(kind, str(item.get("id", "")))] = float(confidence)
    return result


def _hypothesis_confidence(
    hypothesis: Mapping[str, Any],
    operations: Sequence[Mapping[str, Any]],
    confidence_index: Mapping[tuple[str, str], float],
) -> float:
    confidences = [
        confidence_index[(str(operation.get("target_kind")), str(operation.get("target_id")))]
        for operation in operations
        if (
            str(operation.get("target_kind")),
            str(operation.get("target_id")),
        )
        in confidence_index
    ]
    if confidences:
        return round(sum(confidences) / len(confidences), 6)
    impact = float(hypothesis.get("impact_score", 0))
    # No evidence-derived confidence exists for an intent-only question.
    # Ranking it at maximum uncertainty makes the operator boundary visible.
    return 0.5 if impact >= 0 else 0.5


def _with_subject_operation(
    operations: Sequence[Mapping[str, Any]], op: str, hypothesis_id: str
) -> list[dict[str, Any]]:
    result = [deepcopy(dict(operation)) for operation in operations]
    if not any(
        operation.get("target_kind") == "hypothesis"
        and operation.get("target_id") == hypothesis_id
        for operation in result
    ):
        result.append(
            {
                "op": op,
                "target_kind": "hypothesis",
                "target_id": hypothesis_id,
            }
        )
    return result


def _why_it_matters(
    blocking: bool, target_kinds: Sequence[str], operation_count: int
) -> str:
    targets = ", ".join(target_kinds) if target_kinds else "project intent"
    effect = (
        "Compilation is blocked until an authorized operator decides it."
        if blocking
        else "Leaving it unresolved preserves the inference but grants no authority."
    )
    return (
        f"The answer changes {operation_count} proposed graph operation(s) "
        f"across {targets}. {effect}"
    )


def _parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InterviewError(f"invalid timestamp {value!r}") from exc
    if parsed.tzinfo is None:
        raise InterviewError("timestamp must include a timezone")
    return parsed


def _normalize_timestamp(value: str) -> str:
    return (
        _parse_timestamp(value)
        .astimezone(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


# CLI-friendly aliases.
questions = generate_questions
decide = make_decision
