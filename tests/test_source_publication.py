from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from concordloom.catalog import validate_catalog
from concordloom.loops import validate_registry
from concordloom.run import RunStateError, create_run_card


ROOT = Path(__file__).resolve().parents[1]
V5 = ROOT / "framework" / "concordloom" / "v5"
V6 = ROOT / "framework" / "concordloom" / "v6"
EXPECTED_PROPOSAL_DIGEST = (
    "sha256:f43ce97fd4c5cb01d86ccf147ebd298a5b5e5c2dfed043f28975e92baa28f18a"
)
NEW_CYCLES = {
    "publish-source-change",
    "accept-source-change",
    "maintain-organization-presence",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class SourcePublicationEvolutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.v5_binding = load(V5 / "binding.json")
        self.v5_registry = load(V5 / "cycle-registry.json")
        self.v6_model = load(V6 / "development-model.json")
        self.v6_policy = load(V6 / "policy.json")
        self.v6_registry = load(V6 / "cycle-registry.json")
        self.v6_proposal = load(V6 / "binding-proposal.json")

    def test_proposal_did_not_self_activate_and_exact_successor_is_active(self) -> None:
        self.assertEqual(
            EXPECTED_PROPOSAL_DIGEST,
            self.v6_proposal["proposal_digest"],
        )
        self.assertEqual(
            self.v5_binding["binding_digest"],
            self.v6_proposal["predecessor_binding_digest"],
        )
        evolution = load(V6 / "evolution-proposal.json")
        self.assertEqual("proposed", evolution["status"])
        self.assertTrue(evolution["decision_required"])
        self.assertFalse(evolution["activation_allowed"])
        binding = load(V6 / "binding.json")
        catalog = load(ROOT / "framework" / "concordloom" / "catalog.json")
        self.assertEqual(
            binding["binding_digest"],
            catalog["active_binding_digest"],
        )
        self.assertEqual(
            self.v5_binding["binding_digest"],
            binding["predecessor_binding_digest"],
        )
        self.assertEqual(
            "activate-concordloom-self-binding-v6",
            binding["accepted_by"]["decision_id"],
        )

    def test_v6_adds_only_the_three_accepted_release_cycles(self) -> None:
        v5_nodes = {node["id"]: node for node in load(V5 / "development-model.json")["nodes"]}
        v6_nodes = {node["id"]: node for node in self.v6_model["nodes"]}
        self.assertEqual(55, len(v5_nodes))
        self.assertEqual(58, len(v6_nodes))
        self.assertEqual(NEW_CYCLES, set(v6_nodes) - set(v5_nodes))
        self.assertEqual(set(), set(v5_nodes) - set(v6_nodes))
        for cycle_id in NEW_CYCLES:
            self.assertEqual(
                "release-distribution",
                v6_nodes[cycle_id]["parent_id"],
            )
        validate_registry(self.v6_registry, self.v6_policy)

    def test_default_route_keeps_each_external_effect_at_its_leaf(self) -> None:
        manifest = {
            "kind": "concordloom.candidate-manifest",
            "schema_version": "0.1",
            "id": "v6-route-contract",
            "generated_at": "2026-07-27T18:02:00Z",
            "revision": "a" * 40,
            "tree_digest": "sha256:" + ("b" * 64),
            "dirty": False,
            "files": [],
        }
        # A proposal cannot authorize a run. Use a temporary activation below
        # and exercise the resulting binding against the exact v6 registry.
        with tempfile.TemporaryDirectory() as directory:
            checkout = self._isolated_checkout(Path(directory))
            self._run_generator(
                checkout,
                "--activate",
                "--accepted-proposal-digest",
                EXPECTED_PROPOSAL_DIGEST,
            )
            binding = load(
                checkout / "framework" / "concordloom" / "v6" / "binding.json"
            )
            card = create_run_card(
                binding,
                self.v6_registry,
                self.v6_policy,
                manifest,
                run_id="v6-route-contract",
                root_loop_id="steward-concordloom",
                candidate_author_principal_ids=["example-executor"],
            )

        routes = {route["loop_id"]: route for route in card["planned_route"]}
        effects = {
            loop_id: route["scope"]["external_mutations"]
            for loop_id, route in routes.items()
            if route["scope"]["external_mutations"]
        }
        self.assertEqual(
            {
                "publish-site": ["github-pages"],
                "maintain-repository-presence": [
                    "github-repository-homepage",
                    "github-repository-social-preview",
                ],
                "publish-source-change": [
                    "github-pull-request",
                    "github-repository-source",
                ],
                "accept-source-change": ["github-pull-request-merge"],
                "maintain-organization-presence": [
                    "github-organization-profile"
                ],
            },
            effects,
        )
        self.assertEqual("publisher", routes["publish-source-change"]["role"])
        self.assertEqual("operator", routes["accept-source-change"]["role"])
        self.assertEqual(
            "publisher",
            routes["maintain-organization-presence"]["role"],
        )
        self.assertEqual([], routes["steward-concordloom"]["scope"]["external_mutations"])
        self.assertEqual([], routes["release-distribution"]["scope"]["external_mutations"])

        adversarial = [dict(route) for route in card["planned_route"]]
        source = next(
            route for route in adversarial
            if route["loop_id"] == "publish-source-change"
        )
        source["role"] = "executor"
        with self.assertRaisesRegex(RunStateError, "routing capability"):
            create_run_card(
                binding,
                self.v6_registry,
                self.v6_policy,
                manifest,
                run_id="v6-adversarial-route",
                root_loop_id="steward-concordloom",
                candidate_author_principal_ids=["example-executor"],
                planned_route=adversarial,
            )

    def test_activation_requires_the_exact_operator_accepted_digest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            checkout = self._isolated_checkout(Path(directory))
            binding_path = (
                checkout
                / "framework"
                / "concordloom"
                / "v6"
                / "binding.json"
            )
            catalog_path = (
                checkout / "framework" / "concordloom" / "catalog.json"
            )
            binding_before = binding_path.read_bytes()
            catalog_before = catalog_path.read_bytes()
            failed = self._run_generator(
                checkout,
                "--activate",
                "--accepted-proposal-digest",
                "sha256:" + ("0" * 64),
                check=False,
            )
            self.assertNotEqual(0, failed.returncode)
            self.assertEqual(binding_before, binding_path.read_bytes())
            self.assertEqual(catalog_before, catalog_path.read_bytes())
            self._run_generator(
                checkout,
                "--activate",
                "--accepted-proposal-digest",
                EXPECTED_PROPOSAL_DIGEST,
            )
            binding = load(binding_path)
            catalog = load(catalog_path)
            validate_catalog(catalog, artifact_root=checkout)
            self.assertEqual(
                binding["binding_digest"],
                catalog["active_binding_digest"],
            )
            self.assertEqual(
                "activate-concordloom-self-binding-v6",
                binding["accepted_by"]["decision_id"],
            )

    def _isolated_checkout(self, directory: Path) -> Path:
        checkout = directory / "repo"
        (checkout / "tools").mkdir(parents=True)
        shutil.copytree(ROOT / "src", checkout / "src")
        shutil.copytree(ROOT / "schemas", checkout / "schemas")
        shutil.copytree(ROOT / "framework", checkout / "framework")
        shutil.copytree(
            ROOT / "docs" / ".concord-transition",
            checkout / "docs" / ".concord-transition",
        )
        shutil.copy2(
            ROOT / "tools" / "authorize_source_publication.py",
            checkout / "tools" / "authorize_source_publication.py",
        )
        return checkout

    def _run_generator(
        self,
        checkout: Path,
        *arguments: str,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(checkout / "src")
        return subprocess.run(
            [
                "python3",
                str(checkout / "tools" / "authorize_source_publication.py"),
                *arguments,
            ],
            cwd=checkout,
            env=environment,
            text=True,
            capture_output=True,
            check=check,
        )


if __name__ == "__main__":
    unittest.main()
