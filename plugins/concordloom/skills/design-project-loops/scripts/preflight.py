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

from concordloom_cli import CliRoute, install_argv, resolve_route


GIT_TIMEOUT_SECONDS = 15
GIT_OUTPUT_BYTES = 1_048_576
MAX_STATUS_ENTRIES = 10_000
DEFAULT_BINDING_PATHS = (
    ".concord/current-binding.json",
    ".concord/binding.json",
    "concord/binding.json",
)
REPOSITORY_CATALOG_PATH = "framework/concordloom/catalog.json"


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


def _repository_file(root: Path, candidate: Path, label: str) -> tuple[Path, str]:
    candidate = candidate if candidate.is_absolute() else root / candidate
    try:
        resolved = candidate.resolve()
        relative = resolved.relative_to(root)
    except ValueError as exc:
        raise RuntimeError(f"{label} path must remain inside the repository") from exc
    if candidate.is_symlink():
        raise RuntimeError(f"{label} path must not be a symbolic link")
    if not resolved.is_file():
        raise RuntimeError(f"{label} file does not exist: {candidate}")
    if resolved.stat().st_size > GIT_OUTPUT_BYTES:
        raise RuntimeError(
            f"{label} file exceeds the {GIT_OUTPUT_BYTES}-byte onboarding cap"
        )
    return resolved, relative.as_posix()


def _read_object(path: Path, label: str) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot read {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"{label} must be a JSON object")
    return value


def _run_validation(
    route: CliRoute,
    root: Path,
    arguments: list[str],
    label: str,
) -> None:
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        result = subprocess.run(
            [*route.argv, *arguments],
            check=False,
            cwd=root,
            env=route.environment(),
            stdin=subprocess.DEVNULL,
            stdout=stdout,
            stderr=stderr,
            timeout=GIT_TIMEOUT_SECONDS,
        )
        stdout_size = stdout.tell()
        stderr_size = stderr.tell()
        if stdout_size > GIT_OUTPUT_BYTES or stderr_size > GIT_OUTPUT_BYTES:
            raise RuntimeError(
                f"{label} validation output exceeded the "
                f"{GIT_OUTPUT_BYTES}-byte onboarding cap"
            )
        stdout.seek(0)
        stderr.seek(0)
        output = stdout.read().decode("utf-8", errors="replace").strip()
        error = stderr.read().decode("utf-8", errors="replace").strip()
    if result.returncode:
        detail = error or output or "validation command failed"
        raise RuntimeError(f"{label} validation failed: {detail}")


def _artifact_path(
    root: Path,
    binding: dict[str, object],
    role: str,
) -> Path:
    artifacts = binding.get("artifacts")
    if not isinstance(artifacts, list):
        raise RuntimeError("binding artifacts must be an array")
    matches = [
        item.get("path")
        for item in artifacts
        if isinstance(item, dict) and item.get("role") == role
    ]
    if len(matches) != 1 or not isinstance(matches[0], str):
        raise RuntimeError(f"binding must name exactly one {role} artifact")
    path, _ = _repository_file(root, Path(matches[0]), role)
    return path


def _validate_binding(
    root: Path,
    candidate: Path,
    route: CliRoute,
) -> tuple[str, str]:
    binding_path, relative = _repository_file(root, candidate, "binding")
    binding = _read_object(binding_path, "binding")
    if binding.get("kind") != "concordloom.binding":
        raise RuntimeError("binding candidate is not a Concord Loom binding")
    digest = binding.get("binding_digest")
    if not isinstance(digest, str) or not digest.startswith("sha256:"):
        raise RuntimeError("binding candidate has no valid binding_digest")

    proposal, _ = _repository_file(
        root,
        binding_path.parent / "binding-proposal.json",
        "binding proposal",
    )
    registry = _artifact_path(root, binding, "cycle_registry")
    policy = _artifact_path(root, binding, "policy")
    _run_validation(
        route,
        root,
        [
            "validate",
            "--input",
            str(binding_path),
            "--binding-proposal",
            str(proposal),
            "--registry",
            str(registry),
            "--policy",
            str(policy),
            "--artifact-root",
            str(root),
        ],
        "binding",
    )
    return relative, digest


def _catalog_binding(
    root: Path,
    route: CliRoute,
) -> tuple[str, str] | None:
    catalog_candidate = root / REPOSITORY_CATALOG_PATH
    if not (catalog_candidate.exists() or catalog_candidate.is_symlink()):
        return None
    catalog_path, _ = _repository_file(root, catalog_candidate, "catalog")
    catalog = _read_object(catalog_path, "catalog")
    _run_validation(
        route,
        root,
        [
            "validate",
            "--input",
            str(catalog_path),
            "--artifact-root",
            str(root),
        ],
        "catalog",
    )

    active_digest = catalog.get("active_binding_digest")
    entries = catalog.get("entries")
    if (
        not isinstance(active_digest, str)
        or not active_digest.startswith("sha256:")
        or not isinstance(entries, list)
        or not entries
        or not isinstance(entries[-1], dict)
    ):
        raise RuntimeError("catalog does not contain a valid active head")
    head = entries[-1]
    if head.get("binding_digest") != active_digest:
        raise RuntimeError("catalog tail does not match active_binding_digest")
    path = head.get("path")
    if not isinstance(path, str) or not path:
        raise RuntimeError("active catalog entry does not name an exact binding path")
    relative, binding_digest = _validate_binding(root, Path(path), route)
    if binding_digest != active_digest:
        raise RuntimeError("active binding digest does not match the catalog head")
    return relative, binding_digest


def _binding(
    root: Path,
    explicit: Path | None,
    route: CliRoute,
) -> tuple[str | None, str, str | None]:
    if explicit is not None:
        candidate = explicit if explicit.is_absolute() else root / explicit
        relative, digest = _validate_binding(root, candidate, route)
        return relative, "validated", digest

    catalog_binding = _catalog_binding(root, route)
    if catalog_binding is not None:
        relative, digest = catalog_binding
        return relative, "validated", digest

    candidates = [
        root / relative
        for relative in DEFAULT_BINDING_PATHS
        if (root / relative).exists() or (root / relative).is_symlink()
    ]
    if len(candidates) > 1:
        names = ", ".join(str(path) for path in candidates)
        raise RuntimeError(
            f"multiple binding candidates found ({names}); pass --binding explicitly"
        )
    if not candidates:
        return None, "absent", None
    relative, digest = _validate_binding(root, candidates[0], route)
    return relative, "validated", digest


def inspect(repo: Path, binding: Path | None = None) -> dict[str, object]:
    root = Path(git(repo, "rev-parse", "--show-toplevel")).resolve()
    revision = git(root, "rev-parse", "HEAD")
    status = git(root, "status", "--porcelain=v1", "--untracked-files=all")
    entries = len(status.splitlines()) if status else 0
    if entries > MAX_STATUS_ENTRIES:
        raise RuntimeError(
            f"Git status exceeded the {MAX_STATUS_ENTRIES}-entry discovery cap"
        )
    route = resolve_route()
    if route is None and (
        binding is not None
        or (root / REPOSITORY_CATALOG_PATH).exists()
        or (root / REPOSITORY_CATALOG_PATH).is_symlink()
        or any(
            (root / path).exists() or (root / path).is_symlink()
            for path in DEFAULT_BINDING_PATHS
        )
    ):
        raise RuntimeError(
            "a binding or catalog exists, but the matching Concord Loom CLI "
            "is unavailable for validation"
        )
    binding_path, binding_status, binding_digest = (
        _binding(root, binding, route)
        if route is not None
        else (None, "absent", None)
    )
    mode = (
        "bound-governance"
        if binding_path is not None
        else "bootstrap-discovery"
    )
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
        "binding_digest": binding_digest,
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
            "Exact binding path. Without one, preflight validates a repository "
            "catalog or known local binding before considering bootstrap."
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
