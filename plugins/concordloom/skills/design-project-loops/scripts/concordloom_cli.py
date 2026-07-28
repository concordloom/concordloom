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


RELEASE_VERSION = "0.1.5"
RELEASE_SPEC = (
    "concordloom @ "
    "git+https://github.com/concordloom/concordloom"
    f"@v{RELEASE_VERSION}"
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


def _managed_venv() -> Path:
    data_home = os.environ.get("XDG_DATA_HOME")
    base = Path(data_home) if data_home else Path.home() / ".local" / "share"
    return base / "concordloom" / "venvs" / RELEASE_VERSION


def _venv_executable(venv: Path, name: str) -> Path:
    if os.name == "nt":
        return venv / "Scripts" / f"{name}.exe"
    return venv / "bin" / name


def installation_plan() -> dict[str, object]:
    """Return one safe, pinned installation route without executing it."""

    pipx = shutil.which("pipx")
    if pipx is not None:
        commands = [[pipx, "install", RELEASE_SPEC]]
        kind = "pipx"
    else:
        uv = shutil.which("uv")
        if uv is not None:
            commands = [[uv, "tool", "install", RELEASE_SPEC]]
            kind = "uv-tool"
        else:
            venv = _managed_venv()
            commands = [
                [sys.executable, "-m", "venv", str(venv)],
                [
                    str(_venv_executable(venv, "python")),
                    "-m",
                    "pip",
                    "install",
                    RELEASE_SPEC,
                ],
            ]
            kind = "isolated-venv"
    return {
        "kind": kind,
        "commands": commands,
        "release": RELEASE_VERSION,
        "requires_operator_approval": True,
        "network": "read",
        "repository_writes": 0,
    }


def install_argv() -> tuple[str, ...]:
    """Return the first command for older callers of the launcher contract."""

    plan = installation_plan()
    commands = plan["commands"]
    assert isinstance(commands, list) and commands
    return tuple(commands[0])


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
    managed = _venv_executable(_managed_venv(), "concordloom")
    if managed.is_file():
        return CliRoute(kind="managed-venv", argv=(str(managed),))
    return None


def missing_dependency_report() -> dict[str, object]:
    plan = installation_plan()
    return {
        "ready": False,
        "error": (
            "Concord Loom CLI v0.1 is unavailable. Present install_plan to "
            "the operator, obtain approval, execute every command exactly, "
            "then rerun preflight."
        ),
        "install_plan": plan,
        "install_argv": list(install_argv()),
        "retry_argv": [sys.executable, str(Path(__file__)), "--resolve"],
    }


def main(arguments: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if arguments is None else arguments)
    route = resolve_route()

    if args in (["--install-command"], ["--install-plan"]):
        print(
            json.dumps(
                {
                    "install_plan": installation_plan(),
                    "install_argv": list(install_argv()),
                },
                sort_keys=True,
            )
        )
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
