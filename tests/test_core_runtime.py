from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from concordloom.canonical import digest, dumps, load
from concordloom.compiler import (
    activate_binding,
    compile_registry,
    create_binding_proposal,
    propose_loop_design,
)
from concordloom.loops import InvariantError, validate_loop_design, validate_registry
from concordloom.run import (
    RunStateError,
    authorize_run,
    build_candidate_manifest,
    complete_node,
    create_run_card,
    record_attempt,
    record_evidence,
    verify_candidate_manifest,
)
from concordloom.schema import SchemaError, SchemaStore, ValidationError


ROOT = Path(__file__).resolve().parents[1]
NOW = "2026-07-24T10:00:00Z"


def documents() -> tuple[dict, dict, dict, dict]:
    policy = load(ROOT / "framework/generic-sdlc/policy.json")
    decisions = load(ROOT / "framework/generic-sdlc/decision-log.json")
    graph = load(ROOT / "framework/generic-sdlc/accepted-project-graph.json")
    design = load(ROOT / "framework/generic-sdlc/loop-design.json")
    return graph, decisions, design, policy


def compiled() -> tuple[dict, dict, dict, dict, dict]:
    graph, decisions, design, policy = documents()
    registry = compile_registry(
        graph,
        decisions,
        design,
        policy,
        loop_design_proposal=load(
            ROOT / "framework/generic-sdlc/loop-design-proposal.json"
        ),
    )
    return graph, decisions, design, policy, registry


def binding_for(graph: dict, decisions: dict, design: dict, policy: dict, registry: dict) -> dict:
    design_proposal = load(
        ROOT / "framework/generic-sdlc/loop-design-proposal.json"
    )
    proposal = create_binding_proposal(
        graph,
        decisions,
        design,
        registry,
        policy,
        loop_design_proposal=design_proposal,
        artifact_paths={
            "accepted_project_graph": "framework/accepted-project-graph.json",
            "decision_log": "framework/decision-log.json",
            "loop_design_proposal": "framework/loop-design-proposal.json",
            "accepted_loop_design": "framework/loop-design.json",
            "cycle_registry": "framework/cycle-registry.json",
            "policy": "framework/policy.json",
        },
        proposal_id="test-binding-proposal",
        created_at=NOW,
    )
    return activate_binding(
        proposal,
        graph,
        decisions,
        design_proposal,
        design,
        registry,
        policy,
        activation_decision={
            "decision_id": "accept-nested-sdlc",
            "actor": {"id": "example-operator", "kind": "operator"},
            "authority_ref": "operator",
            "accepted_at": NOW,
            "rationale": "Activate this exact test proposal.",
        },
        binding_id="test-binding",
    )


class CoreRuntimeTests(unittest.TestCase):
    def test_canonical_json_is_stable_and_interoperable(self) -> None:
        self.assertEqual(
            dumps({"z": 1.0, "tiny": 1e-6, "large": 1e20}),
            '{"large":100000000000000000000,"tiny":0.000001,"z":1}',
        )
        self.assertEqual(digest({"a": 1}), digest(json.loads('{"a":1}')))

    def test_schema_subset_fails_closed(self) -> None:
        store = SchemaStore()
        with self.assertRaises(SchemaError):
            store.validate({}, {"type": "object", "unevaluatedProperties": False})
        policy = documents()[3]
        policy["unexpected"] = True
        with self.assertRaises(ValidationError):
            store.validate_public(policy)

    def test_compile_requires_accepted_design_and_rejects_containment_cycle(self) -> None:
        graph, decisions, design, policy = documents()
        proposal = propose_loop_design(graph, decisions, policy)
        with self.assertRaises(ValidationError):
            compile_registry(
                graph,
                decisions,
                proposal,
                policy,
                loop_design_proposal=proposal,
            )
        cyclic = deepcopy(design)
        cyclic["containment"].append(
            {
                "id": "testing-delivery",
                "parent_loop_id": "testing",
                "child_loop_id": "delivery",
                "decision_id": "accept-nested-sdlc",
            }
        )
        with self.assertRaises(InvariantError):
            validate_loop_design(
                cyclic,
                decisions,
                policy,
                proposal=load(
                    ROOT / "framework/generic-sdlc/loop-design-proposal.json"
                ),
                accepted_graph=graph,
            )

    def test_compile_preserves_the_operator_accepted_child_sequence(self) -> None:
        _, _, design, _, registry = compiled()
        expected = [
            edge["id"]
            for edge in design["containment"]
            if edge["parent_loop_id"] == "delivery"
        ]
        actual_edges = [
            edge["id"]
            for edge in registry["containment_graph"]["edges"]
            if edge["parent_loop_id"] == "delivery"
        ]
        delivery = next(
            loop for loop in registry["loops"] if loop["id"] == "delivery"
        )
        actual_states = [
            state["invocation_id"]
            for state in delivery["local_control_flow"]["states"]
            if state["kind"] == "child"
        ]
        self.assertEqual(actual_edges, expected)
        self.assertEqual(actual_states, expected)

    def test_unbudgeted_scc_and_nested_authority_escalation_are_rejected(self) -> None:
        *_, policy, registry = compiled()
        unbounded = deepcopy(registry)
        testing = next(loop for loop in unbounded["loops"] if loop["id"] == "testing")
        retry = next(
            edge
            for edge in testing["local_control_flow"]["transitions"]
            if edge["id"] == "retry"
        )
        retry["kind"] = "progress"
        retry.pop("feedback_budget")
        with self.assertRaises(InvariantError):
            validate_registry(unbounded, policy)

        broader = deepcopy(registry)
        parent = next(
            edge
            for edge in broader["containment_graph"]["edges"]
            if edge["id"] == "delivery-testing"
        )
        parent["grant"]["scope"]["read_paths"] = ["src"]
        parent["grant"]["scope"]["write_paths"] = ["src"]
        with self.assertRaises(InvariantError):
            validate_registry(broader, policy)

    def test_binding_is_content_addressed(self) -> None:
        graph, decisions, design, policy, registry = compiled()
        binding = binding_for(graph, decisions, design, policy, registry)
        expected = binding["binding_digest"]
        changed = deepcopy(binding)
        changed["id"] = "changed-binding"
        self.assertNotEqual(
            expected,
            digest({key: value for key, value in changed.items() if key != "binding_digest"}),
        )

    def test_candidate_manifest_detects_content_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
            (root / "service.py").write_text("answer = 42\n", encoding="utf-8")
            subprocess.run(["git", "add", "service.py"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-m", "seed"], cwd=root, check=True, capture_output=True)
            (root / "scenario.txt").write_text("smoke\n", encoding="utf-8")
            manifest = build_candidate_manifest(
                root, include_untracked=["scenario.txt"], generated_at=NOW
            )
            self.assertEqual(verify_candidate_manifest(root, manifest), manifest["tree_digest"])
            (root / "service.py").write_text("answer = 0\n", encoding="utf-8")
            with self.assertRaises(RunStateError):
                verify_candidate_manifest(root, manifest)

    def test_independent_gate_rejects_candidate_author(self) -> None:
        graph, decisions, design, policy, registry = compiled()
        binding = binding_for(graph, decisions, design, policy, registry)
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            root = parent / "repository"
            root.mkdir()
            subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
            (root / "service.py").write_text("answer = 42\n", encoding="utf-8")
            subprocess.run(["git", "add", "service.py"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-m", "seed"], cwd=root, check=True, capture_output=True)
            manifest = build_candidate_manifest(root, generated_at=NOW)
            card = create_run_card(
                binding,
                registry,
                policy,
                manifest,
                run_id="test-run",
                root_loop_id="delivery",
                candidate_author_principal_ids=["example-executor"],
            )
            card = authorize_run(
                card,
                binding,
                registry,
                policy,
                manifest,
                actor={"id": "example-operator", "kind": "operator"},
                authority_ref="operator",
                authorized_at=NOW,
                repository=root,
            )
            card = record_attempt(
                card,
                policy,
                manifest,
                node_id="testing",
                attempt_id="testing-attempt",
                started_at=NOW,
                finished_at=NOW,
                effective_principal_id="example-reviewer",
                effective_agent="review-agent",
                effective_model="none",
                effective_reasoning="deterministic",
                effective_skill="review",
                effective_tools=["python"],
                result="pass",
                repository=root,
            )
            evidence = {
                "kind": "concordloom.evidence",
                "schema_version": "0.1",
                "id": "testing-evidence",
                "run_id": "test-run",
                "node_id": "testing",
                "loop_id": "testing",
                "contract_id": "testing-acceptance",
                "attempt_id": "testing-attempt",
                "binding_digest": binding["binding_digest"],
                "policy_digest": digest(policy),
                "candidate": {
                    "tree_digest": manifest["tree_digest"],
                    "manifest_digest": digest(manifest),
                    "artifact_digests": [],
                },
                "producer": {"id": "example-reviewer", "kind": "reviewer"},
                "effective_route": {
                    "principal_id": "example-reviewer",
                    "agent": "review-agent",
                    "model": "none",
                    "reasoning": "deterministic",
                    "skill": "review",
                    "subagents": [],
                    "tools": ["python"],
                    "data_egress": {
                        "provider": "",
                        "path_prefixes": [],
                        "content_classes": [],
                    },
                },
                "started_at": NOW,
                "finished_at": NOW,
                "result": "pass",
                "claims": [
                    {
                        "id": "testing-outcome",
                        "statement": "Pinned candidate passed.",
                        "result": "pass",
                    }
                ],
                "provenance": [{"kind": "command", "ref": "python -m unittest"}],
                "payload": {
                    "format": "json",
                    "path": "evidence/testing.json",
                    "digest": "sha256:" + ("a" * 64),
                },
            }
            payload_root = parent / "payloads"
            payload = payload_root / evidence["payload"]["path"]
            payload.parent.mkdir(parents=True)
            payload_bytes = b'{"passed":true}\n'
            payload.write_bytes(payload_bytes)
            evidence["payload"]["digest"] = (
                "sha256:" + sha256(payload_bytes).hexdigest()
            )
            author_evidence = deepcopy(evidence)
            author_evidence["producer"] = {"id": "example-executor", "kind": "executor"}
            author_evidence["effective_route"]["principal_id"] = "example-executor"
            with self.assertRaises(RunStateError):
                record_evidence(
                    card,
                    author_evidence,
                    registry,
                    policy,
                    manifest,
                    payload_root=payload_root,
                    repository=root,
                )

            card = record_evidence(
                card,
                evidence,
                registry,
                policy,
                manifest,
                payload_root=payload_root,
                repository=root,
            )
            card = complete_node(
                card,
                "testing",
                registry,
                policy,
                manifest,
                {"testing-evidence": evidence},
                accepted_by={"id": "example-orchestrator", "kind": "orchestrator"},
                payload_root=payload_root,
                repository=root,
            )
            self.assertEqual(
                next(node for node in card["nodes"] if node["node_id"] == "testing")[
                    "status"
                ],
                "passed",
            )


if __name__ == "__main__":
    unittest.main()
