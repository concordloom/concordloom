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
        self.assertEqual(manifest["version"], "0.1.1")
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
            "creating that binding ends bootstrap",
            "scripts/concordloom_cli.py",
            "run `activate` only as a separate capable operator",
            "payload against real bytes",
            "model-routing.md",
            "least costly eligible route",
            "input and output tokens",
            "install_plan",
            "Never use a system `pip`",
        ):
            self.assertIn(phrase, content)

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
            re.compile(r'default_prompt: "Use \$design-project-loops '),
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
            self.assertIn("@v0.1.1", serialized)
            self.assertNotIn("--break-system-packages", serialized)

    def test_install_plan_falls_back_to_a_dedicated_venv(self) -> None:
        plan = self._installation_plan()
        commands = plan["commands"]

        self.assertEqual(plan["kind"], "isolated-venv")
        self.assertEqual(commands[0][1:3], ["-m", "venv"])
        self.assertEqual(commands[1][1:4], ["-m", "pip", "install"])
        self.assertIn("concordloom/venvs/0.1.1", commands[0][3])
        self.assertIn("@v0.1.1", commands[1][-1])
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
