from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from concordloom.canonical import digest, document_digest, load
from concordloom.atlas import render_atlas
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


ROOT = Path(__file__).resolve().parents[1]
NOW = "2026-07-24T10:00:00Z"
OID_DIGEST = "sha256:" + ("a" * 64)


def git(repository: Path, *arguments: str) -> None:
    subprocess.run(
        ["git", *arguments],
        cwd=repository,
        check=True,
        capture_output=True,
    )


def repository_at(parent: Path) -> Path:
    root = parent / "repository"
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "Security Test")
    git(root, "config", "user.email", "security@example.invalid")
    (root / "service.py").write_text("answer = 42\n", encoding="utf-8")
    git(root, "add", "service.py")
    git(root, "commit", "-m", "seed")
    return root


def runtime_documents(
    *, remote_model: bool = False
) -> tuple[dict, dict, dict]:
    policy = load(ROOT / "framework/generic-sdlc/policy.json")
    if remote_model:
        model_policy = policy["execution"]["model_policy"]
        model_policy["allowed_providers"] = ["approved-provider"]
        model_policy["privacy"] = "approved_remote"
        model_policy["allowed_path_prefixes"] = ["docs"]
        model_policy["allowed_content_classes"] = ["source"]
        model_policy["allowed_models"].append(
            {"provider": "approved-provider", "model": "remote-model"}
        )

    contract = {
        "id": "testing-acceptance",
        "description": "Independent test evidence.",
        "required_claims": ["testing-outcome"],
        "accepted_results": ["pass"],
        "producer_capability": "produce-evidence",
        "reviewer_capability": "review-candidate",
        "independent_from_capability": "execute-work",
        "candidate_binding_required": True,
        "policy_binding_required": True,
    }
    loop = {
        "id": "testing",
        "label": "Testing",
        "purpose": "Independently test a pinned candidate.",
        "inputs": [],
        "outputs": [],
        "budgets": deepcopy(policy["execution"]["default_budgets"]),
        "authority": {
            "execute_capability": "execute-work",
            "accept_capability": "accept-parent",
            "escalate_capability": "escalate",
        },
        "local_control_flow": {
            "entry_state": "start",
            "terminal_state_ids": ["accepted"],
            "states": [
                {"id": "start", "kind": "start", "label": "Start"},
                {
                    "id": "accepted",
                    "kind": "terminal",
                    "label": "Accepted",
                    "outcome": "succeeded",
                },
            ],
            "transitions": [
                {
                    "id": "accept",
                    "from": "start",
                    "to": "accepted",
                    "kind": "success",
                    "guard": "Independent evidence passes.",
                    "evidence_contract_ids": ["testing-acceptance"],
                }
            ],
        },
    }
    registry = {
        "kind": "concordloom.cycle-registry",
        "schema_version": "0.1",
        "id": "security-registry",
        "source_graph_digest": OID_DIGEST,
        "source_decisions_digest": OID_DIGEST,
        "source_loop_design_digest": OID_DIGEST,
        "policy_digest": digest(policy),
        "evidence_contracts": [contract],
        "loops": [loop],
        "containment_graph": {"roots": ["testing"], "edges": []},
    }
    binding = {
        "kind": "concordloom.binding",
        "schema_version": "0.1",
        "id": "security-binding",
        "framework_version": "0.1.0",
        "created_at": NOW,
        "binding_digest": OID_DIGEST,
        "digest_contract": {
            "algorithm": "sha256",
            "canonicalization": "rfc8785",
            "excluded_fields": ["/binding_digest"],
        },
        "active_root_loop_ids": ["testing"],
        "artifacts": [
            {
                "role": "accepted_project_graph",
                "path": "framework/graph.json",
                "digest": OID_DIGEST,
            },
            {
                "role": "decision_log",
                "path": "framework/decisions.json",
                "digest": OID_DIGEST,
            },
            {
                "role": "loop_design_proposal",
                "path": "framework/design-proposal.json",
                "digest": OID_DIGEST,
            },
            {
                "role": "accepted_loop_design",
                "path": "framework/design.json",
                "digest": OID_DIGEST,
            },
            {
                "role": "cycle_registry",
                "path": "framework/registry.json",
                "digest": digest(registry),
            },
            {
                "role": "policy",
                "path": "framework/policy.json",
                "digest": digest(policy),
            },
        ],
        "accepted_by": {
            "decision_id": "activate-security-binding",
            "actor": {"id": "example-operator", "kind": "operator"},
            "authority_ref": "operator",
            "accepted_at": NOW,
            "proposal_digest": OID_DIGEST,
            "rationale": "Test fixture activation.",
        },
    }
    binding["binding_digest"] = document_digest(
        binding, excluded_fields=["/binding_digest"]
    )
    return binding, registry, policy


def evidence_for(
    binding: dict,
    policy: dict,
    manifest: dict,
    *,
    model: str = "none",
    provider: str = "",
    paths: list[str] | None = None,
    content_classes: list[str] | None = None,
    attempt_id: str = "attempt",
) -> dict:
    return {
        "kind": "concordloom.evidence",
        "schema_version": "0.1",
        "id": "testing-evidence",
        "run_id": "security-run",
        "node_id": "testing",
        "loop_id": "testing",
        "contract_id": "testing-acceptance",
        "attempt_id": attempt_id,
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
            "model": model,
            "reasoning": "deterministic",
            "skill": "review",
            "subagents": [],
            "tools": ["python"],
            "data_egress": {
                "provider": provider,
                "path_prefixes": paths or [],
                "content_classes": content_classes or [],
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
            "digest": OID_DIGEST,
        },
    }


def payload_at(parent: Path, evidence: dict) -> Path:
    root = parent / "payloads"
    target = root / evidence["payload"]["path"]
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = b'{"passed":true}\n'
    target.write_bytes(payload)
    evidence["payload"]["digest"] = "sha256:" + sha256(payload).hexdigest()
    return root


def running_card(
    repository: Path, *, remote_model: bool = False
) -> tuple[dict, dict, dict, dict, dict]:
    binding, registry, policy = runtime_documents(remote_model=remote_model)
    manifest = build_candidate_manifest(repository, generated_at=NOW)
    card = create_run_card(
        binding,
        registry,
        policy,
        manifest,
        run_id="security-run",
        root_loop_id="testing",
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
        repository=repository,
    )
    return card, binding, registry, policy, manifest


class CandidateManifestSecurityTests(unittest.TestCase):
    def test_manifest_disables_malicious_fsmonitor(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            repository = repository_at(parent)
            marker = parent / "fsmonitor-ran"
            hook = parent / "malicious-fsmonitor"
            hook.write_text(
                "#!/bin/sh\n: > \"$FSMONITOR_MARKER\"\n",
                encoding="utf-8",
            )
            hook.chmod(0o755)
            git(repository, "config", "core.fsmonitor", str(hook))
            previous = os.environ.get("FSMONITOR_MARKER")
            os.environ["FSMONITOR_MARKER"] = str(marker)
            try:
                build_candidate_manifest(repository, generated_at=NOW)
            finally:
                if previous is None:
                    os.environ.pop("FSMONITOR_MARKER", None)
                else:
                    os.environ["FSMONITOR_MARKER"] = previous
            self.assertFalse(marker.exists())

    def test_verify_detects_untracked_inventory_and_dirty_transition(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = repository_at(Path(temporary))
            manifest = build_candidate_manifest(repository, generated_at=NOW)
            (repository / "surprise.txt").write_text("not manifested\n")
            with self.assertRaisesRegex(RunStateError, "untracked candidate inventory"):
                verify_candidate_manifest(repository, manifest)

            (repository / "surprise.txt").unlink()
            (repository / "service.py").write_text("answer = 7\n")
            with self.assertRaisesRegex(RunStateError, "dirty state changed"):
                verify_candidate_manifest(repository, manifest)

    def test_explicit_untracked_is_stable_but_implicit_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = repository_at(Path(temporary))
            (repository / "scenario.txt").write_text("smoke\n")
            with self.assertRaisesRegex(RunStateError, "explicitly manifested"):
                build_candidate_manifest(repository, generated_at=NOW)
            manifest = build_candidate_manifest(
                repository,
                include_untracked=["scenario.txt"],
                generated_at=NOW,
            )
            self.assertEqual(
                verify_candidate_manifest(repository, manifest),
                manifest["tree_digest"],
            )
            git(repository, "add", "scenario.txt")
            with self.assertRaisesRegex(RunStateError, "mode, content, or inventory"):
                verify_candidate_manifest(repository, manifest)


class RunPolicySecurityTests(unittest.TestCase):
    def test_multiroot_route_stays_inside_the_selected_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = repository_at(Path(temporary))
            binding, registry, policy = runtime_documents()
            second_loop = deepcopy(registry["loops"][0])
            second_loop["id"] = "secondary-testing"
            second_loop["label"] = "Secondary testing"
            registry["loops"].append(second_loop)
            registry["containment_graph"]["roots"].append("secondary-testing")
            policy["authority"]["separation_rules"][0][
                "applies_to_loop_ids"
            ].append("secondary-testing")
            registry["policy_digest"] = digest(policy)
            binding["active_root_loop_ids"].append("secondary-testing")
            registry_artifact = next(
                item
                for item in binding["artifacts"]
                if item["role"] == "cycle_registry"
            )
            registry_artifact["digest"] = digest(registry)
            policy_artifact = next(
                item
                for item in binding["artifacts"]
                if item["role"] == "policy"
            )
            policy_artifact["digest"] = digest(policy)
            binding["binding_digest"] = document_digest(
                binding, excluded_fields=["/binding_digest"]
            )
            manifest = build_candidate_manifest(repository, generated_at=NOW)

            card = create_run_card(
                binding,
                registry,
                policy,
                manifest,
                run_id="selected-root-run",
                root_loop_id="testing",
                candidate_author_principal_ids=["example-executor"],
            )
            self.assertEqual(
                {item["loop_id"] for item in card["planned_route"]},
                {"testing"},
            )
            rendered = render_atlas(
                binding=binding,
                registry=registry,
                policy=policy,
                run_card=card,
            )
            self.assertIn('"default_root":"testing"', rendered)

            foreign_card = create_run_card(
                binding,
                registry,
                policy,
                manifest,
                run_id="foreign-root-run",
                root_loop_id="secondary-testing",
                candidate_author_principal_ids=["example-executor"],
            )
            with self.assertRaisesRegex(
                RunStateError, "selected run root subtree"
            ):
                create_run_card(
                    binding,
                    registry,
                    policy,
                    manifest,
                    run_id="cross-root-run",
                    root_loop_id="testing",
                    candidate_author_principal_ids=["example-executor"],
                    planned_route=[
                        *card["planned_route"],
                        *foreign_card["planned_route"],
                    ],
                )

    def test_card_scope_budget_and_role_cannot_broaden_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = repository_at(Path(temporary))
            binding, registry, policy = runtime_documents()
            manifest = build_candidate_manifest(repository, generated_at=NOW)
            broad_scope = deepcopy(policy["execution"]["default_scope"])
            broad_scope["network"] = "read"
            with self.assertRaisesRegex(RunStateError, "scope broadens"):
                create_run_card(
                    binding,
                    registry,
                    policy,
                    manifest,
                    run_id="scope-run",
                    root_loop_id="testing",
                    candidate_author_principal_ids=["example-executor"],
                    scope=broad_scope,
                )
            broad_budget = deepcopy(policy["execution"]["default_budgets"])
            broad_budget["max_attempts"] += 1
            with self.assertRaisesRegex(RunStateError, "budgets broaden"):
                create_run_card(
                    binding,
                    registry,
                    policy,
                    manifest,
                    run_id="budget-run",
                    root_loop_id="testing",
                    candidate_author_principal_ids=["example-executor"],
                    budgets=broad_budget,
                )

            valid = create_run_card(
                binding,
                registry,
                policy,
                manifest,
                run_id="valid-run",
                root_loop_id="testing",
                candidate_author_principal_ids=["example-executor"],
            )
            bad_route = deepcopy(valid["planned_route"])
            bad_route[0]["role"] = "operator"
            with self.assertRaisesRegex(RunStateError, "routing capability"):
                create_run_card(
                    binding,
                    registry,
                    policy,
                    manifest,
                    run_id="role-run",
                    root_loop_id="testing",
                    candidate_author_principal_ids=["example-executor"],
                    planned_route=bad_route,
                )

    def test_evidence_route_must_match_attempt_and_model_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = repository_at(Path(temporary))
            card, binding, registry, policy, manifest = running_card(repository)
            card = record_attempt(
                card,
                policy,
                manifest,
                node_id="testing",
                attempt_id="attempt-local",
                started_at=NOW,
                finished_at=NOW,
                effective_principal_id="example-reviewer",
                effective_agent="review-agent",
                effective_model="none",
                effective_reasoning="deterministic",
                effective_skill="review",
                effective_tools=["python"],
                result="pass",
                repository=repository,
            )
            mismatched = evidence_for(
                binding,
                policy,
                manifest,
                model="fabricated",
                attempt_id="attempt-local",
            )
            payload_root = payload_at(Path(temporary), mismatched)
            with self.assertRaisesRegex(RunStateError, "factual recorded attempt"):
                record_evidence(
                    card,
                    mismatched,
                    registry,
                    policy,
                    manifest,
                    payload_root=payload_root,
                    repository=repository,
                )

    def test_attempt_cost_time_and_model_allowlist_are_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = repository_at(Path(temporary))
            card, _, _, policy, manifest = running_card(repository)
            with self.assertRaisesRegex(RunStateError, "cost budget"):
                record_attempt(
                    card,
                    policy,
                    manifest,
                    node_id="testing",
                    attempt_id="too-expensive",
                    started_at=NOW,
                    finished_at=NOW,
                    effective_principal_id="example-reviewer",
                    effective_agent="review-agent",
                    effective_model="none",
                    effective_reasoning="deterministic",
                    effective_skill="review",
                    effective_tools=["python"],
                    cost_units=card["budgets"]["max_cost_units"] + 1,
                    result="pass",
                    repository=repository,
                )
            with self.assertRaisesRegex(RunStateError, "elapsed-time budget"):
                record_attempt(
                    card,
                    policy,
                    manifest,
                    node_id="testing",
                    attempt_id="too-slow",
                    started_at=NOW,
                    finished_at="2026-07-25T10:00:00Z",
                    effective_principal_id="example-reviewer",
                    effective_agent="review-agent",
                    effective_model="none",
                    effective_reasoning="deterministic",
                    effective_skill="review",
                    effective_tools=["python"],
                    result="pass",
                    repository=repository,
                )
            with self.assertRaisesRegex(RunStateError, "model outside"):
                record_attempt(
                    card,
                    policy,
                    manifest,
                    node_id="testing",
                    attempt_id="unknown-model",
                    started_at=NOW,
                    finished_at=NOW,
                    effective_principal_id="example-reviewer",
                    effective_agent="review-agent",
                    effective_model="unbound-model",
                    effective_reasoning="deterministic",
                    effective_skill="review",
                    effective_tools=["python"],
                    result="pass",
                    repository=repository,
                )

    def test_payload_digest_is_checked_against_real_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            repository = repository_at(parent)
            card, binding, registry, policy, manifest = running_card(repository)
            card = record_attempt(
                card,
                policy,
                manifest,
                node_id="testing",
                attempt_id="attempt",
                started_at=NOW,
                finished_at=NOW,
                effective_principal_id="example-reviewer",
                effective_agent="review-agent",
                effective_model="none",
                effective_reasoning="deterministic",
                effective_skill="review",
                effective_tools=["python"],
                result="pass",
                repository=repository,
            )
            evidence = evidence_for(binding, policy, manifest)
            payload_root = payload_at(parent, evidence)
            (payload_root / evidence["payload"]["path"]).write_text(
                '{"passed":false}\n', encoding="utf-8"
            )
            with self.assertRaisesRegex(RunStateError, "payload digest"):
                record_evidence(
                    card,
                    evidence,
                    registry,
                    policy,
                    manifest,
                    payload_root=payload_root,
                    repository=repository,
                )

    def test_remote_egress_must_match_attempt_and_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = repository_at(Path(temporary))
            card, binding, registry, policy, manifest = running_card(
                repository, remote_model=True
            )
            card = record_attempt(
                card,
                policy,
                manifest,
                node_id="testing",
                attempt_id="attempt-remote",
                started_at=NOW,
                finished_at=NOW,
                effective_principal_id="example-reviewer",
                effective_agent="review-agent",
                effective_model="remote-model",
                effective_reasoning="deterministic",
                effective_skill="review",
                effective_tools=["python"],
                data_egress={
                    "provider": "approved-provider",
                    "path_prefixes": ["docs"],
                    "content_classes": ["source"],
                },
                result="pass",
                repository=repository,
            )
            outside_path = evidence_for(
                binding,
                policy,
                manifest,
                model="remote-model",
                provider="approved-provider",
                paths=["src"],
                content_classes=["source"],
                attempt_id="attempt-remote",
            )
            payload_root = payload_at(Path(temporary), outside_path)
            with self.assertRaisesRegex(RunStateError, "does not match"):
                record_evidence(
                    card,
                    outside_path,
                    registry,
                    policy,
                    manifest,
                    payload_root=payload_root,
                    repository=repository,
                )

    def test_completion_rejects_same_id_evidence_substitution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = repository_at(Path(temporary))
            card, binding, registry, policy, manifest = running_card(repository)
            card = record_attempt(
                card,
                policy,
                manifest,
                node_id="testing",
                attempt_id="attempt",
                started_at=NOW,
                finished_at=NOW,
                effective_principal_id="example-reviewer",
                effective_agent="review-agent",
                effective_model="none",
                effective_reasoning="deterministic",
                effective_skill="review",
                effective_tools=["python"],
                result="pass",
                repository=repository,
            )
            evidence = evidence_for(binding, policy, manifest)
            payload_root = payload_at(Path(temporary), evidence)
            card = record_evidence(
                card,
                evidence,
                registry,
                policy,
                manifest,
                payload_root=payload_root,
                repository=repository,
            )
            substituted = deepcopy(evidence)
            substituted["claims"][0]["statement"] = "Substituted after receipt."
            with self.assertRaisesRegex(RunStateError, "document digest mismatch"):
                complete_node(
                    card,
                    "testing",
                    registry,
                    policy,
                    manifest,
                    {"testing-evidence": substituted},
                    accepted_by={
                        "id": "example-orchestrator",
                        "kind": "orchestrator",
                    },
                    payload_root=payload_root,
                    repository=repository,
                )
            completed = complete_node(
                card,
                "testing",
                registry,
                policy,
                manifest,
                {"testing-evidence": evidence},
                accepted_by={
                    "id": "example-orchestrator",
                    "kind": "orchestrator",
                },
                payload_root=payload_root,
                repository=repository,
            )
            self.assertEqual(completed["nodes"][0]["status"], "passed")


if __name__ == "__main__":
    unittest.main()
