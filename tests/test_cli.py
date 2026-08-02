from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def run_cli(
        self,
        *arguments: str,
        cwd: Path | None = None,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        source = str(ROOT / "src")
        environment["PYTHONPATH"] = (
            source
            if not environment.get("PYTHONPATH")
            else source + os.pathsep + environment["PYTHONPATH"]
        )
        return subprocess.run(
            [sys.executable, "-m", "concordloom", *arguments],
            cwd=cwd or ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )

    def write_json(self, path: Path, value: object) -> Path:
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return path

    def make_git_repository(self, parent: Path, *, ignore_runs: bool = False) -> Path:
        repository = parent / "repository"
        repository.mkdir()
        subprocess.run(
            ["git", "init", "-b", "main"],
            cwd=repository,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "CLI Test"],
            cwd=repository,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "cli@example.invalid"],
            cwd=repository,
            check=True,
            capture_output=True,
        )
        (repository / "service.py").write_text("answer = 42\n", encoding="utf-8")
        if ignore_runs:
            (repository / ".gitignore").write_text(
                ".concord/runs/\n", encoding="utf-8"
            )
        subprocess.run(
            ["git", "add", "."],
            cwd=repository,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "seed"],
            cwd=repository,
            check=True,
            capture_output=True,
        )
        return repository

    def test_version_matches_the_package_release(self) -> None:
        result = self.run_cli("--version")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "concordloom 0.1.5")

    def test_run_attempt_forwards_structured_route_metadata(self) -> None:
        from concordloom.cli import _cmd_run_attempt

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            card = self.write_json(root / "card.json", {})
            policy = self.write_json(root / "policy.json", {})
            candidate = self.write_json(root / "candidate.json", {})
            output = root / "output.json"
            attempt = self.write_json(
                root / "attempt.json",
                {
                    "id": "attempt-1",
                    "started_at": "2026-07-28T11:30:00Z",
                    "finished_at": "2026-07-28T11:30:00Z",
                    "effective_principal_id": "example-publisher",
                    "effective_agent": "publisher",
                    "effective_model": "none",
                    "effective_model_provider": "",
                    "effective_reasoning": "deterministic",
                    "effective_skill": "release",
                    "effective_skills": [{"id": "release", "version": "1"}],
                    "effective_mcp_servers": [],
                    "effective_resources": [],
                    "effective_tool_capabilities": ["github"],
                    "effective_subagent_identities": [],
                    "effective_subagents": [],
                    "effective_tools": ["github"],
                    "data_egress": {
                        "provider": "",
                        "path_prefixes": [],
                        "content_classes": [],
                    },
                    "network": "write",
                    "external_mutations": ["github-release-assets"],
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "reasoning_tokens": 0,
                    "cached_tokens": 0,
                    "token_accounting": "not-applicable",
                    "cost_units": 0,
                    "result": "pass",
                },
            )
            args = SimpleNamespace(
                card=str(card),
                policy=str(policy),
                candidate=str(candidate),
                node="publish",
                attempt=str(attempt),
                repository=str(root),
                output=str(output),
            )

            with patch(
                "concordloom.run.record_attempt", return_value={"recorded": True}
            ) as record:
                _cmd_run_attempt(args)

            kwargs = record.call_args.kwargs
            self.assertEqual(kwargs["effective_model_provider"], "")
            self.assertEqual(
                kwargs["effective_skills"], [{"id": "release", "version": "1"}]
            )
            self.assertEqual(kwargs["effective_mcp_servers"], [])
            self.assertEqual(kwargs["effective_resources"], [])
            self.assertEqual(kwargs["effective_tool_capabilities"], ["github"])
            self.assertEqual(kwargs["effective_subagent_identities"], [])

    def observed_graph(self) -> dict[str, object]:
        oid = "1" * 40
        digest = "sha256:" + "a" * 64
        return {
            "kind": "concordloom.project-graph",
            "schema_version": "0.1",
            "id": "cli-test-project",
            "phase": "observed",
            "generated_at": "2026-07-24T10:00:00Z",
            "repository": {
                "id": "cli-test-repository",
                "revision": oid,
                "tree_digest": digest,
                "history_head": oid,
                "dirty": False,
            },
            "nodes": [
                {
                    "id": "source",
                    "kind": "component",
                    "label": "Source",
                    "category": "source",
                    "status": "inferred",
                    "confidence": 0.75,
                    "provenance": [{"kind": "file", "ref": "src/example.py"}],
                }
            ],
            "edges": [],
            "hypotheses": [
                {
                    "id": "source-boundary",
                    "claim": "Source is one governed boundary.",
                    "status": "unresolved",
                    "blocking": True,
                    "impact_score": 1,
                    "evidence": [{"kind": "file", "ref": "src/example.py"}],
                    "graph_delta": [
                        {
                            "op": "confirm",
                            "target_kind": "node",
                            "target_id": "source",
                        }
                    ],
                }
            ],
        }

    def make_accepted_artifacts(
        self, directory: Path
    ) -> tuple[Path, Path, Path]:
        graph_path = self.write_json(directory / "observed.json", self.observed_graph())
        policy_path = self.write_json(
            directory / "policy.json",
            json.loads(
                (ROOT / "framework" / "generic-sdlc" / "policy.json").read_text()
            ),
        )
        questions_path = directory / "questions.json"
        decision_path = directory / "decision.json"
        log_path = directory / "decisions.json"
        accepted_path = directory / "accepted.json"

        questions = self.run_cli(
            "questions",
            "--graph",
            str(graph_path),
            "--output",
            str(questions_path),
        )
        self.assertEqual(questions.returncode, 0, questions.stderr)
        question_id = json.loads(questions_path.read_text())["questions"][0]["id"]

        decide = self.run_cli(
            "decide",
            "--questions",
            str(questions_path),
            "--question",
            question_id,
            "--verdict",
            "confirmed",
            "--actor-id",
            "example-operator",
            "--actor-kind",
            "operator",
            "--authority-ref",
            "operator",
            "--rationale",
            "The boundary is intentional.",
            "--decided-at",
            "2026-07-24T10:01:00Z",
            "--output",
            str(decision_path),
        )
        self.assertEqual(decide.returncode, 0, decide.stderr)

        accept = self.run_cli(
            "accept",
            "--graph",
            str(graph_path),
            "--policy",
            str(policy_path),
            "--decision",
            str(decision_path),
            "--actor-id",
            "example-operator",
            "--actor-kind",
            "operator",
            "--authority-ref",
            "operator",
            "--accepted-at",
            "2026-07-24T10:02:00Z",
            "--decision-log-output",
            str(log_path),
            "--output",
            str(accepted_path),
        )
        self.assertEqual(accept.returncode, 0, accept.stderr)
        return accepted_path, log_path, policy_path

    def test_top_level_help_lists_the_complete_v01_surface(self) -> None:
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        for command in (
            "inspect",
            "questions",
            "decide",
            "accept",
            "propose",
            "compile",
            "activate",
            "validate",
            "candidate",
            "catalog",
            "route",
            "run",
            "atlas",
            "evolve",
        ):
            self.assertIn(command, result.stdout)

    def test_nested_help_does_not_import_optional_atlas_renderer(self) -> None:
        atlas = self.run_cli("atlas", "--help")
        self.assertEqual(atlas.returncode, 0, atlas.stderr)
        self.assertIn("--check", atlas.stdout)

        run = self.run_cli("run", "--help")
        self.assertEqual(run.returncode, 0, run.stderr)
        for command in (
            "migrate",
            "new",
            "authorize",
            "attempt",
            "evidence",
            "guard",
            "complete",
        ):
            self.assertIn(command, run.stdout)

        run_new = self.run_cli("run", "new", "--help")
        self.assertEqual(run_new.returncode, 0, run_new.stderr)
        for option in (
            "--target-loop",
            "--portfolio",
            "--planned-route",
            "--development-model",
            "--route-preview",
            "--replaced-route-preview",
        ):
            self.assertIn(option, run_new.stdout)

        route_preview = self.run_cli("route", "preview", "--help")
        self.assertEqual(route_preview.returncode, 0, route_preview.stderr)
        for option in (
            "--request-file",
            "--request-digest",
            "--target-loop",
            "--branch-choice",
            "--retry-choice",
            "--replaces-preview",
        ):
            self.assertIn(option, route_preview.stdout)

    def test_route_preview_rejects_ambiguous_choice_syntax_before_io(self) -> None:
        common = (
            "route",
            "preview",
            "--binding",
            "missing-binding.json",
            "--registry",
            "missing-registry.json",
            "--policy",
            "missing-policy.json",
            "--candidate",
            "missing-candidate.json",
            "--repository",
            ".",
            "--preview-id",
            "invalid-choice",
            "--request-digest",
            "sha256:" + ("a" * 64),
            "--target-loop",
            "maintain-cli",
            "--created-at",
            "2026-08-02T08:01:00Z",
            "--output",
            "missing-output.json",
        )

        malformed_branch = self.run_cli(
            *common,
            "--branch-choice",
            "loop-state=transition",
        )
        self.assertEqual(malformed_branch.returncode, 2)
        self.assertIn(
            "--branch-choice must use LOOP:STATE=TRANSITION",
            malformed_branch.stderr,
        )
        self.assertNotIn("missing-binding.json", malformed_branch.stderr)

        negative_retry = self.run_cli(
            *common,
            "--retry-choice",
            "loop:feedback=-1",
        )
        self.assertEqual(negative_retry.returncode, 2)
        self.assertIn(
            "--retry-choice count must be a non-negative integer: -1",
            negative_retry.stderr,
        )
        self.assertNotIn("missing-binding.json", negative_retry.stderr)

        duplicate_branch = self.run_cli(
            *common,
            "--branch-choice",
            "loop:state=first",
            "--branch-choice",
            "loop:state=second",
        )
        self.assertEqual(duplicate_branch.returncode, 2)
        self.assertIn(
            "--branch-choice repeats the same loop and state: loop:state",
            duplicate_branch.stderr,
        )

        duplicate_retry = self.run_cli(
            *common,
            "--retry-choice",
            "loop:feedback=1",
            "--retry-choice",
            "loop:feedback=2",
        )
        self.assertEqual(duplicate_retry.returncode, 2)
        self.assertIn(
            "--retry-choice repeats the same loop and transition: loop:feedback",
            duplicate_retry.stderr,
        )

    def test_route_preview_forwards_explicit_branch_and_retry_choices(self) -> None:
        from concordloom.cli import _cmd_route_preview

        args = SimpleNamespace(
            binding="binding.json",
            registry="registry.json",
            policy="policy.json",
            candidate="candidate.json",
            repository=".",
            development_model="development-model.json",
            preview_id="choice-preview",
            request_ref="task-request",
            request_file=None,
            request_digest="sha256:" + ("a" * 64),
            root_loop="root",
            target_loop=["target"],
            branch_choice=[
                "root:choose-path=choose-target",
                "target:choose-mode=use-safe-mode",
            ],
            retry_choice=["target:retry-check=2"],
            created_at="2026-08-02T08:01:00Z",
            replaces_preview=None,
            output="preview.json",
        )
        documents = {
            "binding": {"active_root_loop_ids": ["root"]},
            "candidate manifest": {},
            "cycle registry": {},
            "policy": {},
        }

        with (
            patch(
                "concordloom.cli._object",
                side_effect=lambda _path, label="artifact": documents[label],
            ),
            patch(
                "concordloom.cli._bound_development_model",
                return_value={},
            ),
            patch("concordloom.run.verify_candidate_manifest"),
            patch(
                "concordloom.route.create_route_preview",
                return_value={"kind": "concordloom.route-preview"},
            ) as create,
            patch(
                "concordloom.cli._safe_route_preview_output",
                return_value=Path("preview.json"),
            ),
            patch("concordloom.cli._save_new_output"),
        ):
            _cmd_route_preview(args)

        self.assertEqual(
            create.call_args.kwargs["branch_choices"],
            {
                "root:choose-path": "choose-target",
                "target:choose-mode": "use-safe-mode",
            },
        )
        self.assertEqual(
            create.call_args.kwargs["retry_choices"],
            {"target:retry-check": 2},
        )

    def test_route_preview_becomes_the_exact_draft_run(self) -> None:
        from concordloom.run import build_candidate_manifest

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source = ROOT / "framework" / "concordloom" / "v9"
            repository = self.make_git_repository(directory)
            request = directory / "request.txt"
            request.write_text("Update the command line interface.\n", encoding="utf-8")
            candidate = self.write_json(
                directory / "candidate.json",
                build_candidate_manifest(
                    repository,
                    manifest_id="route-preview-candidate",
                    generated_at="2026-08-02T08:00:00Z",
                ),
            )
            preview_path = directory / "preview.json"
            preview = self.run_cli(
                "route",
                "preview",
                "--binding",
                str(source / "binding.json"),
                "--registry",
                str(source / "cycle-registry.json"),
                "--policy",
                str(source / "policy.json"),
                "--candidate",
                str(candidate),
                "--repository",
                str(repository),
                "--development-model",
                str(source / "development-model.json"),
                "--preview-id",
                "cli-route-preview",
                "--request-file",
                str(request),
                "--target-loop",
                "maintain-cli",
                "--created-at",
                "2026-08-02T08:01:00Z",
                "--output",
                str(preview_path),
            )
            self.assertEqual(preview.returncode, 0, preview.stderr)
            preview_value = json.loads(preview_path.read_text(encoding="utf-8"))
            self.assertEqual(preview_value["schema_version"], "0.1")
            self.assertEqual(preview_value["status"], "proposed")
            self.assertFalse(preview_value["execution_allowed"])
            self.assertNotIn("Update the command", preview_path.read_text(encoding="utf-8"))

            preview_bytes = preview_path.read_bytes()
            collision = self.run_cli(
                "run",
                "new",
                "--binding",
                str(source / "binding.json"),
                "--registry",
                str(source / "cycle-registry.json"),
                "--policy",
                str(source / "policy.json"),
                "--candidate",
                str(candidate),
                "--development-model",
                str(source / "development-model.json"),
                "--run-id",
                "cli-preview-collision",
                "--root-loop",
                "steward-concordloom",
                "--candidate-author",
                "example-executor",
                "--route-preview",
                str(preview_path),
                "--output",
                str(preview_path),
            )
            self.assertEqual(collision.returncode, 2)
            self.assertIn("cannot replace an input artifact", collision.stderr)
            self.assertEqual(preview_bytes, preview_path.read_bytes())

            card_path = directory / "card.json"
            run = self.run_cli(
                "run",
                "new",
                "--binding",
                str(source / "binding.json"),
                "--registry",
                str(source / "cycle-registry.json"),
                "--policy",
                str(source / "policy.json"),
                "--candidate",
                str(candidate),
                "--development-model",
                str(source / "development-model.json"),
                "--run-id",
                "cli-preview-run",
                "--root-loop",
                "steward-concordloom",
                "--candidate-author",
                "example-executor",
                "--route-preview",
                str(preview_path),
                "--output",
                str(card_path),
            )
            self.assertEqual(run.returncode, 0, run.stderr)
            card = json.loads(card_path.read_text(encoding="utf-8"))
            self.assertEqual(card["status"], "draft")
            self.assertEqual(
                card["route_preview_digest"], preview_value["preview_digest"]
            )
            self.assertEqual(card["planned_route"], preview_value["proposed_route"])
            card_bytes = card_path.read_bytes()
            duplicate_card = self.run_cli(
                "run",
                "new",
                "--binding",
                str(source / "binding.json"),
                "--registry",
                str(source / "cycle-registry.json"),
                "--policy",
                str(source / "policy.json"),
                "--candidate",
                str(candidate),
                "--development-model",
                str(source / "development-model.json"),
                "--run-id",
                "cli-preview-run-duplicate",
                "--root-loop",
                "steward-concordloom",
                "--candidate-author",
                "example-executor",
                "--route-preview",
                str(preview_path),
                "--output",
                str(card_path),
            )
            self.assertEqual(duplicate_card.returncode, 2)
            self.assertIn("already exists", duplicate_card.stderr)
            self.assertEqual(card_bytes, card_path.read_bytes())

            corrected_path = directory / "corrected-preview.json"
            corrected = self.run_cli(
                "route",
                "preview",
                "--binding",
                str(source / "binding.json"),
                "--registry",
                str(source / "cycle-registry.json"),
                "--policy",
                str(source / "policy.json"),
                "--candidate",
                str(candidate),
                "--repository",
                str(repository),
                "--development-model",
                str(source / "development-model.json"),
                "--preview-id",
                "cli-route-preview-correction",
                "--request-file",
                str(request),
                "--target-loop",
                "project-atlas",
                "--created-at",
                "2026-08-02T08:02:00Z",
                "--replaces-preview",
                str(preview_path),
                "--output",
                str(corrected_path),
            )
            self.assertEqual(corrected.returncode, 0, corrected.stderr)
            corrected_value = json.loads(
                corrected_path.read_text(encoding="utf-8")
            )
            corrected_card_path = directory / "corrected-card.json"
            corrected_run = self.run_cli(
                "run",
                "new",
                "--binding",
                str(source / "binding.json"),
                "--registry",
                str(source / "cycle-registry.json"),
                "--policy",
                str(source / "policy.json"),
                "--candidate",
                str(candidate),
                "--development-model",
                str(source / "development-model.json"),
                "--run-id",
                "cli-corrected-preview-run",
                "--root-loop",
                "steward-concordloom",
                "--candidate-author",
                "example-executor",
                "--route-preview",
                str(corrected_path),
                "--replaced-route-preview",
                str(preview_path),
                "--output",
                str(corrected_card_path),
            )
            self.assertEqual(corrected_run.returncode, 0, corrected_run.stderr)
            corrected_card = json.loads(
                corrected_card_path.read_text(encoding="utf-8")
            )
            self.assertEqual(
                corrected_value["preview_digest"],
                corrected_card["route_preview_digest"],
            )
            self.assertEqual(
                corrected_value["proposed_route"],
                corrected_card["planned_route"],
            )

            missing_predecessor = self.run_cli(
                "run",
                "new",
                "--binding",
                str(source / "binding.json"),
                "--registry",
                str(source / "cycle-registry.json"),
                "--policy",
                str(source / "policy.json"),
                "--candidate",
                str(candidate),
                "--development-model",
                str(source / "development-model.json"),
                "--run-id",
                "cli-missing-preview-predecessor",
                "--root-loop",
                "steward-concordloom",
                "--candidate-author",
                "example-executor",
                "--route-preview",
                str(corrected_path),
                "--output",
                str(directory / "missing-predecessor-card.json"),
            )
            self.assertEqual(missing_predecessor.returncode, 2)
            self.assertIn("provided together", missing_predecessor.stderr)

    def test_v10_route_preview_emits_target_plans_in_schema_v02(self) -> None:
        from concordloom.run import build_candidate_manifest

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source = ROOT / "framework" / "concordloom" / "v10"
            repository = self.make_git_repository(directory)
            candidate = self.write_json(
                directory / "candidate.json",
                build_candidate_manifest(
                    repository,
                    manifest_id="v10-route-preview-candidate",
                    generated_at="2026-08-02T13:00:00Z",
                ),
            )
            preview_path = directory / "preview-v02.json"

            preview = self.run_cli(
                "route",
                "preview",
                "--binding",
                str(source / "binding.json"),
                "--registry",
                str(source / "cycle-registry.json"),
                "--policy",
                str(source / "policy.json"),
                "--candidate",
                str(candidate),
                "--repository",
                str(repository),
                "--development-model",
                str(source / "development-model.json"),
                "--preview-id",
                "v10-cli-route-preview",
                "--request-digest",
                "sha256:" + ("b" * 64),
                "--target-loop",
                "maintain-cli",
                "--created-at",
                "2026-08-02T13:01:00Z",
                "--output",
                str(preview_path),
            )

            self.assertEqual(preview.returncode, 0, preview.stderr)
            value = json.loads(preview_path.read_text(encoding="utf-8"))
            self.assertEqual(value["schema_version"], "0.2")
            self.assertEqual(
                value["target_plans"],
                [
                    {
                        "target_loop_id": "maintain-cli",
                        "action_loop_ids": ["maintain-cli"],
                        "branch_choices": [],
                        "retry_choices": [],
                    }
                ],
            )
            self.assertFalse(value["execution_allowed"])

    def test_route_preview_validate_rejects_forged_documents(self) -> None:
        from concordloom.canonical import document_digest, load
        from concordloom.route import create_route_preview
        from concordloom.run import build_candidate_manifest

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            repository = self.make_git_repository(directory)
            source = ROOT / "framework" / "concordloom" / "v9"
            candidate_value = build_candidate_manifest(
                repository,
                manifest_id="validate-preview-candidate",
                generated_at="2026-08-02T08:00:00Z",
            )
            candidate = self.write_json(
                directory / "candidate.json", candidate_value
            )
            binding = load(source / "binding.json")
            registry = load(source / "cycle-registry.json")
            policy = load(source / "policy.json")
            model = load(source / "development-model.json")
            preview_value = create_route_preview(
                binding,
                registry,
                policy,
                candidate_value,
                model,
                preview_id="validate-preview",
                request_digest="sha256:" + ("a" * 64),
                request_ref="request.user.1",
                root_loop_id="steward-concordloom",
                target_loop_ids=["maintain-cli"],
                created_at="2026-08-02T08:01:00Z",
            )

            def validate(path: Path) -> subprocess.CompletedProcess[str]:
                return self.run_cli(
                    "validate",
                    "--input",
                    str(path),
                    "--binding",
                    str(source / "binding.json"),
                    "--registry",
                    str(source / "cycle-registry.json"),
                    "--policy",
                    str(source / "policy.json"),
                    "--candidate",
                    str(candidate),
                    "--development-model",
                    str(source / "development-model.json"),
                    "--repository",
                    str(repository),
                )

            preview = self.write_json(directory / "preview.json", preview_value)
            accepted = validate(preview)
            self.assertEqual(accepted.returncode, 0, accepted.stderr)

            bad_digest = dict(preview_value)
            bad_digest["preview_digest"] = "sha256:" + ("f" * 64)
            result = validate(
                self.write_json(directory / "bad-digest.json", bad_digest)
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("digest contract", result.stderr)

            forged_route = json.loads(json.dumps(preview_value))
            forged_route["proposed_route"].reverse()
            forged_route["preview_digest"] = document_digest(
                forged_route, excluded_fields=["/preview_digest"]
            )
            result = validate(
                self.write_json(directory / "forged-route.json", forged_route)
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("exact deterministic route", result.stderr)

            wrong_pin = json.loads(json.dumps(preview_value))
            wrong_pin["binding_digest"] = "sha256:" + ("0" * 64)
            wrong_pin["preview_digest"] = document_digest(
                wrong_pin, excluded_fields=["/preview_digest"]
            )
            result = validate(
                self.write_json(directory / "wrong-pin.json", wrong_pin)
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("different binding", result.stderr)

    def test_route_preview_output_is_create_only_and_git_ignored(self) -> None:
        from concordloom.run import build_candidate_manifest, verify_candidate_manifest

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source = ROOT / "framework" / "concordloom" / "v9"
            repository = self.make_git_repository(directory)
            candidate_value = build_candidate_manifest(
                repository,
                manifest_id="safe-output-candidate",
                generated_at="2026-08-02T08:00:00Z",
            )
            candidate = self.write_json(
                directory / "candidate.json", candidate_value
            )
            request = directory / "request.txt"
            request.write_text("Update the CLI.\n", encoding="utf-8")

            def preview(
                output: Path,
                *,
                repo: Path = repository,
                manifest: Path = candidate,
                replaces: Path | None = None,
                preview_id: str = "safe-output-preview",
            ) -> subprocess.CompletedProcess[str]:
                arguments = [
                    "route",
                    "preview",
                    "--binding",
                    str(source / "binding.json"),
                    "--registry",
                    str(source / "cycle-registry.json"),
                    "--policy",
                    str(source / "policy.json"),
                    "--candidate",
                    str(manifest),
                    "--repository",
                    str(repo),
                    "--development-model",
                    str(source / "development-model.json"),
                    "--preview-id",
                    preview_id,
                    "--request-file",
                    str(request),
                    "--target-loop",
                    "project-atlas" if replaces else "maintain-cli",
                    "--created-at",
                    "2026-08-02T08:01:00Z",
                ]
                if replaces is not None:
                    arguments.extend(["--replaces-preview", str(replaces)])
                arguments.extend(["--output", str(output)])
                return self.run_cli(*arguments)

            internal = repository / ".concord" / "runs" / "preview.json"
            rejected = preview(internal)
            self.assertEqual(rejected.returncode, 2)
            self.assertIn("explicitly ignored", rejected.stderr)
            self.assertFalse(internal.exists())
            verify_candidate_manifest(repository, candidate_value)

            tracked = repository / "service.py"
            tracked_bytes = tracked.read_bytes()
            rejected = preview(tracked)
            self.assertEqual(rejected.returncode, 2)
            self.assertEqual(tracked_bytes, tracked.read_bytes())

            existing = directory / "existing-preview.json"
            existing.write_text("keep me\n", encoding="utf-8")
            existing_bytes = existing.read_bytes()
            rejected = preview(existing)
            self.assertEqual(rejected.returncode, 2)
            self.assertIn("already exists", rejected.stderr)
            self.assertEqual(existing_bytes, existing.read_bytes())

            base = directory / "base-preview.json"
            created = preview(base)
            self.assertEqual(created.returncode, 0, created.stderr)
            base_bytes = base.read_bytes()
            correction = preview(
                base,
                replaces=base,
                preview_id="same-path-correction",
            )
            self.assertEqual(correction.returncode, 2)
            self.assertEqual(base_bytes, base.read_bytes())

            ignored_parent = directory / "ignored"
            ignored_parent.mkdir()
            ignored_repository = self.make_git_repository(
                ignored_parent, ignore_runs=True
            )
            ignored_candidate_value = build_candidate_manifest(
                ignored_repository,
                manifest_id="ignored-output-candidate",
                generated_at="2026-08-02T08:00:00Z",
            )
            ignored_candidate = self.write_json(
                ignored_parent / "candidate.json", ignored_candidate_value
            )
            ignored_output = (
                ignored_repository / ".concord" / "runs" / "preview.json"
            )
            created = preview(
                ignored_output,
                repo=ignored_repository,
                manifest=ignored_candidate,
                preview_id="ignored-output-preview",
            )
            self.assertEqual(created.returncode, 0, created.stderr)
            self.assertTrue(ignored_output.is_file())
            verify_candidate_manifest(ignored_repository, ignored_candidate_value)

    def test_route_preview_request_is_bounded_regular_and_not_a_link(self) -> None:
        from concordloom.run import build_candidate_manifest

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source = ROOT / "framework" / "concordloom" / "v9"
            repository = self.make_git_repository(directory)
            candidate = self.write_json(
                directory / "candidate.json",
                build_candidate_manifest(
                    repository,
                    manifest_id="request-safety-candidate",
                    generated_at="2026-08-02T08:00:00Z",
                ),
            )

            def preview(request: Path, preview_id: str) -> subprocess.CompletedProcess[str]:
                return self.run_cli(
                    "route",
                    "preview",
                    "--binding",
                    str(source / "binding.json"),
                    "--registry",
                    str(source / "cycle-registry.json"),
                    "--policy",
                    str(source / "policy.json"),
                    "--candidate",
                    str(candidate),
                    "--repository",
                    str(repository),
                    "--development-model",
                    str(source / "development-model.json"),
                    "--preview-id",
                    preview_id,
                    "--request-file",
                    str(request),
                    "--target-loop",
                    "maintain-cli",
                    "--created-at",
                    "2026-08-02T08:01:00Z",
                    "--output",
                    str(directory / f"{preview_id}.json"),
                    timeout=3,
                )

            oversized = directory / "oversized.txt"
            oversized.write_bytes(b"x" * 65_537)
            result = preview(oversized, "oversized-request")
            self.assertEqual(result.returncode, 2)
            self.assertIn("exceeds the 64 KiB", result.stderr)

            request = directory / "request.txt"
            request.write_text("Update the CLI.\n", encoding="utf-8")
            linked = directory / "linked-request.txt"
            linked.symlink_to(request)
            result = preview(linked, "linked-request")
            self.assertEqual(result.returncode, 2)
            self.assertIn("regular, non-symbolic-link", result.stderr)

            fifo = directory / "request.fifo"
            os.mkfifo(fifo)
            result = preview(fifo, "fifo-request")
            self.assertEqual(result.returncode, 2)
            self.assertIn("regular, non-symbolic-link", result.stderr)

    def test_preview_backed_authorize_and_guard_recheck_exact_inputs(self) -> None:
        from concordloom.canonical import load
        from concordloom.route import create_route_preview
        from concordloom.run import build_candidate_manifest, create_run_card

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            repository = self.make_git_repository(directory)
            source = ROOT / "framework" / "concordloom" / "v9"
            binding = load(source / "binding.json")
            registry = load(source / "cycle-registry.json")
            policy = load(source / "policy.json")
            model = load(source / "development-model.json")
            candidate_value = build_candidate_manifest(
                repository,
                manifest_id="guard-preview-candidate",
                generated_at="2026-08-02T08:00:00Z",
            )
            candidate = self.write_json(
                directory / "candidate.json", candidate_value
            )
            first_value = create_route_preview(
                binding,
                registry,
                policy,
                candidate_value,
                model,
                preview_id="guard-preview-a",
                request_digest="sha256:" + ("a" * 64),
                request_ref="request.user.1",
                root_loop_id="steward-concordloom",
                target_loop_ids=["maintain-cli"],
                created_at="2026-08-02T08:01:00Z",
            )
            second_value = create_route_preview(
                binding,
                registry,
                policy,
                candidate_value,
                model,
                preview_id="guard-preview-b",
                request_digest="sha256:" + ("a" * 64),
                request_ref="request.user.1",
                root_loop_id="steward-concordloom",
                target_loop_ids=["project-atlas"],
                created_at="2026-08-02T08:01:00Z",
            )
            first = self.write_json(directory / "preview-a.json", first_value)
            second = self.write_json(directory / "preview-b.json", second_value)
            draft_value = create_run_card(
                binding,
                registry,
                policy,
                candidate_value,
                run_id="guard-preview-run",
                root_loop_id="steward-concordloom",
                candidate_author_principal_ids=["example-executor"],
                development_model=model,
                route_preview=first_value,
            )
            draft = self.write_json(directory / "draft.json", draft_value)
            authorized = directory / "authorized.json"
            result = self.run_cli(
                "run",
                "authorize",
                "--card",
                str(draft),
                "--binding",
                str(source / "binding.json"),
                "--registry",
                str(source / "cycle-registry.json"),
                "--policy",
                str(source / "policy.json"),
                "--candidate",
                str(candidate),
                "--development-model",
                str(source / "development-model.json"),
                "--route-preview",
                str(first),
                "--actor-id",
                "example-operator",
                "--actor-kind",
                "operator",
                "--authority-ref",
                "operator",
                "--authorized-at",
                "2026-08-02T08:02:00Z",
                "--repository",
                str(repository),
                "--output",
                str(authorized),
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            def guard(card: Path, preview: Path) -> subprocess.CompletedProcess[str]:
                return self.run_cli(
                    "run",
                    "guard",
                    "--card",
                    str(card),
                    "--node",
                    "steward-concordloom",
                    "--binding",
                    str(source / "binding.json"),
                    "--registry",
                    str(source / "cycle-registry.json"),
                    "--policy",
                    str(source / "policy.json"),
                    "--candidate",
                    str(candidate),
                    "--repository",
                    str(repository),
                    "--development-model",
                    str(source / "development-model.json"),
                    "--route-preview",
                    str(preview),
                )

            accepted = guard(authorized, first)
            self.assertEqual(accepted.returncode, 0, accepted.stderr)

            swapped_value = json.loads(authorized.read_text(encoding="utf-8"))
            swapped_value["route_preview_digest"] = second_value["preview_digest"]
            swapped_value["planned_route"] = second_value["proposed_route"]
            swapped_value["nodes"] = [
                {
                    "node_id": item["node_id"],
                    "loop_id": item["loop_id"],
                    "status": "pending",
                    "attempts": [],
                    "evidence_ids": [],
                }
                for item in second_value["proposed_route"]
            ]
            swapped = self.write_json(directory / "swapped.json", swapped_value)
            rejected = guard(swapped, second)
            self.assertEqual(rejected.returncode, 2)
            self.assertIn("authorization plan digest", rejected.stderr)

            (repository / "service.py").write_text("answer = 43\n", encoding="utf-8")
            rejected = guard(authorized, first)
            self.assertEqual(rejected.returncode, 2)
            self.assertIn("candidate", rejected.stderr)

    def test_run_new_parses_targeted_and_portfolio_routes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source = ROOT / "framework" / "concordloom" / "v6"
            candidate = self.write_json(
                directory / "candidate.json",
                {
                    "kind": "concordloom.candidate-manifest",
                    "schema_version": "0.1",
                    "id": "cli-route-candidate",
                    "generated_at": "2026-07-27T20:00:00Z",
                    "revision": "a" * 40,
                    "tree_digest": "sha256:" + ("b" * 64),
                    "dirty": False,
                    "files": [],
                },
            )
            common = (
                "run",
                "new",
                "--binding",
                str(source / "binding.json"),
                "--registry",
                str(source / "cycle-registry.json"),
                "--policy",
                str(source / "policy.json"),
                "--candidate",
                str(candidate),
                "--root-loop",
                "steward-concordloom",
                "--candidate-author",
                "example-executor",
            )
            targeted_path = directory / "targeted.json"
            targeted = self.run_cli(
                *common,
                "--run-id",
                "cli-targeted-route",
                "--target-loop",
                "maintain-cli",
                "--target-loop",
                "maintain-article",
                "--output",
                str(targeted_path),
            )
            self.assertEqual(0, targeted.returncode, targeted.stderr)
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
                    for item in json.loads(
                        targeted_path.read_text(encoding="utf-8")
                    )["planned_route"]
                ],
            )

            portfolio_path = directory / "portfolio.json"
            portfolio = self.run_cli(
                *common,
                "--run-id",
                "cli-portfolio-route",
                "--portfolio",
                "--output",
                str(portfolio_path),
            )
            self.assertEqual(0, portfolio.returncode, portfolio.stderr)
            self.assertEqual(
                58,
                len(
                    json.loads(
                        portfolio_path.read_text(encoding="utf-8")
                    )["planned_route"]
                ),
            )

            unknown = self.run_cli(
                *common,
                "--run-id",
                "cli-unknown-route",
                "--target-loop",
                "not-a-loop",
                "--output",
                str(directory / "unknown.json"),
            )
            self.assertEqual(2, unknown.returncode)
            self.assertIn("unknown target loops", unknown.stderr)

    def test_run_new_route_selection_flags_are_mutually_exclusive(self) -> None:
        common = (
            "run",
            "new",
            "--binding",
            "binding.json",
            "--registry",
            "registry.json",
            "--policy",
            "policy.json",
            "--candidate",
            "candidate.json",
            "--run-id",
            "conflicting-route",
            "--root-loop",
            "root",
            "--candidate-author",
            "author",
            "--output",
            "run-card.json",
        )
        for conflicting in (
            ("--target-loop", "leaf", "--portfolio"),
            ("--target-loop", "leaf", "--planned-route", "route.json"),
            ("--target-loop", "leaf", "--route-preview", "preview.json"),
        ):
            result = self.run_cli(*common, *conflicting)
            self.assertEqual(2, result.returncode)
            payload = json.loads(result.stderr)
            self.assertEqual("usage_error", payload["error"]["code"])
            self.assertIn("not allowed with argument", payload["error"]["message"])

        predecessor_without_preview = self.run_cli(
            *common,
            "--replaced-route-preview",
            "previous.json",
        )
        self.assertEqual(2, predecessor_without_preview.returncode)
        self.assertIn(
            "--replaced-route-preview requires --route-preview",
            predecessor_without_preview.stderr,
        )

    def test_usage_errors_are_one_concise_json_object(self) -> None:
        result = self.run_cli("questions")
        self.assertEqual(result.returncode, 2)
        payload = json.loads(result.stderr)
        self.assertEqual(payload["error"]["code"], "usage_error")
        self.assertNotIn("Traceback", result.stderr)

    def test_questions_decide_and_accept_use_explicit_artifact_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            accepted_path, log_path, _ = self.make_accepted_artifacts(directory)
            accepted = json.loads(accepted_path.read_text())
            self.assertEqual(accepted["phase"], "accepted")
            self.assertEqual(accepted["nodes"][0]["status"], "confirmed")
            self.assertEqual(
                json.loads(log_path.read_text())["acceptance"]["state"], "complete"
            )

    def test_propose_accept_design_and_compile_are_separate_steps(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            graph, decisions, policy = self.make_accepted_artifacts(directory)
            proposal = directory / "proposal.json"
            design = directory / "accepted-design.json"
            registry = directory / "registry.json"
            binding_proposal = directory / "binding-proposal.json"
            binding = directory / "binding.json"

            proposed = self.run_cli(
                "propose",
                "--graph",
                str(graph),
                "--decisions",
                str(decisions),
                "--policy",
                str(policy),
                "--design-id",
                "cli-design-proposal",
                "--output",
                str(proposal),
            )
            self.assertEqual(proposed.returncode, 0, proposed.stderr)
            self.assertEqual(json.loads(proposal.read_text())["status"], "proposed")

            accepted = self.run_cli(
                "accept",
                "--proposal",
                str(proposal),
                "--accepted-graph",
                str(graph),
                "--decisions",
                str(decisions),
                "--policy",
                str(policy),
                "--decision-id",
                "accept-cli-loop-design",
                "--actor-id",
                "example-operator",
                "--actor-kind",
                "operator",
                "--authority-ref",
                "operator",
                "--accepted-at",
                "2026-07-24T10:03:00Z",
                "--rationale",
                "Accept this exact loop proposal.",
                "--output",
                str(design),
            )
            self.assertEqual(accepted.returncode, 0, accepted.stderr)
            self.assertEqual(json.loads(design.read_text())["status"], "accepted")

            compiled = self.run_cli(
                "compile",
                "--graph",
                str(graph),
                "--decisions",
                str(decisions),
                "--design-proposal",
                str(proposal),
                "--design",
                str(design),
                "--policy",
                str(policy),
                "--proposal-id",
                "cli-binding-proposal",
                "--created-at",
                "2026-07-24T10:04:00Z",
                "--artifact-root",
                str(directory),
                "--registry-output",
                str(registry),
                "--proposal-output",
                str(binding_proposal),
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertEqual(
                json.loads(registry.read_text())["kind"],
                "concordloom.cycle-registry",
            )
            self.assertEqual(
                json.loads(binding_proposal.read_text())["kind"],
                "concordloom.binding-proposal",
            )

            activated = self.run_cli(
                "activate",
                "--proposal",
                str(binding_proposal),
                "--graph",
                str(graph),
                "--decisions",
                str(decisions),
                "--design-proposal",
                str(proposal),
                "--design",
                str(design),
                "--registry",
                str(registry),
                "--policy",
                str(policy),
                "--binding-id",
                "cli-binding",
                "--decision-id",
                "activate-cli-binding",
                "--actor-id",
                "example-operator",
                "--actor-kind",
                "operator",
                "--authority-ref",
                "operator",
                "--accepted-at",
                "2026-07-24T10:04:30Z",
                "--rationale",
                "Activate the exact compiled proposal.",
                "--output",
                str(binding),
            )
            self.assertEqual(activated.returncode, 0, activated.stderr)
            self.assertEqual(
                json.loads(binding.read_text())["kind"], "concordloom.binding"
            )

    def test_compile_rejects_a_proposal_before_invoking_the_compiler(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            graph = self.write_json(directory / "graph.json", {})
            decisions = self.write_json(directory / "decisions.json", {})
            design = self.write_json(
                directory / "design.json",
                {"kind": "concordloom.loop-design-manifest", "status": "proposed"},
            )
            policy = self.write_json(directory / "policy.json", {})
            proposal = self.write_json(directory / "proposal.json", {})
            result = self.run_cli(
                "compile",
                "--graph",
                str(graph),
                "--decisions",
                str(decisions),
                "--design-proposal",
                str(proposal),
                "--design",
                str(design),
                "--policy",
                str(policy),
                "--created-at",
                "2026-07-24T10:03:00Z",
                "--registry-output",
                str(directory / "registry.json"),
                "--proposal-output",
                str(directory / "binding-proposal.json"),
            )
            self.assertEqual(result.returncode, 2)
            error = json.loads(result.stderr)["error"]
            self.assertIn("operator-accepted", error["message"])
            self.assertFalse((directory / "registry.json").exists())
            self.assertFalse((directory / "binding-proposal.json").exists())

    def test_validate_checks_the_full_generic_digest_chain(self) -> None:
        example = ROOT / "framework" / "generic-sdlc"
        observed = example / "observed-project-graph.json"
        questions = example / "questions.json"
        decisions = example / "decision-log.json"
        accepted = example / "accepted-project-graph.json"
        design_proposal = example / "loop-design-proposal.json"
        design = example / "loop-design.json"
        registry = example / "cycle-registry.json"
        policy = example / "policy.json"
        binding_proposal = example / "binding-proposal.json"
        binding = example / "binding.json"
        catalog = example / "catalog.json"
        evolution_signal = example / "evolution-signal-1.json"
        evolution_proposal = example / "evolution-proposal.json"
        invocations = [
            ("--input", str(observed)),
            ("--input", str(questions), "--graph", str(observed)),
            (
                "--input",
                str(decisions),
                "--graph",
                str(observed),
                "--policy",
                str(policy),
            ),
            (
                "--input",
                str(accepted),
                "--observed-graph",
                str(observed),
                "--decisions",
                str(decisions),
                "--policy",
                str(policy),
            ),
            (
                "--input",
                str(design_proposal),
                "--graph",
                str(accepted),
                "--decisions",
                str(decisions),
                "--policy",
                str(policy),
            ),
            (
                "--input",
                str(design),
                "--graph",
                str(accepted),
                "--proposal",
                str(design_proposal),
                "--decisions",
                str(decisions),
                "--policy",
                str(policy),
            ),
            (
                "--input",
                str(registry),
                "--graph",
                str(accepted),
                "--decisions",
                str(decisions),
                "--proposal",
                str(design_proposal),
                "--design",
                str(design),
                "--policy",
                str(policy),
            ),
            (
                "--input",
                str(binding_proposal),
                "--graph",
                str(accepted),
                "--decisions",
                str(decisions),
                "--proposal",
                str(design_proposal),
                "--design",
                str(design),
                "--registry",
                str(registry),
                "--policy",
                str(policy),
                "--artifact-root",
                str(ROOT),
            ),
            (
                "--input",
                str(binding),
                "--binding-proposal",
                str(binding_proposal),
                "--registry",
                str(registry),
                "--policy",
                str(policy),
                "--artifact-root",
                str(ROOT),
            ),
            (
                "--input",
                str(catalog),
                "--artifact-root",
                str(ROOT),
            ),
            (
                "--input",
                str(evolution_signal),
                "--base-binding",
                str(binding),
            ),
            (
                "--input",
                str(evolution_proposal),
                "--base-binding",
                str(binding),
                "--policy",
                str(policy),
            ),
        ]
        for arguments in invocations:
            with self.subTest(input=arguments[1]):
                result = self.run_cli("validate", *arguments)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_catalog_command_creates_the_initial_append_only_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "catalog.json"
            result = self.run_cli(
                "catalog",
                "--binding",
                str(ROOT / "framework/generic-sdlc/binding.json"),
                "--artifact-root",
                str(ROOT),
                "--catalog-id",
                "cli-catalog",
                "--output",
                str(output),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            catalog = json.loads(output.read_text())
            self.assertEqual(catalog["kind"], "concordloom.catalog")
            self.assertEqual(
                catalog["active_binding_digest"],
                catalog["entries"][0]["binding_digest"],
            )


if __name__ == "__main__":
    unittest.main()
