#!/usr/bin/env python3
"""Small trust-seed runner used to govern Concord Loom's first release."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TERMINAL = {"PASSED", "REVISE", "BLOCKED", "CANCELLED"}
REVIEW_NODES = {"R", "L", "Q", "M"}
DIGEST_PATTERN = re.compile(r"sha256:[0-9a-f]{64}")
OID_PATTERN = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?")
RFC3339_PATTERN = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
    r"(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})"
)


class RunError(RuntimeError):
    pass


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RunError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RunError(f"{path} must contain a JSON object")
    return value


def save(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary_name = stream.name
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
    finally:
        if temporary_name is not None:
            try:
                Path(temporary_name).unlink()
            except FileNotFoundError:
                pass


def digest(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def validate_bootstrap_policy(policy: dict[str, Any]) -> None:
    if set(policy) != {"schema_version", "policy_id", "intent", "requirements"}:
        raise RunError("bootstrap compute policy does not match the v0.1 contract")
    if policy.get("schema_version") != 1:
        raise RunError("bootstrap compute policy schema_version must be 1")
    if not isinstance(policy.get("policy_id"), str) or not policy["policy_id"]:
        raise RunError("bootstrap compute policy needs a non-empty policy_id")
    intent = policy.get("intent")
    if not isinstance(intent, dict) or set(intent) != {"quality", "cost", "privacy"}:
        raise RunError("bootstrap compute policy intent is malformed")
    if not all(isinstance(value, str) and value for value in intent.values()):
        raise RunError("bootstrap compute policy intent values must be non-empty")
    requirements = policy.get("requirements")
    if (
        not isinstance(requirements, list)
        or not requirements
        or not all(isinstance(item, str) and item for item in requirements)
        or len(requirements) != len(set(requirements))
    ):
        raise RunError("bootstrap compute policy requirements are invalid")


def validate_bootstrap_cycle(cycle: dict[str, Any]) -> None:
    if set(cycle) != {"schema_version", "cycle_id", "title", "nodes"}:
        raise RunError("bootstrap cycle does not match the v0.1 contract")
    if cycle.get("schema_version") != 1:
        raise RunError("bootstrap cycle schema_version must be 1")
    if not all(
        isinstance(cycle.get(field), str) and cycle[field]
        for field in ("cycle_id", "title")
    ):
        raise RunError("bootstrap cycle identity is invalid")
    raw_nodes = cycle.get("nodes")
    if not isinstance(raw_nodes, list) or not raw_nodes:
        raise RunError("bootstrap cycle nodes must be a non-empty array")
    for node in raw_nodes:
        if not isinstance(node, dict) or set(node) not in (
            {"id", "title", "depends_on", "mode"},
            {"id", "title", "depends_on", "mode", "independent"},
        ):
            raise RunError("bootstrap cycle node does not match the v0.1 contract")
        if not all(
            isinstance(node.get(field), str) and node[field]
            for field in ("id", "title")
        ):
            raise RunError("bootstrap cycle node identity is invalid")
        dependencies = node.get("depends_on")
        if (
            not isinstance(dependencies, list)
            or not all(isinstance(item, str) and item for item in dependencies)
            or len(dependencies) != len(set(dependencies))
        ):
            raise RunError("bootstrap cycle dependencies are invalid")
        if node.get("mode") not in {"write", "read_only"}:
            raise RunError("bootstrap cycle node mode is invalid")
        if "independent" in node and not isinstance(node["independent"], bool):
            raise RunError("bootstrap cycle independent flag is invalid")
        if node.get("independent") and node.get("mode") != "read_only":
            raise RunError("independent bootstrap nodes must be read-only")
    cycle_nodes(cycle)


def valid_digest(value: Any) -> bool:
    return isinstance(value, str) and DIGEST_PATTERN.fullmatch(value) is not None


def valid_rfc3339(value: Any) -> bool:
    if not isinstance(value, str) or RFC3339_PATTERN.fullmatch(value) is None:
        return False
    try:
        datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError:
        return False
    return True


def git_head() -> str:
    try:
        return git_query("rev-parse", "--verify", "HEAD").strip()
    except RunError:
        return "UNCOMMITTED"


def git_query_bytes(*arguments: str) -> bytes:
    environment = dict(os.environ)
    for key in tuple(environment):
        if key.startswith("GIT_"):
            environment.pop(key)
    environment.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_EXTERNAL_DIFF": "",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_NO_LAZY_FETCH": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_PAGER": "cat",
            "GIT_TERMINAL_PROMPT": "0",
            "LC_ALL": "C",
        }
    )
    command = [
        "git",
        "-c",
        "core.hooksPath=/dev/null",
        "-c",
        "core.fsmonitor=false",
        "-c",
        f"core.worktree={ROOT}",
        "-c",
        "diff.external=",
        "-c",
        "protocol.ext.allow=never",
        "-c",
        "protocol.file.allow=never",
        *arguments,
    ]
    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            env=environment,
            check=False,
            capture_output=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RunError(f"safe Git query failed: {exc}") from exc
    if result.returncode:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise RunError(message or "safe Git query failed")
    if len(result.stdout) > 16 * 1024 * 1024:
        raise RunError("safe Git query exceeded 16 MiB")
    return result.stdout


def git_query(*arguments: str) -> str:
    try:
        return git_query_bytes(*arguments).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RunError("safe Git query returned non-UTF-8 output") from exc


def _parse_tree_entries(raw: bytes) -> dict[bytes, tuple[str, str]]:
    entries: dict[bytes, tuple[str, str]] = {}
    for record in raw.split(b"\0"):
        if not record:
            continue
        try:
            metadata, path = record.split(b"\t", 1)
            mode, object_type, object_id = metadata.decode("ascii").split(" ")
        except (UnicodeDecodeError, ValueError) as exc:
            raise RunError("malformed Git tree entry") from exc
        if object_type != "blob" or mode not in {"100644", "100755", "120000"}:
            raise RunError("bootstrap candidates do not support gitlinks or special modes")
        if path in entries:
            raise RunError("duplicate path in Git tree")
        entries[path] = (mode, object_id)
    return entries


def _parse_index_entries(raw: bytes) -> dict[bytes, tuple[str, str]]:
    entries: dict[bytes, tuple[str, str]] = {}
    for record in raw.split(b"\0"):
        if not record:
            continue
        try:
            metadata, path = record.split(b"\t", 1)
            mode, object_id, stage = metadata.decode("ascii").split(" ")
        except (UnicodeDecodeError, ValueError) as exc:
            raise RunError("malformed Git index entry") from exc
        if stage != "0" or path in entries:
            raise RunError("candidate index contains conflicts or duplicate paths")
        entries[path] = (mode, object_id)
    return entries


def _worktree_blob_id(path: Path, mode: str, algorithm: str) -> str:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise RunError(f"candidate path is missing: {path.relative_to(ROOT)}") from exc

    if mode == "120000":
        if not stat.S_ISLNK(metadata.st_mode):
            raise RunError(f"candidate path changed type: {path.relative_to(ROOT)}")
        payload = os.fsencode(os.readlink(path))
        hasher = hashlib.new(algorithm)
        hasher.update(f"blob {len(payload)}\0".encode("ascii"))
        hasher.update(payload)
        return hasher.hexdigest()

    if not stat.S_ISREG(metadata.st_mode):
        raise RunError(f"candidate path changed type: {path.relative_to(ROOT)}")
    executable = bool(metadata.st_mode & 0o111)
    if executable != (mode == "100755"):
        raise RunError(f"candidate mode drift: {path.relative_to(ROOT)}")
    hasher = hashlib.new(algorithm)
    hasher.update(f"blob {metadata.st_size}\0".encode("ascii"))
    try:
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                hasher.update(chunk)
    except OSError as exc:
        raise RunError(f"cannot read candidate path: {path.relative_to(ROOT)}") from exc
    return hasher.hexdigest()


def _repo_path_from_git(raw_path: bytes) -> Path:
    relative = Path(os.fsdecode(raw_path))
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise RunError("Git reported a path outside the candidate repository")
    cursor = ROOT
    for part in relative.parts[:-1]:
        cursor /= part
        try:
            metadata = cursor.lstat()
        except OSError as exc:
            raise RunError(f"candidate parent is missing: {relative}") from exc
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise RunError(f"candidate parent is not a real directory: {relative}")
    return ROOT / relative


def _allowed_runtime_receipt(raw_path: bytes) -> bool:
    relative = Path(os.fsdecode(raw_path))
    if (
        relative.is_absolute()
        or len(relative.parts) < 3
        or relative.parts[0] != ".concord"
        or relative.parts[1] not in {"runs", "signals"}
        or ".." in relative.parts
        or relative.suffix != ".json"
    ):
        return False
    path = _repo_path_from_git(raw_path)
    try:
        return not stat.S_ISLNK(path.lstat().st_mode)
    except OSError:
        return False


def _candidate_snapshot_once() -> dict[str, str]:
    untracked = [
        path
        for path in git_query_bytes("ls-files", "--others", "-z").split(b"\0")
        if path
    ]
    if any(not _allowed_runtime_receipt(path) for path in untracked):
        raise RunError("candidate repository contains untracked non-receipt bytes")

    flags = git_query_bytes("ls-files", "-v", "-z")
    for record in flags.split(b"\0"):
        if record and record[:1] != b"H":
            raise RunError("candidate index contains hidden or special path flags")

    revision = git_query("rev-parse", "--verify", "HEAD").strip()
    tree_oid = git_query("rev-parse", "--verify", "HEAD^{tree}").strip()
    if len(revision) not in {40, 64} or len(tree_oid) not in {40, 64}:
        raise RunError("candidate Git identity is malformed")
    algorithm = git_query("rev-parse", "--show-object-format").strip()
    if algorithm not in {"sha1", "sha256"}:
        raise RunError("unsupported Git object format")

    tree_entries = _parse_tree_entries(
        git_query_bytes("ls-tree", "-rz", "--full-tree", "HEAD")
    )
    index_entries = _parse_index_entries(git_query_bytes("ls-files", "--stage", "-z"))
    if index_entries != tree_entries:
        raise RunError("candidate index differs from HEAD")
    for raw_path, (mode, object_id) in tree_entries.items():
        path = _repo_path_from_git(raw_path)
        if _worktree_blob_id(path, mode, algorithm) != object_id:
            raise RunError("candidate repository must be clean before pinning")

    return {
        "kind": "git",
        "value": revision,
        "tree_oid": tree_oid,
        "tree_digest": digest({"revision": revision, "tree_oid": tree_oid}),
    }


def candidate_snapshot() -> dict[str, str]:
    first = _candidate_snapshot_once()
    second = _candidate_snapshot_once()
    if first != second:
        raise RunError("candidate changed while it was being verified")
    return first


def verify_candidate(card: dict[str, Any]) -> dict[str, Any]:
    candidate = card.get("candidate")
    if not isinstance(candidate, dict):
        raise RunError("run has no pinned candidate")
    actual = candidate_snapshot()
    if candidate != actual:
        raise RunError("pinned candidate no longer matches repository bytes")
    return candidate


def cycle_nodes(cycle: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw = cycle.get("nodes")
    if not isinstance(raw, list) or not raw:
        raise RunError("cycle.nodes must be a non-empty array")
    result: dict[str, dict[str, Any]] = {}
    for node in raw:
        if not isinstance(node, dict) or not isinstance(node.get("id"), str):
            raise RunError("every cycle node needs a string id")
        node_id = node["id"]
        if node_id in result:
            raise RunError(f"duplicate cycle node {node_id}")
        result[node_id] = node
    for node_id, node in result.items():
        for dependency in node.get("depends_on", []):
            if dependency not in result:
                raise RunError(f"{node_id} depends on unknown node {dependency}")
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node_id: str) -> None:
        if node_id in visiting:
            raise RunError(f"dependency cycle reaches {node_id}")
        if node_id in visited:
            return
        visiting.add(node_id)
        for dependency in result[node_id].get("depends_on", []):
            visit(dependency)
        visiting.remove(node_id)
        visited.add(node_id)

    for node_id in result:
        visit(node_id)
    return result


def validate_card(card: dict[str, Any], cycle: dict[str, Any]) -> None:
    validate_bootstrap_cycle(cycle)
    allowed_card_fields = {
        "kind",
        "schema_version",
        "run_id",
        "objective",
        "cycle_path",
        "cycle_digest",
        "policy_path",
        "policy_digest",
        "created_from",
        "candidate",
        "nodes",
        "route_amendments",
        "status",
    }
    if set(card).difference(allowed_card_fields):
        raise RunError("bootstrap run card contains unknown fields")
    if card.get("kind") != "concordloom.bootstrap-run-card":
        raise RunError("run card kind must be concordloom.bootstrap-run-card")
    if card.get("schema_version") != 1:
        raise RunError("run card schema_version must be 1")
    if not all(
        isinstance(card.get(field), str) and card[field]
        for field in (
            "run_id",
            "objective",
            "cycle_path",
            "created_from",
            "policy_path",
        )
    ):
        raise RunError("bootstrap run card identity fields must be non-empty")
    if card.get("cycle_digest") != digest(cycle):
        raise RunError("run card is not bound to the exact bootstrap cycle")
    if not valid_digest(card.get("policy_digest")):
        raise RunError("run card has no bootstrap policy_digest")
    if not valid_scope_path(card["cycle_path"]) or not valid_scope_path(
        card["policy_path"]
    ):
        raise RunError("bootstrap protocol paths must be repository-relative")
    expected = cycle_nodes(cycle)
    actual = card.get("nodes")
    if not isinstance(actual, dict) or set(actual) != set(expected):
        raise RunError("run card nodes do not match the bound cycle")
    for node_id, state in actual.items():
        if not isinstance(state, dict):
            raise RunError(f"node {node_id} state must be an object")
        if set(state) != {
            "status",
            "scope",
            "authorized_by",
            "executor",
            "attempt",
            "evidence",
        }:
            raise RunError(f"node {node_id} state does not match bootstrap schema")
        if state.get("status") not in {"PENDING", "AUTHORIZED"} | TERMINAL:
            raise RunError(f"node {node_id} has invalid status")
        scope = state.get("scope")
        if (
            not isinstance(scope, dict)
            or set(scope) != {"read", "write"}
            or not isinstance(scope.get("read"), list)
            or not isinstance(scope.get("write"), list)
        ):
            raise RunError(f"node {node_id} has no scope")
        if "read" not in scope or "write" not in scope:
            raise RunError(f"node {node_id} scope needs read and write arrays")
        if not all(
            isinstance(item, str) and valid_scope_path(item)
            for item in scope.get("read", [])
        ):
            raise RunError(f"node {node_id} read scope must be paths")
        if not all(
            isinstance(item, str) and valid_scope_path(item)
            for item in scope.get("write", [])
        ):
            raise RunError(f"node {node_id} write scope must be paths")
        if len(scope["read"]) != len(set(scope["read"])) or len(
            scope["write"]
        ) != len(set(scope["write"])):
            raise RunError(f"node {node_id} scope paths must be unique")
        if expected[node_id].get("mode") == "read_only" and scope.get("write"):
            raise RunError(f"read-only node {node_id} cannot have write scope")
        for identity_field in ("authorized_by", "executor"):
            identity = state.get(identity_field)
            if identity is not None and (
                not isinstance(identity, str) or not identity
            ):
                raise RunError(f"node {node_id} has invalid {identity_field}")
        attempt = state.get("attempt")
        if attempt is not None:
            if not isinstance(attempt, dict) or set(attempt) != {
                "agent",
                "model",
                "reasoning",
                "skill",
                "subagents",
                "policy_digest",
            }:
                raise RunError(f"node {node_id} attempt does not match bootstrap schema")
            if not all(
                isinstance(attempt.get(field), str) and attempt[field]
                for field in ("agent", "model", "reasoning", "skill", "policy_digest")
            ):
                raise RunError(f"node {node_id} attempt has invalid fields")
            subagents = attempt.get("subagents")
            if (
                not isinstance(subagents, list)
                or not all(isinstance(item, str) and item for item in subagents)
                or len(subagents) != len(set(subagents))
            ):
                raise RunError(f"node {node_id} attempt subagents are invalid")
            if attempt["agent"] != state.get("executor"):
                raise RunError(f"node {node_id} attempt agent differs from executor")
            if attempt["policy_digest"] != card["policy_digest"]:
                raise RunError(f"node {node_id} attempt policy differs from the run")
        evidence = state.get("evidence")
        if not isinstance(evidence, list) or not all(
            isinstance(item, dict) for item in evidence
        ):
            raise RunError(f"node {node_id} evidence must be structured objects")
        if state["status"] == "PENDING" and any(
            state.get(field) is not None
            for field in ("authorized_by", "executor", "attempt")
        ):
            raise RunError(f"pending node {node_id} contains execution state")
        if state["status"] == "PENDING" and evidence:
            raise RunError(f"pending node {node_id} contains evidence")
        if state["status"] != "PENDING" and (
            not state.get("authorized_by") or not state.get("executor")
        ):
            raise RunError(f"active node {node_id} lacks authorization identities")
        if state["status"] in TERMINAL and attempt is None:
            raise RunError(f"terminal node {node_id} has no factual attempt")
        if state["status"] == "PASSED" and not evidence:
            raise RunError(f"passed node {node_id} has no evidence")

    candidate = card.get("candidate")
    if candidate is not None:
        if not isinstance(candidate, dict) or set(candidate) != {
            "kind",
            "value",
            "tree_oid",
            "tree_digest",
        }:
            raise RunError("candidate does not match bootstrap schema")
        if candidate.get("kind") != "git":
            raise RunError("bootstrap candidate kind must be git")
        if (
            OID_PATTERN.fullmatch(candidate.get("value", "")) is None
            or OID_PATTERN.fullmatch(candidate.get("tree_oid", "")) is None
            or not valid_digest(candidate.get("tree_digest"))
        ):
            raise RunError("bootstrap candidate fields are invalid")

    amendments = card.get("route_amendments", [])
    if not isinstance(amendments, list):
        raise RunError("route_amendments must be an array")
    for amendment in amendments:
        if not isinstance(amendment, dict) or set(amendment) != {
            "node",
            "actor",
            "write_path",
            "reason",
        }:
            raise RunError("route amendment does not match bootstrap schema")
        if not all(
            isinstance(value, str) and value for value in amendment.values()
        ):
            raise RunError("route amendment fields must be non-empty strings")
        if not valid_scope_path(amendment["write_path"]):
            raise RunError("route amendment write_path is invalid")
    if card.get("status") not in {None, "COMPLETE"}:
        raise RunError("bootstrap run status is invalid")


def resolve_repo_path(raw: str) -> Path:
    path = (ROOT / raw).resolve() if not Path(raw).is_absolute() else Path(raw).resolve()
    try:
        path.relative_to(ROOT)
    except ValueError as exc:
        raise RunError(f"path escapes repository: {raw}") from exc
    return path


def valid_scope_path(raw: str) -> bool:
    if not raw:
        return False
    path = Path(raw)
    if path.is_absolute() or ".." in path.parts:
        return False
    try:
        resolve_repo_path(raw)
    except RunError:
        return False
    return True


def path_allowed(raw: str, patterns: list[str]) -> bool:
    requested = resolve_repo_path(raw)
    for pattern in patterns:
        base = resolve_repo_path(pattern)
        if requested == base or base in requested.parents:
            return True
    return False


def require_node(
    card: dict[str, Any], cycle: dict[str, Any], node_id: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    nodes = cycle_nodes(cycle)
    if node_id not in nodes:
        raise RunError(f"unknown node {node_id}")
    return nodes[node_id], card["nodes"][node_id]


def cmd_new(args: argparse.Namespace) -> None:
    cycle_path = resolve_repo_path(args.cycle)
    cycle = load(cycle_path)
    policy_path = resolve_repo_path(args.policy)
    policy = load(policy_path)
    validate_bootstrap_policy(policy)
    nodes = cycle_nodes(cycle)
    scopes = load(resolve_repo_path(args.scopes))
    if set(scopes) != set(nodes):
        raise RunError("scope file must define exactly every cycle node")
    card = {
        "kind": "concordloom.bootstrap-run-card",
        "schema_version": 1,
        "run_id": args.run_id,
        "objective": args.objective,
        "cycle_path": str(cycle_path.relative_to(ROOT)),
        "cycle_digest": digest(cycle),
        "policy_path": str(policy_path.relative_to(ROOT)),
        "policy_digest": digest(policy),
        "created_from": git_head(),
        "candidate": None,
        "nodes": {
            node_id: {
                "status": "PENDING",
                "scope": scopes[node_id],
                "authorized_by": None,
                "executor": None,
                "attempt": None,
                "evidence": [],
            }
            for node_id in nodes
        },
    }
    validate_card(card, cycle)
    save(Path(args.card), card)
    print(Path(args.card).resolve())


def read_pair(card_path: str) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    path = Path(card_path).resolve()
    card = load(path)
    raw_cycle_path = card.get("cycle_path")
    if not isinstance(raw_cycle_path, str):
        raise RunError("bootstrap run card has no cycle_path")
    cycle = load(resolve_repo_path(raw_cycle_path))
    validate_card(card, cycle)
    policy = load(resolve_repo_path(card["policy_path"]))
    validate_bootstrap_policy(policy)
    if digest(policy) != card["policy_digest"]:
        raise RunError("bootstrap compute policy drifted from the run card")
    return path, card, cycle


def cmd_authorize(args: argparse.Namespace) -> None:
    path, card, cycle = read_pair(args.card)
    definition, state = require_node(card, cycle, args.node)
    if state["status"] != "PENDING":
        raise RunError(f"{args.node} is {state['status']}, expected PENDING")
    for dependency in definition.get("depends_on", []):
        if card["nodes"][dependency]["status"] != "PASSED":
            raise RunError(f"{args.node} dependency {dependency} has not passed")
    state["status"] = "AUTHORIZED"
    state["authorized_by"] = args.actor
    state["executor"] = args.executor
    save(path, card)
    print(f"AUTHORIZED {args.node}")


def cmd_guard(args: argparse.Namespace) -> None:
    _, card, cycle = read_pair(args.card)
    definition, state = require_node(card, cycle, args.node)
    if state["status"] != "AUTHORIZED":
        raise RunError(f"{args.node} is {state['status']}, expected AUTHORIZED")
    scope = state["scope"]
    for raw in args.read_path:
        if not path_allowed(raw, scope["read"] + scope["write"]):
            raise RunError(f"read outside {args.node} scope: {raw}")
    for raw in args.write_path:
        if definition.get("mode") == "read_only":
            raise RunError(f"{args.node} is read-only")
        if not path_allowed(raw, scope["write"]):
            raise RunError(f"write outside {args.node} scope: {raw}")
    print(f"GUARD_OK {args.node}")


def cmd_attempt(args: argparse.Namespace) -> None:
    path, card, cycle = read_pair(args.card)
    _, state = require_node(card, cycle, args.node)
    if state["status"] != "AUTHORIZED":
        raise RunError(f"{args.node} is not authorized")
    if args.agent != state.get("executor"):
        raise RunError("factual attempt agent must equal the authorized executor")
    policy_path = Path(args.policy).resolve()
    if policy_path != resolve_repo_path(card["policy_path"]):
        raise RunError("attempt policy path differs from the bound bootstrap policy")
    policy = load(policy_path)
    validate_bootstrap_policy(policy)
    if digest(policy) != card["policy_digest"]:
        raise RunError("attempt policy differs from the bound bootstrap policy")
    state["attempt"] = {
        "agent": args.agent,
        "model": args.model,
        "reasoning": args.reasoning,
        "skill": args.skill,
        "subagents": args.subagent,
        "policy_digest": digest(policy),
    }
    save(path, card)
    print(f"ATTEMPT_RECORDED {args.node}")


def cmd_route_scope(args: argparse.Namespace) -> None:
    """Append a narrowly audited write grant to an authorized write node."""
    path, card, cycle = read_pair(args.card)
    definition, state = require_node(card, cycle, args.node)
    if state["status"] != "AUTHORIZED":
        raise RunError(f"{args.node} is not authorized")
    if definition.get("mode") == "read_only":
        raise RunError(f"{args.node} is read-only")
    if state.get("authorized_by") != args.actor:
        raise RunError("only the node's authorizing actor may amend its route")
    if not valid_scope_path(args.write_path):
        raise RunError("route write path must be a non-empty repository-relative path")
    writes = state["scope"]["write"]
    if args.write_path not in writes:
        writes.append(args.write_path)
        writes.sort()
    card.setdefault("route_amendments", []).append(
        {
            "node": args.node,
            "actor": args.actor,
            "write_path": args.write_path,
            "reason": args.reason,
        }
    )
    save(path, card)
    print(f"ROUTE_AMENDED {args.node} {args.write_path}")


def cmd_pin(args: argparse.Namespace) -> None:
    path, card, _ = read_pair(args.card)
    if args.kind != "git":
        raise RunError("bootstrap v0.1 only supports exact clean Git candidates")
    if card.get("candidate") is not None:
        raise RunError("candidate is immutable within a bootstrap run; start a new run")
    candidate = candidate_snapshot()
    if args.value != candidate["value"]:
        raise RunError("requested candidate revision is not the current clean HEAD")
    card["candidate"] = candidate
    save(path, card)
    print(f"PINNED {candidate['value']} {candidate['tree_digest']}")


def cmd_record(args: argparse.Namespace) -> None:
    path, card, cycle = read_pair(args.card)
    definition, state = require_node(card, cycle, args.node)
    if state["status"] != "AUTHORIZED":
        raise RunError(f"{args.node} is not authorized")
    if state.get("attempt") is None:
        raise RunError(f"{args.node} has no factual runtime attempt")
    if args.status not in TERMINAL:
        raise RunError(f"invalid terminal status {args.status}")
    evidence = [load(Path(item).resolve()) for item in args.evidence]
    if args.status == "PASSED" and not evidence:
        raise RunError("PASSED requires structured evidence")
    if definition.get("independent"):
        candidate = verify_candidate(card)
        validate_independence(card, cycle, args.node)
        validate_review_evidence(card, args.node, args.status, evidence, candidate)
    state["status"] = args.status
    state["evidence"] = evidence
    save(path, card)
    print(f"{args.status} {args.node}")


def cmd_status(args: argparse.Namespace) -> None:
    _, card, cycle = read_pair(args.card)
    nodes = cycle_nodes(cycle)
    for node_id in nodes:
        state = card["nodes"][node_id]
        print(f"{node_id}\t{state['status']}\t{state.get('executor') or '-'}")


def cmd_complete(args: argparse.Namespace) -> None:
    path, card, cycle = read_pair(args.card)
    failures = [
        node_id
        for node_id in cycle_nodes(cycle)
        if card["nodes"][node_id]["status"] != "PASSED"
    ]
    if failures:
        raise RunError("run is not complete: " + ", ".join(failures))
    candidate = verify_candidate(card)
    nodes = cycle_nodes(cycle)
    for node_id, definition in nodes.items():
        if definition.get("independent"):
            validate_independence(card, cycle, node_id)
            validate_review_evidence(
                card,
                node_id,
                "PASSED",
                card["nodes"][node_id].get("evidence", []),
                candidate,
            )
    card["status"] = "COMPLETE"
    save(path, card)
    print(f"COMPLETE {card['run_id']}")


def build_receipt_bundle(
    card: dict[str, Any],
    cycle: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    bundle = {
        "kind": "concordloom.bootstrap-receipt-bundle",
        "schema_version": 1,
        "run_id": card["run_id"],
        "candidate_tree_digest": card["candidate"]["tree_digest"],
        "run_card_digest": digest(card),
        "cycle_digest": digest(cycle),
        "policy_digest": digest(policy),
        "run_card": card,
        "cycle": cycle,
        "policy": policy,
    }
    bundle["bundle_digest"] = digest(bundle)
    return bundle


def validate_receipt_bundle(bundle: dict[str, Any]) -> None:
    required = {
        "kind",
        "schema_version",
        "run_id",
        "candidate_tree_digest",
        "run_card_digest",
        "cycle_digest",
        "policy_digest",
        "run_card",
        "cycle",
        "policy",
        "bundle_digest",
    }
    if set(bundle) != required:
        raise RunError("bootstrap receipt bundle does not match the v0.1 contract")
    if bundle.get("kind") != "concordloom.bootstrap-receipt-bundle":
        raise RunError("bootstrap receipt bundle kind is invalid")
    if bundle.get("schema_version") != 1:
        raise RunError("bootstrap receipt bundle schema_version is invalid")
    card = bundle.get("run_card")
    cycle = bundle.get("cycle")
    policy = bundle.get("policy")
    if not all(isinstance(item, dict) for item in (card, cycle, policy)):
        raise RunError("bootstrap receipt bundle documents are malformed")
    validate_bootstrap_policy(policy)
    validate_card(card, cycle)
    if card.get("status") != "COMPLETE":
        raise RunError("bootstrap receipt bundle run is not COMPLETE")
    nodes = cycle_nodes(cycle)
    candidate = card.get("candidate")
    if not isinstance(candidate, dict):
        raise RunError("bootstrap receipt bundle has no candidate")
    for node_id, definition in nodes.items():
        if card["nodes"][node_id].get("status") != "PASSED":
            raise RunError(f"bootstrap receipt bundle node {node_id} did not pass")
        if definition.get("independent"):
            validate_independence(card, cycle, node_id)
            validate_review_evidence(
                card,
                node_id,
                "PASSED",
                card["nodes"][node_id].get("evidence", []),
                candidate,
            )
    if bundle.get("run_id") != card.get("run_id"):
        raise RunError("bootstrap receipt bundle run_id drifted")
    if bundle.get("candidate_tree_digest") != card.get("candidate", {}).get(
        "tree_digest"
    ):
        raise RunError("bootstrap receipt bundle candidate drifted")
    if bundle.get("run_card_digest") != digest(card):
        raise RunError("bootstrap receipt bundle run card digest drifted")
    if bundle.get("cycle_digest") != digest(cycle):
        raise RunError("bootstrap receipt bundle cycle digest drifted")
    if bundle.get("policy_digest") != digest(policy):
        raise RunError("bootstrap receipt bundle policy digest drifted")
    if card.get("policy_digest") != bundle.get("policy_digest"):
        raise RunError("bootstrap receipt bundle card policy drifted")
    body = dict(bundle)
    claimed = body.pop("bundle_digest")
    if claimed != digest(body):
        raise RunError("bootstrap receipt bundle self-digest drifted")


def receipt_output_path(raw: str, run_id: str) -> Path:
    path = Path(os.path.abspath(raw))
    try:
        relative = path.relative_to(ROOT)
    except ValueError as exc:
        raise RunError("bootstrap receipt export must stay inside the repository") from exc
    prefix = Path(".concord") / "runs" / run_id
    try:
        relative.relative_to(prefix)
    except ValueError as exc:
        raise RunError(
            f"bootstrap receipt export must stay under {prefix}"
        ) from exc
    if relative == prefix:
        raise RunError("bootstrap receipt export needs a file path")
    cursor = ROOT
    for part in relative.parts[:-1]:
        cursor /= part
        if not cursor.exists():
            continue
        metadata = cursor.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise RunError("bootstrap receipt export parent is unsafe")
    if path.exists() and (
        stat.S_ISLNK(path.lstat().st_mode) or not stat.S_ISREG(path.lstat().st_mode)
    ):
        raise RunError("bootstrap receipt export target is unsafe")
    if git_query_bytes("ls-files", "--stage", "-z", "--", str(relative)):
        raise RunError("bootstrap receipt export cannot overwrite tracked candidate bytes")
    return path


def cmd_export(args: argparse.Namespace) -> None:
    _, card, cycle = read_pair(args.card)
    if card.get("status") != "COMPLETE":
        raise RunError("receipt export requires a COMPLETE bootstrap run")
    candidate = verify_candidate(card)
    nodes = cycle_nodes(cycle)
    for node_id, definition in nodes.items():
        if card["nodes"][node_id]["status"] != "PASSED":
            raise RunError(f"receipt export found non-passing node {node_id}")
        if definition.get("independent"):
            validate_independence(card, cycle, node_id)
            validate_review_evidence(
                card,
                node_id,
                "PASSED",
                card["nodes"][node_id].get("evidence", []),
                candidate,
            )
    policy = load(resolve_repo_path(card["policy_path"]))
    bundle = build_receipt_bundle(card, cycle, policy)
    validate_receipt_bundle(bundle)
    output = receipt_output_path(args.output, card["run_id"])
    save(output, bundle)
    print(f"EXPORTED {bundle['bundle_digest']} {output}")


def validate_independence(
    card: dict[str, Any],
    cycle: dict[str, Any],
    node_id: str,
) -> None:
    authors: set[str] = set()
    nodes = cycle_nodes(cycle)
    for other_id, node_state in card["nodes"].items():
        if (
            nodes[other_id].get("mode") == "read_only"
            or node_state.get("status") != "PASSED"
        ):
            continue
        if isinstance(node_state.get("executor"), str):
            authors.add(node_state["executor"])
        attempt = node_state.get("attempt")
        if isinstance(attempt, dict):
            if isinstance(attempt.get("agent"), str):
                authors.add(attempt["agent"])
            authors.update(
                item
                for item in attempt.get("subagents", [])
                if isinstance(item, str)
            )
    state = card["nodes"][node_id]
    attempt = state.get("attempt")
    if not isinstance(attempt, dict):
        raise RunError(f"{node_id} has no factual runtime attempt")
    reviewers = {state.get("executor"), attempt.get("agent")}
    reviewers.update(
        item for item in attempt.get("subagents", []) if isinstance(item, str)
    )
    if authors.intersection(item for item in reviewers if isinstance(item, str)):
        raise RunError(
            f"{node_id} reviewer or subagent authored bytes in the pinned candidate"
        )


def validate_review_evidence(
    card: dict[str, Any],
    node_id: str,
    status: str,
    evidence: list[dict[str, Any]],
    candidate: dict[str, Any],
) -> None:
    if not evidence:
        raise RunError(f"{node_id} has no review evidence")
    state = card["nodes"][node_id]
    attempt = state.get("attempt")
    if not isinstance(attempt, dict):
        raise RunError(f"{node_id} has no factual runtime attempt")
    required = {
        "kind",
        "schema_version",
        "run_id",
        "cycle_digest",
        "node",
        "result",
        "candidate_tree_digest",
        "attempt_digest",
        "reviewer",
        "policy_digest",
        "checks",
        "summary",
        "produced_at",
    }
    for document in evidence:
        if set(document) != required:
            raise RunError("review evidence does not match the bootstrap evidence contract")
        if document.get("kind") != "concordloom.bootstrap-review-evidence":
            raise RunError("review evidence kind is invalid")
        if document.get("schema_version") != 1:
            raise RunError("review evidence schema_version is invalid")
        if document.get("run_id") != card["run_id"]:
            raise RunError("review evidence names a different run")
        if document.get("cycle_digest") != card["cycle_digest"]:
            raise RunError("review evidence names a different cycle")
        if document.get("node") != node_id:
            raise RunError("review evidence names a different node")
        if document.get("result") != status:
            raise RunError("review evidence result differs from node status")
        if document.get("candidate_tree_digest") != candidate["tree_digest"]:
            raise RunError("review evidence is not bound to the pinned candidate")
        if document.get("attempt_digest") != digest(attempt):
            raise RunError("review evidence is not bound to the factual attempt")
        if document.get("reviewer") != attempt.get("agent"):
            raise RunError("review evidence names a different effective reviewer")
        if document.get("policy_digest") != attempt.get("policy_digest"):
            raise RunError("review evidence is not bound to the attempt policy")
        if not isinstance(document.get("summary"), str) or not document["summary"]:
            raise RunError("review evidence summary must be non-empty")
        if not valid_rfc3339(document.get("produced_at")):
            raise RunError("review evidence produced_at must be an RFC 3339 date-time")
        checks = document.get("checks")
        if not isinstance(checks, list) or not checks:
            raise RunError("review evidence checks must be a non-empty array")
        check_ids: set[str] = set()
        for check in checks:
            if not isinstance(check, dict) or set(check) != {"id", "result", "detail"}:
                raise RunError("review evidence check is malformed")
            if not isinstance(check["id"], str) or not check["id"]:
                raise RunError("review evidence check id must be non-empty")
            if check["id"] in check_ids:
                raise RunError("review evidence check ids must be unique")
            check_ids.add(check["id"])
            if check["result"] not in {"PASS", "FAIL", "NOT_APPLICABLE"}:
                raise RunError("review evidence check result is invalid")
            if not isinstance(check["detail"], str) or not check["detail"]:
                raise RunError("review evidence check detail must be non-empty")
        if status == "PASSED" and any(check["result"] == "FAIL" for check in checks):
            raise RunError("PASSED review evidence contains a failed check")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="concord-run")
    sub = result.add_subparsers(dest="command", required=True)

    new = sub.add_parser("new")
    new.add_argument("--cycle", required=True)
    new.add_argument("--scopes", required=True)
    new.add_argument("--policy", required=True)
    new.add_argument("--card", required=True)
    new.add_argument("--run-id", required=True)
    new.add_argument("--objective", required=True)
    new.set_defaults(func=cmd_new)

    authorize = sub.add_parser("authorize")
    authorize.add_argument("--card", required=True)
    authorize.add_argument("--node", required=True)
    authorize.add_argument("--actor", required=True)
    authorize.add_argument("--executor", required=True)
    authorize.set_defaults(func=cmd_authorize)

    guard = sub.add_parser("guard")
    guard.add_argument("--card", required=True)
    guard.add_argument("--node", required=True)
    guard.add_argument("--read-path", action="append", default=[])
    guard.add_argument("--write-path", action="append", default=[])
    guard.set_defaults(func=cmd_guard)

    attempt = sub.add_parser("attempt")
    attempt.add_argument("--card", required=True)
    attempt.add_argument("--node", required=True)
    attempt.add_argument("--policy", required=True)
    attempt.add_argument("--agent", required=True)
    attempt.add_argument("--model", required=True)
    attempt.add_argument("--reasoning", required=True)
    attempt.add_argument("--skill", required=True)
    attempt.add_argument("--subagent", action="append", default=[])
    attempt.set_defaults(func=cmd_attempt)

    route_scope = sub.add_parser("route-scope")
    route_scope.add_argument("--card", required=True)
    route_scope.add_argument("--node", required=True)
    route_scope.add_argument("--actor", required=True)
    route_scope.add_argument("--write-path", required=True)
    route_scope.add_argument("--reason", required=True)
    route_scope.set_defaults(func=cmd_route_scope)

    pin = sub.add_parser("pin")
    pin.add_argument("--card", required=True)
    pin.add_argument("--kind", required=True, choices=["git"])
    pin.add_argument("--value", required=True)
    pin.set_defaults(func=cmd_pin)

    record = sub.add_parser("record")
    record.add_argument("--card", required=True)
    record.add_argument("--node", required=True)
    record.add_argument("--status", required=True, choices=sorted(TERMINAL))
    record.add_argument("--evidence", action="append", default=[])
    record.set_defaults(func=cmd_record)

    status = sub.add_parser("status")
    status.add_argument("--card", required=True)
    status.set_defaults(func=cmd_status)

    complete = sub.add_parser("complete")
    complete.add_argument("--card", required=True)
    complete.set_defaults(func=cmd_complete)

    export = sub.add_parser("export")
    export.add_argument("--card", required=True)
    export.add_argument("--output", required=True)
    export.set_defaults(func=cmd_export)
    return result


def main() -> int:
    try:
        args = parser().parse_args()
        args.func(args)
    except RunError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
