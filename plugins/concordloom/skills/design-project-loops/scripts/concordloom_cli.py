#!/usr/bin/env python3
"""Run the Concord Loom CLI from this release without PATH assumptions."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Sequence


RELEASE_VERSION = "0.1.0"
RELEASE_ARCHIVE = (
    "https://github.com/concordloom/concordloom/"
    f"archive/refs/tags/v{RELEASE_VERSION}.zip"
)


@dataclass(frozen=True)
class CliRoute:
    """One supported, version-matched way to invoke the CLI."""

    kind: str
    argv: tuple[str, ...]
    source_root: str | None = None

    def environment(self) -> dict[str, str]:
        environment = os.environ.copy()
        if self.source_root is not None:
            # Do not inherit an unrelated package path into the bundled
            # same-checkout route.
            environment["PYTHONPATH"] = str(Path(self.source_root) / "src")
        return environment

    def report(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "argv": list(self.argv),
            "source_root": self.source_root,
        }


def install_argv() -> tuple[str, ...]:
    """Return the explicit install path for this plugin's matching release."""

    return (
        sys.executable,
        "-m",
        "pip",
        "install",
        RELEASE_ARCHIVE,
    )


def _source_checkout(start: Path) -> Path | None:
    """Find the bounded same-repository distribution containing this plugin."""

    current = start.resolve()
    for _ in range(8):
        if (
            (current / "pyproject.toml").is_file()
            and (current / "src" / "concordloom" / "__main__.py").is_file()
            and (
                current
                / "plugins"
                / "concordloom"
                / ".codex-plugin"
                / "plugin.json"
            ).is_file()
        ):
            return current
        if current.parent == current:
            break
        current = current.parent
    return None


def resolve_route(script: Path | None = None) -> CliRoute | None:
    """Prefer the exact same-checkout CLI, then an installed executable."""

    source = _source_checkout((script or Path(__file__)).parent)
    if source is not None:
        return CliRoute(
            kind="same-release-source",
            argv=(sys.executable, "-P", "-m", "concordloom"),
            source_root=str(source),
        )

    executable = shutil.which("concordloom")
    if executable is not None:
        return CliRoute(kind="installed-command", argv=(executable,))
    return None


def missing_dependency_report() -> dict[str, object]:
    return {
        "ready": False,
        "error": (
            "Concord Loom CLI v0.1 is unavailable. Install the plugin's "
            "matching release, then rerun preflight."
        ),
        "install_argv": list(install_argv()),
        "retry_argv": [sys.executable, str(Path(__file__)), "--resolve"],
    }


def main(arguments: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if arguments is None else arguments)
    route = resolve_route()

    if args == ["--install-command"]:
        print(json.dumps({"install_argv": list(install_argv())}, sort_keys=True))
        return 0
    if args == ["--resolve"]:
        if route is None:
            print(json.dumps(missing_dependency_report(), sort_keys=True))
            return 3
        print(json.dumps({"ready": True, "route": route.report()}, sort_keys=True))
        return 0
    if route is None:
        print(
            json.dumps(missing_dependency_report(), sort_keys=True),
            file=sys.stderr,
        )
        return 3

    completed = subprocess.run(
        [*route.argv, *args],
        check=False,
        env=route.environment(),
    )
    return completed.returncode


if __name__ == "__main__":
    sys.exit(main())
