from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest

from concordloom.canonical import digest, load
from concordloom.evolution import EvolutionError, propose_evolution
from concordloom.loops import InvariantError
from concordloom.schema import ValidationError, validate_named


ROOT = Path(__file__).resolve().parents[1]
NOW = "2026-07-24T12:00:00Z"
BASE_BINDING = digest({"binding": "v0.1"})


def policy() -> dict:
    return load(ROOT / "framework/generic-sdlc/policy.json")


def signal(identifier: str, source: str) -> dict:
    return {
        "kind": "concordloom.evolution-signal",
        "schema_version": "0.1",
        "id": identifier,
        "base_binding_digest": BASE_BINDING,
        "source_digest": digest({"source": source}),
        "category": "friction",
        "severity": "warning",
        "occurrences": 2,
        "summary": f"Repeated friction in {source}.",
        "provenance": [{"kind": "evidence", "ref": source}],
    }


def risk() -> dict:
    return {
        "level": "medium",
        "failure_modes": ["The proposed loop may add coordination overhead."],
        "rollback": "Keep the currently active binding.",
    }


def propose(**overrides: object) -> dict:
    arguments: dict[str, object] = {
        "base_binding_digest": BASE_BINDING,
        "signals": [signal("signal-one", "run-one"), signal("signal-two", "run-two")],
        "operations": [
            {
                "op": "add",
                "target_kind": "loop",
                "target_id": "diagnosis",
                "value": {"objective": "Bound repeated diagnosis."},
            }
        ],
        "proposed_by": {"id": "example-orchestrator", "kind": "orchestrator"},
        "decision_authority_ref": "operator",
        "expected_effect": "Reduce repeated diagnosis effort.",
        "risk": risk(),
        "generated_at": NOW,
        "policy": policy(),
        "proposal_id": "diagnosis-loop-proposal",
    }
    arguments.update(overrides)
    return propose_evolution(**arguments)  # type: ignore[arg-type]


class EvolutionTests(unittest.TestCase):
    def test_valid_proposal_is_deterministic_and_never_self_activates(self) -> None:
        first = propose()
        second = propose(signals=list(reversed(first["signals"])))

        self.assertEqual(first, second)
        self.assertEqual(first["status"], "proposed")
        self.assertIs(first["decision_required"], True)
        self.assertIs(first["activation_allowed"], False)
        validate_named(first)

    def test_signals_are_validated_pinned_and_deduplicated_by_source(self) -> None:
        repeated = signal("signal-one", "run-one")
        with self.assertRaisesRegex(EvolutionError, "distinct source signals"):
            propose(signals=[repeated, deepcopy(repeated)])

        mismatched = signal("signal-other-binding", "run-three")
        mismatched["base_binding_digest"] = digest({"binding": "other"})
        with self.assertRaisesRegex(EvolutionError, "different base binding"):
            propose(signals=[signal("signal-one", "run-one"), mismatched])

        malformed = signal("signal-invalid", "run-four")
        malformed["occurrences"] = 0
        with self.assertRaises(ValidationError):
            propose(signals=[signal("signal-one", "run-one"), malformed])

        conflicting = signal("signal-conflict-a", "same-run")
        collision = deepcopy(conflicting)
        collision["id"] = "signal-conflict-b"
        with self.assertRaisesRegex(EvolutionError, "conflicting evolution signals"):
            propose(signals=[conflicting, collision])

    def test_bound_capabilities_control_proposer_and_decision_authority(self) -> None:
        with self.assertRaisesRegex(InvariantError, "lacks capability"):
            propose(
                proposed_by={"id": "example-executor", "kind": "executor"},
            )

        with self.assertRaisesRegex(EvolutionError, "lacks evolution decision"):
            propose(decision_authority_ref="orchestrator")

    def test_policy_threshold_counts_distinct_sources(self) -> None:
        strict = policy()
        strict["evolution"]["minimum_repeated_signals"] = 3
        with self.assertRaisesRegex(EvolutionError, "at least 3"):
            propose(policy=strict)

    def test_non_add_operations_require_a_matching_precondition(self) -> None:
        target = {
            "id": "testing",
            "budgets": {"max_attempts": 3},
        }
        operation = {
            "op": "replace",
            "target_kind": "loop",
            "target_id": "testing",
            "path": "/budgets/max_attempts",
            "value": 4,
        }

        with self.assertRaisesRegex(EvolutionError, "precondition_digest"):
            propose(operations=[operation])

        operation["precondition_digest"] = digest(3)
        with self.assertRaisesRegex(EvolutionError, "requires base_targets"):
            propose(operations=[operation])

        accepted = propose(
            operations=[operation],
            base_targets={"loop:testing": target},
        )
        self.assertEqual(accepted["operations"], [operation])

        stale = deepcopy(operation)
        stale["precondition_digest"] = digest(2)
        with self.assertRaisesRegex(EvolutionError, "stale precondition"):
            propose(
                operations=[stale],
                base_targets={"loop": {"testing": target}},
            )

    def test_compare_and_swap_fails_closed_on_missing_or_ambiguous_targets(self) -> None:
        operation = {
            "op": "remove",
            "target_kind": "policy",
            "target_id": "old-rule",
            "precondition_digest": digest({"id": "old-rule"}),
        }
        with self.assertRaisesRegex(EvolutionError, "unavailable"):
            propose(operations=[operation], base_targets={})

        with self.assertRaisesRegex(EvolutionError, "ambiguously"):
            propose(
                operations=[operation],
                base_targets={
                    "policy:old-rule": {"id": "old-rule"},
                    "old-rule": {"id": "old-rule", "changed": True},
                },
            )


if __name__ == "__main__":
    unittest.main()
