from __future__ import annotations

import json
from pathlib import Path
import re
import unittest

from concordloom.canonical import digest, document_digest, load
from concordloom.catalog import validate_catalog
from concordloom.graph import apply_decisions
from concordloom.evolution import validate_evolution_proposal
from concordloom.loops import validate_loop_design, validate_registry
from concordloom.run import validate_binding
from concordloom.schema import SchemaStore


ROOT = Path(__file__).resolve().parents[1]


class PublicContractTests(unittest.TestCase):
    def test_every_json_file_parses(self) -> None:
        roots = ["schemas", "framework", "examples", "plugins", ".agents"]
        paths = sorted(
            path
            for name in roots
            for path in (ROOT / name).rglob("*.json")
            if path.is_file()
        )
        self.assertGreaterEqual(len(paths), 10)
        for path in paths:
            with self.subTest(path=path.relative_to(ROOT)):
                json.loads(path.read_text(encoding="utf-8"))

    def test_no_product_specific_engine_contracts(self) -> None:
        forbidden = ("player_visible_outcome", "gameplay", "engine_version")
        for path in (ROOT / "schemas").glob("*.json"):
            text = path.read_text(encoding="utf-8").lower()
            for token in forbidden:
                self.assertNotIn(token, text)

    def test_schema_ids_are_public_and_product_clean(self) -> None:
        for path in (ROOT / "schemas").glob("*.schema.json"):
            payload = json.loads(path.read_text(encoding="utf-8"))
            schema_id = payload.get("$id", "")
            self.assertTrue(schema_id.startswith("https://concordloom.dev/"))

    def test_onboarding_adapter_actor_kinds_match_the_public_schema(self) -> None:
        common = load(ROOT / "schemas/common.schema.json")
        allowed = set(
            common["$defs"]["actor"]["properties"]["kind"]["enum"]
        )
        adapter = (
            ROOT
            / "plugins"
            / "concordloom"
            / "skills"
            / "design-project-loops"
            / "scripts"
            / "record_answer.py"
        ).read_text(encoding="utf-8")
        documented = set(
            re.findall(
                r'"--actor-kind",\s*"([a-z][a-z0-9_-]*)"',
                adapter,
                flags=re.DOTALL,
            )
        )
        self.assertTrue(documented)
        self.assertLessEqual(documented, allowed)

    def test_quickstart_keeps_actor_kinds_out_of_the_beginner_path(self) -> None:
        quickstart = (ROOT / "docs/QUICKSTART.md").read_text(encoding="utf-8")
        self.assertNotIn("--actor-kind", quickstart)

    def test_generic_example_has_a_real_unmodified_digest_chain(self) -> None:
        example = ROOT / "framework" / "generic-sdlc"
        documents = {
            path.name: load(path)
            for path in sorted(example.glob("*.json"))
        }
        store = SchemaStore()
        for name, document in documents.items():
            with self.subTest(name=name):
                store.validate_public(document)

        observed = documents["observed-project-graph.json"]
        questions = documents["questions.json"]
        decisions = documents["decision-log.json"]
        accepted = documents["accepted-project-graph.json"]
        design_proposal = documents["loop-design-proposal.json"]
        design = documents["loop-design.json"]
        policy = documents["policy.json"]
        registry = documents["cycle-registry.json"]
        binding_proposal = documents["binding-proposal.json"]
        binding = documents["binding.json"]
        catalog = documents["catalog.json"]
        evolution_proposal = documents["evolution-proposal.json"]

        self.assertEqual(questions["source_graph_digest"], digest(observed))
        self.assertEqual(decisions["source_graph_digest"], digest(observed))
        self.assertEqual(decisions["authority_policy_digest"], digest(policy))
        self.assertEqual(accepted["decision_log_digest"], digest(decisions))
        self.assertEqual(accepted, apply_decisions(observed, decisions, policy))
        self.assertEqual(design_proposal["source_graph_digest"], digest(accepted))
        self.assertEqual(design["proposal_digest"], digest(design_proposal))
        self.assertNotIn(
            design["accepted_by"]["decision_id"],
            {item["id"] for item in decisions["decisions"]},
        )
        validate_loop_design(
            design,
            decisions,
            policy,
            proposal=design_proposal,
            accepted_graph=accepted,
            schema_store=store,
        )
        validate_registry(registry, policy, schema_store=store)
        self.assertEqual(
            binding_proposal["proposal_digest"],
            document_digest(
                binding_proposal,
                excluded_fields=binding_proposal["digest_contract"][
                    "excluded_fields"
                ],
            ),
        )
        self.assertEqual(
            binding["accepted_by"]["proposal_digest"],
            binding_proposal["proposal_digest"],
        )
        for artifact in binding["artifacts"]:
            self.assertEqual(
                artifact["digest"],
                digest(load(ROOT / artifact["path"])),
                artifact["role"],
            )
        validate_binding(binding, registry, policy, schema_store=store)
        validate_catalog(catalog, artifact_root=ROOT, schema_store=store)
        validate_evolution_proposal(
            evolution_proposal,
            policy,
            base_binding=binding,
        )


if __name__ == "__main__":
    unittest.main()
