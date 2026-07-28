from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "concordloom"
SKILL = PLUGIN / "skills" / "design-project-loops"
LAUNCHER = SKILL / "scripts" / "concordloom_cli.py"
ONBOARD = SKILL / "scripts" / "onboard.py"
RECORD_ANSWER = SKILL / "scripts" / "record_answer.py"


class PluginLayoutTests(unittest.TestCase):
    def _init_repository(self, repo: Path) -> None:
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        subprocess.run(
            ["git", "-C", str(repo), "config", "user.name", "Test"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(repo), "config", "user.email", "test@example.com"],
            check=True,
        )
        (repo / "file.txt").write_text("candidate\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", "file.txt"], check=True)
        subprocess.run(
            ["git", "-C", str(repo), "commit", "-qm", "seed"], check=True
        )

    def _installation_plan(self, *available_tools: str) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            for name in available_tools:
                executable = bin_dir / name
                executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
                executable.chmod(0o755)
            environment = os.environ.copy()
            environment["PATH"] = str(bin_dir)
            environment["HOME"] = str(root / "home")
            environment["XDG_DATA_HOME"] = str(root / "data")
            result = subprocess.run(
                [sys.executable, str(LAUNCHER), "--install-plan"],
                env=environment,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)["install_plan"]

    def test_manifest_and_marketplace_are_linked(self) -> None:
        manifest = json.loads(
            (PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        marketplace = json.loads(
            (ROOT / ".agents" / "plugins" / "marketplace.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(manifest["name"], "concordloom")
        self.assertEqual(manifest["version"], "0.1.5")
        self.assertEqual(manifest["skills"], "./skills/")
        self.assertEqual(manifest["license"], "Apache-2.0")
        self.assertNotIn("[TODO:", json.dumps(manifest))
        self.assertEqual(marketplace["name"], "concordloom")
        self.assertEqual(
            marketplace["plugins"][0]["source"]["path"],
            "./plugins/concordloom",
        )
        self.assertEqual(
            marketplace["plugins"][0]["policy"],
            {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
        )

    def test_skill_metadata_and_authority_guards_are_present(self) -> None:
        content = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(content.startswith("---\nname: design-project-loops\n"))
        self.assertNotIn("[TODO:", content)
        for phrase in (
            "observed",
            "inferred",
            "confirmed",
            "graph operations",
            "Never activate an evolution proposal automatically",
            "effective route",
            "Fail closed",
            "zero-authority, read-only lane",
            "first binding cannot approve its own creation retroactively",
            "scripts/concordloom_cli.py",
            "run `activate` only as a separate capable operator",
            "payload against real bytes",
            "model-routing.md",
            "least costly eligible route",
            "input and output tokens",
            "install_plan",
            "Never use a system `pip`",
            "## 0. Learn how to address the person",
            "communication_locale",
            "Do not infer the answer",
            "Always pass the session's",
            "`--locale en` or `--locale ru`",
            "## Speak plainly and keep the conversation moving",
            "Never mix untranslated English prose",
            "Do not end onboarding with a status report",
            "ask exactly one next question",
            "operator-conversation.md",
            "Do not paste CLI JSON",
            "End with the operator outcome and the one next action",
            "Ask these two short questions one at a time",
            "scripts/onboard.py",
            "ask only whether the map describes the project",
            "Any participant may suggest a correction",
            "Never debug actor kinds",
            "scripts/record_answer.py",
            "Never assemble `decide` arguments by hand",
        ):
            self.assertIn(phrase, content)

        self.assertLess(
            content.index("## 0. Learn how to address the person"),
            content.index("## 1. Build the first Atlas"),
        )

        routing = (SKILL / "references" / "model-routing.md").read_text(
            encoding="utf-8"
        )
        for phrase in (
            "Use `none` for deterministic transforms",
            "planned, actual, and verified routes separately",
            "proposal cannot accept or",
        ):
            self.assertIn(phrase, routing)

        openai_yaml = (SKILL / "agents" / "openai.yaml").read_text(
            encoding="utf-8"
        )
        self.assertRegex(
            openai_yaml,
            re.compile(
                r'default_prompt: "Use \$design-project-loops .*'
                r'Ask for the language and name.*build the draft Atlas'
                r'.*map is correct'
            ),
        )

        conversation = (
            SKILL / "references" / "operator-conversation.md"
        ).read_text(encoding="utf-8")
        conversation_ru = (
            SKILL / "references" / "operator-conversation.ru.md"
        ).read_text(encoding="utf-8")
        for heading in (
            "## Comprehension gate",
            "### Name",
            "### Installation permission",
            "### Read-only inspection",
            "### First Atlas",
            "### Decision recorded",
            "### Project map ready",
            "### Loop design ready",
            "### Activation",
            "### Atlas",
            "### Governed task",
            "### Failure",
            "### Evolution",
            "## Completion rule",
        ):
            self.assertIn(heading, conversation)
        for requirement in (
            "contains at most one primary question",
            "ends with a direct question or one concrete next action",
            "Never expose a raw machine report",
            "Until then, every response must continue the conversation",
        ):
            self.assertIn(requirement, conversation)
        for requirement in (
            "## Проверка понятности",
            "В сообщении не больше одного главного вопроса",
            "Нельзя выдавать сырой машинный отчёт",
            "каждый ответ продолжает разговор одним понятным вопросом",
        ):
            self.assertIn(requirement, conversation_ru)

        commands = (SKILL / "references" / "commands.md").read_text(
            encoding="utf-8"
        )
        commands_ru = (SKILL / "references" / "commands.ru.md").read_text(
            encoding="utf-8"
        )
        for reference in (commands, commands_ru):
            self.assertIn("`--locale en`", reference)
            self.assertIn("`--locale ru`", reference)

        artifact_contract = (
            SKILL / "references" / "artifact-contract.md"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "Communication and presentation locale are display metadata",
            artifact_contract,
        )

    def test_onboarding_builds_a_read_only_russian_draft_atlas(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            self._init_repository(repo)
            (repo / "tests").mkdir()
            (repo / "tests" / "test_demo.py").write_text(
                "def test_demo():\n    assert True\n", encoding="utf-8"
            )
            (repo / "<img src=x onerror=alert(1)>.py").write_text(
                "SAFE = True\n", encoding="utf-8"
            )
            subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
            subprocess.run(
                ["git", "-C", str(repo), "commit", "-qm", "tests"], check=True
            )
            atlas = root / "atlas.html"
            model = root / "model.json"
            before = subprocess.run(
                ["git", "-C", str(repo), "status", "--porcelain=v1"],
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            ).stdout
            result = subprocess.run(
                [
                    sys.executable,
                    str(ONBOARD),
                    "--repo",
                    str(repo),
                    "--locale",
                    "ru",
                    "--person-name",
                    "Михаил",
                    "--output",
                    str(atlas),
                    "--model-output",
                    str(model),
                ],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            after = subprocess.run(
                ["git", "-C", str(repo), "status", "--porcelain=v1"],
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            ).stdout
            html = atlas.read_text(encoding="utf-8")
            payload = json.loads(model.read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(before, after)
        self.assertIn("Подготовлено для: Михаил", html)
        self.assertIn("Эта карта правильно описывает проект?", html)
        self.assertIn("Проверять изменения", html)
        self.assertNotIn("current-operator", html)
        self.assertNotIn("governed delivery boundary", html)
        self.assertNotIn("<img src=x", html)
        self.assertIn("\\u003cimg src=x", html)
        self.assertGreaterEqual(len(payload["loops"]), 2)

    def test_onboarding_rejects_a_cyclic_corrected_model(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = root / "model.json"
            atlas = root / "atlas.html"
            model.write_text(
                json.dumps(
                    {
                        "project": "demo",
                        "person_name": "Mikhail",
                        "revision": "abc",
                        "warnings": [],
                        "loops": [
                            {
                                "id": "first",
                                "parent_id": "second",
                                "label": "First",
                                "purpose": "First loop",
                                "state": "inferred",
                                "evidence": [],
                            },
                            {
                                "id": "second",
                                "parent_id": "first",
                                "label": "Second",
                                "purpose": "Second loop",
                                "state": "inferred",
                                "evidence": [],
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(ONBOARD),
                    "--model",
                    str(model),
                    "--locale",
                    "en",
                    "--person-name",
                    "Mikhail",
                    "--output",
                    str(atlas),
                ],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exactly one root loop", result.stderr)
        self.assertFalse(atlas.exists())

    def test_plain_answer_adapter_records_valid_machine_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            self._init_repository(repo)
            graph = root / "graph.json"
            questions = root / "questions.json"
            decision = root / "decision.json"
            subprocess.run(
                [
                    sys.executable, str(LAUNCHER), "inspect", str(repo),
                    "--output", str(graph),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
            )
            subprocess.run(
                [
                    sys.executable, str(LAUNCHER), "questions",
                    "--graph", str(graph), "--output", str(questions),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
            )
            question_id = json.loads(
                questions.read_text(encoding="utf-8")
            )["questions"][0]["id"]
            result = subprocess.run(
                [
                    sys.executable, str(RECORD_ANSWER),
                    "--questions", str(questions),
                    "--question", question_id,
                    "--answer", "confirm",
                    "--person-name", "Михаил",
                    "--rationale", "Карта проекта верна.",
                    "--output", str(decision),
                ],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            payload = json.loads(decision.read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(payload["decision"]["actor"]["kind"], "operator")
        self.assertEqual(payload["decision"]["actor"]["display_name"], "Михаил")
        self.assertEqual(
            payload["decision"]["authority_ref"], "bootstrap-operator"
        )

    def test_preflight_reports_bounded_bootstrap_without_mutating_repo(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            self._init_repository(repo)
            before = subprocess.run(
                ["git", "-C", str(repo), "status", "--porcelain=v1"],
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            ).stdout

            result = subprocess.run(
                [
                    sys.executable,
                    str(SKILL / "scripts" / "preflight.py"),
                    "--repo",
                    str(repo),
                ],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            report = json.loads(result.stdout)
            after = subprocess.run(
                ["git", "-C", str(repo), "status", "--porcelain=v1"],
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            ).stdout

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["repository_root"], str(repo.resolve()))
        self.assertRegex(report["revision"], r"^[0-9a-f]{40}$")
        self.assertFalse(report["dirty"])
        self.assertEqual(report["status_entries"], 0)
        self.assertEqual(report["mode"], "bootstrap-discovery")
        self.assertEqual(report["binding_status"], "absent")
        self.assertIs(report["authority_granted"], False)
        self.assertIs(report["repository_mutation_allowed"], False)
        self.assertEqual(report["discovery_limits"]["repository_writes"], 0)
        self.assertEqual(report["discovery_limits"]["network_calls"], 0)
        self.assertEqual(report["discovery_limits"]["external_mutations"], 0)
        self.assertEqual(report["cli_route"]["kind"], "same-release-source")
        self.assertIsNone(report["install_plan"])
        self.assertEqual(before, after)
        self.assertFalse((repo / ".concord").exists())

    def test_install_plan_prefers_isolated_tool_installers(self) -> None:
        pipx = self._installation_plan("uv", "pipx")
        self.assertEqual(pipx["kind"], "pipx")
        self.assertEqual(Path(pipx["commands"][0][0]).name, "pipx")

        uv = self._installation_plan("uv")
        self.assertEqual(uv["kind"], "uv-tool")
        self.assertEqual(Path(uv["commands"][0][0]).name, "uv")

        for plan in (pipx, uv):
            self.assertTrue(plan["requires_operator_approval"])
            self.assertEqual(plan["repository_writes"], 0)
            serialized = json.dumps(plan)
            self.assertIn("@v0.1.5", serialized)
            self.assertNotIn("--break-system-packages", serialized)

    def test_install_plan_falls_back_to_a_dedicated_venv(self) -> None:
        plan = self._installation_plan()
        commands = plan["commands"]

        self.assertEqual(plan["kind"], "isolated-venv")
        self.assertEqual(commands[0][1:3], ["-m", "venv"])
        self.assertEqual(commands[1][1:4], ["-m", "pip", "install"])
        self.assertIn("concordloom/venvs/0.1.5", commands[0][3])
        self.assertIn("@v0.1.5", commands[1][-1])
        self.assertNotIn("--break-system-packages", json.dumps(plan))

    def test_preflight_auto_discovers_and_validates_the_catalog_head(self) -> None:
        catalog = json.loads(
            (ROOT / "framework" / "concordloom" / "catalog.json").read_text(
                encoding="utf-8"
            )
        )
        head = catalog["entries"][-1]
        result = subprocess.run(
            [
                sys.executable,
                str(SKILL / "scripts" / "preflight.py"),
                "--repo",
                str(ROOT),
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["mode"], "bound-governance")
        self.assertEqual(report["binding_status"], "validated")
        self.assertEqual(report["binding_path"], head["path"])
        self.assertEqual(report["binding_digest"], head["binding_digest"])
        self.assertIsNone(report["bootstrap_exit"])

        explicit = catalog["entries"][-2]
        explicit_result = subprocess.run(
            [
                sys.executable,
                str(SKILL / "scripts" / "preflight.py"),
                "--repo",
                str(ROOT),
                "--binding",
                explicit["path"],
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        explicit_report = json.loads(explicit_result.stdout)
        self.assertEqual(explicit_result.returncode, 0, explicit_result.stderr)
        self.assertEqual(explicit_report["binding_path"], explicit["path"])
        self.assertEqual(
            explicit_report["binding_digest"],
            explicit["binding_digest"],
        )

    def test_preflight_rejects_malformed_and_stale_catalogs(self) -> None:
        preflight = str(SKILL / "scripts" / "preflight.py")
        with self.subTest("malformed"):
            with tempfile.TemporaryDirectory() as directory:
                repo = Path(directory)
                self._init_repository(repo)
                catalog_path = repo / "framework" / "concordloom" / "catalog.json"
                catalog_path.parent.mkdir(parents=True)
                catalog_path.write_text("{", encoding="utf-8")
                result = subprocess.run(
                    [sys.executable, preflight, "--repo", str(repo)],
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                report = json.loads(result.stdout)

            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertFalse(report["ready"])
            self.assertIn("cannot read catalog", report["error"])

        with self.subTest("stale-head"):
            with tempfile.TemporaryDirectory() as directory:
                repo = Path(directory)
                self._init_repository(repo)
                shutil.copytree(ROOT / "framework", repo / "framework")
                transition = repo / "docs" / ".concord-transition"
                transition.parent.mkdir(parents=True)
                shutil.copytree(
                    ROOT / "docs" / ".concord-transition",
                    transition,
                )
                catalog_path = repo / "framework" / "concordloom" / "catalog.json"
                catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
                catalog["active_binding_digest"] = f"sha256:{'0' * 64}"
                catalog_path.write_text(
                    json.dumps(
                        catalog,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    + "\n",
                    encoding="utf-8",
                )
                result = subprocess.run(
                    [sys.executable, preflight, "--repo", str(repo)],
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                report = json.loads(result.stdout)

            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertFalse(report["ready"])
            self.assertIn("catalog validation failed", report["error"])

    def test_bundled_launcher_works_from_clean_environment_and_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            clean_cwd = Path(directory)
            environment = os.environ.copy()
            environment.pop("PYTHONPATH", None)
            result = subprocess.run(
                [sys.executable, str(LAUNCHER), "--help"],
                cwd=clean_cwd,
                env=environment,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=20,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Discover, negotiate, compile", result.stdout)

        commands = (SKILL / "references" / "commands.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("scripts/concordloom_cli.py", commands)
        self.assertIn("install_plan", commands)
        self.assertIn("install_argv", commands)
        self.assertIn(
            "git+https://github.com/concordloom/concordloom",
            LAUNCHER.read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
