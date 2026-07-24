from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from concordloom.inspect_repo import InspectionLimits, inspect_repository
from concordloom.interview import generate_questions
from concordloom.schema import validate_named


class InspectionInterviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Concord Test")
        self.git("config", "user.email", "concord@example.invalid")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def git(
        self, *arguments: str, date: str | None = None
    ) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        if date is not None:
            environment["GIT_AUTHOR_DATE"] = date
            environment["GIT_COMMITTER_DATE"] = date
        return subprocess.run(
            ["git", "-C", str(self.root), *arguments],
            env=environment,
            check=True,
            text=True,
            capture_output=True,
        )

    def commit(self, message: str, date: str) -> None:
        self.git("add", ".")
        self.git("commit", "-m", message, date=date)

    def seed_clean_repository(self) -> None:
        (self.root / "src").mkdir()
        (self.root / "tests").mkdir()
        (self.root / "src" / "helper.py").write_text(
            "VALUE = 1\n", encoding="utf-8"
        )
        (self.root / "src" / "app.py").write_text(
            "import src.helper\n\nprint(src.helper.VALUE)\n", encoding="utf-8"
        )
        (self.root / "tests" / "test_app.py").write_text(
            "def test_value():\n    assert 1 == 1\n", encoding="utf-8"
        )
        self.commit("initial", "2026-07-24T10:00:00Z")

    def test_clean_inspection_is_deterministic_and_schema_valid(self) -> None:
        self.seed_clean_repository()

        first = inspect_repository(self.root)
        second = inspect_repository(self.root)

        self.assertEqual(first, second)
        validate_named(first)
        self.assertFalse(first["repository"]["dirty"])
        self.assertEqual(first["coverage"]["truncated"], [])
        paths = {node["path"]: node for node in first["nodes"]}
        self.assertEqual(paths["src/app.py"]["category"], "source")
        self.assertEqual(paths["tests/test_app.py"]["category"], "test")
        self.assertEqual(paths["src/app.py"]["languages"], ["Python"])
        self.assertTrue(
            any(edge["kind"] == "imports" for edge in first["edges"])
        )

    def test_history_and_subprocess_truncation_are_visible(self) -> None:
        self.seed_clean_repository()
        (self.root / "src" / "helper.py").write_text(
            "VALUE = 2\n", encoding="utf-8"
        )
        self.commit("second", "2026-07-24T10:01:00Z")
        (self.root / "src" / "helper.py").write_text(
            "VALUE = 3\n", encoding="utf-8"
        )
        self.commit("third", "2026-07-24T10:02:00Z")

        history_limited = inspect_repository(
            self.root, limits=InspectionLimits(max_history_commits=1)
        )
        validate_named(history_limited)
        self.assertIn("history", history_limited["coverage"]["truncated"])
        self.assertEqual(history_limited["coverage"]["history_commits_seen"], 1)
        self.assertIn(
            "inspection-coverage-acceptance",
            {item["id"] for item in history_limited["hypotheses"]},
        )

        long_path = "z" * 180 + ".py"
        (self.root / long_path).write_text("VALUE = 4\n", encoding="utf-8")
        self.commit("long path", "2026-07-24T10:03:00Z")
        output_limited = inspect_repository(
            self.root,
            limits=InspectionLimits(
                max_history_commits=1,
                max_subprocess_bytes=128,
            ),
        )
        validate_named(output_limited)
        self.assertIn(
            "subprocess-output", output_limited["coverage"]["truncated"]
        )

    def test_untracked_files_require_explicit_opt_in_but_are_counted(self) -> None:
        self.seed_clean_repository()
        (self.root / "scratch.py").write_text("SECRET = False\n", encoding="utf-8")

        excluded = inspect_repository(self.root)
        included = inspect_repository(self.root, include_untracked=True)

        validate_named(excluded)
        validate_named(included)
        self.assertTrue(excluded["repository"]["dirty"])
        self.assertEqual(excluded["coverage"]["untracked_files_seen"], 1)
        self.assertNotIn("scratch.py", {node["path"] for node in excluded["nodes"]})
        self.assertIn("scratch.py", {node["path"] for node in included["nodes"]})
        self.assertNotEqual(
            excluded["repository"]["tree_digest"],
            included["repository"]["tree_digest"],
        )

    def test_repository_config_cannot_execute_hooks_fsmonitor_or_external_diff(
        self,
    ) -> None:
        self.seed_clean_repository()
        marker = self.root / "executed-marker"
        hostile = self.root / "hostile.sh"
        hostile.write_text(
            "#!/bin/sh\nprintf executed >> \"$1\"\n",
            encoding="utf-8",
        )
        hostile.chmod(0o755)
        hook_dir = self.root / "hooks"
        hook_dir.mkdir()
        hook = hook_dir / "post-index-change"
        hook.write_text(
            f"#!/bin/sh\nprintf hook >> {marker!s}\n",
            encoding="utf-8",
        )
        hook.chmod(0o755)
        # fsmonitor and external diff receive Git-defined arguments; either
        # execution is a failure, so each script writes a fixed marker.
        fixed_hostile = self.root / "fixed-hostile.sh"
        fixed_hostile.write_text(
            f"#!/bin/sh\nprintf config >> {marker!s}\nexit 1\n",
            encoding="utf-8",
        )
        fixed_hostile.chmod(0o755)
        self.git("config", "core.hooksPath", str(hook_dir))
        self.git("config", "core.fsmonitor", str(fixed_hostile))
        self.git("config", "diff.external", str(fixed_hostile))

        graph = inspect_repository(self.root, include_untracked=False)

        validate_named(graph)
        self.assertFalse(marker.exists())

    def test_questions_are_ranked_deterministically_and_schema_valid(self) -> None:
        self.seed_clean_repository()
        graph = inspect_repository(self.root)

        first = generate_questions(graph)
        second = generate_questions(graph)

        self.assertEqual(first, second)
        validate_named(first)
        self.assertEqual(first["kind"], "concordloom.question-set")
        self.assertGreaterEqual(len(first["questions"]), 1)
        for question in first["questions"]:
            verdicts = {option["verdict"] for option in question["options"]}
            self.assertEqual(
                verdicts, {"confirmed", "rejected", "corrected"}
            )
            for option in question["options"]:
                self.assertIn("graph_delta", option)


if __name__ == "__main__":
    unittest.main()
