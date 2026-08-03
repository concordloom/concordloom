from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from concordloom.canonical import digest, save
from concordloom.compiler import validate_loop_design_proposal
from concordloom.evolution import validate_evolution_proposal


ROOT = Path(__file__).resolve().parents[1]
FRAMEWORK = ROOT / "framework" / "concordloom"
V9 = FRAMEWORK / "v9"
V10 = FRAMEWORK / "v10"
BASE_BINDING_DIGEST = (
    "sha256:1940a57ca917d6136c5742048dfccc68d0434c530da2ad3ef3b2ba486f866597"
)
ACTIVE_BINDING_DIGEST = (
    "sha256:7ab2f2e59e3f08a914bb9af266165f5ef9868489d43e4eb841f23fb52b9b04c4"
)
BINDING_PROPOSAL_DIGEST = (
    "sha256:e19ebf34082aaff8f6a52d8f7b9420b60db146ca8b0acb22d2ec7fa7dd3d84bd"
)
PROPOSAL_FILES = {
    "evolution-proposal.json",
    "loop-design-proposal.json",
}
MATERIALIZED_V10_FILES = {
    "binding-proposal.json",
    "cycle-registry.json",
    "development-model.json",
    "evolution-history.json",
    "loop-design.json",
    "policy.json",
    "publication-route.json",
}
ALLOWED_V10_FILES = PROPOSAL_FILES


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class TaskRouteEvolutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.graph = load(FRAMEWORK / "v3" / "accepted-project-graph.json")
        cls.decisions = load(FRAMEWORK / "v3" / "decision-log.json")
        cls.policy = load(V9 / "policy.json")
        cls.binding = load(V9 / "binding.json")
        cls.registry = load(V9 / "cycle-registry.json")
        cls.old_design = load(V9 / "loop-design-proposal.json")
        cls.design = load(V10 / "loop-design-proposal.json")
        cls.evolution = load(V10 / "evolution-proposal.json")
        validate_loop_design_proposal(
            cls.design,
            cls.graph,
            cls.decisions,
            cls.policy,
        )
        validate_evolution_proposal(
            cls.evolution,
            cls.policy,
            base_binding=cls.binding,
            base_targets={
                "containment": {
                    "runtime-tooling.operate-run-lifecycle": next(
                        edge
                        for edge in cls.registry["containment_graph"]["edges"]
                        if edge["id"]
                        == "runtime-tooling.operate-run-lifecycle"
                    ),
                    "steward-concordloom.runtime-tooling": next(
                        edge
                        for edge in cls.registry["containment_graph"]["edges"]
                        if edge["id"] == "steward-concordloom.runtime-tooling"
                    ),
                }
            },
        )

    def test_exact_65_to_66_loop_and_64_to_65_containment_delta(self) -> None:
        old_loops = self.old_design["loops"]
        new_loops = self.design["loops"]
        self.assertEqual((65, 66), (len(old_loops), len(new_loops)))
        added_loop = next(loop for loop in new_loops if loop["id"] == "plan-task-route")
        self.assertEqual(
            old_loops,
            [loop for loop in new_loops if loop["id"] != "plan-task-route"],
        )
        added_index = [loop["id"] for loop in new_loops].index("plan-task-route")
        self.assertEqual("maintain-compiler-core", new_loops[added_index - 1]["id"])
        self.assertEqual("operate-run-lifecycle", new_loops[added_index + 1]["id"])
        self.assertIn("before any run card exists", added_loop["purpose"])
        self.assertIn(
            "immutable candidate-bound proposed route preview",
            added_loop["output_outcome"],
        )
        self.assertNotIn("draft", added_loop["output_outcome"].lower())

        old_edges = self.old_design["containment"]
        new_edges = self.design["containment"]
        self.assertEqual((64, 65), (len(old_edges), len(new_edges)))
        self.assertEqual(
            old_edges,
            [
                edge
                for edge in new_edges
                if edge["id"] != "runtime-tooling.plan-task-route"
            ],
        )
        edge_index = [edge["id"] for edge in new_edges].index(
            "runtime-tooling.plan-task-route"
        )
        self.assertEqual(
            "runtime-tooling.maintain-compiler-core",
            new_edges[edge_index - 1]["id"],
        )
        self.assertEqual(
            "runtime-tooling.operate-run-lifecycle",
            new_edges[edge_index + 1]["id"],
        )
        self.assertEqual("runtime-tooling", new_edges[edge_index]["parent_loop_id"])
        self.assertEqual("plan-task-route", new_edges[edge_index]["child_loop_id"])

    def test_full_proposal_exposes_exact_graph_and_keeps_policy(self) -> None:
        expected_delta = [
            {
                "op": "add",
                "target_kind": "loop",
                "target_id": loop["id"],
                "value": loop,
            }
            for loop in self.design["loops"]
        ] + [
            {
                "op": "add",
                "target_kind": "containment",
                "target_id": edge["id"],
                "value": edge,
            }
            for edge in self.design["containment"]
        ]
        self.assertEqual(expected_delta, self.design["graph_delta"])
        self.assertEqual(
            self.old_design["authority_policy_digest"],
            self.design["authority_policy_digest"],
        )
        self.assertEqual(digest(self.policy), self.design["authority_policy_digest"])
        self.assertTrue(self.design["acceptance_required"])
        self.assertEqual("proposed", self.design["status"])

    def test_evolution_is_two_additions_and_two_exact_scope_replacements(self) -> None:
        catalog = load(FRAMEWORK / "catalog.json")
        self.assertEqual(BASE_BINDING_DIGEST, self.binding["binding_digest"])
        self.assertEqual(BASE_BINDING_DIGEST, self.evolution["base_binding_digest"])
        v10_entry = next(
            entry
            for entry in catalog["entries"]
            if entry["binding_digest"] == ACTIVE_BINDING_DIGEST
        )
        self.assertEqual(
            "concordloom-self-binding-v10",
            v10_entry["binding_id"],
        )
        self.assertEqual(
            BASE_BINDING_DIGEST,
            v10_entry["previous_binding_digest"],
        )
        self.assertEqual(
            [
                ("add", "loop", "plan-task-route"),
                (
                    "add",
                    "containment",
                    "runtime-tooling.plan-task-route",
                ),
                (
                    "replace",
                    "containment",
                    "runtime-tooling.operate-run-lifecycle",
                ),
                (
                    "replace",
                    "containment",
                    "steward-concordloom.runtime-tooling",
                ),
            ],
            [
                (operation["op"], operation["target_kind"], operation["target_id"])
                for operation in self.evolution["operations"]
            ],
        )
        self.assertNotIn(
            "policy",
            {operation["target_kind"] for operation in self.evolution["operations"]},
        )
        loop_value = self.evolution["operations"][0]["value"]
        self.assertEqual("runtime-tooling", loop_value["parent_loop_id"])
        self.assertEqual("maintain-compiler-core", loop_value["after_child_loop_id"])
        self.assertEqual("operate-run-lifecycle", loop_value["before_child_loop_id"])

        old_edge = next(
            edge
            for edge in self.registry["containment_graph"]["edges"]
            if edge["id"] == "runtime-tooling.operate-run-lifecycle"
        )
        replacement = self.evolution["operations"][2]
        self.assertEqual(digest(old_edge), replacement["precondition_digest"])
        new_edge = replacement["value"]
        old_without_scope = json.loads(json.dumps(old_edge))
        new_without_scope = json.loads(json.dumps(new_edge))
        old_scope = old_without_scope["grant"].pop("scope")
        new_scope = new_without_scope["grant"].pop("scope")
        self.assertEqual(old_without_scope, new_without_scope)
        self.assertEqual(old_scope["network"], new_scope["network"])
        self.assertEqual(
            old_scope["external_mutations"],
            new_scope["external_mutations"],
        )
        self.assertEqual(
            ["src/concordloom/route.py", "src/concordloom/schema.py"],
            sorted(set(new_scope["read_paths"]) - set(old_scope["read_paths"])),
        )
        self.assertEqual(
            ["src/concordloom/route.py", "src/concordloom/schema.py"],
            sorted(set(new_scope["write_paths"]) - set(old_scope["write_paths"])),
        )
        self.assertEqual(
            set(old_scope["read_paths"]),
            set(new_scope["read_paths"])
            - {"src/concordloom/route.py", "src/concordloom/schema.py"},
        )
        self.assertEqual(
            set(old_scope["write_paths"]),
            set(new_scope["write_paths"])
            - {"src/concordloom/route.py", "src/concordloom/schema.py"},
        )
        old_parent = next(
            edge
            for edge in self.registry["containment_graph"]["edges"]
            if edge["id"] == "steward-concordloom.runtime-tooling"
        )
        parent_replacement = self.evolution["operations"][3]
        self.assertEqual(digest(old_parent), parent_replacement["precondition_digest"])
        for mode in ("read_paths", "write_paths"):
            self.assertEqual(
                {"src/concordloom/route.py", "src/concordloom/schema.py"},
                set(parent_replacement["value"]["grant"]["scope"][mode])
                - set(old_parent["grant"]["scope"][mode]),
            )

    def test_route_contract_is_least_privilege_and_exact(self) -> None:
        contract = self.evolution["operations"][0]["value"][
            "proposed_runtime_contract"
        ]
        authority = contract["authority"]
        self.assertEqual(
            {
                "execute_capability": "route-run",
                "accept_capability": "accept-parent",
                "escalate_capability": "escalate",
            },
            authority,
        )
        orchestrator = next(
            role for role in self.policy["authority"]["roles"]
            if role["id"] == "orchestrator"
        )
        self.assertEqual(set(authority.values()), set(orchestrator["capabilities"]))
        self.assertFalse(
            {"authorize-run", "activate-binding", "decide-evolution"}
            & set(authority.values())
        )
        self.assertEqual(
            {
                "repository_candidate_write_paths": [],
                "network": "none",
                "external_mutations": [],
            },
            contract["candidate_effects"],
        )
        self.assertEqual(
            {
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
            contract["preview_artifact"],
        )
        self.assertIn(
            "separate explicit confirmation before run new",
            self.evolution["expected_effect"],
        )
        self.assertIn(
            "full accepted local execution flow",
            self.evolution["expected_effect"],
        )
        self.assertIn(
            "delegation ceiling",
            self.evolution["expected_effect"],
        )

        deterministic = contract["routes"]["exact_route_compiler"]
        self.assertEqual(
            {
                "required": True,
                "model_provider": "",
                "model": "none",
                "reasoning": "deterministic",
                "skills": [],
                "mcp_servers": [],
                "resources": [],
                "tool_capabilities": [],
                "subagent_identities": [],
            },
            deterministic,
        )
        semantic = contract["routes"]["semantic_target_selection"]
        self.assertEqual("openai", semantic["model_provider"])
        self.assertEqual("gpt-5.6-luna", semantic["model"])
        self.assertEqual("low", semantic["reasoning"])
        self.assertTrue(semantic["optional"])
        self.assertEqual("require-explicit-target-loop", semantic["fallback"])
        self.assertEqual(
            [{"id": "design-project-loops", "version": "0.1.0"}],
            semantic["skills"],
        )
        for field in (
            "mcp_servers",
            "resources",
            "tool_capabilities",
            "subagent_identities",
        ):
            self.assertEqual([], semantic[field], field)
        allowed_models = {
            (item["provider"], item["model"])
            for item in self.policy["execution"]["model_policy"]["allowed_models"]
        }
        self.assertIn(("openai", "gpt-5.6-luna"), allowed_models)

    def test_completed_activation_does_not_rewrite_proposal_truth(self) -> None:
        expected = PROPOSAL_FILES | MATERIALIZED_V10_FILES | {
            "binding.json",
            "activation-receipt.json",
        }
        self.assertEqual(expected, {path.name for path in V10.iterdir()})
        self.assertFalse((V10 / "catalog.json").exists())
        self.assertEqual("proposed", self.evolution["status"])
        self.assertTrue(self.evolution["decision_required"])
        self.assertFalse(self.evolution["activation_allowed"])
        self.assertEqual("operator", self.evolution["decision_authority_ref"])
        self.assertNotIn("accepted_by", self.evolution)
        self.assertNotIn("accepted_by", self.design)
        binding = load(V10 / "binding.json")
        self.assertEqual(ACTIVE_BINDING_DIGEST, binding["binding_digest"])
        self.assertEqual(BASE_BINDING_DIGEST, binding["predecessor_binding_digest"])
        self.assertEqual(
            BINDING_PROPOSAL_DIGEST,
            binding["accepted_by"]["proposal_digest"],
        )
        self.assertEqual(
            "activate-v10-task-route",
            binding["accepted_by"]["decision_id"],
        )
        receipt = load(V10 / "activation-receipt.json")
        self.assertEqual(ACTIVE_BINDING_DIGEST, receipt["binding_digest"])
        self.assertEqual(
            BINDING_PROPOSAL_DIGEST,
            receipt["binding_proposal_digest"],
        )
        catalog = load(FRAMEWORK / "catalog.json")
        v10_entry = next(
            entry
            for entry in catalog["entries"]
            if entry["binding_digest"] == ACTIVE_BINDING_DIGEST
        )
        self.assertEqual("concordloom-self-binding-v10", v10_entry["binding_id"])
        self.assertEqual(BASE_BINDING_DIGEST, v10_entry["previous_binding_digest"])

    def test_generator_is_deterministic_checkable_and_fails_closed(self) -> None:
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(ROOT / "src")
        checked = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "authorize_task_route.py"), "--check"],
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=True,
        )
        self.assertIn("TASK_ROUTE_PROPOSAL_CHECK_OK", checked.stdout)

        with tempfile.TemporaryDirectory() as temporary:
            checkout = Path(temporary)
            target_source = checkout / "framework" / "concordloom"
            target_source.mkdir(parents=True)
            shutil.copytree(FRAMEWORK / "v3", target_source / "v3")
            shutil.copytree(V9, target_source / "v9")
            historical_catalog = load(FRAMEWORK / "catalog.json")
            while historical_catalog["entries"][-1]["binding_id"] != (
                "concordloom-self-binding-v9"
            ):
                historical_catalog["entries"].pop()
            historical_catalog["active_binding_digest"] = BASE_BINDING_DIGEST
            save(target_source / "catalog.json", historical_catalog)
            catalog_before = (target_source / "catalog.json").read_bytes()
            generated = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "authorize_task_route.py"),
                    "--root",
                    str(checkout),
                ],
                cwd=ROOT,
                env=environment,
                text=True,
                capture_output=True,
                check=True,
            )
            self.assertIn("TASK_ROUTE_PROPOSAL_OK", generated.stdout)
            self.assertEqual(catalog_before, (target_source / "catalog.json").read_bytes())
            self.assertEqual(
                PROPOSAL_FILES,
                {path.name for path in (target_source / "v10").iterdir()},
            )
            for name in PROPOSAL_FILES:
                self.assertEqual(
                    (V10 / name).read_bytes(),
                    (target_source / "v10" / name).read_bytes(),
                )
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "authorize_task_route.py"),
                    "--check",
                    "--root",
                    str(checkout),
                ],
                cwd=ROOT,
                env=environment,
                text=True,
                capture_output=True,
                check=True,
            )

            forbidden = target_source / "v10" / "binding.json"
            forbidden.write_text("{}\n", encoding="utf-8")
            rejected = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "authorize_task_route.py"),
                    "--check",
                    "--root",
                    str(checkout),
                ],
                cwd=ROOT,
                env=environment,
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(0, rejected.returncode)
            self.assertIn(
                "incomplete activation lifecycle",
                rejected.stdout + rejected.stderr,
            )


if __name__ == "__main__":
    unittest.main()
