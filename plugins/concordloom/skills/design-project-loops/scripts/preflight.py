#!/usr/bin/env python3
"""Report the bounded, non-authorizing Concord Loom onboarding lane."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from concordloom_cli import install_argv, resolve_route


GIT_TIMEOUT_SECONDS = 15
GIT_OUTPUT_BYTES = 1_048_576
MAX_STATUS_ENTRIES = 10_000
DEFAULT_BINDING_PATHS = (
    ".concord/current-binding.json",
    ".concord/binding.json",
    "concord/binding.json",
)


def git(repo: Path, *args: str) -> str:
    executable = shutil.which("git")
    if executable is None:
        raise RuntimeError("git is not available on PATH")
    environment = {
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_PAGER": "cat",
        "GIT_TERMINAL_PROMPT": "0",
        "HOME": os.environ.get("HOME", ""),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PATH": os.environ.get("PATH", ""),
    }
    command = [
        executable,
        "-c",
        "core.hooksPath=/dev/null",
        "-c",
        "core.pager=cat",
        "-c",
        "interactive.diffFilter=",
        "-c",
        "diff.external=",
        "-c",
        "core.fsmonitor=false",
        "-C",
        str(repo),
        *args,
    ]
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        result = subprocess.run(
            command,
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=stdout,
            stderr=stderr,
            timeout=GIT_TIMEOUT_SECONDS,
            env=environment,
        )
        stdout_size = stdout.tell()
        stderr_size = stderr.tell()
        if stdout_size > GIT_OUTPUT_BYTES or stderr_size > GIT_OUTPUT_BYTES:
            raise RuntimeError(
                f"Git output exceeded the {GIT_OUTPUT_BYTES}-byte discovery cap"
            )
        stdout.seek(0)
        stderr.seek(0)
        output = stdout.read().decode("utf-8", errors="strict").rstrip("\n")
        error = stderr.read().decode("utf-8", errors="replace").strip()
    if result.returncode:
        detail = error or "Git command failed"
        raise RuntimeError(detail)
    return output


def _binding(
    root: Path,
    explicit: Path | None,
) -> tuple[str | None, str]:
    if explicit is not None:
        candidate = explicit if explicit.is_absolute() else root / explicit
        candidates = [candidate]
    else:
        candidates = [
            root / relative
            for relative in DEFAULT_BINDING_PATHS
            if (root / relative).exists()
        ]
    if len(candidates) > 1:
        names = ", ".join(str(path) for path in candidates)
        raise RuntimeError(
            f"multiple binding candidates found ({names}); pass --binding explicitly"
        )
    if not candidates:
        return None, "absent"

    candidate = candidates[0]
    try:
        relative = candidate.resolve().relative_to(root)
    except ValueError as exc:
        raise RuntimeError("binding path must remain inside the repository") from exc
    if candidate.is_symlink():
        raise RuntimeError("binding path must not be a symbolic link")
    if not candidate.is_file():
        raise RuntimeError(f"binding file does not exist: {candidate}")
    if candidate.stat().st_size > GIT_OUTPUT_BYTES:
        raise RuntimeError(
            f"binding file exceeds the {GIT_OUTPUT_BYTES}-byte onboarding cap"
        )
    try:
        value = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot read binding candidate: {exc}") from exc
    if not isinstance(value, dict) or value.get("kind") != "concordloom.binding":
        raise RuntimeError(
            "binding candidate is not a Concord Loom binding; validate the exact "
            "artifact with the CLI"
        )
    return relative.as_posix(), "present-unvalidated"


def inspect(repo: Path, binding: Path | None = None) -> dict[str, object]:
    root = Path(git(repo, "rev-parse", "--show-toplevel")).resolve()
    revision = git(root, "rev-parse", "HEAD")
    status = git(root, "status", "--porcelain=v1", "--untracked-files=all")
    entries = len(status.splitlines()) if status else 0
    if entries > MAX_STATUS_ENTRIES:
        raise RuntimeError(
            f"Git status exceeded the {MAX_STATUS_ENTRIES}-entry discovery cap"
        )
    binding_path, binding_status = _binding(root, binding)
    route = resolve_route()
    mode = "bound" if binding_path is not None else "bootstrap-discovery"
    return {
        "artifact_kind": "concordloom.skill-preflight",
        "schema_version": 1,
        "repository_root": str(root),
        "revision": revision,
        "dirty": bool(status),
        "status_entries": entries,
        "mode": mode,
        "binding_path": binding_path,
        "binding_status": binding_status,
        "authority_granted": False,
        "repository_mutation_allowed": False,
        "discovery_limits": {
            "git_commands": 3,
            "git_timeout_seconds": GIT_TIMEOUT_SECONDS,
            "git_output_bytes_per_stream": GIT_OUTPUT_BYTES,
            "status_entries": MAX_STATUS_ENTRIES,
            "repository_writes": 0,
            "network_calls": 0,
            "external_mutations": 0,
        },
        "bootstrap_exit": (
            "explicit operator acceptance and a content-addressed first binding"
            if mode == "bootstrap-discovery"
            else None
        ),
        "cli_route": route.report() if route is not None else None,
        "install_argv": list(install_argv()) if route is None else None,
        "ready": route is not None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Resolve Git identity and the Concord Loom CLI without executing "
            "repository code."
        )
    )
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument(
        "--binding",
        type=Path,
        help=(
            "Exact binding path. Without one, preflight enters the read-only "
            "bootstrap-discovery lane."
        ),
    )
    args = parser.parse_args()
    try:
        report = inspect(args.repo.resolve(), args.binding)
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(
            json.dumps(
                {
                    "artifact_kind": "concordloom.skill-preflight",
                    "schema_version": 1,
                    "ready": False,
                    "error": str(error),
                    "install_argv": list(install_argv()),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 2
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["ready"] else 3


if __name__ == "__main__":
    sys.exit(main())
