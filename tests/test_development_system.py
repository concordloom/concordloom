from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
import unittest

from concordloom.catalog import validate_catalog
from concordloom.loops import validate_registry
from concordloom.run import RunStateError, create_run_card


ROOT = Path(__file__).resolve().parents[1]
V5 = ROOT / "framework" / "concordloom" / "v5"


def load(name: str) -> dict:
    return json.loads((V5 / name).read_text(encoding="utf-8"))


class CompleteDevelopmentSystemTests(unittest.TestCase):
    def setUp(self) -> None:
        self.model = load("development-model.json")
        self.registry = load("cycle-registry.json")
        self.policy = load("policy.json")

    def test_every_development_responsibility_is_reachable_once(self) -> None:
        nodes = {node["id"]: node for node in self.model["nodes"]}
        self.assertEqual(55, len(nodes))
        self.assertEqual("steward-concordloom", self.model["root_loop_id"])
        seen: set[str] = set()

        def visit(node_id: str) -> None:
            self.assertNotIn(node_id, seen)
            seen.add(node_id)
            for child_id in nodes[node_id]["children"]:
                self.assertEqual(node_id, nodes[child_id]["parent_id"])
                visit(child_id)

        visit(self.model["root_loop_id"])
        self.assertEqual(set(nodes), seen)
        self.assertEqual(54, sum(len(node["children"]) for node in nodes.values()))

    def test_plain_bilingual_copy_and_resource_provenance_are_complete(self) -> None:
        profiles = self.model["profiles"]
        for node in self.model["nodes"]:
            for locale in ("en", "ru"):
                self.assertTrue(node["copy"][locale]["label"])
                self.assertTrue(node["copy"][locale]["purpose"])
                self.assertTrue(node["responsible_role"][locale])
            profile = profiles[node["execution_profile"]]
            self.assertEqual("planned", profile["truth_layer"])
            self.assertEqual("not-declared", profile["mcp"]["status"])
            self.assertTrue(profile["model_intent"]["en"])
            self.assertTrue(profile["model_intent"]["ru"])
            self.assertTrue(node["artifacts"])
            self.assertNotEqual(
                node["contract"]["en"]["input"],
                node["contract"]["ru"]["input"],
            )
            self.assertRegex(node["contract"]["ru"]["input"], r"[А-Яа-яЁё]")
            self.assertRegex(node["contract"]["ru"]["output"], r"[А-Яа-яЁё]")
        for phase in self.model["shared_run_grammar"]:
            self.assertNotEqual(
                phase["copy"]["en"]["purpose"],
                phase["copy"]["ru"]["purpose"],
            )
            self.assertRegex(phase["copy"]["ru"]["purpose"], r"[А-Яа-яЁё]")

    def test_comprehension_and_full_evolution_are_first_class_cycles(self) -> None:
        ids = {node["id"] for node in self.model["nodes"]}
        self.assertIn("review-comprehension", ids)
        self.assertEqual(
            [
                "collect-evolution-signals",
                "propose-successor",
                "review-successor",
                "activate-successor",
                "observe-migration",
            ],
            self.model["evolution_circuit"],
        )
        self.assertFalse(
            self.model["activation_boundary"]["self_activation_allowed"]
        )
        self.assertEqual(
            "operator only",
            self.model["activation_boundary"]["authority"],
        )

    def test_only_release_cycles_receive_external_effects(self) -> None:
        edges = self.registry["containment_graph"]["edges"]
        external = {
            edge["child_loop_id"]: edge["grant"]["scope"]["external_mutations"]
            for edge in edges
            if edge["grant"]["scope"]["external_mutations"]
        }
        self.assertEqual(
            {
                "release-distribution": [
                    "github-pages",
                    "github-repository-homepage",
                    "github-repository-social-preview",
                ],
                "publish-site": ["github-pages"],
                "maintain-repository-presence": [
                    "github-repository-homepage",
                    "github-repository-social-preview",
                ],
            },
            external,
        )
        validate_registry(self.registry, self.policy)

    def test_catalog_head_is_v5(self) -> None:
        catalog = json.loads(
            (ROOT / "framework" / "concordloom" / "catalog.json").read_text(
                encoding="utf-8"
            )
        )
        validate_catalog(catalog, artifact_root=ROOT)
        binding = load("binding.json")
        self.assertEqual(binding["binding_digest"], catalog["active_binding_digest"])
        self.assertEqual(
            "activate-concordloom-self-binding-v5",
            binding["accepted_by"]["decision_id"],
        )

    def test_default_and_adversarial_routes_enforce_direct_effect_authority(
        self,
    ) -> None:
        binding = load("binding.json")
        manifest = {
            "kind": "concordloom.candidate-manifest",
            "schema_version": "0.1",
            "id": "route-contract-candidate",
            "generated_at": "2026-07-27T13:50:00Z",
            "revision": "a" * 40,
            "tree_digest": "sha256:" + ("b" * 64),
            "dirty": False,
            "files": [],
        }
        card = create_run_card(
            binding,
            self.registry,
            self.policy,
            manifest,
            run_id="route-contract",
            root_loop_id="steward-concordloom",
            candidate_author_principal_ids=["example-executor"],
        )
        routes = {item["loop_id"]: item for item in card["planned_route"]}
        external = {
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
            },
            external,
        )
        self.assertEqual("publisher", routes["publish-site"]["role"])
        self.assertEqual(
            "publisher",
            routes["maintain-repository-presence"]["role"],
        )
        self.assertEqual("operator", routes["activate-successor"]["role"])
        self.assertEqual("reviewer", routes["review-comprehension"]["role"])
        self.assertEqual([], routes["release-distribution"]["scope"]["external_mutations"])
        self.assertEqual([], routes["steward-concordloom"]["scope"]["external_mutations"])

        broad_research = deepcopy(card["planned_route"])
        next(
            route
            for route in broad_research
            if route["loop_id"] == "research-theory"
        )["scope"] = deepcopy(self.policy["execution"]["default_scope"])
        with self.assertRaisesRegex(RunStateError, "containment grant"):
            create_run_card(
                binding,
                self.registry,
                self.policy,
                manifest,
                run_id="adversarial-external-route",
                root_loop_id="steward-concordloom",
                candidate_author_principal_ids=["example-executor"],
                planned_route=broad_research,
            )

        executor_activation = deepcopy(card["planned_route"])
        next(
            route
            for route in executor_activation
            if route["loop_id"] == "activate-successor"
        )["role"] = "executor"
        with self.assertRaisesRegex(RunStateError, "routing capability"):
            create_run_card(
                binding,
                self.registry,
                self.policy,
                manifest,
                run_id="adversarial-activation-route",
                root_loop_id="steward-concordloom",
                candidate_author_principal_ids=["example-executor"],
                planned_route=executor_activation,
            )


if __name__ == "__main__":
    unittest.main()
