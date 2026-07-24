from __future__ import annotations

import argparse
from contextlib import contextmanager
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from typing import Iterator

from concordloom.schema import SchemaStore, ValidationError


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "concord_run", ROOT / "tools" / "concord_run.py"
)
assert SPEC and SPEC.loader
RUN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUN)


class BootstrapRunnerTests(unittest.TestCase):
    @staticmethod
    def _git(repository: Path, *arguments: str) -> str:
        result = subprocess.run(
            ["git", *arguments],
            cwd=repository,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    @contextmanager
    def _sandboxed_repository(
        self,
        cycle: dict[str, object] | None = None,
    ) -> Iterator[tuple[Path, Path]]:
        definition = cycle or {
            "schema_version": 1,
            "cycle_id": "concordloom-test-cycle",
            "title": "Concord Loom adversarial test cycle",
            "nodes": [
                {
                    "id": "T",
                    "title": "Author candidate",
                    "depends_on": [],
                    "mode": "write",
                },
                {
                    "id": "R",
                    "title": "Review candidate",
                    "depends_on": ["T"],
                    "mode": "read_only",
                    "independent": True,
                },
            ]
        }
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            repository = base / "repository"
            repository.mkdir()
            self._git(repository, "init", "--quiet")
            self._git(repository, "config", "user.email", "tests@example.invalid")
            self._git(repository, "config", "user.name", "Concord Loom Tests")
            (repository / "cycle.json").write_text(
                json.dumps(definition, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            policy = {
                "schema_version": 1,
                "policy_id": "concordloom-test-policy",
                "intent": {
                    "quality": "high",
                    "cost": "bounded",
                    "privacy": "repository-local",
                },
                "requirements": [
                    "Record every factual runtime attempt.",
                    "Keep independent review separate from authoring.",
                ],
            }
            (repository / "policy.json").write_text(
                json.dumps(policy, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            (repository / "payload.txt").write_text("candidate\n", encoding="utf-8")
            self._git(repository, "add", "cycle.json", "policy.json", "payload.txt")
            self._git(repository, "commit", "--quiet", "-m", "candidate")

            nodes = {}
            for node_id, node in RUN.cycle_nodes(definition).items():
                read_only = node.get("mode") == "read_only"
                nodes[node_id] = {
                    "status": "PENDING",
                    "scope": {
                        "read": ["."],
                        "write": [] if read_only else ["payload.txt"],
                    },
                    "authorized_by": None,
                    "executor": None,
                    "attempt": None,
                    "evidence": [],
                }
            card_path = base / "run-card.json"
            card = {
                "kind": "concordloom.bootstrap-run-card",
                "schema_version": 1,
                "run_id": "adversarial-test",
                "objective": "exercise bootstrap trust boundaries",
                "cycle_path": "cycle.json",
                "cycle_digest": RUN.digest(definition),
                "policy_path": "policy.json",
                "policy_digest": RUN.digest(policy),
                "created_from": self._git(repository, "rev-parse", "HEAD"),
                "candidate": None,
                "nodes": nodes,
            }

            previous_root = RUN.ROOT
            RUN.ROOT = repository
            try:
                RUN.save(card_path, card)
                yield repository, card_path
            finally:
                RUN.ROOT = previous_root

    @staticmethod
    def _pin(card_path: Path, revision: str) -> None:
        RUN.cmd_pin(
            argparse.Namespace(
                card=str(card_path),
                kind="git",
                value=revision,
            )
        )

    @staticmethod
    def _prepare_review(
        card_path: Path,
        author: str = "author-agent",
        reviewer: str = "review-agent",
        write_subagents: list[str] | None = None,
    ) -> dict[str, object]:
        card = RUN.load(card_path)
        policy_digest = card["policy_digest"]
        card["nodes"]["T"].update(
            {
                "status": "PASSED",
                "authorized_by": "operator",
                "executor": author,
                "attempt": {
                    "agent": author,
                    "model": "test-model",
                    "reasoning": "test",
                    "skill": "test",
                    "subagents": write_subagents or [],
                    "policy_digest": policy_digest,
                },
                "evidence": [{"result": "PASSED"}],
            }
        )
        card["nodes"]["R"].update(
            {
                "status": "AUTHORIZED",
                "authorized_by": "operator",
                "executor": reviewer,
                "attempt": {
                    "agent": reviewer,
                    "model": "test-model",
                    "reasoning": "test",
                    "skill": "test",
                    "subagents": [],
                    "policy_digest": policy_digest,
                },
            }
        )
        RUN.save(card_path, card)
        return card

    @staticmethod
    def _review_evidence(
        card: dict[str, object],
        node_id: str = "R",
        result: str = "PASSED",
    ) -> dict[str, object]:
        state = card["nodes"][node_id]
        attempt = state["attempt"]
        return {
            "kind": "concordloom.bootstrap-review-evidence",
            "schema_version": 1,
            "run_id": card["run_id"],
            "cycle_digest": card["cycle_digest"],
            "node": node_id,
            "result": result,
            "candidate_tree_digest": card["candidate"]["tree_digest"],
            "attempt_digest": RUN.digest(attempt),
            "reviewer": attempt["agent"],
            "policy_digest": attempt["policy_digest"],
            "checks": [
                {
                    "id": "candidate-review",
                    "result": "PASS",
                    "detail": "candidate satisfies the independent review contract",
                }
            ],
            "summary": "Independent review passed.",
            "produced_at": "2026-07-24T00:00:00Z",
        }

    @staticmethod
    def _record_review(card_path: Path, evidence_path: Path) -> None:
        RUN.cmd_record(
            argparse.Namespace(
                card=str(card_path),
                node="R",
                status="PASSED",
                evidence=[str(evidence_path)],
            )
        )

    def _complete_run(
        self,
        repository: Path,
        card_path: Path,
    ) -> dict[str, object]:
        revision = self._git(repository, "rev-parse", "HEAD")
        self._pin(card_path, revision)
        card = self._prepare_review(card_path)
        evidence_path = repository.parent / "review-evidence.json"
        RUN.save(evidence_path, self._review_evidence(card))
        self._record_review(card_path, evidence_path)
        RUN.cmd_complete(argparse.Namespace(card=str(card_path)))
        return RUN.load(card_path)

    def test_bootstrap_cycle_is_well_formed(self) -> None:
        cycle = RUN.load(ROOT / "concord" / "bootstrap-cycle.json")
        nodes = RUN.cycle_nodes(cycle)
        self.assertEqual(list(nodes), ["O", "P", "D", "I", "T", "N", "A", "R", "L", "Q", "M", "X", "E"])
        self.assertTrue(nodes["R"]["independent"])
        self.assertEqual(nodes["R"]["mode"], "read_only")

    def test_cycle_digest_is_deterministic(self) -> None:
        cycle = RUN.load(ROOT / "concord" / "bootstrap-cycle.json")
        self.assertEqual(RUN.digest(cycle), RUN.digest(json.loads(json.dumps(cycle))))

    def test_path_scope_is_fail_closed(self) -> None:
        self.assertTrue(RUN.path_allowed("docs/ARTICLE.md", ["docs"]))
        with self.assertRaises(RUN.RunError):
            RUN.path_allowed("../outside-repository/AGENTS.md", ["docs"])
        self.assertFalse(RUN.path_allowed("src/concordloom/core.py", ["docs"]))

    def test_invalid_scope_grants_are_rejected(self) -> None:
        with self._sandboxed_repository() as (repository, card_path):
            card = RUN.load(card_path)
            cycle = RUN.load(repository / "cycle.json")
            invalid_grants = {
                "empty": [""],
                "duplicate": ["payload.txt", "payload.txt"],
                "absolute": [str(repository / "payload.txt")],
                "parent traversal": ["../outside-repository"],
            }
            for label, grants in invalid_grants.items():
                with self.subTest(label=label):
                    invalid = json.loads(json.dumps(card))
                    invalid["nodes"]["T"]["scope"]["write"] = grants
                    with self.assertRaises(RUN.RunError):
                        RUN.validate_card(invalid, cycle)

    def test_invalid_route_grants_cannot_broaden_guard(self) -> None:
        with self._sandboxed_repository() as (repository, card_path):
            card = RUN.load(card_path)
            card["nodes"]["T"].update(
                {
                    "status": "AUTHORIZED",
                    "authorized_by": "operator",
                    "executor": "test-agent",
                }
            )
            RUN.save(card_path, card)
            original_writes = list(card["nodes"]["T"]["scope"]["write"])

            for label, grant in (
                ("empty", ""),
                ("absolute", str(repository / "cycle.json")),
                ("parent traversal", "../outside-repository"),
            ):
                with self.subTest(label=label):
                    with self.assertRaises(RUN.RunError):
                        RUN.cmd_route_scope(
                            argparse.Namespace(
                                card=str(card_path),
                                node="T",
                                actor="operator",
                                write_path=grant,
                                reason="must fail closed",
                            )
                        )
                    current = RUN.load(card_path)
                    self.assertEqual(
                        current["nodes"]["T"]["scope"]["write"],
                        original_writes,
                    )
                    self.assertNotIn("route_amendments", current)

            with self.assertRaisesRegex(RUN.RunError, "write outside T scope"):
                RUN.cmd_guard(
                    argparse.Namespace(
                        card=str(card_path),
                        node="T",
                        read_path=[],
                        write_path=["cycle.json"],
                    )
                )

    def test_dependency_cycle_is_rejected(self) -> None:
        cycle = {
            "nodes": [
                {"id": "A", "depends_on": ["B"]},
                {"id": "B", "depends_on": ["A"]},
            ]
        }
        with self.assertRaises(RUN.RunError):
            RUN.cycle_nodes(cycle)

    def test_save_is_deterministic_and_newline_terminated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "value.json"
            RUN.save(target, {"z": 1, "a": 2})
            self.assertEqual(target.read_text(), '{\n  "a": 2,\n  "z": 1\n}\n')

    def test_route_scope_command_is_registered(self) -> None:
        parsed = RUN.parser().parse_args(
            [
                "route-scope",
                "--card",
                "card.json",
                "--node",
                "I",
                "--actor",
                "operator",
                "--write-path",
                "schemas",
                "--reason",
                "public contract discovered during forward implementation",
            ]
        )
        self.assertIs(parsed.func, RUN.cmd_route_scope)

    def test_pin_rejects_wrong_or_dirty_revision_and_computes_digest(self) -> None:
        with self._sandboxed_repository() as (repository, card_path):
            revision = self._git(repository, "rev-parse", "HEAD")
            with self.assertRaisesRegex(
                RUN.RunError,
                "requested candidate revision is not the current clean HEAD",
            ):
                self._pin(card_path, "0" * len(revision))

            (repository / "payload.txt").write_text("dirty\n", encoding="utf-8")
            with self.assertRaisesRegex(
                RUN.RunError,
                "candidate repository must be clean before pinning",
            ):
                self._pin(card_path, revision)

            self._git(repository, "checkout", "--", "payload.txt")
            RUN.cmd_pin(
                argparse.Namespace(
                    card=str(card_path),
                    kind="git",
                    value=revision,
                    tree_digest="sha256:" + "f" * 64,
                )
            )
            card = RUN.load(card_path)
            tree_oid = self._git(repository, "rev-parse", "HEAD^{tree}")
            self.assertEqual(
                card["candidate"],
                {
                    "kind": "git",
                    "value": revision,
                    "tree_oid": tree_oid,
                    "tree_digest": RUN.digest(
                        {"revision": revision, "tree_oid": tree_oid}
                    ),
                },
            )
            self.assertNotEqual(
                card["candidate"]["tree_digest"],
                "sha256:" + "f" * 64,
            )

    def test_candidate_cannot_be_repinned_after_independent_review(self) -> None:
        with self._sandboxed_repository() as (repository, card_path):
            revision = self._git(repository, "rev-parse", "HEAD")
            self._pin(card_path, revision)
            card = self._prepare_review(card_path)
            evidence_path = repository.parent / "review-evidence.json"
            RUN.save(evidence_path, self._review_evidence(card))
            self._record_review(card_path, evidence_path)

            with self.assertRaisesRegex(
                RUN.RunError,
                "candidate is immutable within a bootstrap run",
            ):
                self._pin(card_path, revision)

    def test_attempt_agent_must_match_authorized_executor(self) -> None:
        with self._sandboxed_repository() as (repository, card_path):
            card = RUN.load(card_path)
            card["nodes"]["T"].update(
                {
                    "status": "AUTHORIZED",
                    "authorized_by": "operator",
                    "executor": "authorized-agent",
                }
            )
            RUN.save(card_path, card)
            policy_path = repository.parent / "policy.json"
            RUN.save(policy_path, {"policy": "test"})

            with self.assertRaisesRegex(
                RUN.RunError,
                "attempt agent must equal the authorized executor",
            ):
                RUN.cmd_attempt(
                    argparse.Namespace(
                        card=str(card_path),
                        node="T",
                        policy=str(policy_path),
                        agent="different-agent",
                        model="test-model",
                        reasoning="test",
                        skill="test",
                        subagent=[],
                    )
                )
            self.assertIsNone(RUN.load(card_path)["nodes"]["T"]["attempt"])

    def test_empty_bootstrap_policy_is_rejected(self) -> None:
        with self._sandboxed_repository() as (repository, card_path):
            empty_policy_path = repository / "empty-policy.json"
            RUN.save(empty_policy_path, {})
            existing_card = RUN.load(card_path)
            scopes_path = repository.parent / "scopes.json"
            RUN.save(
                scopes_path,
                {
                    node_id: state["scope"]
                    for node_id, state in existing_card["nodes"].items()
                },
            )

            with self.assertRaises(RUN.RunError):
                RUN.cmd_new(
                    argparse.Namespace(
                        cycle=str(repository / "cycle.json"),
                        scopes=str(scopes_path),
                        policy=str(empty_policy_path),
                        card=str(repository.parent / "empty-policy-card.json"),
                        run_id="empty-policy",
                        objective="must fail closed",
                    )
                )

    def test_attempt_rejects_policy_from_different_path(self) -> None:
        with self._sandboxed_repository() as (repository, card_path):
            card = RUN.load(card_path)
            card["nodes"]["T"].update(
                {
                    "status": "AUTHORIZED",
                    "authorized_by": "operator",
                    "executor": "authorized-agent",
                }
            )
            RUN.save(card_path, card)
            alternate_policy_path = repository.parent / "alternate-policy.json"
            RUN.save(
                alternate_policy_path,
                RUN.load(repository / card["policy_path"]),
            )

            with self.assertRaisesRegex(
                RUN.RunError,
                "policy path differs from the bound bootstrap policy",
            ):
                RUN.cmd_attempt(
                    argparse.Namespace(
                        card=str(card_path),
                        node="T",
                        policy=str(alternate_policy_path),
                        agent="authorized-agent",
                        model="test-model",
                        reasoning="test",
                        skill="test",
                        subagent=[],
                    )
                )
            self.assertIsNone(RUN.load(card_path)["nodes"]["T"]["attempt"])

    def test_read_pair_rejects_bound_policy_drift(self) -> None:
        with self._sandboxed_repository() as (repository, card_path):
            policy_path = repository / "policy.json"
            policy = RUN.load(policy_path)
            policy["intent"]["cost"] = "unbounded"
            RUN.save(policy_path, policy)

            with self.assertRaisesRegex(
                RUN.RunError,
                "bootstrap compute policy drifted from the run card",
            ):
                RUN.read_pair(str(card_path))

    def test_ignored_in_repo_run_card_does_not_dirty_pinned_candidate(self) -> None:
        with self._sandboxed_repository() as (repository, external_card_path):
            (repository / ".gitignore").write_text(
                ".concord/runs/\n",
                encoding="utf-8",
            )
            self._git(repository, "add", ".gitignore")
            self._git(repository, "commit", "--quiet", "-m", "ignore run receipts")
            revision = self._git(repository, "rev-parse", "HEAD")

            in_repo_card_path = (
                repository / ".concord" / "runs" / "ignored-run" / "run-card.json"
            )
            RUN.save(in_repo_card_path, RUN.load(external_card_path))
            self.assertEqual(
                self._git(
                    repository,
                    "status",
                    "--porcelain=v1",
                    "--untracked-files=all",
                ),
                "",
            )

            self._pin(in_repo_card_path, revision)
            pinned_card = RUN.load(in_repo_card_path)

            self.assertEqual(RUN.verify_candidate(pinned_card), pinned_card["candidate"])
            self.assertEqual(
                self._git(
                    repository,
                    "status",
                    "--porcelain=v1",
                    "--untracked-files=all",
                ),
                "",
            )

    def test_candidate_snapshot_does_not_execute_configured_fsmonitor(self) -> None:
        with self._sandboxed_repository() as (repository, _):
            marker = repository.parent / "fsmonitor-executed"
            hook = repository.parent / "malicious-fsmonitor"
            hook.write_text(
                "#!/bin/sh\n"
                f"touch '{marker}'\n"
                "exit 1\n",
                encoding="utf-8",
            )
            hook.chmod(0o755)
            self._git(repository, "config", "core.fsmonitor", str(hook))

            snapshot = RUN.candidate_snapshot()

            self.assertEqual(snapshot["value"], self._git(repository, "rev-parse", "HEAD"))
            self.assertFalse(marker.exists(), "configured fsmonitor was executed")

    def test_candidate_snapshot_rejects_hidden_index_drift(self) -> None:
        for enabled, disabled in (
            ("--assume-unchanged", "--no-assume-unchanged"),
            ("--skip-worktree", "--no-skip-worktree"),
        ):
            with self.subTest(flag=enabled):
                with self._sandboxed_repository() as (repository, _):
                    self._git(repository, "update-index", enabled, "payload.txt")
                    (repository / "payload.txt").write_text(
                        "hidden drift\n",
                        encoding="utf-8",
                    )

                    with self.assertRaisesRegex(
                        RUN.RunError,
                        "candidate index contains hidden or special path flags",
                    ):
                        RUN.candidate_snapshot()

                    self._git(repository, "update-index", disabled, "payload.txt")

    def test_candidate_snapshot_never_executes_clean_filter(self) -> None:
        with self._sandboxed_repository() as (repository, _):
            (repository / ".gitattributes").write_text(
                "payload.txt filter=malicious\n",
                encoding="utf-8",
            )
            self._git(repository, "add", ".gitattributes")
            self._git(repository, "commit", "--quiet", "-m", "declare clean filter")
            marker = repository.parent / "clean-filter-executed"
            filter_program = repository.parent / "malicious-clean-filter"
            filter_program.write_text(
                "#!/bin/sh\n"
                f"touch '{marker}'\n"
                "cat\n",
                encoding="utf-8",
            )
            filter_program.chmod(0o755)
            self._git(
                repository,
                "config",
                "filter.malicious.clean",
                str(filter_program),
            )
            self._git(repository, "config", "filter.malicious.required", "true")

            RUN.candidate_snapshot()
            self.assertFalse(marker.exists(), "configured clean filter was executed")

            (repository / "payload.txt").write_bytes(b"raw byte drift\n")
            with self.assertRaisesRegex(
                RUN.RunError,
                "candidate repository must be clean before pinning",
            ):
                RUN.candidate_snapshot()
            self.assertFalse(marker.exists(), "configured clean filter was executed")

    def test_missing_promisor_object_never_executes_remote_uploadpack(self) -> None:
        with self._sandboxed_repository() as (repository, _):
            marker = repository.parent / "uploadpack-executed"
            uploadpack = repository.parent / "malicious-uploadpack"
            uploadpack.write_text(
                "#!/bin/sh\n"
                f"touch '{marker}'\n"
                "exit 1\n",
                encoding="utf-8",
            )
            uploadpack.chmod(0o755)
            remote = repository.parent / "promisor-remote"
            remote.mkdir()
            self._git(repository, "config", "core.repositoryformatversion", "1")
            self._git(repository, "config", "extensions.partialClone", "origin")
            self._git(repository, "config", "remote.origin.promisor", "true")
            self._git(
                repository,
                "config",
                "remote.origin.partialclonefilter",
                "blob:none",
            )
            self._git(repository, "config", "remote.origin.url", str(remote))
            self._git(
                repository,
                "config",
                "remote.origin.uploadpack",
                str(uploadpack),
            )
            tree_oid = self._git(repository, "rev-parse", "HEAD^{tree}")
            tree_object = (
                repository
                / ".git"
                / "objects"
                / tree_oid[:2]
                / tree_oid[2:]
            )
            self.assertTrue(tree_object.is_file())
            tree_object.unlink()

            with self.assertRaises(RUN.RunError):
                RUN.candidate_snapshot()
            self.assertFalse(marker.exists(), "remote uploadpack was executed")

    def test_independent_reviewer_cannot_match_any_write_node_author(self) -> None:
        with self._sandboxed_repository() as (repository, card_path):
            revision = self._git(repository, "rev-parse", "HEAD")
            self._pin(card_path, revision)
            card = self._prepare_review(
                card_path,
                author="shared-agent",
                reviewer="shared-agent",
            )
            evidence_path = repository.parent / "review-evidence.json"
            RUN.save(evidence_path, self._review_evidence(card))

            with self.assertRaisesRegex(
                RUN.RunError,
                "reviewer or subagent authored bytes in the pinned candidate",
            ):
                self._record_review(card_path, evidence_path)

    def test_write_node_subagent_cannot_review_candidate(self) -> None:
        with self._sandboxed_repository() as (repository, card_path):
            revision = self._git(repository, "rev-parse", "HEAD")
            self._pin(card_path, revision)
            card = self._prepare_review(
                card_path,
                author="author-agent",
                reviewer="tainted-subagent",
                write_subagents=["tainted-subagent"],
            )
            evidence_path = repository.parent / "review-evidence.json"
            RUN.save(evidence_path, self._review_evidence(card))

            with self.assertRaisesRegex(
                RUN.RunError,
                "reviewer or subagent authored bytes in the pinned candidate",
            ):
                self._record_review(card_path, evidence_path)

    def test_review_evidence_requires_exact_candidate_tree_digest(self) -> None:
        with self._sandboxed_repository() as (repository, card_path):
            revision = self._git(repository, "rev-parse", "HEAD")
            self._pin(card_path, revision)
            card = self._prepare_review(card_path)
            evidence_path = repository.parent / "review-evidence.json"
            baseline = self._review_evidence(card)
            missing = dict(baseline)
            missing.pop("candidate_tree_digest")
            wrong = dict(baseline)
            wrong["candidate_tree_digest"] = "sha256:" + "0" * 64

            for label, document in (
                ("missing", missing),
                ("wrong", wrong),
            ):
                with self.subTest(label=label):
                    RUN.save(evidence_path, document)
                    with self.assertRaisesRegex(
                        RUN.RunError,
                        "review evidence",
                    ):
                        self._record_review(card_path, evidence_path)

    def test_review_evidence_cannot_be_replayed_across_contexts(self) -> None:
        substitutions = {
            "run_id": "different-run",
            "cycle_digest": "sha256:" + "0" * 64,
            "attempt_digest": "sha256:" + "1" * 64,
            "reviewer": "different-reviewer",
            "policy_digest": "sha256:" + "2" * 64,
        }
        for field, replacement in substitutions.items():
            with self.subTest(field=field):
                with self._sandboxed_repository() as (repository, card_path):
                    revision = self._git(repository, "rev-parse", "HEAD")
                    self._pin(card_path, revision)
                    card = self._prepare_review(card_path)
                    evidence = self._review_evidence(card)
                    evidence[field] = replacement
                    evidence_path = repository.parent / "review-evidence.json"
                    RUN.save(evidence_path, evidence)

                    with self.assertRaises(RUN.RunError):
                        self._record_review(card_path, evidence_path)
                    self.assertEqual(
                        RUN.load(card_path)["nodes"]["R"]["status"],
                        "AUTHORIZED",
                    )

    def test_receipt_bundle_is_deterministic_and_detects_tampering(self) -> None:
        with self._sandboxed_repository() as (repository, card_path):
            card = self._complete_run(repository, card_path)
            cycle = RUN.load(repository / card["cycle_path"])
            policy = RUN.load(repository / card["policy_path"])

            first = RUN.build_receipt_bundle(card, cycle, policy)
            second = RUN.build_receipt_bundle(card, cycle, policy)

            self.assertEqual(first, second)
            self.assertEqual(RUN.digest(first), RUN.digest(second))
            RUN.validate_receipt_bundle(first)

            for label, mutate in (
                (
                    "nested run card",
                    lambda bundle: bundle["run_card"].update(
                        {"objective": "tampered objective"}
                    ),
                ),
                (
                    "self digest",
                    lambda bundle: bundle.update(
                        {"bundle_digest": "sha256:" + "0" * 64}
                    ),
                ),
            ):
                with self.subTest(label=label):
                    tampered = json.loads(json.dumps(first))
                    mutate(tampered)
                    with self.assertRaises(RUN.RunError):
                        RUN.validate_receipt_bundle(tampered)

    def test_all_bootstrap_json_schemas_load_from_closed_store(self) -> None:
        store = SchemaStore(ROOT / "concord", require_common=False)
        expected = tuple(
            path.name for path in sorted((ROOT / "concord").glob("*.schema.json"))
        )
        self.assertEqual(store.names, expected)
        self.assertEqual(
            set(store.names),
            {
                "bootstrap-compute-policy.schema.json",
                "bootstrap-cycle.schema.json",
                "bootstrap-receipt-bundle.schema.json",
                "bootstrap-review-evidence.schema.json",
                "bootstrap-run-card.schema.json",
            },
        )

    def test_bootstrap_documents_match_schemas_and_manual_validators(self) -> None:
        with self._sandboxed_repository() as (repository, card_path):
            card = self._complete_run(repository, card_path)
            cycle = RUN.load(repository / card["cycle_path"])
            policy = RUN.load(repository / card["policy_path"])
            review_evidence = card["nodes"]["R"]["evidence"][0]
            bundle = RUN.build_receipt_bundle(card, cycle, policy)
            store = SchemaStore(ROOT / "concord", require_common=False)

            store.validate(cycle, "bootstrap-cycle.schema.json")
            RUN.cycle_nodes(cycle)
            store.validate(policy, "bootstrap-compute-policy.schema.json")
            RUN.validate_bootstrap_policy(policy)
            store.validate(card, "bootstrap-run-card.schema.json")
            RUN.validate_card(card, cycle)
            store.validate(
                review_evidence,
                "bootstrap-review-evidence.schema.json",
            )
            RUN.validate_review_evidence(
                card,
                "R",
                "PASSED",
                [review_evidence],
                card["candidate"],
            )
            store.validate(bundle, "bootstrap-receipt-bundle.schema.json")
            RUN.validate_receipt_bundle(bundle)

    def test_recomputed_forged_bundle_fails_semantic_validation(self) -> None:
        with self._sandboxed_repository() as (repository, card_path):
            card = self._complete_run(repository, card_path)
            cycle = RUN.load(repository / card["cycle_path"])
            policy = RUN.load(repository / card["policy_path"])
            valid = RUN.build_receipt_bundle(card, cycle, policy)
            store = SchemaStore(ROOT / "concord", require_common=False)

            def reseal(bundle: dict[str, object]) -> None:
                bundle["run_card_digest"] = RUN.digest(bundle["run_card"])
                bundle["cycle_digest"] = RUN.digest(bundle["cycle"])
                bundle["policy_digest"] = RUN.digest(bundle["policy"])
                body = dict(bundle)
                body.pop("bundle_digest")
                bundle["bundle_digest"] = RUN.digest(body)

            cases = (
                (
                    "incomplete card",
                    lambda bundle: bundle["run_card"]["nodes"]["T"].update(
                        {"status": "PENDING"}
                    ),
                    True,
                ),
                (
                    "empty cycle",
                    lambda bundle: (
                        bundle.update({"cycle": {}}),
                        bundle["run_card"].update(
                            {"cycle_digest": RUN.digest({})}
                        ),
                    ),
                    False,
                ),
                (
                    "empty policy",
                    lambda bundle: (
                        bundle.update({"policy": {}}),
                        bundle["run_card"].update(
                            {"policy_digest": RUN.digest({})}
                        ),
                    ),
                    False,
                ),
            )
            for label, mutate, structurally_valid in cases:
                with self.subTest(label=label):
                    forged = json.loads(json.dumps(valid))
                    mutate(forged)
                    reseal(forged)
                    self.assertEqual(
                        forged["run_card_digest"],
                        RUN.digest(forged["run_card"]),
                    )
                    self.assertEqual(
                        forged["cycle_digest"],
                        RUN.digest(forged["cycle"]),
                    )
                    self.assertEqual(
                        forged["policy_digest"],
                        RUN.digest(forged["policy"]),
                    )
                    body = dict(forged)
                    claimed = body.pop("bundle_digest")
                    self.assertEqual(claimed, RUN.digest(body))

                    if structurally_valid:
                        store.validate(
                            forged,
                            "bootstrap-receipt-bundle.schema.json",
                        )
                    else:
                        with self.assertRaises(ValidationError):
                            store.validate(
                                forged,
                                "bootstrap-receipt-bundle.schema.json",
                            )
                    with self.assertRaises(RUN.RunError):
                        RUN.validate_receipt_bundle(forged)

    def test_bootstrap_schemas_and_manual_validators_reject_invalid_values(
        self,
    ) -> None:
        with self._sandboxed_repository() as (repository, card_path):
            card = self._complete_run(repository, card_path)
            cycle = RUN.load(repository / card["cycle_path"])
            policy = RUN.load(repository / card["policy_path"])
            evidence = card["nodes"]["R"]["evidence"][0]
            bundle = RUN.build_receipt_bundle(card, cycle, policy)
            store = SchemaStore(ROOT / "concord", require_common=False)

            cases = []
            for label, valid, schema_name, manual, mutation in (
                (
                    "policy extra",
                    policy,
                    "bootstrap-compute-policy.schema.json",
                    RUN.validate_bootstrap_policy,
                    lambda value: value.update({"unexpected": True}),
                ),
                (
                    "policy empty id",
                    policy,
                    "bootstrap-compute-policy.schema.json",
                    RUN.validate_bootstrap_policy,
                    lambda value: value.update({"policy_id": ""}),
                ),
                (
                    "card extra",
                    card,
                    "bootstrap-run-card.schema.json",
                    lambda value: RUN.validate_card(value, cycle),
                    lambda value: value.update({"unexpected": True}),
                ),
                (
                    "card empty policy path",
                    card,
                    "bootstrap-run-card.schema.json",
                    lambda value: RUN.validate_card(value, cycle),
                    lambda value: value.update({"policy_path": ""}),
                ),
                (
                    "evidence extra",
                    evidence,
                    "bootstrap-review-evidence.schema.json",
                    lambda value: RUN.validate_review_evidence(
                        card,
                        "R",
                        "PASSED",
                        [value],
                        card["candidate"],
                    ),
                    lambda value: value.update({"unexpected": True}),
                ),
                (
                    "evidence empty summary",
                    evidence,
                    "bootstrap-review-evidence.schema.json",
                    lambda value: RUN.validate_review_evidence(
                        card,
                        "R",
                        "PASSED",
                        [value],
                        card["candidate"],
                    ),
                    lambda value: value.update({"summary": ""}),
                ),
                (
                    "bundle extra",
                    bundle,
                    "bootstrap-receipt-bundle.schema.json",
                    RUN.validate_receipt_bundle,
                    lambda value: value.update({"unexpected": True}),
                ),
                (
                    "bundle empty run id",
                    bundle,
                    "bootstrap-receipt-bundle.schema.json",
                    RUN.validate_receipt_bundle,
                    lambda value: value.update({"run_id": ""}),
                ),
            ):
                invalid = json.loads(json.dumps(valid))
                mutation(invalid)
                cases.append((label, invalid, schema_name, manual))

            for label, invalid, schema_name, manual in cases:
                with self.subTest(label=label):
                    with self.assertRaises(ValidationError):
                        store.validate(invalid, schema_name)
                    with self.assertRaises(RUN.RunError):
                        manual(invalid)

    def test_receipt_export_rejects_unsafe_output_paths(self) -> None:
        with self._sandboxed_repository() as (repository, card_path):
            receipt_root = (
                repository / ".concord" / "runs" / "adversarial-test"
            )
            receipt_root.mkdir(parents=True)
            tracked_target = receipt_root / "tracked-receipt.json"
            tracked_target.write_text("tracked candidate bytes\n", encoding="utf-8")
            external_directory = repository.parent / "external-directory"
            external_directory.mkdir()
            symlink_parent = receipt_root / "linked-parent"
            symlink_parent.symlink_to(external_directory, target_is_directory=True)
            self._git(
                repository,
                "add",
                ".concord/runs/adversarial-test/tracked-receipt.json",
                ".concord/runs/adversarial-test/linked-parent",
            )
            self._git(repository, "commit", "--quiet", "-m", "tracked path traps")
            self._complete_run(repository, card_path)

            cases = (
                (
                    "source path",
                    repository / "payload.txt",
                    "must stay under",
                ),
                (
                    "outside repository",
                    repository.parent / "outside-receipt.json",
                    "must stay inside the repository",
                ),
                (
                    "tracked target",
                    tracked_target,
                    "cannot overwrite tracked candidate bytes",
                ),
                (
                    "symlink parent",
                    symlink_parent / "receipt.json",
                    "export parent is unsafe",
                ),
            )
            for label, output, expected_error in cases:
                with self.subTest(label=label):
                    with self.assertRaisesRegex(RUN.RunError, expected_error):
                        RUN.cmd_export(
                            argparse.Namespace(
                                card=str(card_path),
                                output=str(output),
                            )
                        )

    def test_complete_run_exports_ignored_receipt_without_candidate_drift(
        self,
    ) -> None:
        with self._sandboxed_repository() as (repository, card_path):
            (repository / ".gitignore").write_text(
                ".concord/runs/\n",
                encoding="utf-8",
            )
            self._git(repository, "add", ".gitignore")
            self._git(repository, "commit", "--quiet", "-m", "ignore run receipts")
            completed_card = self._complete_run(repository, card_path)
            output = (
                repository
                / ".concord"
                / "runs"
                / completed_card["run_id"]
                / "receipt-bundle.json"
            )

            RUN.cmd_export(
                argparse.Namespace(
                    card=str(card_path),
                    output=str(output),
                )
            )

            bundle = RUN.load(output)
            RUN.validate_receipt_bundle(bundle)
            self.assertEqual(bundle["run_card"], completed_card)
            self.assertEqual(
                self._git(
                    repository,
                    "check-ignore",
                    ".concord/runs/adversarial-test/receipt-bundle.json",
                ),
                ".concord/runs/adversarial-test/receipt-bundle.json",
            )
            self.assertEqual(
                self._git(
                    repository,
                    "status",
                    "--porcelain=v1",
                    "--untracked-files=all",
                ),
                "",
            )
            self.assertEqual(
                RUN.verify_candidate(completed_card),
                completed_card["candidate"],
            )

    def test_complete_rejects_repository_drift_after_pin(self) -> None:
        with self._sandboxed_repository() as (repository, card_path):
            self._complete_run(repository, card_path)
            (repository / "payload.txt").write_text(
                "post-pin drift\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                RUN.RunError,
                "candidate repository must be clean before pinning",
            ):
                RUN.cmd_complete(argparse.Namespace(card=str(card_path)))


if __name__ == "__main__":
    unittest.main()
