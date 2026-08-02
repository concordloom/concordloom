from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from concordloom.canonical import canonical_bytes, digest, load, save
from concordloom.catalog import validate_catalog
from concordloom.run import build_candidate_manifest


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
SPEC = importlib.util.spec_from_file_location(
    "activate_task_route", TOOLS / "activate_task_route.py"
)
assert SPEC and SPEC.loader
ACTIVATION = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ACTIVATION
SPEC.loader.exec_module(ACTIVATION)


class TaskRouteActivationTests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        base = Path(self.temporary.name)
        self.repository = base / "reviewed"
        self.receipts = base / "receipts"
        self.receipts.mkdir()
        self._copy_activation_inputs(self.repository)
        self._git(self.repository, "init", "-q")
        self._git(self.repository, "config", "user.email", "test@example.com")
        self._git(self.repository, "config", "user.name", "Activation Test")
        self._git(self.repository, "add", ".")
        self._git(self.repository, "commit", "-qm", "reviewed candidate")
        self.candidate = build_candidate_manifest(
            self.repository,
            generated_at="2026-08-02T16:30:00Z",
            manifest_id="isolated-v10-reviewed-candidate",
        )
        self.candidate_path = base / "candidate.json"
        save(self.candidate_path, self.candidate)
        self.review_card = {
            "status": "authorized",
            "binding_digest": ACTIVATION.EXPECTATIONS.base_binding_digest,
            "candidate_manifest_digest": digest(self.candidate),
            "candidate_tree_digest": self.candidate["tree_digest"],
            "candidate_author_principal_ids": ["example-executor"],
            "nodes": [{"node_id": "review-successor", "status": "pending"}],
        }
        self.review_card_path = base / "review-card.json"
        save(self.review_card_path, self.review_card)
        self.expectations = ACTIVATION.ActivationExpectations(
            base_binding_digest=ACTIVATION.EXPECTATIONS.base_binding_digest,
            proposal_digest=ACTIVATION.EXPECTATIONS.proposal_digest,
            proposal_tree_digest=ACTIVATION.EXPECTATIONS.proposal_tree_digest,
            review_card_digest=digest(self.review_card),
            reviewed_manifest_digest=digest(self.candidate),
            reviewed_tree_digest=self.candidate["tree_digest"],
        )
        self.review_path, review_digest = self._write_receipt(
            "review.json",
            {
                **self._common_receipt(),
                "kind": "concordloom.review-recommendation-receipt",
                "id": "review-v10-task-route",
                "principal": {"id": "example-reviewer", "kind": "agent"},
                "capability": "review-candidate",
            },
        )
        self.evolution_path, evolution_digest = self._write_receipt(
            "evolution.json",
            {
                **self._common_receipt(),
                "kind": "concordloom.evolution-decision-receipt",
                "id": "decide-v10-task-route-receipt",
                "principal": {"id": "example-operator", "kind": "human"},
                "capability": "decide-evolution",
                "decision_id": "decide-v10-task-route",
                "review_recommendation_digest": review_digest,
            },
        )
        self.activation_path, _activation_digest = self._write_receipt(
            "activation.json",
            {
                **self._common_receipt(),
                "kind": "concordloom.activation-evidence-receipt",
                "id": "activate-v10-task-route-evidence",
                "principal": {"id": "example-operator", "kind": "human"},
                "capability": "activate-binding",
                "decision_id": "activate-v10-task-route",
                "review_recommendation_digest": review_digest,
                "evolution_decision_digest": evolution_digest,
            },
        )

    @staticmethod
    def _git(repository: Path, *args: str) -> None:
        subprocess.run(
            ["git", *args],
            cwd=repository,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    @staticmethod
    def _copy_activation_inputs(target: Path) -> None:
        shutil.copytree(ROOT / "framework" / "concordloom", target / "framework" / "concordloom")
        shutil.copytree(ROOT / "framework" / "generic-sdlc", target / "framework" / "generic-sdlc")
        shutil.copytree(
            ROOT / "docs" / ".concord-transition",
            target / "docs" / ".concord-transition",
        )
        v10 = target / "framework" / "concordloom" / "v10"
        (v10 / "binding.json").unlink(missing_ok=True)
        (v10 / "activation-receipt.json").unlink(missing_ok=True)
        catalog_path = target / "framework" / "concordloom" / "catalog.json"
        catalog = load(catalog_path)
        while catalog["entries"][-1]["binding_id"] != "concordloom-self-binding-v9":
            catalog["entries"].pop()
        catalog["active_binding_digest"] = catalog["entries"][-1]["binding_digest"]
        save(catalog_path, catalog)

    def _common_receipt(self) -> dict:
        return {
            "schema": "concordloom://activation-receipt/0.1",
            "schema_version": "0.1",
            "verdict": "pass",
            "proposal_digest": self.expectations.proposal_digest,
            "proposal_tree_digest": self.expectations.proposal_tree_digest,
            "base_binding_digest": self.expectations.base_binding_digest,
            "candidate_tree_digest": self.expectations.proposal_tree_digest,
            "candidate_author_principal_ids": ["example-executor"],
        }

    def _write_receipt(self, name: str, body: dict) -> tuple[Path, str]:
        receipt_digest = digest(body)
        path = self.receipts / name
        path.write_bytes(
            canonical_bytes({**body, "receipt_digest": receipt_digest}) + b"\n"
        )
        return path, receipt_digest

    def _activate(self, *, output_root: Path | None = None) -> dict:
        return ACTIVATION.materialize_activation(
            reviewed_repository=self.repository,
            output_root=output_root or self.repository,
            review_card_path=self.review_card_path,
            reviewed_candidate_path=self.candidate_path,
            review_recommendation_path=self.review_path,
            evolution_decision_path=self.evolution_path,
            activation_evidence_path=self.activation_path,
            accepted_proposal_digest=self.expectations.proposal_digest,
            activated_at="2026-08-02T16:35:00Z",
            expectations=self.expectations,
        )

    def test_happy_path_activates_exact_binding_and_writes_catalog_last(self) -> None:
        writes: list[str] = []
        real_save = ACTIVATION.save

        def recording_save(path: Path, value: object, *, pretty: bool = True) -> None:
            writes.append(Path(path).relative_to(self.repository).as_posix())
            real_save(path, value, pretty=pretty)

        with mock.patch.object(ACTIVATION, "save", side_effect=recording_save):
            result = self._activate()
        self.assertEqual(
            [
                "framework/concordloom/v10/binding.json",
                "framework/concordloom/v10/activation-receipt.json",
                "framework/concordloom/catalog.json",
            ],
            writes,
        )
        catalog = result["catalog"]
        binding = result["binding"]
        receipt = result["activation_receipt"]
        self.assertEqual(binding["binding_digest"], catalog["active_binding_digest"])
        self.assertEqual(self.expectations.base_binding_digest, binding["predecessor_binding_digest"])
        self.assertEqual(self.expectations.review_card_digest, receipt["review_card_digest"])
        self.assertEqual(
            self.expectations.reviewed_manifest_digest,
            receipt["reviewed_candidate_manifest_digest"],
        )
        self.assertEqual(
            self.expectations.reviewed_tree_digest,
            receipt["reviewed_candidate_tree_digest"],
        )
        validate_catalog(catalog, artifact_root=self.repository)

    def test_candidate_drift_fails_before_activation_outputs(self) -> None:
        proposal = self.repository / ACTIVATION.PROPOSAL_REL
        proposal.write_bytes(proposal.read_bytes() + b" ")
        with self.assertRaisesRegex(Exception, "candidate|changed|differ"):
            self._activate()
        self.assertFalse((self.repository / ACTIVATION.V10_BINDING_REL).exists())
        self.assertFalse((self.repository / ACTIVATION.V10_RECEIPT_REL).exists())
        self.assertEqual(
            self.expectations.base_binding_digest,
            load(self.repository / ACTIVATION.CATALOG_REL)["active_binding_digest"],
        )

    def test_noncanonical_receipt_is_rejected(self) -> None:
        document = load(self.review_path)
        save(self.review_path, document)
        with self.assertRaisesRegex(SystemExit, "not canonical"):
            self._activate()
        self.assertFalse((self.repository / ACTIVATION.V10_BINDING_REL).exists())

    def test_stale_output_catalog_head_is_rejected(self) -> None:
        output = Path(self.temporary.name) / "output"
        shutil.copytree(self.repository, output)
        catalog_path = output / ACTIVATION.CATALOG_REL
        catalog = load(catalog_path)
        catalog["active_binding_digest"] = catalog["entries"][-2]["binding_digest"]
        save(catalog_path, catalog)
        with self.assertRaisesRegex(Exception, "active binding|catalog"):
            self._activate(output_root=output)
        self.assertFalse((output / ACTIVATION.V10_BINDING_REL).exists())

    def test_output_artifact_drift_is_rejected(self) -> None:
        output = Path(self.temporary.name) / "output"
        shutil.copytree(self.repository, output)
        policy = output / "framework" / "concordloom" / "v10" / "policy.json"
        policy.write_bytes(policy.read_bytes() + b" ")
        with self.assertRaisesRegex(ACTIVATION.ActivationError, "output artifact differs"):
            self._activate(output_root=output)
        self.assertFalse((output / ACTIVATION.V10_BINDING_REL).exists())

    def test_evolution_and_activation_decision_ids_must_differ(self) -> None:
        activation = load(self.activation_path)
        activation.pop("receipt_digest")
        activation["decision_id"] = "decide-v10-task-route"
        self.activation_path, _digest = self._write_receipt(
            "activation.json", activation
        )
        with self.assertRaisesRegex(SystemExit, "decision ids must be distinct"):
            self._activate()
        self.assertFalse((self.repository / ACTIVATION.V10_BINDING_REL).exists())


if __name__ == "__main__":
    unittest.main()
