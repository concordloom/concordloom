from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

from concordloom.canonical import canonical_bytes, digest
from concordloom.catalog import validate_catalog
from concordloom.loops import validate_policy, validate_registry


ROOT = Path(__file__).resolve().parents[1]
V6 = ROOT / "framework" / "concordloom" / "v6"
METADATA_PATHS = {"CITATION.cff", "pyproject.toml"}
EXACT_PUBLICATION_EFFECTS = {
    "distribute-package": [
        "github-release-assets",
        "github-version-tag",
    ],
    "publish-site": ["github-pages"],
    "maintain-repository-presence": [
        "github-repository-homepage",
        "github-repository-security-settings",
        "github-repository-social-preview",
    ],
    "publish-source-change": [
        "github-pull-request",
        "github-repository-source",
    ],
    "accept-source-change": ["github-pull-request-merge"],
    "maintain-organization-presence": ["github-organization-profile"],
}
PUBLISHER_LOOPS = {
    "distribute-package",
    "publish-site",
    "maintain-repository-presence",
    "publish-source-change",
    "maintain-organization-presence",
}
RECEIPT_SCHEMA = "concordloom://activation-receipt/0.1"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def path_is_within(path: str, scope: str) -> bool:
    return path == scope or path.startswith(scope.rstrip("/") + "/")


def write_receipt(path: Path, payload: dict) -> str:
    body = dict(payload)
    body.pop("receipt_digest", None)
    receipt_digest = digest(body)
    document = {**body, "receipt_digest": receipt_digest}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(document) + b"\n")
    return receipt_digest


class MetadataMaintenanceEvolutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        cls.checkout = Path(cls.temporary.name) / "repo"
        (cls.checkout / "tools").mkdir(parents=True)
        shutil.copytree(ROOT / "src", cls.checkout / "src")
        shutil.copytree(ROOT / "schemas", cls.checkout / "schemas")
        shutil.copytree(ROOT / "framework", cls.checkout / "framework")
        shutil.copytree(
            ROOT / "docs" / ".concord-transition",
            cls.checkout / "docs" / ".concord-transition",
        )
        for name in (
            "authorize_source_publication.py",
            "authorize_metadata_maintenance.py",
        ):
            shutil.copy2(ROOT / "tools" / name, cls.checkout / "tools" / name)

        cls.catalog_before = (
            cls.checkout / "framework" / "concordloom" / "catalog.json"
        ).read_bytes()
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(cls.checkout / "src")
        cls.generator = subprocess.run(
            [
                "python3",
                str(
                    cls.checkout
                    / "tools"
                    / "authorize_metadata_maintenance.py"
                ),
            ],
            cwd=cls.checkout,
            env=environment,
            text=True,
            capture_output=True,
            check=True,
        )
        cls.generated = (
            cls.checkout / "framework" / "concordloom" / "v7"
        )
        cls.v6_model = load(V6 / "development-model.json")
        cls.v7_model = load(cls.generated / "development-model.json")
        cls.v7_policy = load(cls.generated / "policy.json")
        cls.v7_registry = load(cls.generated / "cycle-registry.json")
        cls.proposal = load(cls.generated / "binding-proposal.json")
        cls.base_binding_digest = load(V6 / "binding.json")["binding_digest"]
        cls.proposal_tree_digest = digest(cls.proposal["artifacts"])
        cls.candidate_tree_digest = cls.proposal_tree_digest
        cls.receipt_directory = cls.checkout / "receipts"
        common = {
            "schema": RECEIPT_SCHEMA,
            "schema_version": "0.1",
            "verdict": "pass",
            "proposal_digest": cls.proposal["proposal_digest"],
            "proposal_tree_digest": cls.proposal_tree_digest,
            "base_binding_digest": cls.base_binding_digest,
            "candidate_tree_digest": cls.candidate_tree_digest,
            "candidate_author_principal_ids": ["example-executor"],
        }
        cls.review_path = cls.receipt_directory / "review.json"
        cls.review_digest = write_receipt(
            cls.review_path,
            {
                **common,
                "kind": "concordloom.review-recommendation-receipt",
                "id": "review-v7-successor",
                "principal": {"id": "example-reviewer", "kind": "agent"},
                "capability": "review-candidate",
            },
        )
        cls.evolution_path = cls.receipt_directory / "evolution.json"
        cls.evolution_digest = write_receipt(
            cls.evolution_path,
            {
                **common,
                "kind": "concordloom.evolution-decision-receipt",
                "id": "decide-v7-evolution-receipt",
                "principal": {"id": "example-operator", "kind": "human"},
                "capability": "decide-evolution",
                "decision_id": "decide-v7-evolution",
                "review_recommendation_digest": cls.review_digest,
            },
        )
        cls.activation_path = cls.receipt_directory / "activation.json"
        cls.activation_digest = write_receipt(
            cls.activation_path,
            {
                **common,
                "kind": "concordloom.activation-evidence-receipt",
                "id": "activate-v7-binding-evidence",
                "principal": {"id": "example-operator", "kind": "human"},
                "capability": "activate-binding",
                "decision_id": "activate-v7-binding",
                "review_recommendation_digest": cls.review_digest,
                "evolution_decision_digest": cls.evolution_digest,
            },
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def edges(self) -> dict[str, dict]:
        return {
            edge["child_loop_id"]: edge
            for edge in self.v7_registry["containment_graph"]["edges"]
        }

    def activation_checkout(self, directory: Path) -> Path:
        checkout = directory / "repo"
        shutil.copytree(self.checkout, checkout)
        catalog_path = (
            checkout / "framework" / "concordloom" / "catalog.json"
        )
        catalog = load(catalog_path)
        v6_digest = load(
            checkout / "framework" / "concordloom" / "v6" / "binding.json"
        )["binding_digest"]
        v6_index = next(
            index
            for index, entry in enumerate(catalog["entries"])
            if entry["binding_digest"] == v6_digest
        )
        catalog["entries"] = catalog["entries"][: v6_index + 1]
        catalog["active_binding_digest"] = v6_digest
        catalog_path.write_bytes(canonical_bytes(catalog) + b"\n")
        return checkout

    def run_activation(
        self,
        checkout: Path,
        *,
        check: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(checkout / "src")
        return subprocess.run(
            [
                "python3",
                str(
                    checkout
                    / "tools"
                    / "authorize_metadata_maintenance.py"
                ),
                "--activate",
                "--accepted-proposal-digest",
                self.proposal["proposal_digest"],
                "--review-recommendation",
                str(checkout / "receipts" / "review.json"),
                "--evolution-decision",
                str(checkout / "receipts" / "evolution.json"),
                "--activation-evidence",
                str(checkout / "receipts" / "activation.json"),
            ],
            cwd=checkout,
            env=environment,
            text=True,
            capture_output=True,
            check=check,
        )

    def assert_rejected_receipts(
        self,
        mutate,
        message: str,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            checkout = self.activation_checkout(Path(directory))
            mutate(checkout)
            catalog_path = (
                checkout / "framework" / "concordloom" / "catalog.json"
            )
            catalog_before = catalog_path.read_bytes()
            result = self.run_activation(checkout)
            self.assertNotEqual(0, result.returncode)
            self.assertIn(message, result.stderr + result.stdout)
            self.assertEqual(catalog_before, catalog_path.read_bytes())

    def test_v7_keeps_the_complete_58_cycle_graph(self) -> None:
        self.assertEqual(58, len(self.v7_model["nodes"]))
        self.assertEqual(
            [
                (node["id"], node["parent_id"], node["children"])
                for node in self.v6_model["nodes"]
            ],
            [
                (node["id"], node["parent_id"], node["children"])
                for node in self.v7_model["nodes"]
            ],
        )

    def test_scopes_are_finite_and_responsibility_specific(self) -> None:
        validate_policy(self.v7_policy)
        validate_registry(self.v7_registry, self.v7_policy)
        for loop_id, edge in self.edges().items():
            scope = edge["grant"]["scope"]
            self.assertNotIn(".", scope["read_paths"], loop_id)
            self.assertNotIn(".", scope["write_paths"], loop_id)
            self.assertEqual(
                len(scope["read_paths"]),
                len(set(scope["read_paths"])),
                loop_id,
            )
            self.assertEqual(
                len(scope["write_paths"]),
                len(set(scope["write_paths"])),
                loop_id,
            )

    def test_release_metadata_authoring_is_separate_from_distribution(
        self,
    ) -> None:
        edges = self.edges()
        self.assertTrue(
            METADATA_PATHS.issubset(
                edges["plan-release"]["grant"]["scope"]["write_paths"]
            )
        )
        for loop_id, edge in edges.items():
            if loop_id in {"release-distribution", "plan-release"}:
                continue
            self.assertTrue(
                METADATA_PATHS.isdisjoint(
                    edge["grant"]["scope"]["write_paths"]
                ),
                loop_id,
            )
        authoring_scope = edges["plan-release"]["grant"]["scope"]
        self.assertEqual("none", authoring_scope["network"])
        self.assertEqual([], authoring_scope["external_mutations"])
        distribution_scope = edges["distribute-package"]["grant"]["scope"]
        self.assertEqual([], distribution_scope["write_paths"])
        self.assertEqual("write", distribution_scope["network"])
        self.assertEqual(
            ["github-release-assets", "github-version-tag"],
            distribution_scope["external_mutations"],
        )
        evolution = load(self.generated / "evolution-proposal.json")
        operation = evolution["operations"][0]["value"]
        self.assertEqual("plan-release", operation["metadata_owner_loop_id"])
        self.assertIn(
            "tag and GitHub release asset publication",
            evolution["expected_effect"],
        )

    def test_product_root_and_evolution_use_operator_capabilities(self) -> None:
        loops = {loop["id"]: loop for loop in self.v7_registry["loops"]}
        expected = {
            "steward-concordloom": "authorize-run",
            "product-direction": "accept-intent",
            "decide-product": "accept-intent",
            "system-evolution": "decide-evolution",
            "activate-successor": "activate-binding",
        }
        for loop_id, capability in expected.items():
            self.assertEqual(
                capability,
                loops[loop_id]["authority"]["execute_capability"],
                loop_id,
            )
        activation_grant = self.edges()["activate-successor"]["grant"]
        self.assertTrue(
            {"decide-evolution", "activate-binding"}.issubset(
                activation_grant["capabilities"]
            )
        )

    def test_review_recommends_but_operator_separately_decides_and_activates(
        self,
    ) -> None:
        loops = {loop["id"]: loop for loop in self.v7_registry["loops"]}
        contracts = {
            contract["id"]: contract
            for contract in self.v7_registry["evidence_contracts"]
        }
        self.assertEqual(
            "review-candidate",
            loops["review-successor"]["authority"]["execute_capability"],
        )
        self.assertEqual(
            ["review-successor-recommendation"],
            contracts["review-successor-acceptance"]["required_claims"],
        )
        self.assertEqual(
            [
                "review-successor-recommendation",
                "decide-evolution-decision",
                "activate-successor-outcome",
            ],
            contracts["activate-successor-acceptance"]["required_claims"],
        )
        model = {node["id"]: node for node in self.v7_model["nodes"]}
        review_output = model["review-successor"]["contract"]["en"]["output"]
        self.assertIn("recommendation", review_output)
        self.assertNotIn("acceptance decision", review_output)
        activation_input = model["activate-successor"]["contract"]["en"][
            "input"
        ]
        self.assertIn("separate operator evolution decision", activation_input)
        self.assertIn("activation evidence", activation_input)
        requirements = self.v7_model["activation_requirements"]
        self.assertEqual(
            "recommendation",
            requirements["review_successor"]["outcome"],
        )
        self.assertFalse(
            requirements["review_successor"]["may_decide_evolution"]
        )
        self.assertEqual(
            "decide-evolution",
            requirements["evolution_decision"]["capability"],
        )
        self.assertTrue(
            requirements["evolution_decision"][
                "separate_from_activation_decision"
            ]
        )
        for receipt_type in (
            "review_successor",
            "evolution_decision",
            "activation",
        ):
            self.assertTrue(
                requirements[receipt_type]["exact_receipt_digest_required"]
            )
        self.assertEqual(
            ["/receipt_digest"],
            requirements["digest_contract"]["receipt_digest_excludes"],
        )
        proposal = load(self.generated / "binding-proposal.json")
        model_artifact = next(
            artifact
            for artifact in proposal["artifacts"]
            if artifact["role"] == "atlas_input"
        )
        self.assertEqual(digest(self.v7_model), model_artifact["digest"])

    def test_distribution_effects_and_routes_are_exact(self) -> None:
        edges = self.edges()
        leaf_effects = {
            loop_id: edge["grant"]["scope"]["external_mutations"]
            for loop_id, edge in edges.items()
            if loop_id in EXACT_PUBLICATION_EFFECTS
        }
        self.assertEqual(EXACT_PUBLICATION_EFFECTS, leaf_effects)
        self.assertEqual(
            sorted(
                {
                    effect
                    for effects in EXACT_PUBLICATION_EFFECTS.values()
                    for effect in effects
                }
            ),
            edges["release-distribution"]["grant"]["scope"][
                "external_mutations"
            ],
        )

        route = load(self.generated / "publication-route.json")
        routed_effects = {
            item["loop_id"]: item["scope"]["external_mutations"]
            for item in route
            if item["scope"]["external_mutations"]
        }
        self.assertEqual(EXACT_PUBLICATION_EFFECTS, routed_effects)
        for item in route:
            self.assertNotIn(".", item["scope"]["read_paths"])
            self.assertEqual([], item["scope"]["write_paths"])
            if "github-repository-security-settings" in item["scope"][
                "external_mutations"
            ]:
                self.assertEqual(
                    "maintain-repository-presence",
                    item["loop_id"],
                )
                self.assertEqual("publisher", item["role"])

        publisher_nodes = {
            node["id"]
            for node in self.v7_model["nodes"]
            if node["responsible_role"]["en"] == "publisher"
        }
        for loop_id, edge in edges.items():
            if loop_id in publisher_nodes:
                continue
            self.assertNotIn(
                "github-repository-security-settings",
                edge["grant"]["scope"]["external_mutations"],
                loop_id,
            )

    def test_every_tracked_source_has_a_leaf_owner(self) -> None:
        catalog = load(ROOT / "framework" / "concordloom" / "catalog.json")
        active_entry = next(
            entry
            for entry in catalog["entries"]
            if entry["binding_digest"] == catalog["active_binding_digest"]
        )
        active_binding = load(ROOT / active_entry["path"])
        active_registry_path = next(
            artifact["path"]
            for artifact in active_binding["artifacts"]
            if artifact["role"] == "cycle_registry"
        )
        active_model_path = next(
            artifact["path"]
            for artifact in active_binding["artifacts"]
            if artifact["role"] == "atlas_input"
        )
        active_registry = load(ROOT / active_registry_path)
        active_model = load(ROOT / active_model_path)
        leaves = {
            node["id"]
            for node in active_model["nodes"]
            if not node["children"]
        }
        edges = {
            edge["child_loop_id"]: edge
            for edge in active_registry["containment_graph"]["edges"]
        }
        leaf_scopes = {
            loop_id: edges[loop_id]["grant"]["scope"]["write_paths"]
            for loop_id in leaves
        }
        tracked = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.splitlines()
        missing = [
            path
            for path in tracked
            if not any(
                path_is_within(path, scope)
                for scopes in leaf_scopes.values()
                for scope in scopes
            )
        ]
        self.assertEqual([], missing)

    def test_active_catalog_is_unchanged_by_proposal_generation(self) -> None:
        catalog_path = (
            self.checkout / "framework" / "concordloom" / "catalog.json"
        )
        self.assertEqual(self.catalog_before, catalog_path.read_bytes())
        catalog = load(catalog_path)
        validate_catalog(catalog, artifact_root=self.checkout)
        active = catalog["entries"][-1]
        self.assertEqual(
            active["binding_digest"],
            catalog["active_binding_digest"],
        )
        active_binding = load(self.checkout / active["path"])
        self.assertEqual(
            active_binding["binding_digest"],
            catalog["active_binding_digest"],
        )
        proposal = load(self.generated / "binding-proposal.json")
        self.assertEqual(
            self.base_binding_digest,
            proposal["predecessor_binding_digest"],
        )
        self.assertIn("METADATA_MAINTENANCE_V7_PROPOSED", self.generator.stdout)

    def test_successor_proposal_remains_non_self_activating(self) -> None:
        evolution = load(self.generated / "evolution-proposal.json")
        proposal = load(self.generated / "binding-proposal.json")
        self.assertEqual("proposed", evolution["status"])
        self.assertTrue(evolution["decision_required"])
        self.assertFalse(evolution["activation_allowed"])
        self.assertTrue(proposal["activation_required"])
        self.assertEqual(
            digest(self.v7_policy),
            self.v7_registry["policy_digest"],
        )

    def test_proposal_generation_is_deterministic(self) -> None:
        proposal_path = self.generated / "binding-proposal.json"
        before = proposal_path.read_bytes()
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(self.checkout / "src")
        subprocess.run(
            [
                "python3",
                str(
                    self.checkout
                    / "tools"
                    / "authorize_metadata_maintenance.py"
                ),
            ],
            cwd=self.checkout,
            env=environment,
            text=True,
            capture_output=True,
            check=True,
        )
        self.assertEqual(before, proposal_path.read_bytes())

    def test_valid_exact_receipts_activate_only_an_isolated_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            checkout = self.activation_checkout(Path(directory))
            result = self.run_activation(checkout, check=True)
            self.assertIn("METADATA_MAINTENANCE_V7_ACTIVATED", result.stdout)
            receipt = load(
                checkout
                / "framework"
                / "concordloom"
                / "v7"
                / "activation-receipt.json"
            )
            self.assertEqual(
                self.review_digest,
                receipt["review_recommendation_digest"],
            )
            self.assertEqual(
                self.evolution_digest,
                receipt["evolution_decision_digest"],
            )
            self.assertEqual(
                self.activation_digest,
                receipt["activation_evidence_digest"],
            )
            self.assertEqual(
                self.proposal_tree_digest,
                receipt["proposal_tree_digest"],
            )
            self.assertEqual(
                "decide-v7-evolution",
                receipt["evolution_decision_id"],
            )
            self.assertEqual(
                "activate-v7-binding",
                receipt["activation_decision_id"],
            )
            catalog = load(
                checkout / "framework" / "concordloom" / "catalog.json"
            )
            validate_catalog(catalog, artifact_root=checkout)
            binding = load(
                checkout
                / "framework"
                / "concordloom"
                / "v7"
                / "binding.json"
            )
            self.assertEqual(
                binding["binding_digest"],
                catalog["active_binding_digest"],
            )

    def test_activation_rejects_a_forged_receipt_digest(self) -> None:
        def mutate(checkout: Path) -> None:
            path = checkout / "receipts" / "review.json"
            document = load(path)
            document["receipt_digest"] = "sha256:" + ("0" * 64)
            path.write_bytes(canonical_bytes(document) + b"\n")

        self.assert_rejected_receipts(mutate, "receipt digest mismatch")

    def test_activation_rejects_the_wrong_proposal(self) -> None:
        def mutate(checkout: Path) -> None:
            path = checkout / "receipts" / "review.json"
            document = load(path)
            document["proposal_digest"] = "sha256:" + ("0" * 64)
            write_receipt(path, document)

        self.assert_rejected_receipts(mutate, "pins the wrong proposal")

    def test_activation_rejects_a_stale_base_binding(self) -> None:
        def mutate(checkout: Path) -> None:
            path = checkout / "receipts" / "review.json"
            document = load(path)
            document["base_binding_digest"] = "sha256:" + ("0" * 64)
            write_receipt(path, document)

        self.assert_rejected_receipts(mutate, "pins a stale base binding")

    def test_activation_rejects_the_wrong_capability(self) -> None:
        def mutate(checkout: Path) -> None:
            path = checkout / "receipts" / "review.json"
            document = load(path)
            document["capability"] = "execute-work"
            write_receipt(path, document)

        self.assert_rejected_receipts(mutate, "uses the wrong capability")

    def test_activation_rejects_a_non_pass_verdict(self) -> None:
        def mutate(checkout: Path) -> None:
            path = checkout / "receipts" / "review.json"
            document = load(path)
            document["verdict"] = "fail"
            write_receipt(path, document)

        self.assert_rejected_receipts(mutate, "verdict is not pass")

    def test_activation_rejects_noncanonical_receipt_bytes(self) -> None:
        def mutate(checkout: Path) -> None:
            path = checkout / "receipts" / "review.json"
            document = load(path)
            path.write_text(
                json.dumps(document, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

        self.assert_rejected_receipts(mutate, "is not canonical")

    def test_activation_rejects_mismatched_candidate_trees(self) -> None:
        def mutate(checkout: Path) -> None:
            path = checkout / "receipts" / "activation.json"
            document = load(path)
            document["candidate_tree_digest"] = "sha256:" + ("d" * 64)
            write_receipt(path, document)

        self.assert_rejected_receipts(
            mutate,
            "candidate tree does not match the exact proposal artifact tree",
        )

    def test_activation_rejects_reused_decision_ids(self) -> None:
        def mutate(checkout: Path) -> None:
            evolution = load(checkout / "receipts" / "evolution.json")
            path = checkout / "receipts" / "activation.json"
            activation = load(path)
            activation["decision_id"] = evolution["decision_id"]
            write_receipt(path, activation)

        self.assert_rejected_receipts(
            mutate,
            "evolution and activation decision ids must be distinct",
        )

    def test_workflow_actions_are_pinned_to_full_commit_shas(self) -> None:
        uses_pattern = re.compile(r"^\s*-?\s*uses:\s*([^#\s]+)")
        failures: list[str] = []
        for workflow in sorted((ROOT / ".github" / "workflows").glob("*.y*ml")):
            for line_number, line in enumerate(
                workflow.read_text(encoding="utf-8").splitlines(),
                start=1,
            ):
                match = uses_pattern.match(line)
                if not match:
                    continue
                action = match.group(1).strip("\"'")
                if action.startswith("./"):
                    continue
                _name, separator, ref = action.rpartition("@")
                if separator != "@" or not re.fullmatch(
                    r"[0-9a-fA-F]{40}", ref
                ):
                    failures.append(f"{workflow.name}:{line_number}:{action}")
        self.assertEqual([], failures)


if __name__ == "__main__":
    unittest.main()
