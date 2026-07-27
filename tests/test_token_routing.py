from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from concordloom.canonical import canonical_bytes, digest, document_digest
from concordloom.run import RunStateError, create_run_card


ROOT = Path(__file__).resolve().parents[1]
V7 = ROOT / "framework" / "concordloom" / "v7"
ROUTE_FIELDS = {
    "model_provider",
    "model",
    "reasoning",
    "skills",
    "mcp_servers",
    "resources",
    "tool_capabilities",
    "subagent_identities",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class TokenAwareRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        cls.checkout = Path(cls.temporary.name) / "repo"
        (cls.checkout / "tools").mkdir(parents=True)
        shutil.copytree(ROOT / "src", cls.checkout / "src")
        shutil.copytree(ROOT / "schemas", cls.checkout / "schemas")
        shutil.copytree(ROOT / "framework", cls.checkout / "framework")
        shutil.copy2(
            ROOT / "tools" / "authorize_token_routing.py",
            cls.checkout / "tools" / "authorize_token_routing.py",
        )
        shutil.copy2(
            ROOT / "tools" / "authorize_metadata_maintenance.py",
            cls.checkout / "tools" / "authorize_metadata_maintenance.py",
        )
        shutil.copy2(
            ROOT / "tools" / "authorize_source_publication.py",
            cls.checkout / "tools" / "authorize_source_publication.py",
        )
        # Exercise proposal and activation from the predecessor state even after
        # v8 has become the active binding in the source repository.
        catalog_path = (
            cls.checkout / "framework" / "concordloom" / "catalog.json"
        )
        catalog = load(catalog_path)
        if catalog["entries"][-1]["binding_id"] == "concordloom-self-binding-v8":
            catalog["entries"].pop()
            catalog["active_binding_digest"] = catalog["entries"][-1][
                "binding_digest"
            ]
            catalog_path.write_bytes(canonical_bytes(catalog) + b"\n")
        for name in ("binding.json", "activation-receipt.json"):
            activated_output = (
                cls.checkout / "framework" / "concordloom" / "v8" / name
            )
            activated_output.unlink(missing_ok=True)
        cls.catalog_before = (
            cls.checkout / "framework" / "concordloom" / "catalog.json"
        ).read_bytes()
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(cls.checkout / "src")
        cls.result = subprocess.run(
            [
                "python3",
                str(cls.checkout / "tools" / "authorize_token_routing.py"),
            ],
            cwd=cls.checkout,
            env=environment,
            text=True,
            capture_output=True,
            check=True,
        )
        cls.v8 = cls.checkout / "framework" / "concordloom" / "v8"
        cls.policy = load(cls.v8 / "policy.json")
        cls.registry = load(cls.v8 / "cycle-registry.json")
        cls.model = load(cls.v8 / "development-model.json")
        cls.proposal = load(cls.v8 / "binding-proposal.json")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_successor_keeps_topology_and_does_not_activate(self) -> None:
        v7_registry = load(V7 / "cycle-registry.json")
        self.assertEqual(
            [loop["id"] for loop in v7_registry["loops"]],
            [loop["id"] for loop in self.registry["loops"]],
        )
        self.assertEqual(
            [
                (
                    edge["id"],
                    edge["parent_loop_id"],
                    edge["child_loop_id"],
                )
                for edge in v7_registry["containment_graph"]["edges"]
            ],
            [
                (
                    edge["id"],
                    edge["parent_loop_id"],
                    edge["child_loop_id"],
                )
                for edge in self.registry["containment_graph"]["edges"]
            ],
        )
        self.assertEqual(58, len(self.registry["loops"]))
        self.assertEqual(57, len(self.registry["containment_graph"]["edges"]))
        evolution = load(self.v8 / "evolution-proposal.json")
        self.assertFalse(evolution["activation_allowed"])
        self.assertTrue(evolution["decision_required"])
        self.assertTrue(self.proposal["activation_required"])
        self.assertEqual(
            load(V7 / "binding.json")["binding_digest"],
            self.proposal["predecessor_binding_digest"],
        )
        self.assertEqual(
            self.catalog_before,
            (
                self.checkout / "framework" / "concordloom" / "catalog.json"
            ).read_bytes(),
        )
        self.assertFalse((self.v8 / "binding.json").exists())

    def test_model_policy_is_exact_and_sol_is_not_the_default(self) -> None:
        allowed = {
            (item["provider"], item["model"])
            for item in self.policy["execution"]["model_policy"][
                "allowed_models"
            ]
        }
        self.assertEqual(
            {
                ("", "none"),
                ("openai", "gpt-5.6-luna"),
                ("openai", "gpt-5.6-terra"),
                ("openai", "gpt-5.6-sol"),
            },
            allowed,
        )
        nodes = self.model["nodes"]
        materialized = []
        for node in nodes:
            profile = self.model["profiles"][node["execution_profile"]]
            route = node.get(
                "route_materialization",
                profile["route_materialization"],
            )
            self.assertEqual(ROUTE_FIELDS, set(route), node["id"])
            materialized.append((node["id"], route))
            self.assertNotEqual("max", route["reasoning"], node["id"])
            for field in ("mcp_servers", "resources", "subagent_identities"):
                self.assertEqual([], route[field], (node["id"], field))
            self.assertEqual(
                sorted(
                    self.model["profiles"][node["execution_profile"]]["tools"]
                ),
                route["tool_capabilities"],
                node["id"],
            )
        sol = {
            node_id
            for node_id, route in materialized
            if route["model"] == "gpt-5.6-sol"
        }
        terra = {
            node_id
            for node_id, route in materialized
            if route["model"] == "gpt-5.6-terra"
        }
        self.assertLess(len(sol), len(terra))
        self.assertNotIn("steward-concordloom", sol)
        self.assertIn("protocol-design", sol)
        self.assertIn("review-successor", sol)
        node_profiles = {
            node["id"]: node["execution_profile"] for node in nodes
        }
        self.assertTrue(
            all(
                node_profiles[node_id]
                in {
                    "strategy",
                    "protocol",
                    "assurance",
                    "evolution-analysis",
                    "evolution-proposal",
                    "evolution-review",
                }
                for node_id in sol
            )
        )
        self.assertEqual(
            "gpt-5.6-luna",
            dict(materialized)["collect-friction"]["model"],
        )
        for node_id in (
            "maintain-cli",
            "maintain-self-binding",
            "author-documentation",
            "localize-content",
        ):
            self.assertEqual(
                "gpt-5.6-terra",
                dict(materialized)[node_id]["model"],
            )
        skill = {"id": "design-project-loops", "version": "0.1.0"}
        for node_id in (
            "discover-product-needs",
            "operate-run-lifecycle",
            "maintain-self-binding",
            "propose-successor",
            "review-successor",
        ):
            self.assertEqual([skill], dict(materialized)[node_id]["skills"])
        self.assertEqual([], dict(materialized)["maintain-cli"]["skills"])

    def test_operator_release_and_activation_are_model_none(self) -> None:
        nodes = {node["id"]: node for node in self.model["nodes"]}
        for node_id in (
            "steward-concordloom",
            "decide-product",
            "plan-release",
            "distribute-package",
            "publish-site",
            "accept-source-change",
            "activate-successor",
        ):
            node = nodes[node_id]
            profile = self.model["profiles"][node["execution_profile"]]
            route = node.get(
                "route_materialization",
                profile["route_materialization"],
            )
            self.assertEqual("", route["model_provider"], node_id)
            self.assertEqual("none", route["model"], node_id)
        operator = next(
            principal
            for principal in self.policy["authority"]["principals"]
            if principal["id"] == "example-operator"
        )
        self.assertEqual("human", operator["kind"])

    def test_targeted_run_materializes_exact_bound_route_metadata(self) -> None:
        binding = load(V7 / "binding.json")
        binding["id"] = "token-routing-test-binding"
        binding["predecessor_binding_digest"] = binding["binding_digest"]
        binding["accepted_by"]["proposal_digest"] = self.proposal[
            "proposal_digest"
        ]
        replacements = {
            "cycle_registry": self.registry,
            "policy": self.policy,
            "atlas_input": self.model,
        }
        for artifact in binding["artifacts"]:
            if artifact["role"] in replacements:
                artifact["digest"] = digest(replacements[artifact["role"]])
        binding["binding_digest"] = document_digest(
            binding, excluded_fields=["/binding_digest"]
        )
        candidate = {
            "kind": "concordloom.candidate-manifest",
            "schema_version": "0.1",
            "id": "token-route-candidate",
            "generated_at": "2026-07-28T00:01:00Z",
            "revision": "a" * 40,
            "tree_digest": "sha256:" + ("b" * 64),
            "dirty": False,
            "files": [],
        }
        card = create_run_card(
            binding,
            self.registry,
            self.policy,
            candidate,
            run_id="token-target",
            root_loop_id="steward-concordloom",
            candidate_author_principal_ids=["example-executor"],
            target_loop_ids=["maintain-cli"],
            development_model=self.model,
        )
        routes = {item["loop_id"]: item for item in card["planned_route"]}
        self.assertEqual("none", routes["steward-concordloom"]["model"])
        self.assertEqual("gpt-5.6-terra", routes["runtime-tooling"]["model"])
        self.assertEqual("gpt-5.6-terra", routes["maintain-cli"]["model"])
        for route in routes.values():
            self.assertTrue(ROUTE_FIELDS.issubset(route))
        self.assertEqual(
            ["github", "shell", "tests"],
            routes["maintain-cli"]["tool_capabilities"],
        )

        changed = json.loads(json.dumps(self.model))
        changed["id"] = "unbound-development-model"
        with self.assertRaisesRegex(RunStateError, "exact atlas input"):
            create_run_card(
                binding,
                self.registry,
                self.policy,
                candidate,
                run_id="unbound-token-target",
                root_loop_id="steward-concordloom",
                candidate_author_principal_ids=["example-executor"],
                target_loop_ids=["maintain-cli"],
                development_model=changed,
            )

    def test_cli_auto_loads_exact_bound_development_model(self) -> None:
        binding = load(V7 / "binding.json")
        binding["id"] = "token-routing-cli-binding"
        binding["predecessor_binding_digest"] = binding["binding_digest"]
        binding["accepted_by"]["proposal_digest"] = self.proposal[
            "proposal_digest"
        ]
        replacements = {
            "cycle_registry": self.registry,
            "policy": self.policy,
            "atlas_input": self.model,
        }
        for artifact in binding["artifacts"]:
            if artifact["role"] in replacements:
                artifact["digest"] = digest(replacements[artifact["role"]])
            if artifact["role"] == "atlas_input":
                artifact["path"] = (
                    "framework/concordloom/v8/development-model.json"
                )
            elif artifact["role"] == "cycle_registry":
                artifact["path"] = (
                    "framework/concordloom/v8/cycle-registry.json"
                )
            elif artifact["role"] == "policy":
                artifact["path"] = "framework/concordloom/v8/policy.json"
        binding["binding_digest"] = document_digest(
            binding, excluded_fields=["/binding_digest"]
        )
        binding_path = self.v8 / "test-binding.json"
        binding_path.write_text(
            json.dumps(binding, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        candidate_path = self.checkout / "candidate.json"
        candidate_path.write_text(
            json.dumps(
                {
                    "kind": "concordloom.candidate-manifest",
                    "schema_version": "0.1",
                    "id": "token-cli-candidate",
                    "generated_at": "2026-07-28T00:02:00Z",
                    "revision": "a" * 40,
                    "tree_digest": "sha256:" + ("b" * 64),
                    "dirty": False,
                    "files": [],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        output = self.checkout / "targeted-run.json"
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(self.checkout / "src")
        result = subprocess.run(
            [
                "python3",
                "-m",
                "concordloom",
                "run",
                "new",
                "--binding",
                str(binding_path),
                "--registry",
                str(self.v8 / "cycle-registry.json"),
                "--policy",
                str(self.v8 / "policy.json"),
                "--candidate",
                str(candidate_path),
                "--run-id",
                "token-cli-target",
                "--root-loop",
                "steward-concordloom",
                "--candidate-author",
                "example-executor",
                "--target-loop",
                "maintain-cli",
                "--output",
                str(output),
            ],
            cwd=self.checkout,
            env=environment,
            text=True,
            capture_output=True,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        routes = {
            item["loop_id"]: item
            for item in load(output)["planned_route"]
        }
        self.assertEqual("gpt-5.6-terra", routes["maintain-cli"]["model"])
        self.assertEqual(
            ["github", "shell", "tests"],
            routes["maintain-cli"]["tool_capabilities"],
        )

    def test_proposal_output_reports_exact_digest_and_tree(self) -> None:
        expected = (
            f"proposal={self.proposal['proposal_digest']} "
            f"tree={digest(self.proposal['artifacts'])}"
        )
        self.assertIn(expected, self.result.stdout)

    def test_activation_requires_linked_review_decision_and_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            checkout = Path(directory) / "repo"
            shutil.copytree(self.checkout, checkout)
            proposal = load(
                checkout
                / "framework"
                / "concordloom"
                / "v8"
                / "binding-proposal.json"
            )
            base_digest = load(
                checkout
                / "framework"
                / "concordloom"
                / "v7"
                / "binding.json"
            )["binding_digest"]
            proposal_tree = digest(proposal["artifacts"])
            common = {
                "schema": "concordloom://activation-receipt/0.1",
                "schema_version": "0.1",
                "verdict": "pass",
                "proposal_digest": proposal["proposal_digest"],
                "proposal_tree_digest": proposal_tree,
                "base_binding_digest": base_digest,
                "candidate_tree_digest": proposal_tree,
                "candidate_author_principal_ids": ["example-orchestrator"],
            }
            receipts = checkout / "receipts"

            def write_receipt(name: str, body: dict) -> tuple[Path, str]:
                receipt_digest = digest(body)
                path = receipts / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(
                    canonical_bytes({**body, "receipt_digest": receipt_digest})
                    + b"\n"
                )
                return path, receipt_digest

            review_path, review_digest = write_receipt(
                "review.json",
                {
                    **common,
                    "kind": "concordloom.review-recommendation-receipt",
                    "id": "review-v8-token-routing",
                    "principal": {"id": "example-reviewer", "kind": "agent"},
                    "capability": "review-candidate",
                },
            )
            evolution_path, evolution_digest = write_receipt(
                "evolution.json",
                {
                    **common,
                    "kind": "concordloom.evolution-decision-receipt",
                    "id": "decide-v8-token-routing-receipt",
                    "principal": {"id": "example-operator", "kind": "human"},
                    "capability": "decide-evolution",
                    "decision_id": "decide-v8-token-routing",
                    "review_recommendation_digest": review_digest,
                },
            )
            activation_path, activation_digest = write_receipt(
                "activation.json",
                {
                    **common,
                    "kind": "concordloom.activation-evidence-receipt",
                    "id": "activate-v8-token-routing-evidence",
                    "principal": {"id": "example-operator", "kind": "human"},
                    "capability": "activate-binding",
                    "decision_id": "activate-v8-token-routing",
                    "review_recommendation_digest": review_digest,
                    "evolution_decision_digest": evolution_digest,
                },
            )
            environment = dict(os.environ)
            environment["PYTHONPATH"] = str(checkout / "src")
            activated = subprocess.run(
                [
                    "python3",
                    str(checkout / "tools" / "authorize_token_routing.py"),
                    "--activate",
                    "--accepted-proposal-digest",
                    proposal["proposal_digest"],
                    "--review-recommendation",
                    str(review_path),
                    "--evolution-decision",
                    str(evolution_path),
                    "--activation-evidence",
                    str(activation_path),
                ],
                cwd=checkout,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, activated.returncode, activated.stderr)
            binding = load(
                checkout / "framework" / "concordloom" / "v8" / "binding.json"
            )
            catalog = load(
                checkout / "framework" / "concordloom" / "catalog.json"
            )
            receipt = load(
                checkout
                / "framework"
                / "concordloom"
                / "v8"
                / "activation-receipt.json"
            )
            self.assertIn("TOKEN_ROUTING_V8_ACTIVATED", activated.stdout)
            self.assertEqual(binding["binding_digest"], catalog["active_binding_digest"])
            self.assertEqual(review_digest, receipt["review_recommendation_digest"])
            self.assertEqual(
                evolution_digest, receipt["evolution_decision_digest"]
            )
            self.assertEqual(
                activation_digest, receipt["activation_evidence_digest"]
            )


if __name__ == "__main__":
    unittest.main()
