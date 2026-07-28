from __future__ import annotations

import json
from pathlib import Path
import unittest

from concordloom.loops import scope_subset, validate_policy, validate_registry


ROOT = Path(__file__).resolve().parents[1]
V8 = ROOT / "framework" / "concordloom" / "v8"
V9 = ROOT / "framework" / "concordloom" / "v9"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class FrontendDevelopmentSystemTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = load(V9 / "cycle-registry.json")
        cls.policy = load(V9 / "policy.json")
        cls.model = load(V9 / "development-model.json")
        cls.proposal = load(V9 / "binding-proposal.json")
        validate_policy(cls.policy)
        validate_registry(cls.registry, cls.policy)

    def test_successor_adds_exact_frontend_composite_with_separate_activation(self) -> None:
        old = load(V8 / "cycle-registry.json")
        old_ids = {loop["id"] for loop in old["loops"]}
        new_ids = {loop["id"] for loop in self.registry["loops"]}
        expected = {
            "define-frontend-concept",
            "accept-frontend-concept",
            "maintain-component-workshop",
            "implement-frontend-surface",
            "maintain-frontend-verification",
            "verify-frontend-candidate",
            "critique-frontend-experience",
        }
        self.assertEqual(expected, new_ids - old_ids)
        self.assertEqual(65, len(self.registry["loops"]))
        self.assertEqual(64, len(self.registry["containment_graph"]["edges"]))
        self.assertTrue(self.proposal["activation_required"])
        self.assertEqual(
            load(V8 / "binding.json")["binding_digest"],
            self.proposal["predecessor_binding_digest"],
        )
        evolution = load(V9 / "evolution-proposal.json")
        self.assertFalse(evolution["activation_allowed"])
        self.assertTrue(evolution["decision_required"])
        binding = load(V9 / "binding.json")
        receipt = load(V9 / "activation-receipt.json")
        self.assertEqual(
            "decide-v9-frontend-system",
            receipt["evolution_decision_id"],
        )
        self.assertEqual(
            "activate-v9-frontend-system",
            receipt["activation_decision_id"],
        )
        self.assertNotEqual(
            receipt["evolution_decision_id"],
            receipt["activation_decision_id"],
        )
        self.assertEqual(binding["binding_digest"], receipt["binding_digest"])

    def test_visual_contract_browser_evidence_and_critique_are_mandatory(self) -> None:
        parent = next(
            loop for loop in self.registry["loops"]
            if loop["id"] == "design-site-experience"
        )
        child_states = [
            state["invocation_id"].split(".", 1)[1]
            for state in parent["local_control_flow"]["states"]
            if state["kind"] == "child"
        ]
        self.assertEqual(
            [
                "define-frontend-concept",
                "accept-frontend-concept",
                "maintain-component-workshop",
                "implement-frontend-surface",
                "maintain-frontend-verification",
                "verify-frontend-candidate",
                "critique-frontend-experience",
            ],
            child_states,
        )
        transitions = parent["local_control_flow"]["transitions"]
        for child in child_states:
            failure = next(
                item for item in transitions
                if item["id"] == f"design-site-experience.{child}-failure"
            )
            self.assertEqual("escalated", failure["to"])

    def test_author_verifier_critic_and_operator_routes_are_distinct(self) -> None:
        nodes = {node["id"]: node for node in self.model["nodes"]}
        author = nodes["implement-frontend-surface"]["route_materialization"]
        verifier = nodes["verify-frontend-candidate"]["route_materialization"]
        critic = nodes["critique-frontend-experience"]["route_materialization"]
        operator = nodes["accept-frontend-concept"]["route_materialization"]
        self.assertEqual(("gpt-5.6-terra", "medium"), (author["model"], author["reasoning"]))
        self.assertEqual(("none", "deterministic"), (verifier["model"], verifier["reasoning"]))
        self.assertEqual(("gpt-5.6-sol", "high"), (critic["model"], critic["reasoning"]))
        self.assertEqual(("none", "human-decision"), (operator["model"], operator["reasoning"]))
        self.assertEqual([], critic["mcp_servers"])
        self.assertNotIn("playwright-mcp", critic["tool_capabilities"])
        self.assertIn(
            {"id": "impeccable", "version": "4.0.3"},
            author["skills"],
        )
        harness = nodes["maintain-frontend-verification"]["route_materialization"]
        self.assertEqual(("gpt-5.6-terra", "low"), (harness["model"], harness["reasoning"]))
        self.assertEqual([], harness["skills"])
        self.assertNotIn("image-generation", harness["tool_capabilities"])

    def test_frontend_children_have_least_privilege_scopes(self) -> None:
        edges = {
            edge["child_loop_id"]: edge
            for edge in self.registry["containment_graph"]["edges"]
        }
        parent_scope = edges["design-site-experience"]["grant"]["scope"]
        for child in (
            "define-frontend-concept",
            "accept-frontend-concept",
            "maintain-component-workshop",
            "implement-frontend-surface",
            "maintain-frontend-verification",
            "verify-frontend-candidate",
            "critique-frontend-experience",
        ):
            exact = edges[child]["grant"]["scope"]
            self.assertTrue(scope_subset(exact, parent_scope), child)
            self.assertEqual("none", exact["network"], child)
            self.assertEqual([], exact["external_mutations"], child)
        self.assertEqual(
            ["design/frontend"],
            edges["define-frontend-concept"]["grant"]["scope"]["write_paths"],
        )
        self.assertEqual(
            [],
            edges["verify-frontend-candidate"]["grant"]["scope"]["write_paths"],
        )
        self.assertEqual(
            [],
            edges["critique-frontend-experience"]["grant"]["scope"]["write_paths"],
        )
        harness_writes = edges["maintain-frontend-verification"]["grant"]["scope"][
            "write_paths"
        ]
        self.assertIn("tests/frontend", harness_writes)
        self.assertNotIn("design/frontend", harness_writes)
        self.assertNotIn("site", harness_writes)
        self.assertEqual(
            ["frontend-workshop"],
            edges["maintain-component-workshop"]["grant"]["scope"]["write_paths"],
        )

    def test_independent_frontend_gates_are_policy_separated(self) -> None:
        separated = set(
            self.policy["authority"]["separation_rules"][0]["applies_to_loop_ids"]
        )
        self.assertIn("verify-frontend-candidate", separated)
        self.assertIn("critique-frontend-experience", separated)
        contracts = {
            item["id"]: item for item in self.registry["evidence_contracts"]
        }
        self.assertEqual(
            "review-candidate",
            contracts["verify-frontend-candidate-acceptance"]["producer_capability"],
        )
        self.assertEqual(
            "review-candidate",
            contracts["critique-frontend-experience-acceptance"]["producer_capability"],
        )

    def test_child_receipts_and_publication_gate_are_machine_bound(self) -> None:
        loops = {loop["id"]: loop for loop in self.registry["loops"]}
        transitions = {
            item["id"]: item
            for item in loops["design-site-experience"]["local_control_flow"][
                "transitions"
            ]
        }
        for child in (
            "define-frontend-concept",
            "accept-frontend-concept",
            "maintain-component-workshop",
            "implement-frontend-surface",
            "maintain-frontend-verification",
            "verify-frontend-candidate",
            "critique-frontend-experience",
        ):
            self.assertEqual(
                [f"{child}-acceptance"],
                transitions[f"design-site-experience.{child}-success"][
                    "evidence_contract_ids"
                ],
            )
        contracts = {
            item["id"]: item for item in self.registry["evidence_contracts"]
        }
        for contract_id in (
            "design-site-experience-acceptance",
            "assure-release-acceptance",
            "publish-site-acceptance",
        ):
            claims = contracts[contract_id]["required_claims"]
            self.assertIn("verify-frontend-candidate-outcome", claims)
            self.assertIn("critique-frontend-experience-outcome", claims)
        route = load(V9 / "publication-route.json")
        ids = [item["loop_id"] for item in route]
        publish_index = ids.index("publish-site")
        self.assertLess(ids.index("verify-frontend-candidate"), publish_index)
        self.assertLess(ids.index("critique-frontend-experience"), publish_index)
        publish = route[publish_index]
        self.assertEqual(
            [
                "design-site-experience-acceptance",
                "verify-frontend-candidate-acceptance",
                "critique-frontend-experience-acceptance",
            ],
            publish["required_evidence_contract_ids"],
        )

    def test_evolution_has_exact_precondition_and_generator_cannot_activate(self) -> None:
        evolution = load(V9 / "evolution-proposal.json")
        operation = evolution["operations"][0]
        old_loop = next(
            loop for loop in load(V8 / "cycle-registry.json")["loops"]
            if loop["id"] == "design-site-experience"
        )
        from concordloom.canonical import digest
        self.assertEqual("replace", operation["op"])
        self.assertEqual("/purpose", operation["path"])
        self.assertEqual(digest(old_loop["purpose"]), operation["precondition_digest"])
        self.assertEqual(
            7,
            len([
                item for item in evolution["operations"]
                if item["op"] == "add" and item["target_kind"] == "loop"
            ]),
        )
        self.assertEqual(
            7,
            len([
                item for item in evolution["operations"]
                if item["op"] == "add" and item["target_kind"] == "containment"
            ]),
        )
        from concordloom.evolution import EvolutionError, validate_evolution_proposal
        stale = dict(old_loop)
        stale["purpose"] = "stale"
        with self.assertRaises(EvolutionError):
            validate_evolution_proposal(
                evolution,
                policy=load(V8 / "policy.json"),
                base_binding=load(V8 / "binding.json"),
                base_targets={"loop": {"design-site-experience": stale}},
            )
        source = (ROOT / "tools" / "authorize_frontend_system.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("--activate", source)
        self.assertNotIn("append_binding", source)
        self.assertNotIn("activate_binding(", source)


if __name__ == "__main__":
    unittest.main()
