from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def run_cli(
        self, *arguments: str, cwd: Path | None = None
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
        )

    def write_json(self, path: Path, value: object) -> Path:
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return path

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
        for command in ("new", "authorize", "attempt", "evidence", "guard", "complete"):
            self.assertIn(command, run.stdout)

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
