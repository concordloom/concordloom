from __future__ import annotations

import json
from pathlib import Path
import unittest

from concordloom.catalog import validate_catalog
from concordloom.evolution import validate_evolution_proposal
from concordloom.run import validate_binding


ROOT = Path(__file__).resolve().parents[1]
TRANSITION = ROOT / "docs" / ".concord-transition"
FRAMEWORK = ROOT / "framework" / "concordloom"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def active_binding() -> dict:
    catalog = load(FRAMEWORK / "catalog.json")
    entry = next(
        item
        for item in catalog["entries"]
        if item["binding_digest"] == catalog["active_binding_digest"]
    )
    return load(ROOT / entry["path"])


class SelfHostingEvolutionTests(unittest.TestCase):
    def test_successor_closes_original_scope_deadlock(self) -> None:
        original = load(ROOT / "framework" / "generic-sdlc" / "policy.json")
        successor = load(FRAMEWORK / "policy.json")

        original_scope = original["execution"]["default_scope"]
        successor_scope = successor["execution"]["default_scope"]
        self.assertNotIn("framework", original_scope["write_paths"])
        self.assertEqual(original_scope["network"], "none")
        self.assertEqual(original_scope["external_mutations"], [])

        self.assertIn("framework", successor_scope["write_paths"])
        self.assertIn(".github", successor_scope["write_paths"])
        self.assertEqual(successor_scope["network"], "write")
        self.assertEqual(successor_scope["external_mutations"], ["github-pages"])

    def test_evolution_proposal_cannot_activate_itself(self) -> None:
        predecessor = load(TRANSITION / "binding.json")
        policy = load(FRAMEWORK / "policy.json")
        proposal = load(FRAMEWORK / "evolution-proposal.json")

        validate_evolution_proposal(
            proposal,
            policy,
            base_binding=predecessor,
        )
        self.assertTrue(proposal["decision_required"])
        self.assertFalse(proposal["activation_allowed"])
        self.assertEqual(proposal["decision_authority_ref"], "operator")
        self.assertGreaterEqual(len(proposal["signals"]), 2)

    def test_durable_binding_is_valid_and_chained(self) -> None:
        predecessor = load(TRANSITION / "binding.json")
        binding = load(FRAMEWORK / "binding.json")
        registry = load(FRAMEWORK / "cycle-registry.json")
        policy = load(FRAMEWORK / "policy.json")

        validate_binding(binding, registry, policy)
        self.assertEqual(
            binding["predecessor_binding_digest"],
            predecessor["binding_digest"],
        )
        self.assertEqual(binding["active_root_loop_ids"], ["concord-change"])
        self.assertNotEqual(
            binding["accepted_by"]["decision_id"],
            load(FRAMEWORK / "evolution-proposal.json")["id"],
        )

    def test_catalog_and_atlas_point_to_exact_active_binding(self) -> None:
        catalog = load(FRAMEWORK / "catalog.json")
        validate_catalog(catalog, artifact_root=ROOT)
        binding = active_binding()
        atlas = load(ROOT / "site" / "data" / "atlas.json")

        self.assertEqual(catalog["active_binding_digest"], binding["binding_digest"])
        self.assertEqual(atlas["binding"]["digest"], binding["binding_digest"])
        self.assertEqual(atlas["binding"]["rootLoopIds"], ["steward-concordloom"])

    def test_verification_is_independent_and_publication_is_scoped(self) -> None:
        policy = load(FRAMEWORK / "policy.json")
        route = load(TRANSITION / "hype-route.json")
        separation = policy["authority"]["separation_rules"]
        self.assertEqual(separation[0]["applies_to_loop_ids"], ["verify"])

        nodes = {node["node_id"]: node for node in route}
        self.assertEqual(nodes["verify"]["role"], "reviewer")
        self.assertEqual(nodes["verify"]["scope"]["write_paths"], [])
        self.assertEqual(nodes["publish"]["role"], "publisher")
        self.assertEqual(
            nodes["publish"]["scope"]["external_mutations"],
            ["github-pages"],
        )
        self.assertEqual(nodes["execute"]["scope"]["external_mutations"], [])

    def test_repository_preview_is_a_separate_publisher_effect(self) -> None:
        predecessor = load(FRAMEWORK / "binding.json")
        binding = load(FRAMEWORK / "v3" / "binding.json")
        policy = load(FRAMEWORK / "v3" / "policy.json")
        proposal = load(FRAMEWORK / "v3" / "evolution-proposal.json")
        registry = load(FRAMEWORK / "v3" / "cycle-registry.json")
        route = load(FRAMEWORK / "v3" / "publication-route.json")

        self.assertEqual(binding["predecessor_binding_digest"], predecessor["binding_digest"])
        self.assertFalse(proposal["activation_allowed"])
        self.assertEqual(
            policy["execution"]["default_scope"]["external_mutations"],
            ["github-pages", "github-repository-social-preview"],
        )
        edges = {
            edge["child_loop_id"]: edge
            for edge in registry["containment_graph"]["edges"]
        }
        for child_id, edge in edges.items():
            scope = edge["grant"]["scope"]
            if child_id == "publish":
                self.assertEqual(scope["network"], "write")
                self.assertEqual(
                    scope["external_mutations"],
                    ["github-pages", "github-repository-social-preview"],
                )
            else:
                self.assertEqual(scope["network"], "none")
                self.assertEqual(scope["external_mutations"], [])

        nodes = {node["node_id"]: node for node in route}
        self.assertEqual(set(nodes), {"concord-change", "publish"})
        self.assertEqual(nodes["publish"]["role"], "publisher")
        self.assertEqual(nodes["concord-change"]["scope"]["external_mutations"], [])
        self.assertEqual(nodes["concord-change"]["scope"]["network"], "none")
        self.assertEqual(
            nodes["publish"]["scope"]["external_mutations"],
            ["github-pages", "github-repository-social-preview"],
        )

    def test_repository_homepage_is_a_separate_publisher_effect(self) -> None:
        predecessor = load(FRAMEWORK / "v3" / "binding.json")
        binding = load(FRAMEWORK / "v4" / "binding.json")
        policy = load(FRAMEWORK / "v4" / "policy.json")
        proposal = load(FRAMEWORK / "v4" / "evolution-proposal.json")
        registry = load(FRAMEWORK / "v4" / "cycle-registry.json")
        route = load(FRAMEWORK / "v4" / "publication-route.json")
        effects = [
            "github-pages",
            "github-repository-homepage",
            "github-repository-social-preview",
        ]

        self.assertEqual(binding["predecessor_binding_digest"], predecessor["binding_digest"])
        self.assertFalse(proposal["activation_allowed"])
        edges = {
            edge["child_loop_id"]: edge
            for edge in registry["containment_graph"]["edges"]
        }
        for child_id, edge in edges.items():
            scope = edge["grant"]["scope"]
            if child_id == "publish":
                self.assertEqual(scope["network"], "write")
                self.assertEqual(scope["external_mutations"], effects)
            else:
                self.assertEqual(scope["network"], "none")
                self.assertEqual(scope["external_mutations"], [])

        nodes = {node["node_id"]: node for node in route}
        self.assertEqual(nodes["concord-change"]["scope"]["external_mutations"], [])
        self.assertEqual(nodes["publish"]["role"], "publisher")
        self.assertEqual(nodes["publish"]["scope"]["external_mutations"], effects)


if __name__ == "__main__":
    unittest.main()
