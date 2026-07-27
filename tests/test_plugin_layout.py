from __future__ import annotations

import json
import os
import re
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
        self.assertEqual(manifest["version"], "0.1.0")
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
        ):
            self.assertIn(phrase, content)

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
        self.assertEqual(before, after)
        self.assertFalse((repo / ".concord").exists())

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
        self.assertIn("install_argv", commands)
        self.assertIn(
            "https://github.com/concordloom/concordloom/",
            LAUNCHER.read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
