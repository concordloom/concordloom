from __future__ import annotations

import json
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from concordloom.canonical import canonical_bytes, digest, document_digest
from concordloom.catalog import validate_catalog
from concordloom.compiler import validate_binding_proposal
from concordloom.loops import validate_registry


ROOT = Path(__file__).resolve().parents[1]
FRAMEWORK = ROOT / "framework" / "concordloom"
V3 = FRAMEWORK / "v3"
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
EVOLUTION_PROPOSAL_DIGEST = (
    "sha256:2b6baf9e3d8b917224c29c28ca753acd06f4617e9a11ad0a5b6c776c10914dbc"
)
MATERIALIZED_FILES = {
    "binding-proposal.json",
    "cycle-registry.json",
    "development-model.json",
    "evolution-history.json",
    "loop-design.json",
    "policy.json",
    "publication-route.json",
}
ACTIVATION_FILES = {
    "activation-receipt.json",
    "binding.json",
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class TaskRouteReceiptSerializationTests(unittest.TestCase):
    def test_noncanonical_receipt_bytes_are_rejected(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "materialize_task_route", ROOT / "tools" / "materialize_task_route.py"
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "receipt.json"
            path.write_text('{\n  "kind": "receipt"\n}\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "exact canonical JSON"):
                module._load_canonical_receipt(path, label="test")


class TaskRouteMaterializationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        missing = sorted(name for name in MATERIALIZED_FILES if not (V10 / name).is_file())
        if missing:
            raise unittest.SkipTest("v10 remains proposal-only")
        cls.graph = load(V3 / "accepted-project-graph.json")
        cls.decisions = load(V3 / "decision-log.json")
        cls.design_proposal = load(V10 / "loop-design-proposal.json")
        cls.design = load(V10 / "loop-design.json")
        cls.evolution = load(V10 / "evolution-proposal.json")
        cls.registry = load(V10 / "cycle-registry.json")
        cls.policy = load(V10 / "policy.json")
        cls.model = load(V10 / "development-model.json")
        cls.history = load(V10 / "evolution-history.json")
        cls.proposal = load(V10 / "binding-proposal.json")
        cls.publication_route = load(V10 / "publication-route.json")
        cls.binding = load(V10 / "binding.json")
        cls.activation_receipt = load(V10 / "activation-receipt.json")

    def test_completed_lifecycle_preserves_non_authorizing_source_proposals(self) -> None:
        present = {path.name for path in V10.iterdir()}
        self.assertEqual(
            MATERIALIZED_FILES
            | {"evolution-proposal.json", "loop-design-proposal.json"}
            | ACTIVATION_FILES,
            present,
        )
        catalog = load(FRAMEWORK / "catalog.json")
        validate_catalog(catalog, artifact_root=ROOT)
        self.assertEqual(ACTIVE_BINDING_DIGEST, catalog["active_binding_digest"])
        self.assertEqual(
            {
                "binding_digest": ACTIVE_BINDING_DIGEST,
                "binding_id": "concordloom-self-binding-v10",
                "path": "framework/concordloom/v10/binding.json",
                "previous_binding_digest": BASE_BINDING_DIGEST,
            },
            {
                key: catalog["entries"][-1][key]
                for key in (
                    "binding_digest",
                    "binding_id",
                    "path",
                    "previous_binding_digest",
                )
            },
        )
        self.assertEqual(ACTIVE_BINDING_DIGEST, self.binding["binding_digest"])
        self.assertEqual(BASE_BINDING_DIGEST, self.binding["predecessor_binding_digest"])
        self.assertEqual(
            BINDING_PROPOSAL_DIGEST,
            self.binding["accepted_by"]["proposal_digest"],
        )
        self.assertEqual(
            "activate-v10-task-route",
            self.binding["accepted_by"]["decision_id"],
        )
        self.assertEqual(ACTIVE_BINDING_DIGEST, self.activation_receipt["binding_digest"])
        self.assertEqual(
            BINDING_PROPOSAL_DIGEST,
            self.activation_receipt["binding_proposal_digest"],
        )
        self.assertEqual("proposed", self.proposal["status"])
        self.assertTrue(self.proposal["activation_required"])
        self.assertEqual(BASE_BINDING_DIGEST, self.proposal["predecessor_binding_digest"])
        self.assertEqual("proposed", self.evolution["status"])
        self.assertTrue(self.evolution["decision_required"])
        self.assertFalse(self.evolution["activation_allowed"])

    def test_registry_is_exact_valid_successor_with_least_privilege_route(self) -> None:
        validate_registry(self.registry, self.policy)
        self.assertEqual(66, len(self.registry["loops"]))
        self.assertEqual(65, len(self.registry["containment_graph"]["edges"]))
        self.assertEqual(["steward-concordloom"], self.registry["containment_graph"]["roots"])
        route = next(loop for loop in self.registry["loops"] if loop["id"] == "plan-task-route")
        self.assertEqual("route-run", route["authority"]["execute_capability"])
        edge = next(
            item
            for item in self.registry["containment_graph"]["edges"]
            if item["id"] == "runtime-tooling.plan-task-route"
        )
        self.assertEqual(
            ["accept-parent", "escalate", "route-run"],
            edge["grant"]["capabilities"],
        )
        self.assertEqual([], edge["grant"]["scope"]["write_paths"])
        self.assertEqual("none", edge["grant"]["scope"]["network"])
        self.assertEqual([], edge["grant"]["scope"]["external_mutations"])
        self.assertNotIn(".concord/runs", edge["grant"]["scope"]["read_paths"])

        replacement = self.evolution["operations"][2]["value"]
        lifecycle = next(
            item
            for item in self.registry["containment_graph"]["edges"]
            if item["id"] == "runtime-tooling.operate-run-lifecycle"
        )
        self.assertEqual(replacement, lifecycle)
        parent = next(
            item
            for item in self.registry["containment_graph"]["edges"]
            if item["id"] == "steward-concordloom.runtime-tooling"
        )
        old_parent = next(
            item
            for item in load(V9 / "cycle-registry.json")["containment_graph"]["edges"]
            if item["id"] == "steward-concordloom.runtime-tooling"
        )
        for mode in ("read_paths", "write_paths"):
            self.assertEqual(
                {"src/concordloom/route.py", "src/concordloom/schema.py"},
                set(parent["grant"]["scope"][mode])
                - set(old_parent["grant"]["scope"][mode]),
            )
        self.assertEqual("none", parent["grant"]["scope"]["network"])
        self.assertEqual([], parent["grant"]["scope"]["external_mutations"])

    def test_model_records_deterministic_route_and_optional_luna_selector(self) -> None:
        self.assertEqual(66, len(self.model["nodes"]))
        node = next(item for item in self.model["nodes"] if item["id"] == "plan-task-route")
        self.assertEqual("route-planning", node["execution_profile"])
        profile = self.model["profiles"]["route-planning"]
        self.assertEqual("none", profile["route_materialization"]["model"])
        self.assertEqual(
            "deterministic", profile["route_materialization"]["reasoning"]
        )
        self.assertEqual(
            ["route-compiler"],
            profile["route_materialization"]["tool_capabilities"],
        )
        deterministic = node["route_materialization"]
        self.assertEqual("none", deterministic["model"])
        self.assertEqual("deterministic", deterministic["reasoning"])
        self.assertEqual(["route-compiler"], deterministic["tool_capabilities"])
        semantic = node["route_variants"]["semantic_target_selection"]
        self.assertTrue(semantic["optional"])
        self.assertEqual("openai", semantic["model_provider"])
        self.assertEqual("gpt-5.6-luna", semantic["model"])
        self.assertEqual("low", semantic["reasoning"])
        self.assertEqual("require-explicit-target-loop", semantic["fallback"])

    def test_history_binds_both_decisions_and_publication_route(self) -> None:
        receipts = {item["kind"]: item for item in self.history["decisions"]}
        self.assertEqual(
            "sha256:14af14a4a3eb9310fcf28586ca676c297ebe242af753324b796898ed457bdbc4",
            receipts["accept-loop-design"]["receipt_digest"],
        )
        self.assertEqual(
            "sha256:12883b0cd7a53a47660ce01e5cf981bbc02eb5a874c75c5676065d94c157a56f",
            receipts["decide-evolution"]["receipt_digest"],
        )
        self.assertEqual(
            self.design["accepted_by"]["decision_id"],
            receipts["accept-loop-design"]["id"],
        )
        self.assertEqual(
            EVOLUTION_PROPOSAL_DIGEST,
            self.history["evolution_proposal"]["digest"],
        )
        self.assertEqual(digest(self.publication_route), self.history["publication_route"]["digest"])
        self.assertFalse(self.history["activation_allowed"])

    def test_binding_proposal_validates_exact_source_artifacts(self) -> None:
        validate_binding_proposal(
            self.proposal,
            self.graph,
            self.decisions,
            self.design_proposal,
            self.design,
            self.registry,
            self.policy,
            extra_artifacts={
                "atlas_input": (
                    "framework/concordloom/v10/development-model.json",
                    self.model,
                ),
                "evolution_history": (
                    "framework/concordloom/v10/evolution-history.json",
                    self.history,
                ),
            },
        )
        self.assertEqual(
            self.proposal["proposal_digest"],
            document_digest(
                self.proposal,
                excluded_fields=self.proposal["digest_contract"]["excluded_fields"],
            ),
        )
        self.assertEqual(
            {
                "accepted_project_graph",
                "decision_log",
                "loop_design_proposal",
                "accepted_loop_design",
                "cycle_registry",
                "policy",
                "evolution_history",
                "atlas_input",
            },
            {artifact["role"] for artifact in self.proposal["artifacts"]},
        )

    def test_publication_route_is_preserved_and_validated_separately(self) -> None:
        self.assertEqual(load(V9 / "publication-route.json"), self.publication_route)
        self.assertTrue(self.publication_route)
        for node in self.publication_route:
            self.assertIn("loop_id", node)
            self.assertIn("scope", node)
            scope = node["scope"]
            self.assertIn(scope["network"], {"none", "write"})
            self.assertIsInstance(scope["external_mutations"], list)
            if scope["network"] == "write":
                self.assertTrue(scope["external_mutations"])

    def test_check_mode_and_tampered_decision_fail_closed(self) -> None:
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(ROOT / "src")
        checked = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "materialize_task_route.py"), "--check"],
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=True,
        )
        self.assertIn("TASK_ROUTE_MATERIALIZATION_CHECK_OK", checked.stdout)

        receipt = {
            "activation_allowed": False,
            "authority_ref": "operator",
            "base_binding_digest": BASE_BINDING_DIGEST,
            "candidate_manifest_digest": self.history["candidate_manifest_digest"],
            "candidate_tree_digest": self.history["candidate_tree_digest"],
            "capability": "decide-evolution",
            "decided_at": "2026-08-02T15:55:00Z",
            "evolution_proposal_digest": EVOLUTION_PROPOSAL_DIGEST,
            "id": "accept-v10-task-route-evolution-r2",
            "kind": "concordloom.evolution-decision",
            "principal": {"id": "example-operator", "kind": "human"},
            "rationale": (
                "Accept the exact revised non-activating v10 evolution with "
                "explicit CAS for both authority scope replacements. Activation "
                "remains a separate decision after independent review."
            ),
            "schema_version": "0.1",
            "verdict": "accepted",
        }
        receipt["receipt_digest"] = digest(receipt)
        self.assertEqual(
            self.history["decisions"][0]["receipt_digest"],
            receipt["receipt_digest"],
        )
        receipt["candidate_tree_digest"] = "sha256:" + ("f" * 64)
        payload = dict(receipt)
        payload.pop("receipt_digest")
        receipt["receipt_digest"] = digest(payload)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "tampered-evolution-decision.json"
            path.write_bytes(canonical_bytes(receipt) + b"\n")
            rejected = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "materialize_task_route.py"),
                    "--check",
                    "--evolution-decision",
                    str(path),
                ],
                cwd=ROOT,
                env=environment,
                text=True,
                capture_output=True,
            )
        self.assertNotEqual(0, rejected.returncode)
        self.assertIn("candidate_tree_digest", rejected.stdout + rejected.stderr)

        missing_inputs = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "materialize_task_route.py")],
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(0, missing_inputs.returncode)
        message = missing_inputs.stdout + missing_inputs.stderr
        for flag in (
            "--design-decision",
            "--evolution-decision",
            "--candidate-manifest",
        ):
            self.assertIn(flag, message)


if __name__ == "__main__":
    unittest.main()
