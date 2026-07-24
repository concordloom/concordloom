"""Bounded, read-only Git repository inspection.

The inspector never checks out revisions and never invokes repository code.
It derives a portable graph from index metadata, selected working-tree
metadata, and bounded history queries.
"""

from __future__ import annotations

import ast
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from hashlib import sha256
from itertools import combinations
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
from typing import Any

from .canonical import digest
from .graph import validate_project_graph


class InspectionError(RuntimeError):
    """Repository inspection failed closed."""


@dataclass(frozen=True)
class InspectionLimits:
    max_files: int = 5_000
    max_file_bytes: int = 1_048_576
    max_history_commits: int = 500
    max_paths_per_commit: int = 200
    max_cochange_pairs: int = 20_000
    max_subprocess_bytes: int = 16_777_216
    subprocess_timeout_seconds: int = 30

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            if (
                name == "subprocess_timeout_seconds"
                and isinstance(value, float)
                and value.is_integer()
            ):
                object.__setattr__(self, name, int(value))
                value = int(value)
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                raise InspectionError(f"{name} must be a positive integer")


@dataclass(frozen=True)
class InspectionResult:
    graph: dict[str, Any]
    coverage: dict[str, Any]


@dataclass(frozen=True)
class _CommandResult:
    stdout: bytes
    truncated: bool


LANGUAGES = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".kt": "Kotlin",
    ".cs": "C#",
    ".c": "C",
    ".h": "C",
    ".cc": "C++",
    ".cpp": "C++",
    ".hpp": "C++",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".sh": "Shell",
}
SOURCE_SUFFIXES = set(LANGUAGES)


def _run_git(
    root: Path,
    arguments: list[str],
    limits: InspectionLimits,
    *,
    allow_failure: bool = False,
) -> _CommandResult:
    executable = _git_executable(root)
    command = [
        executable,
        "--no-optional-locks",
        "-c",
        "core.hooksPath=/dev/null",
        "-c",
        "core.fsmonitor=false",
        "-c",
        "diff.external=",
        "-c",
        "pager.branch=false",
        "-c",
        "pager.log=false",
        "-c",
        "pager.show=false",
        "-C",
        str(root),
        *arguments,
    ]
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "LC_ALL": "C",
        "LANG": "C",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_PAGER": "cat",
        "PAGER": "cat",
        "GIT_NO_REPLACE_OBJECTS": "1",
    }
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=stdout,
            stderr=stderr,
            env=environment,
            close_fds=True,
        )
        try:
            return_code = process.wait(timeout=limits.subprocess_timeout_seconds)
        except subprocess.TimeoutExpired as exc:
            process.kill()
            process.wait()
            raise InspectionError(
                f"git command exceeded {limits.subprocess_timeout_seconds}s: "
                f"{arguments[0]}"
            ) from exc
        stdout.seek(0, os.SEEK_END)
        size = stdout.tell()
        truncated = size > limits.max_subprocess_bytes
        stdout.seek(0)
        data = stdout.read(limits.max_subprocess_bytes)
        stderr.seek(0)
        error = stderr.read(min(limits.max_subprocess_bytes, 65_536))
    if return_code != 0 and not allow_failure:
        message = error.decode("utf-8", "replace").strip()
        raise InspectionError(
            f"git {arguments[0]} failed with {return_code}: {message}"
        )
    return _CommandResult(data, truncated)


def _git_executable(root: Path) -> str:
    """Resolve Git without permitting a repository-provided executable."""

    candidates = [Path("/usr/bin/git"), Path("/bin/git")]
    discovered = shutil.which("git")
    if discovered:
        candidates.append(Path(discovered))
    for candidate in candidates:
        if not candidate.is_file():
            continue
        resolved = candidate.resolve()
        try:
            resolved.relative_to(root)
        except ValueError:
            return str(resolved)
    raise InspectionError("no Git executable outside the repository was found")


def _git_text(
    root: Path, arguments: list[str], limits: InspectionLimits
) -> tuple[str, bool]:
    result = _run_git(root, arguments, limits)
    try:
        return result.stdout.decode("utf-8"), result.truncated
    except UnicodeDecodeError as exc:
        raise InspectionError(
            f"git output for {arguments[0]} is not valid UTF-8"
        ) from exc


def _root(path: str | Path, limits: InspectionLimits) -> Path:
    candidate = Path(path).expanduser().resolve()
    text, _ = _git_text(candidate, ["rev-parse", "--show-toplevel"], limits)
    root = Path(text.strip()).resolve()
    if not root.is_dir():
        raise InspectionError(f"not a Git work tree: {path}")
    return root


def _identifier(value: str, fallback: str = "repository") -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not normalized or not normalized[0].isalpha():
        normalized = f"{fallback}-{normalized}" if normalized else fallback
    return normalized


def _node_id(path: str) -> str:
    return "file-" + sha256(path.encode("utf-8")).hexdigest()[:16]


def _category(path: str) -> str:
    lowered = path.lower()
    name = Path(lowered).name
    suffix = Path(lowered).suffix
    if (
        lowered.startswith(("tests/", "test/", "spec/"))
        or "/tests/" in lowered
        or name.startswith(("test_", "spec_"))
        or name.endswith(("_test.py", ".test.js", ".test.ts"))
    ):
        return "test"
    if lowered.startswith((".github/workflows/", ".gitlab/")) or name in {
        "jenkinsfile",
        ".travis.yml",
    }:
        return "ci"
    if "decision" in lowered or lowered.startswith(("adr/", "docs/adr/")):
        return "decision"
    if (
        name in {"agents.md", "codeowners"}
        or ".agents/" in lowered
        or ".codex" in lowered
        or "governance" in lowered
    ):
        return "governance"
    if lowered.startswith(("ops/", "deploy/", "infra/")) or suffix in {
        ".tf",
        ".hcl",
    }:
        return "operations"
    if lowered.startswith("docs/") or suffix in {".md", ".rst", ".adoc"}:
        return "documentation"
    if name in {
        "pyproject.toml",
        "package.json",
        "cargo.toml",
        "go.mod",
        "makefile",
        "cmakelists.txt",
    } or lowered.startswith(("build/", "scripts/build")):
        return "build"
    if suffix in SOURCE_SUFFIXES:
        return "source"
    return "other"


def _parse_index(data: bytes) -> tuple[list[dict[str, str]], bool]:
    records: list[dict[str, str]] = []
    complete = data.endswith(b"\0") or not data
    chunks = data.split(b"\0")
    if not complete:
        chunks = chunks[:-1]
    for raw in chunks:
        if not raw:
            continue
        try:
            metadata, encoded_path = raw.split(b"\t", 1)
            mode, object_id, stage = metadata.decode("ascii").split(" ")
            path = encoded_path.decode("utf-8")
        except (ValueError, UnicodeDecodeError) as exc:
            raise InspectionError("malformed or non-UTF-8 Git index record") from exc
        if stage == "0":
            records.append({"path": path, "mode": mode, "object_id": object_id})
    return records, complete


def _safe_path(root: Path, relative: str) -> Path:
    if not relative or relative.startswith("/") or "\\" in relative:
        raise InspectionError(f"unsafe repository path: {relative!r}")
    parts = Path(relative).parts
    if ".." in parts:
        raise InspectionError(f"path traversal in repository path: {relative!r}")
    target = root.joinpath(*parts)
    try:
        target.parent.resolve().relative_to(root)
    except ValueError as exc:
        raise InspectionError(f"path escapes repository: {relative!r}") from exc
    return target


def _untracked_records(
    root: Path,
    data: bytes,
    limits: InspectionLimits,
    truncated: set[str],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    chunks = data.split(b"\0")
    if data and not data.endswith(b"\0"):
        chunks = chunks[:-1]
        truncated.add("subprocess-output")
    for raw in chunks:
        if not raw:
            continue
        try:
            path = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise InspectionError("untracked path is not valid UTF-8") from exc
        target = _safe_path(root, path)
        info = target.lstat()
        if stat.S_ISLNK(info.st_mode):
            marker = "symlink:" + os.readlink(target)
        elif stat.S_ISREG(info.st_mode) and info.st_size <= limits.max_file_bytes:
            marker = "sha256:" + sha256(target.read_bytes()).hexdigest()
        else:
            marker = f"omitted:{info.st_size}"
            truncated.add("file-bytes")
        records.append(
            {
                "path": path,
                "mode": format(stat.S_IMODE(info.st_mode), "o"),
                "object_id": marker,
                "size": info.st_size,
                "untracked": True,
            }
        )
    return records


def _untracked_paths(data: bytes, truncated: set[str]) -> list[str]:
    chunks = data.split(b"\0")
    if data and not data.endswith(b"\0"):
        chunks = chunks[:-1]
        truncated.add("subprocess-output")
    paths: list[str] = []
    for raw in chunks:
        if not raw:
            continue
        try:
            paths.append(raw.decode("utf-8"))
        except UnicodeDecodeError as exc:
            raise InspectionError("untracked path is not valid UTF-8") from exc
    return paths


def _status_dirty(root: Path, limits: InspectionLimits) -> tuple[bool, bool]:
    result = _run_git(
        root,
        ["status", "--porcelain=v1", "-z", "--untracked-files=all"],
        limits,
    )
    return bool(result.stdout), result.truncated


def _commit_changes(
    root: Path, commit: str, limits: InspectionLimits
) -> tuple[list[tuple[str, str | None, str | None]], bool]:
    result = _run_git(
        root,
        [
            "diff-tree",
            "--root",
            "--no-commit-id",
            "--name-status",
            "-r",
            "-M",
            "-z",
            commit,
        ],
        limits,
    )
    chunks = result.stdout.split(b"\0")
    if result.truncated and result.stdout and not result.stdout.endswith(b"\0"):
        chunks = chunks[:-1]
    tokens = [token for token in chunks if token]
    changes: list[tuple[str, str | None, str | None]] = []
    index = 0
    while index < len(tokens):
        try:
            status_code = tokens[index].decode("ascii")
        except UnicodeDecodeError as exc:
            raise InspectionError("malformed Git history status") from exc
        index += 1
        if status_code.startswith(("R", "C")):
            if index + 1 >= len(tokens):
                break
            old = tokens[index].decode("utf-8")
            new = tokens[index + 1].decode("utf-8")
            index += 2
            changes.append((status_code[0], old, new))
        else:
            if index >= len(tokens):
                break
            path = tokens[index].decode("utf-8")
            index += 1
            changes.append((status_code[:1], path, path))
    return changes, result.truncated


def _file_node(
    path: str,
    *,
    revision: str,
    size: int | None = None,
    object_id: str | None = None,
) -> dict[str, Any]:
    node: dict[str, Any] = {
        "id": _node_id(path),
        "kind": "file",
        "label": path,
        "path": path,
        "category": _category(path),
        "languages": [LANGUAGES[Path(path).suffix.lower()]]
        if Path(path).suffix.lower() in LANGUAGES
        else [],
        "status": "observed",
        "provenance": [{"kind": "file", "ref": path}],
    }
    metrics: dict[str, Any] = {}
    if size is not None:
        metrics["size_bytes"] = size
    if object_id and re.fullmatch(r"[0-9a-f]{40,64}", object_id):
        metrics["index_object_id"] = object_id
    if metrics:
        node["metrics"] = metrics
    return node


def _history(
    root: Path,
    revision: str,
    nodes: dict[str, dict[str, Any]],
    limits: InspectionLimits,
    truncated: set[str],
) -> tuple[list[dict[str, Any]], int]:
    text, output_truncated = _git_text(
        root,
        ["rev-list", f"--max-count={limits.max_history_commits + 1}", revision],
        limits,
    )
    if output_truncated:
        truncated.add("subprocess-output")
    lines = text.splitlines()
    if output_truncated and text and not text.endswith("\n"):
        lines = lines[:-1]
    commits = [line for line in lines if re.fullmatch(r"[0-9a-f]{40,64}", line)]
    if len(commits) > limits.max_history_commits:
        truncated.add("history")
        commits = commits[: limits.max_history_commits]

    churn: Counter[str] = Counter()
    authors: dict[str, set[str]] = defaultdict(set)
    pairs: dict[tuple[str, str], dict[str, Any]] = {}
    rename_edges: list[dict[str, Any]] = []

    for commit in commits:
        changes, command_truncated = _commit_changes(root, commit, limits)
        if command_truncated:
            truncated.add("subprocess-output")
        if len(changes) > limits.max_paths_per_commit:
            truncated.add("paths-per-commit")
            changes = changes[: limits.max_paths_per_commit]
        author, _ = _git_text(root, ["show", "-s", "--format=%an", commit], limits)
        changed_paths: set[str] = set()
        for kind, old, new in changes:
            for path in {old, new} - {None}:
                assert path is not None
                changed_paths.add(path)
                churn[path] += 1
                authors[path].add(author.strip())
                if path not in nodes and len(nodes) < limits.max_files:
                    nodes[path] = _file_node(path, revision=revision)
            if kind == "R" and old and new:
                if old in nodes and new in nodes:
                    rename_edges.append(
                        {
                            "id": "rename-" + sha256(
                                f"{old}\0{new}\0{commit}".encode()
                            ).hexdigest()[:16],
                            "source": _node_id(old),
                            "target": _node_id(new),
                            "kind": "renames_to",
                            "status": "observed",
                            "confidence": 1,
                            "weight": 1,
                            "first_seen": commit,
                            "last_seen": commit,
                            "source_refs": [{"kind": "git_commit", "ref": commit}],
                        }
                    )
        current = sorted(path for path in changed_paths if path in nodes)
        for left, right in combinations(current, 2):
            key = (left, right)
            if key not in pairs and len(pairs) >= limits.max_cochange_pairs:
                truncated.add("cochange-pairs")
                break
            record = pairs.setdefault(
                key, {"weight": 0, "first_seen": commit, "last_seen": commit}
            )
            record["weight"] += 1
            record["first_seen"] = commit

    for path, node in nodes.items():
        metrics = node.setdefault("metrics", {})
        metrics["churn_commits"] = churn[path]
        metrics["author_count"] = len(authors[path])

    edges = rename_edges
    for (left, right), record in sorted(pairs.items()):
        edges.append(
            {
                "id": "cochange-"
                + sha256(f"{left}\0{right}".encode()).hexdigest()[:16],
                "source": _node_id(left),
                "target": _node_id(right),
                "kind": "co_changes",
                "status": "observed",
                "confidence": 1,
                "weight": record["weight"],
                "first_seen": record["first_seen"],
                "last_seen": record["last_seen"],
                "source_refs": [
                    {"kind": "git_commit", "ref": record["last_seen"]}
                ],
            }
        )
    return edges, len(commits)


def _python_import_edges(
    root: Path,
    nodes: dict[str, dict[str, Any]],
    limits: InspectionLimits,
    revision: str,
) -> list[dict[str, Any]]:
    module_paths: dict[str, str] = {}
    for path in nodes:
        if path.endswith(".py"):
            module = path[:-3].replace("/", ".")
            if module.endswith(".__init__"):
                module = module[: -len(".__init__")]
            module_paths[module] = path
    edges: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for path in sorted(nodes):
        if not path.endswith(".py"):
            continue
        target = _safe_path(root, path)
        try:
            info = target.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_size > limits.max_file_bytes:
                continue
            tree = ast.parse(target.read_text(encoding="utf-8"), filename=path)
        except (OSError, UnicodeError, SyntaxError):
            continue
        imported: set[str] = set()
        for item in ast.walk(tree):
            if isinstance(item, ast.Import):
                imported.update(alias.name for alias in item.names)
            elif isinstance(item, ast.ImportFrom) and item.module:
                imported.add(item.module)
        for name in imported:
            candidate = next(
                (
                    module_paths[module]
                    for module in sorted(module_paths, key=len, reverse=True)
                    if name == module or name.startswith(module + ".")
                ),
                None,
            )
            if not candidate or candidate == path or (path, candidate) in seen:
                continue
            seen.add((path, candidate))
            edges.append(
                {
                    "id": "import-"
                    + sha256(f"{path}\0{candidate}".encode()).hexdigest()[:16],
                    "source": _node_id(path),
                    "target": _node_id(candidate),
                    "kind": "imports",
                    "status": "observed",
                    "confidence": 1,
                    "weight": 1,
                    "source_refs": [{"kind": "file", "ref": path}],
                }
            )
    return edges


def inspect_repository_result(
    path: str | Path,
    *,
    limits: InspectionLimits | None = None,
    include_untracked: bool = False,
    generated_at: str | None = None,
) -> InspectionResult:
    """Inspect one local Git work tree and return graph plus coverage."""

    limits = limits or InspectionLimits()
    root = _root(path, limits)
    revision, revision_truncated = _git_text(root, ["rev-parse", "HEAD"], limits)
    revision = revision.strip()
    if not re.fullmatch(r"[0-9a-f]{40}(?:[0-9a-f]{24})?", revision):
        raise InspectionError("repository HEAD is not a supported Git object id")
    timestamp, _ = _git_text(root, ["show", "-s", "--format=%cI", revision], limits)
    index_result = _run_git(root, ["ls-files", "--stage", "-z"], limits)
    index, index_complete = _parse_index(index_result.stdout)
    truncated: set[str] = set()
    if revision_truncated or index_result.truncated or not index_complete:
        truncated.add("subprocess-output")
    tracked_count = len(index)
    if len(index) > limits.max_files:
        truncated.add("files")
        index = index[: limits.max_files]

    records: list[dict[str, Any]] = list(index)
    extra_result = _run_git(
        root, ["ls-files", "--others", "--exclude-standard", "-z"], limits
    )
    if extra_result.truncated:
        truncated.add("subprocess-output")
    untracked_paths = _untracked_paths(extra_result.stdout, truncated)
    untracked_count = len(untracked_paths)
    if include_untracked and len(records) < limits.max_files:
        room = limits.max_files - len(records)
        if len(untracked_paths) > room:
            truncated.add("files")
        selected = b"\0".join(
            repository_path.encode("utf-8")
            for repository_path in untracked_paths[:room]
        )
        if selected:
            selected += b"\0"
        records.extend(_untracked_records(root, selected, limits, truncated))

    dirty, status_truncated = _status_dirty(root, limits)
    if status_truncated:
        truncated.add("subprocess-output")
    node_map: dict[str, dict[str, Any]] = {}
    for record in records:
        repository_path = _safe_path(root, str(record["path"]))
        try:
            size = repository_path.lstat().st_size
        except OSError:
            size = None
        node_map[str(record["path"])] = _file_node(
            str(record["path"]),
            revision=revision,
            size=size,
            object_id=str(record["object_id"]),
        )

    history_edges, history_commits_seen = _history(
        root, revision, node_map, limits, truncated
    )
    import_edges = _python_import_edges(root, node_map, limits, revision)
    coverage = {
        "tracked_files_seen": tracked_count,
        "untracked_files_seen": untracked_count,
        "history_commits_seen": history_commits_seen,
        "truncated": sorted(truncated),
        "limits": asdict(limits),
    }
    evidence = (
        [{"kind": "file", "ref": sorted(node_map)[0]}]
        if node_map
        else [{"kind": "git_commit", "ref": revision}]
    )
    hypotheses = [
        {
            "id": "repository-delivery-boundary",
            "claim": "Treat this repository as one governed delivery boundary.",
            "status": "unresolved",
            "blocking": True,
            "impact_score": max(1, len(node_map)),
            "evidence": evidence,
            "graph_delta": [
                {
                    "op": "confirm",
                    "target_kind": "hypothesis",
                    "target_id": "repository-delivery-boundary",
                }
            ],
        }
    ]
    if dirty or truncated:
        hypotheses.append(
            {
                "id": "inspection-coverage-acceptance",
                "claim": (
                    "Accept the dirty or truncated inspection coverage for design "
                    "inference; release policy may still reject it."
                ),
                "status": "unresolved",
                "blocking": True,
                "impact_score": len(truncated) + int(dirty),
                "evidence": [{"kind": "git_commit", "ref": revision}],
                "graph_delta": [
                    {
                        "op": "confirm",
                        "target_kind": "hypothesis",
                        "target_id": "inspection-coverage-acceptance",
                    }
                ],
            }
        )
    graph: dict[str, Any] = {
        "kind": "concordloom.project-graph",
        "schema_version": "0.1",
        "id": _identifier(root.name) + "-observed",
        "phase": "observed",
        "generated_at": generated_at or timestamp.strip(),
        "repository": {
            "id": _identifier(root.name),
            "revision": revision,
            "tree_digest": digest(
                [
                    {
                        "mode": record["mode"],
                        "object_id": record["object_id"],
                        "path": record["path"],
                    }
                    for record in sorted(records, key=lambda item: str(item["path"]))
                ]
            ),
            "history_head": revision,
            "dirty": dirty,
        },
        "coverage": coverage,
        "nodes": [node_map[path] for path in sorted(node_map)],
        "edges": sorted(
            history_edges + import_edges, key=lambda edge: str(edge["id"])
        ),
        "hypotheses": hypotheses,
    }
    validate_project_graph(graph)
    return InspectionResult(graph=graph, coverage=coverage)


def inspect_repository(
    path: str | Path,
    *,
    limits: InspectionLimits | None = None,
    include_untracked: bool = False,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Return the deterministic project graph for one repository."""

    return inspect_repository_result(
        path,
        limits=limits,
        include_untracked=include_untracked,
        generated_at=generated_at,
    ).graph
