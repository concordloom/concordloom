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
from concordloom.route import create_route_preview
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
    route_metadata: dict | None = None,
) -> dict:
    evidence = {
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
    evidence["effective_route"].update(deepcopy(route_metadata or {}))
    return evidence


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


def structured_route_metadata(resource_digest: str = OID_DIGEST) -> dict:
    return {
        "model_provider": "",
        "model": "none",
        "reasoning": "deterministic",
        "skills": [
            {
                "id": "independent-review",
                "version": "1.0.0",
                "digest": OID_DIGEST,
            }
        ],
        "mcp_servers": [
            {
                "id": "repository-evidence",
                "version": "2.1.0",
                "digest": OID_DIGEST,
            }
        ],
        "resources": [
            {
                "id": "candidate-source",
                "kind": "repository_path",
                "ref": "service.py",
                "digest": resource_digest,
                "access_mode": "read",
            }
        ],
        "tool_capabilities": ["inspect-source"],
        "subagent_identities": [
            {
                "id": "source-inspector",
                "principal_id": "example-executor",
                "agent": "codex",
                "model_provider": "",
                "model": "none",
            }
        ],
    }


def running_card_with_metadata(
    repository: Path,
) -> tuple[dict, dict, dict, dict, dict, dict]:
    binding, registry, policy = runtime_documents()
    manifest = build_candidate_manifest(repository, generated_at=NOW)
    draft = create_run_card(
        binding,
        registry,
        policy,
        manifest,
        run_id="security-run",
        root_loop_id="testing",
        candidate_author_principal_ids=["example-executor"],
    )
    resource_digest = next(
        item["digest"]
        for item in manifest["files"]
        if item["path"] == "service.py"
    )
    metadata = structured_route_metadata(resource_digest)
    planned = deepcopy(draft["planned_route"])
    planned[0].update(deepcopy(metadata))
    card = create_run_card(
        binding,
        registry,
        policy,
        manifest,
        run_id="security-run",
        root_loop_id="testing",
        candidate_author_principal_ids=["example-executor"],
        planned_route=planned,
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
    return card, binding, registry, policy, manifest, metadata


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
    def test_v10_target_plans_remain_non_authorizing_until_exact_run_authorization(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = repository_at(Path(temporary))
            source = ROOT / "framework" / "concordloom" / "v10"
            binding = load(source / "binding.json")
            registry = load(source / "cycle-registry.json")
            policy = load(source / "policy.json")
            model = load(source / "development-model.json")
            candidate = build_candidate_manifest(repository, generated_at=NOW)
            preview = create_route_preview(
                binding,
                registry,
                policy,
                candidate,
                model,
                preview_id="runtime-composite-preview",
                request_digest=OID_DIGEST,
                request_ref="request.user.1",
                root_loop_id="steward-concordloom",
                target_loop_ids=["runtime-tooling"],
                created_at=NOW,
            )
            self.assertEqual("proposed", preview["status"])
            self.assertFalse(preview["execution_allowed"])
            self.assertNotIn("authorization", preview)

            card = create_run_card(
                binding,
                registry,
                policy,
                candidate,
                run_id="runtime-composite-run",
                root_loop_id="steward-concordloom",
                candidate_author_principal_ids=["example-executor"],
                development_model=model,
                route_preview=preview,
            )
            self.assertEqual("draft", card["status"])
            self.assertNotIn("authorization", card)
            self.assertEqual(
                preview["preview_digest"], card["route_preview_digest"]
            )
            self.assertEqual(preview["proposed_route"], card["planned_route"])

            authorized = authorize_run(
                card,
                binding,
                registry,
                policy,
                candidate,
                actor={"id": "example-operator", "kind": "operator"},
                authority_ref="operator",
                authorized_at=NOW,
                repository=repository,
                development_model=model,
                route_preview=preview,
            )
            self.assertEqual("authorized", authorized["status"])
            self.assertEqual(
                preview["preview_digest"],
                authorized["authorization"]["route_preview_digest"],
            )

            tampered = deepcopy(preview)
            tampered["target_plans"][0]["action_loop_ids"] = [
                "runtime-tooling"
            ]
            tampered["preview_digest"] = document_digest(
                tampered,
                excluded_fields=tampered["digest_contract"]["excluded_fields"],
            )
            with self.assertRaisesRegex(ValueError, "exact deterministic target plans"):
                create_run_card(
                    binding,
                    registry,
                    policy,
                    candidate,
                    run_id="tampered-runtime-composite-run",
                    root_loop_id="steward-concordloom",
                    candidate_author_principal_ids=["example-executor"],
                    development_model=model,
                    route_preview=tampered,
                )

    def test_task_targeted_routes_use_only_exact_ancestor_closures(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = repository_at(Path(temporary))
            source = ROOT / "framework" / "concordloom" / "v6"
            binding = load(source / "binding.json")
            registry = load(source / "cycle-registry.json")
            policy = load(source / "policy.json")
            manifest = build_candidate_manifest(repository, generated_at=NOW)
            common = {
                "binding": binding,
                "registry": registry,
                "policy": policy,
                "candidate_manifest": manifest,
                "root_loop_id": "steward-concordloom",
                "candidate_author_principal_ids": ["example-executor"],
            }

            default = create_run_card(
                **common,
                run_id="root-coordinator-only",
            )
            self.assertEqual(
                ["steward-concordloom"],
                [
                    item["loop_id"]
                    for item in default["planned_route"]
                ],
            )

            targeted = create_run_card(
                **common,
                run_id="target-maintain-cli",
                target_loop_ids=["maintain-cli"],
            )
            self.assertEqual(
                [
                    "steward-concordloom",
                    "runtime-tooling",
                    "maintain-cli",
                ],
                [
                    item["loop_id"]
                    for item in targeted["planned_route"]
                ],
            )
            self.assertTrue(
                {
                    "release-distribution",
                    "system-evolution",
                    "maintain-article",
                }.isdisjoint(
                    item["loop_id"]
                    for item in targeted["planned_route"]
                )
            )

            combined = create_run_card(
                **common,
                run_id="two-targets",
                target_loop_ids=["maintain-cli", "maintain-article"],
            )
            self.assertEqual(
                [
                    "steward-concordloom",
                    "research-theory",
                    "maintain-article",
                    "runtime-tooling",
                    "maintain-cli",
                ],
                [
                    item["loop_id"]
                    for item in combined["planned_route"]
                ],
            )

            portfolio = create_run_card(
                **common,
                run_id="explicit-portfolio",
                portfolio=True,
            )
            portfolio_ids = [
                item["loop_id"] for item in portfolio["planned_route"]
            ]
            self.assertEqual(58, len(portfolio_ids))
            self.assertEqual("steward-concordloom", portfolio_ids[0])
            positions = {
                loop_id: index
                for index, loop_id in enumerate(portfolio_ids)
            }
            for edge in registry["containment_graph"]["edges"]:
                self.assertLess(
                    positions[edge["parent_loop_id"]],
                    positions[edge["child_loop_id"]],
                    edge["id"],
                )

            grants = {
                edge["child_loop_id"]: edge["grant"]["scope"]
                for edge in registry["containment_graph"]["edges"]
            }
            leaf_scope = next(
                item["scope"]
                for item in targeted["planned_route"]
                if item["loop_id"] == "maintain-cli"
            )
            self.assertEqual(grants["maintain-cli"], leaf_scope)
            for item in targeted["planned_route"][:-1]:
                self.assertEqual("none", item["scope"]["network"])
                self.assertEqual([], item["scope"]["external_mutations"])

    def test_target_selection_fails_closed_and_excludes_custom_routes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = repository_at(Path(temporary))
            binding, registry, policy = runtime_documents()
            manifest = build_candidate_manifest(repository, generated_at=NOW)
            common = {
                "binding": binding,
                "registry": registry,
                "policy": policy,
                "candidate_manifest": manifest,
                "root_loop_id": "testing",
                "candidate_author_principal_ids": ["example-executor"],
            }
            with self.assertRaisesRegex(RunStateError, "unknown target loops"):
                create_run_card(
                    **common,
                    run_id="unknown-target",
                    target_loop_ids=["missing-loop"],
                )
            with self.assertRaisesRegex(RunStateError, "must be unique"):
                create_run_card(
                    **common,
                    run_id="duplicate-target",
                    target_loop_ids=["testing", "testing"],
                )
            with self.assertRaisesRegex(RunStateError, "mutually exclusive"):
                create_run_card(
                    **common,
                    run_id="target-and-portfolio",
                    target_loop_ids=["testing"],
                    portfolio=True,
                )
            route = create_run_card(
                **common,
                run_id="route-source",
            )["planned_route"]
            with self.assertRaisesRegex(RunStateError, "mutually exclusive"):
                create_run_card(
                    **common,
                    run_id="custom-and-target",
                    planned_route=route,
                    target_loop_ids=["testing"],
                )

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
                    run_id="foreign-target-run",
                    root_loop_id="testing",
                    candidate_author_principal_ids=["example-executor"],
                    target_loop_ids=["secondary-testing"],
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

    def test_structured_route_metadata_round_trips_to_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            repository = repository_at(parent)
            (
                card,
                binding,
                registry,
                policy,
                manifest,
                metadata,
            ) = running_card_with_metadata(repository)
            card = record_attempt(
                card,
                policy,
                manifest,
                node_id="testing",
                attempt_id="attempt-structured",
                started_at=NOW,
                finished_at=NOW,
                effective_principal_id="example-reviewer",
                effective_agent="review-agent",
                effective_model="none",
                effective_model_provider=metadata["model_provider"],
                effective_reasoning="deterministic",
                effective_skill="review",
                effective_skills=metadata["skills"],
                effective_mcp_servers=metadata["mcp_servers"],
                effective_resources=metadata["resources"],
                effective_tool_capabilities=metadata["tool_capabilities"],
                effective_subagent_identities=metadata["subagent_identities"],
                effective_tools=["python"],
                result="pass",
                repository=repository,
            )
            evidence = evidence_for(
                binding,
                policy,
                manifest,
                attempt_id="attempt-structured",
                route_metadata=metadata,
            )
            payload_root = payload_at(parent, evidence)
            card = record_evidence(
                card,
                evidence,
                registry,
                policy,
                manifest,
                payload_root=payload_root,
                repository=repository,
            )
            attempt = card["nodes"][0]["attempts"][0]
            self.assertEqual(
                attempt["effective_resources"],
                metadata["resources"],
            )
            self.assertEqual(
                attempt["effective_mcp_servers"],
                metadata["mcp_servers"],
            )

    def test_declared_resources_are_required_and_must_match(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            repository = repository_at(parent)
            (
                card,
                binding,
                registry,
                policy,
                manifest,
                metadata,
            ) = running_card_with_metadata(repository)
            with self.assertRaisesRegex(RunStateError, "omits declared resources"):
                record_attempt(
                    card,
                    policy,
                    manifest,
                    node_id="testing",
                    attempt_id="attempt-omits-resource",
                    started_at=NOW,
                    finished_at=NOW,
                    effective_principal_id="example-reviewer",
                    effective_agent="review-agent",
                    effective_model="none",
                    effective_model_provider=metadata["model_provider"],
                    effective_reasoning="deterministic",
                    effective_skill="review",
                    effective_skills=metadata["skills"],
                    effective_mcp_servers=metadata["mcp_servers"],
                    effective_tool_capabilities=metadata["tool_capabilities"],
                    effective_subagent_identities=metadata[
                        "subagent_identities"
                    ],
                    effective_tools=["python"],
                    result="pass",
                    repository=repository,
                )

            card = record_attempt(
                card,
                policy,
                manifest,
                node_id="testing",
                attempt_id="attempt-resource",
                started_at=NOW,
                finished_at=NOW,
                effective_principal_id="example-reviewer",
                effective_agent="review-agent",
                effective_model="none",
                effective_model_provider=metadata["model_provider"],
                effective_reasoning="deterministic",
                effective_skill="review",
                effective_skills=metadata["skills"],
                effective_mcp_servers=metadata["mcp_servers"],
                effective_resources=metadata["resources"],
                effective_tool_capabilities=metadata["tool_capabilities"],
                effective_subagent_identities=metadata["subagent_identities"],
                effective_tools=["python"],
                result="pass",
                repository=repository,
            )
            mismatch = deepcopy(metadata)
            mismatch["resources"][0]["digest"] = "sha256:" + ("b" * 64)
            evidence = evidence_for(
                binding,
                policy,
                manifest,
                attempt_id="attempt-resource",
                route_metadata=mismatch,
            )
            payload_root = payload_at(parent, evidence)
            with self.assertRaisesRegex(
                RunStateError, "resources does not match the cited attempt"
            ):
                record_evidence(
                    card,
                    evidence,
                    registry,
                    policy,
                    manifest,
                    payload_root=payload_root,
                    repository=repository,
                )

    def test_actual_resources_cannot_appear_without_a_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = repository_at(Path(temporary))
            card, _, _, policy, manifest = running_card(repository)
            metadata = structured_route_metadata()
            with self.assertRaisesRegex(RunStateError, "undeclared resources"):
                record_attempt(
                    card,
                    policy,
                    manifest,
                    node_id="testing",
                    attempt_id="attempt-undeclared-resource",
                    started_at=NOW,
                    finished_at=NOW,
                    effective_principal_id="example-reviewer",
                    effective_agent="review-agent",
                    effective_model="none",
                    effective_reasoning="deterministic",
                    effective_skill="review",
                    effective_resources=metadata["resources"],
                    effective_tools=["python"],
                    result="pass",
                    repository=repository,
                )

    def test_planned_repository_resource_digest_is_candidate_bound(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = repository_at(Path(temporary))
            binding, registry, policy = runtime_documents()
            manifest = build_candidate_manifest(repository, generated_at=NOW)
            draft = create_run_card(
                binding,
                registry,
                policy,
                manifest,
                run_id="resource-digest-run",
                root_loop_id="testing",
                candidate_author_principal_ids=["example-executor"],
            )
            planned = deepcopy(draft["planned_route"])
            planned[0].update(structured_route_metadata())
            with self.assertRaisesRegex(
                RunStateError, "repository resource digest mismatch"
            ):
                create_run_card(
                    binding,
                    registry,
                    policy,
                    manifest,
                    run_id="resource-digest-run",
                    root_loop_id="testing",
                    candidate_author_principal_ids=["example-executor"],
                    planned_route=planned,
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
                    token_accounting="unavailable",
                    result="pass",
                    repository=repository,
                )

    def test_attempt_records_provider_neutral_token_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = repository_at(Path(temporary))
            card, _, _, policy, manifest = running_card(repository)
            card = record_attempt(
                card,
                policy,
                manifest,
                node_id="testing",
                attempt_id="token-metrics",
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
            attempt = card["nodes"][0]["attempts"][0]
            self.assertEqual(
                (0, 0, 0, 0),
                (
                    attempt["input_tokens"],
                    attempt["output_tokens"],
                    attempt["reasoning_tokens"],
                    attempt["cached_tokens"],
                ),
            )
            self.assertEqual("none", attempt["effective_model"])
            self.assertNotIn("effective_model_provider", attempt)
            self.assertEqual("not-applicable", attempt["token_accounting"])

            for field, value in (
                ("input_tokens", -1),
                ("output_tokens", 1.5),
                ("reasoning_tokens", True),
                ("cached_tokens", -1),
            ):
                kwargs = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "reasoning_tokens": 0,
                    "cached_tokens": 0,
                }
                kwargs[field] = value
                with self.assertRaisesRegex(
                    RunStateError, f"{field} must be a non-negative integer"
                ):
                    record_attempt(
                        running_card(repository)[0],
                        policy,
                        manifest,
                        node_id="testing",
                        attempt_id=f"invalid-{field}",
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
                        **kwargs,
                    )

            with self.assertRaisesRegex(
                RunStateError, "model none requires not-applicable"
            ):
                record_attempt(
                    running_card(repository)[0],
                    policy,
                    manifest,
                    node_id="testing",
                    attempt_id="false-measurement",
                    started_at=NOW,
                    finished_at=NOW,
                    effective_principal_id="example-reviewer",
                    effective_agent="review-agent",
                    effective_model="none",
                    effective_reasoning="deterministic",
                    effective_skill="review",
                    effective_tools=["python"],
                    token_accounting="measured",
                    input_tokens=1,
                    result="pass",
                    repository=repository,
                )

            remote_card, _, _, remote_policy, remote_manifest = running_card(
                repository, remote_model=True
            )
            with self.assertRaisesRegex(
                RunStateError, "must declare measured or unavailable"
            ):
                record_attempt(
                    remote_card,
                    remote_policy,
                    remote_manifest,
                    node_id="testing",
                    attempt_id="unaccounted-model",
                    started_at=NOW,
                    finished_at=NOW,
                    effective_principal_id="example-reviewer",
                    effective_agent="review-agent",
                    effective_model="remote-model",
                    effective_reasoning="deterministic",
                    effective_skill="review",
                    effective_tools=["python"],
                    result="pass",
                    repository=repository,
                )
            measured = record_attempt(
                remote_card,
                remote_policy,
                remote_manifest,
                node_id="testing",
                attempt_id="measured-model",
                started_at=NOW,
                finished_at=NOW,
                effective_principal_id="example-reviewer",
                effective_agent="review-agent",
                effective_model="remote-model",
                effective_reasoning="deterministic",
                effective_skill="review",
                effective_tools=["python"],
                token_accounting="measured",
                input_tokens=12,
                output_tokens=3,
                reasoning_tokens=4,
                cached_tokens=5,
                data_egress={
                    "provider": "approved-provider",
                    "path_prefixes": ["docs"],
                    "content_classes": ["source"],
                },
                result="pass",
                repository=repository,
            )
            self.assertEqual(
                "measured",
                measured["nodes"][0]["attempts"][0]["token_accounting"],
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
                token_accounting="unavailable",
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
