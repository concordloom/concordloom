"""File-backed, evidence-bound lifecycle primitives for Concord Loom runs."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from copy import deepcopy
from datetime import datetime
from hashlib import sha1, sha256
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
from typing import Any

from .canonical import digest, document_digest
from .loops import (
    InvariantError,
    budget_subset,
    path_within,
    policy_principals,
    policy_roles,
    principal_capabilities,
    require_actor_capability,
    scope_subset,
    validate_policy,
    validate_registry,
)
from .schema import SchemaStore


class RunStateError(ValueError):
    """A requested run transition is invalid or insufficiently authorized."""


def _raw_digest(payload: bytes) -> str:
    return "sha256:" + sha256(payload).hexdigest()


def _git(repository: Path, arguments: Sequence[str]) -> bytes:
    environment = dict(os.environ)
    for key in (
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_COMMON_DIR",
        "GIT_CONFIG_COUNT",
        "GIT_DIR",
        "GIT_INDEX_FILE",
        "GIT_NAMESPACE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_WORK_TREE",
    ):
        environment.pop(key, None)
    for key in tuple(environment):
        if key.startswith(("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_")):
            environment.pop(key)
    environment.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_EXTERNAL_DIFF": "",
            "GIT_NO_LAZY_FETCH": "1",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_PAGER": "cat",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    safe_arguments = list(arguments)
    if safe_arguments and safe_arguments[0] in {"diff", "diff-tree", "log", "show"}:
        # Read-only history callers must not invoke repository-selected drivers.
        safe_arguments[1:1] = ["--no-ext-diff", "--no-textconv"]
    command = [
        "git",
        "-c",
        "core.hooksPath=/dev/null",
        "-c",
        "core.fsmonitor=false",
        "-c",
        "diff.external=",
        "-c",
        "filter.lfs.required=false",
        *safe_arguments,
    ]
    try:
        result = subprocess.run(
            command,
            cwd=repository,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RunStateError(f"safe Git query failed: {exc}") from exc
    if result.returncode:
        message = result.stderr.decode("utf-8", "replace").strip()
        raise RunStateError(f"Git query failed ({result.returncode}): {message}")
    if len(result.stdout) > 128 * 1024 * 1024:
        raise RunStateError("Git query exceeded the 128 MiB safety limit")
    return result.stdout


def _decode_path(payload: bytes) -> str:
    try:
        path = payload.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise RunStateError("candidate paths must be valid UTF-8") from exc
    if (
        not path
        or path.startswith("/")
        or "\\" in path
        or ".." in PurePosixPath(path).parts
    ):
        raise RunStateError(f"unsafe candidate path {path!r}")
    return path


def _inside(root: Path, raw: str) -> Path:
    path = _decode_path(raw.encode("utf-8"))
    resolved_parent = (root / path).parent.resolve()
    try:
        resolved_parent.relative_to(root)
    except ValueError as exc:
        raise RunStateError(f"candidate path escapes repository: {raw!r}") from exc
    return root / path


def _entry_bytes(root: Path, path: str, mode: str, git_oid: str | None = None) -> bytes:
    target = _inside(root, path)
    if mode == "160000":
        if not git_oid:
            raise RunStateError(f"submodule {path!r} has no Git object id")
        if target.is_symlink() or not target.is_dir():
            raise RunStateError(f"submodule {path!r} is not initialized safely")
        try:
            target.resolve().relative_to(root)
        except ValueError as exc:
            raise RunStateError(f"submodule {path!r} escapes the repository") from exc
        current_oid = (
            _git(target, ["rev-parse", "--verify", "HEAD"])
            .decode("ascii", "strict")
            .strip()
        )
        if len(current_oid) not in {40, 64}:
            raise RunStateError(f"submodule {path!r} returned an invalid object id")
        return current_oid.encode("ascii")
    if mode == "120000":
        if not target.is_symlink():
            raise RunStateError(f"tracked symlink {path!r} is missing or changed type")
        return os.readlink(target).encode("utf-8")
    if target.is_symlink() or not target.is_file():
        raise RunStateError(f"candidate file {path!r} is missing or changed type")
    try:
        return target.read_bytes()
    except OSError as exc:
        raise RunStateError(f"cannot read candidate file {path!r}: {exc}") from exc


def _worktree_mode(root: Path, path: str, indexed_mode: str | None = None) -> str:
    target = _inside(root, path)
    if indexed_mode == "160000":
        return indexed_mode
    if target.is_symlink():
        return "120000"
    try:
        value = target.stat(follow_symlinks=False)
    except OSError as exc:
        raise RunStateError(f"cannot stat candidate file {path!r}: {exc}") from exc
    if not stat.S_ISREG(value.st_mode):
        raise RunStateError(f"candidate path {path!r} is not a file")
    return "100755" if value.st_mode & stat.S_IXUSR else "100644"


def _tracked_entries(root: Path) -> dict[str, tuple[str, str]]:
    payload = _git(root, ["ls-files", "-s", "-z"])
    result: dict[str, tuple[str, str]] = {}
    for raw_entry in payload.split(b"\0"):
        if not raw_entry:
            continue
        metadata, separator, raw_path = raw_entry.partition(b"\t")
        parts = metadata.split()
        if not separator or len(parts) != 3:
            raise RunStateError("malformed git ls-files output")
        try:
            mode, oid, stage = (part.decode("ascii") for part in parts)
        except UnicodeDecodeError as exc:
            raise RunStateError("malformed git index metadata") from exc
        if stage != "0":
            raise RunStateError("cannot manifest an unmerged Git index")
        path = _decode_path(raw_path)
        if path in result:
            raise RunStateError(f"duplicate tracked candidate path {path!r}")
        result[path] = (mode, oid)
    return result


def _explicit_untracked(root: Path, requested: Iterable[str]) -> set[str]:
    result: set[str] = set()
    for raw in requested:
        normalized = _decode_path(raw.encode("utf-8"))
        matches = _git(
            root,
            [
                "ls-files",
                "--others",
                "--exclude-standard",
                "-z",
                "--",
                normalized,
            ],
        )
        paths = {_decode_path(item) for item in matches.split(b"\0") if item}
        if not paths:
            raise RunStateError(
                f"explicit candidate path {normalized!r} is not an untracked file"
            )
        result.update(paths)
    return result


def _all_untracked(root: Path) -> set[str]:
    payload = _git(
        root,
        ["ls-files", "--others", "--exclude-standard", "-z"],
    )
    return {_decode_path(item) for item in payload.split(b"\0") if item}


def _revision(root: Path) -> str:
    return _git(root, ["rev-parse", "--verify", "HEAD"]).decode("ascii").strip()


def _require_top_level(root: Path) -> None:
    actual_root = Path(
        _git(root, ["rev-parse", "--show-toplevel"])
        .decode("utf-8", "strict")
        .strip()
    ).resolve()
    if actual_root != root:
        raise RunStateError(f"candidate root must be Git top level {actual_root}")


def _head_entries(root: Path, revision: str) -> dict[str, tuple[str, str]]:
    payload = _git(root, ["ls-tree", "-r", "-z", "--full-tree", revision])
    result: dict[str, tuple[str, str]] = {}
    for raw_entry in payload.split(b"\0"):
        if not raw_entry:
            continue
        metadata, separator, raw_path = raw_entry.partition(b"\t")
        parts = metadata.split()
        if not separator or len(parts) != 3:
            raise RunStateError("malformed git ls-tree output")
        try:
            mode, object_type, oid = (part.decode("ascii") for part in parts)
        except UnicodeDecodeError as exc:
            raise RunStateError("malformed git tree metadata") from exc
        if object_type not in {"blob", "commit"}:
            raise RunStateError(f"unsupported Git tree object type {object_type!r}")
        path = _decode_path(raw_path)
        if path in result:
            raise RunStateError(f"duplicate Git tree path {path!r}")
        result[path] = (mode, oid)
    return result


def _git_blob_oid(payload: bytes, exemplar_oid: str) -> str:
    envelope = f"blob {len(payload)}\0".encode("ascii") + payload
    if len(exemplar_oid) == 40:
        return sha1(envelope).hexdigest()
    if len(exemplar_oid) == 64:
        return sha256(envelope).hexdigest()
    raise RunStateError(f"unsupported Git object id length {len(exemplar_oid)}")


def _candidate_entries(
    root: Path,
    tracked: Mapping[str, tuple[str, str]],
    untracked: set[str],
) -> tuple[list[dict[str, Any]], bool]:
    entries: list[dict[str, Any]] = []
    worktree_dirty = False
    for path in sorted(tracked):
        indexed_mode, oid = tracked[path]
        mode = _worktree_mode(root, path, indexed_mode)
        payload = _entry_bytes(root, path, mode, oid)
        if mode != indexed_mode:
            worktree_dirty = True
        elif mode == "160000":
            worktree_dirty = worktree_dirty or payload.decode("ascii") != oid
        elif _git_blob_oid(payload, oid) != oid:
            worktree_dirty = True
        entries.append(
            {
                "path": path,
                "digest": _raw_digest(payload),
                "mode": mode,
                "origin": "tracked",
                "git_object_id": oid,
            }
        )
    for path in sorted(untracked - set(tracked)):
        mode = _worktree_mode(root, path)
        payload = _entry_bytes(root, path, mode)
        entries.append(
            {
                "path": path,
                "digest": _raw_digest(payload),
                "mode": mode,
                "origin": "explicit_untracked",
            }
        )
    entries.sort(key=lambda item: item["path"].encode("utf-8"))
    return entries, worktree_dirty


def _candidate_dirty(
    tracked: Mapping[str, tuple[str, str]],
    head: Mapping[str, tuple[str, str]],
    untracked: set[str],
    worktree_dirty: bool,
) -> bool:
    return bool(untracked or worktree_dirty or dict(tracked) != dict(head))


def build_candidate_manifest(
    repository: str | Path,
    *,
    include_untracked: Iterable[str] = (),
    manifest_id: str = "candidate",
    generated_at: str,
    schema_store: SchemaStore | None = None,
) -> dict[str, Any]:
    """Manifest all tracked bytes plus explicitly selected untracked bytes."""

    root = Path(repository).resolve()
    if not root.is_dir():
        raise RunStateError(f"repository does not exist: {root}")
    _require_top_level(root)
    revision = _revision(root)
    tracked = _tracked_entries(root)
    untracked = _explicit_untracked(root, include_untracked)
    all_untracked = _all_untracked(root)
    unexpected_untracked = all_untracked - untracked
    if unexpected_untracked:
        raise RunStateError(
            "untracked candidate inventory is not explicitly manifested: "
            f"{sorted(unexpected_untracked)!r}"
        )
    head = _head_entries(root, revision)
    entries, worktree_dirty = _candidate_entries(root, tracked, untracked)
    dirty = _candidate_dirty(tracked, head, all_untracked, worktree_dirty)
    repeated_entries, repeated_worktree_dirty = _candidate_entries(
        root, tracked, untracked
    )
    if (
        _revision(root) != revision
        or _tracked_entries(root) != tracked
        or _all_untracked(root) != all_untracked
        or _head_entries(root, revision) != head
        or repeated_entries != entries
        or repeated_worktree_dirty != worktree_dirty
    ):
        raise RunStateError("candidate changed while its manifest was being built")
    manifest = {
        "kind": "concordloom.candidate-manifest",
        "schema_version": "0.1",
        "id": manifest_id,
        "generated_at": generated_at,
        "revision": revision,
        "tree_digest": digest({"files": entries}),
        "dirty": dirty,
        "files": entries,
    }
    (schema_store or SchemaStore()).validate(
        manifest, "candidate-manifest.schema.json"
    )
    return manifest


def verify_candidate_manifest(
    repository: str | Path,
    manifest: dict[str, Any],
    *,
    schema_store: SchemaStore | None = None,
) -> str:
    """Recompute and return the candidate tree digest, failing on drift."""

    store = schema_store or SchemaStore()
    store.validate(manifest, "candidate-manifest.schema.json")
    root = Path(repository).resolve()
    if not root.is_dir():
        raise RunStateError(f"repository does not exist: {root}")
    _require_top_level(root)
    revision = _revision(root)
    if revision != manifest["revision"]:
        raise RunStateError("candidate revision changed")
    tracked = _tracked_entries(root)
    current_untracked = _all_untracked(root)
    head = _head_entries(root, revision)
    manifested_paths = {item["path"] for item in manifest["files"]}
    manifested_untracked = manifested_paths - set(tracked)
    if current_untracked != manifested_untracked:
        added = sorted(current_untracked - manifested_untracked)
        removed = sorted(manifested_untracked - current_untracked)
        raise RunStateError(
            "untracked candidate inventory changed "
            f"(added={added!r}, removed={removed!r})"
        )
    entries, worktree_dirty = _candidate_entries(
        root, tracked, current_untracked
    )
    dirty = _candidate_dirty(tracked, head, current_untracked, worktree_dirty)
    if dirty != manifest["dirty"]:
        raise RunStateError("candidate dirty state changed")
    expected_entries = sorted(
        manifest["files"], key=lambda item: item["path"].encode("utf-8")
    )
    if entries != expected_entries:
        raise RunStateError("candidate mode, content, or inventory changed")
    repeated_entries, repeated_worktree_dirty = _candidate_entries(
        root, tracked, current_untracked
    )
    if (
        _revision(root) != revision
        or _tracked_entries(root) != tracked
        or _all_untracked(root) != current_untracked
        or _head_entries(root, revision) != head
        or repeated_entries != entries
        or repeated_worktree_dirty != worktree_dirty
    ):
        raise RunStateError("candidate changed while its manifest was being verified")
    tree_digest = digest({"files": entries})
    if tree_digest != manifest["tree_digest"]:
        raise RunStateError("candidate tree digest mismatch")
    return tree_digest


def _artifact(binding: Mapping[str, Any], role: str) -> Mapping[str, Any]:
    matches = [item for item in binding["artifacts"] if item["role"] == role]
    if len(matches) != 1:
        raise RunStateError(f"binding must contain exactly one {role!r} artifact")
    return matches[0]


def validate_binding(
    binding: dict[str, Any],
    registry: dict[str, Any],
    policy: dict[str, Any],
    *,
    binding_proposal: Mapping[str, Any] | None = None,
    schema_store: SchemaStore | None = None,
) -> dict[str, Any]:
    store = schema_store or SchemaStore()
    validate_registry(registry, policy, schema_store=store)
    store.validate(binding, "binding.schema.json")
    expected = document_digest(
        binding, excluded_fields=binding["digest_contract"]["excluded_fields"]
    )
    if binding["binding_digest"] != expected:
        raise RunStateError("binding digest does not satisfy its digest contract")
    if _artifact(binding, "cycle_registry")["digest"] != digest(registry):
        raise RunStateError("binding points to a different cycle registry")
    if _artifact(binding, "policy")["digest"] != digest(policy):
        raise RunStateError("binding points to a different policy")
    if binding_proposal is not None:
        store.validate(dict(binding_proposal), "binding-proposal.schema.json")
        expected_proposal = document_digest(
            binding_proposal,
            excluded_fields=binding_proposal["digest_contract"]["excluded_fields"],
        )
        if binding_proposal["proposal_digest"] != expected_proposal:
            raise RunStateError("binding proposal digest contract mismatch")
        if binding["accepted_by"]["proposal_digest"] != expected_proposal:
            raise RunStateError("binding was activated from a different proposal")
        if binding["artifacts"] != binding_proposal["artifacts"]:
            raise RunStateError("binding artifacts differ from accepted proposal")
    return binding


def _reachable_loop_ids(
    registry: Mapping[str, Any], root_loop_id: str
) -> set[str]:
    adjacency: dict[str, list[str]] = {}
    for edge in registry["containment_graph"]["edges"]:
        adjacency.setdefault(edge["parent_loop_id"], []).append(
            edge["child_loop_id"]
        )
    reachable: set[str] = set()
    pending = [root_loop_id]
    while pending:
        loop_id = pending.pop()
        if loop_id in reachable:
            continue
        reachable.add(loop_id)
        pending.extend(reversed(adjacency.get(loop_id, [])))
    return reachable


def _default_route(
    registry: Mapping[str, Any],
    policy: Mapping[str, Any],
    root_loop_id: str,
) -> list[dict[str, Any]]:
    roles = policy_roles(policy)
    scope = policy["execution"]["default_scope"]
    reachable = _reachable_loop_ids(registry, root_loop_id)
    result: list[dict[str, Any]] = []
    for loop in sorted(
        (
            item
            for item in registry["loops"]
            if item["id"] in reachable
        ),
        key=lambda item: item["id"],
    ):
        required_capability = _route_capability(loop, registry)
        eligible_roles = sorted(
            role_id
            for role_id, role in roles.items()
            if required_capability in role["capabilities"]
        )
        if not eligible_roles:
            raise RunStateError(
                f"no policy role can route loop {loop['id']!r} with capability "
                f"{required_capability!r}"
            )
        result.append(
            {
            "node_id": loop["id"],
            "loop_id": loop["id"],
            "role": eligible_roles[0],
            "skill_intent": "select at authorized execution",
            "model_intent": "select within bound model policy",
            "reasoning_intent": "proportionate to evidence contract",
            "subagent_intent": [],
            "scope": deepcopy(scope),
        }
        )
    return result


def _route_capability(
    loop: Mapping[str, Any], registry: Mapping[str, Any]
) -> str:
    """Return the capability that may factually execute this routed node."""

    contracts = {
        contract["id"]: contract for contract in registry["evidence_contracts"]
    }
    contract_ids = {
        contract_id
        for transition in loop["local_control_flow"]["transitions"]
        for contract_id in transition["evidence_contract_ids"]
    }
    reviewer_capabilities = sorted(
        {
            str(contracts[contract_id]["reviewer_capability"])
            for contract_id in contract_ids
            if contracts[contract_id].get("reviewer_capability")
        }
    )
    if len(reviewer_capabilities) > 1:
        raise RunStateError(
            f"loop {loop['id']!r} requires incompatible reviewer capabilities "
            f"{reviewer_capabilities!r}"
        )
    if reviewer_capabilities:
        return reviewer_capabilities[0]
    return str(loop["authority"]["execute_capability"])


def _route(card: Mapping[str, Any], node_id: str) -> Mapping[str, Any]:
    matches = [item for item in card["planned_route"] if item["node_id"] == node_id]
    if len(matches) != 1:
        raise RunStateError(f"unknown or duplicate planned node {node_id!r}")
    return matches[0]


def _node(card: Mapping[str, Any], node_id: str) -> Mapping[str, Any]:
    matches = [item for item in card["nodes"] if item["node_id"] == node_id]
    if len(matches) != 1:
        raise RunStateError(f"unknown or duplicate run node {node_id!r}")
    return matches[0]


def create_run_card(
    binding: dict[str, Any],
    registry: dict[str, Any],
    policy: dict[str, Any],
    candidate_manifest: dict[str, Any],
    *,
    run_id: str,
    root_loop_id: str,
    candidate_author_principal_ids: Sequence[str],
    planned_route: Sequence[Mapping[str, Any]] | None = None,
    scope: Mapping[str, Any] | None = None,
    budgets: Mapping[str, Any] | None = None,
    schema_store: SchemaStore | None = None,
) -> dict[str, Any]:
    store = schema_store or SchemaStore()
    validate_binding(binding, registry, policy, schema_store=store)
    store.validate(candidate_manifest, "candidate-manifest.schema.json")
    roots = registry["containment_graph"]["roots"]
    if root_loop_id not in roots or root_loop_id not in binding["active_root_loop_ids"]:
        raise RunStateError("run root is not active in the binding")
    principals = policy_principals(policy)
    authors = list(candidate_author_principal_ids)
    if not authors or len(authors) != len(set(authors)):
        raise RunStateError("candidate authors must be a non-empty unique list")
    unknown_authors = set(authors) - set(principals)
    if unknown_authors:
        raise RunStateError(f"unknown candidate authors {sorted(unknown_authors)!r}")
    card_scope = deepcopy(dict(scope or policy["execution"]["default_scope"]))
    card_budgets = deepcopy(dict(budgets or policy["execution"]["default_budgets"]))
    if not scope_subset(card_scope, policy["execution"]["default_scope"]):
        raise RunStateError("run scope broadens the bound policy default")
    if not budget_subset(card_budgets, policy["execution"]["default_budgets"]):
        raise RunStateError("run budgets broaden the bound policy defaults")
    if (
        card_budgets["on_exhaustion"]
        != policy["execution"]["default_budgets"]["on_exhaustion"]
    ):
        raise RunStateError("run exhaustion outcome changes the bound policy default")
    if (
        card_budgets["max_cost_units"]
        > policy["execution"]["model_policy"]["max_cost_units"]
    ):
        raise RunStateError("run cost budget broadens the bound model policy")
    reachable = _reachable_loop_ids(registry, root_loop_id)
    route_source = (
        _default_route(registry, policy, root_loop_id)
        if planned_route is None
        else planned_route
    )
    route = deepcopy(list(route_source))
    node_ids: set[str] = set()
    loops = {loop["id"]: loop for loop in registry["loops"]}
    roles = policy_roles(policy)
    for item in route:
        if item["node_id"] in node_ids:
            raise RunStateError(f"duplicate planned node {item['node_id']!r}")
        node_ids.add(item["node_id"])
        if item["loop_id"] not in loops:
            raise RunStateError(f"planned node uses unknown loop {item['loop_id']!r}")
        if item["loop_id"] not in reachable:
            raise RunStateError("planned node leaves the selected run root subtree")
        if item["role"] not in roles:
            raise RunStateError(f"planned node uses unknown role {item['role']!r}")
        required_capability = _route_capability(loops[item["loop_id"]], registry)
        if required_capability not in roles[item["role"]]["capabilities"]:
            raise RunStateError(
                f"planned role {item['role']!r} lacks loop routing capability "
                f"{required_capability!r} for {item['loop_id']!r}"
            )
        if not scope_subset(item["scope"], card_scope):
            raise RunStateError(f"planned node {item['node_id']!r} broadens run scope")
    if not any(item["loop_id"] == root_loop_id for item in route):
        raise RunStateError("planned route omits the root loop")
    card = {
        "kind": "concordloom.run-card",
        "schema_version": "0.1",
        "id": run_id,
        "binding_digest": binding["binding_digest"],
        "registry_digest": digest(registry),
        "policy_digest": digest(policy),
        "candidate_tree_digest": candidate_manifest["tree_digest"],
        "candidate_manifest_digest": digest(candidate_manifest),
        "candidate_author_principal_ids": authors,
        "root_loop_id": root_loop_id,
        "status": "draft",
        "scope": card_scope,
        "budgets": card_budgets,
        "planned_route": route,
        "nodes": [
            {
                "node_id": item["node_id"],
                "loop_id": item["loop_id"],
                "status": "pending",
                "attempts": [],
                "evidence_ids": [],
            }
            for item in route
        ],
        "evidence": [],
    }
    store.validate(card, "run-card.schema.json")
    return card


def _check_card_identity(
    card: Mapping[str, Any],
    binding: dict[str, Any],
    registry: dict[str, Any],
    policy: dict[str, Any],
    candidate_manifest: dict[str, Any],
    *,
    repository: str | Path | None = None,
    schema_store: SchemaStore | None = None,
) -> None:
    store = schema_store or SchemaStore()
    validate_binding(binding, registry, policy, schema_store=store)
    store.validate(dict(card), "run-card.schema.json")
    store.validate(candidate_manifest, "candidate-manifest.schema.json")
    checks = {
        "binding_digest": binding["binding_digest"],
        "registry_digest": digest(registry),
        "policy_digest": digest(policy),
        "candidate_tree_digest": candidate_manifest["tree_digest"],
        "candidate_manifest_digest": digest(candidate_manifest),
    }
    for key, value in checks.items():
        if card[key] != value:
            raise RunStateError(f"run card {key} mismatch")
    if repository is not None:
        verify_candidate_manifest(repository, candidate_manifest, schema_store=store)


def validate_run_card(
    card: dict[str, Any],
    binding: dict[str, Any],
    registry: dict[str, Any],
    policy: dict[str, Any],
    candidate_manifest: dict[str, Any],
    *,
    repository: str | Path,
    schema_store: SchemaStore | None = None,
) -> dict[str, Any]:
    """Validate a public run card against all content-addressed inputs."""

    _check_card_identity(
        card,
        binding,
        registry,
        policy,
        candidate_manifest,
        repository=repository,
        schema_store=schema_store,
    )
    return card


def authorize_run(
    card: dict[str, Any],
    binding: dict[str, Any],
    registry: dict[str, Any],
    policy: dict[str, Any],
    candidate_manifest: dict[str, Any],
    *,
    actor: Mapping[str, Any],
    authority_ref: str,
    authorized_at: str,
    repository: str | Path,
    schema_store: SchemaStore | None = None,
) -> dict[str, Any]:
    store = schema_store or SchemaStore()
    _check_card_identity(
        card,
        binding,
        registry,
        policy,
        candidate_manifest,
        repository=repository,
        schema_store=store,
    )
    if card["status"] != "draft":
        raise RunStateError("only a draft run can be authorized")
    require_actor_capability(
        policy, actor, "authorize-run", authority_ref=authority_ref
    )
    result = deepcopy(card)
    result["authorization"] = {
        "actor": deepcopy(dict(actor)),
        "capability": "authorize-run",
        "authorized_at": authorized_at,
        "binding_digest": binding["binding_digest"],
        "scope_digest": digest(card["scope"]),
    }
    result["status"] = "authorized"
    store.validate(result, "run-card.schema.json")
    return result


def guard(
    card: Mapping[str, Any],
    node_id: str,
    *,
    read_paths: Iterable[str] = (),
    write_paths: Iterable[str] = (),
    principal_id: str | None = None,
    policy: Mapping[str, Any] | None = None,
) -> None:
    if card["status"] not in {"authorized", "running", "review"}:
        raise RunStateError("run is not authorized for execution")
    planned = _route(card, node_id)
    node = _node(card, node_id)
    if node["status"] not in {"pending", "running"}:
        raise RunStateError(f"node {node_id!r} is not executable")
    for path in read_paths:
        if not any(path_within(path, prefix) for prefix in planned["scope"]["read_paths"]):
            raise RunStateError(f"read outside node scope: {path!r}")
    for path in write_paths:
        if not any(path_within(path, prefix) for prefix in planned["scope"]["write_paths"]):
            raise RunStateError(f"write outside node scope: {path!r}")
    if principal_id is not None:
        if policy is None:
            raise RunStateError("principal guard requires the bound policy")
        principals = policy_principals(policy)
        if principal_id not in principals:
            raise RunStateError(f"unknown execution principal {principal_id!r}")
        if planned["role"] not in principals[principal_id]["roles"]:
            raise RunStateError(
                f"principal {principal_id!r} does not hold planned role "
                f"{planned['role']!r}"
            )


def record_attempt(
    card: dict[str, Any],
    policy: dict[str, Any],
    candidate_manifest: dict[str, Any],
    *,
    node_id: str,
    attempt_id: str,
    started_at: str,
    finished_at: str,
    effective_principal_id: str,
    effective_agent: str,
    effective_model: str,
    effective_reasoning: str,
    effective_skill: str,
    effective_subagents: Sequence[str] = (),
    effective_tools: Sequence[str] = (),
    data_egress: Mapping[str, Any] | None = None,
    network: str = "none",
    external_mutations: Sequence[str] = (),
    cost_units: float = 0,
    result: str,
    repository: str | Path,
    schema_store: SchemaStore | None = None,
) -> dict[str, Any]:
    store = schema_store or SchemaStore()
    validate_policy(policy, schema_store=store)
    store.validate(card, "run-card.schema.json")
    store.validate(candidate_manifest, "candidate-manifest.schema.json")
    if card["policy_digest"] != digest(policy):
        raise RunStateError("attempt policy digest mismatch")
    if (
        card["candidate_manifest_digest"] != digest(candidate_manifest)
        or card["candidate_tree_digest"] != candidate_manifest["tree_digest"]
    ):
        raise RunStateError("attempt candidate digest mismatch")
    if repository is not None:
        verify_candidate_manifest(repository, candidate_manifest, schema_store=store)
    guard(card, node_id, principal_id=effective_principal_id, policy=policy)
    if set(effective_tools) - set(policy["execution"]["allowed_tools"]):
        raise RunStateError("attempt used a tool outside the bound policy")
    current = _node(card, node_id)
    if len(current["attempts"]) >= card["budgets"]["max_attempts"]:
        raise RunStateError("run attempt budget is exhausted")
    if any(
        attempt["id"] == attempt_id
        for node in card["nodes"]
        for attempt in node["attempts"]
    ):
        raise RunStateError(f"duplicate attempt id {attempt_id!r}")
    try:
        started = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        finished = datetime.fromisoformat(finished_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RunStateError("attempt timestamps must be valid ISO date-times") from exc
    if started.tzinfo is None or finished.tzinfo is None:
        raise RunStateError("attempt timestamps must include a timezone")
    elapsed_seconds = (finished - started).total_seconds()
    if elapsed_seconds < 0:
        raise RunStateError("attempt cannot finish before it starts")
    if isinstance(cost_units, bool) or cost_units < 0:
        raise RunStateError("attempt cost_units must be a non-negative number")
    used_elapsed = sum(
        float(attempt.get("elapsed_seconds", 0))
        for node in card["nodes"]
        for attempt in node["attempts"]
    )
    used_cost = sum(
        float(attempt.get("cost_units", 0))
        for node in card["nodes"]
        for attempt in node["attempts"]
    )
    if used_elapsed + elapsed_seconds > card["budgets"]["max_elapsed_seconds"]:
        raise RunStateError("run elapsed-time budget is exhausted")
    if used_cost + float(cost_units) > card["budgets"]["max_cost_units"]:
        raise RunStateError("run cost budget is exhausted")
    planned_scope = _route(card, node_id)["scope"]
    network_order = {"none": 0, "read": 1, "write": 2}
    if network not in network_order:
        raise RunStateError(f"unsupported factual network mode {network!r}")
    if network_order[network] > network_order[planned_scope["network"]]:
        raise RunStateError("attempt network use exceeds planned node scope")
    if set(external_mutations) - set(planned_scope["external_mutations"]):
        raise RunStateError("attempt external mutation exceeds planned node scope")
    route = {
        "principal_id": effective_principal_id,
        "agent": effective_agent,
        "model": effective_model,
        "reasoning": effective_reasoning,
        "skill": effective_skill,
        "subagents": sorted(set(effective_subagents)),
        "tools": sorted(set(effective_tools)),
        "data_egress": deepcopy(
            dict(
                data_egress
                or {
                    "provider": "",
                    "path_prefixes": [],
                    "content_classes": [],
                }
            )
        ),
    }
    _verify_effective_route_policy(
        {"effective_route": route, "node_id": node_id},
        card,
        policy,
    )
    attempt = {
        "id": attempt_id,
        "started_at": started_at,
        "finished_at": finished_at,
        "effective_principal_id": effective_principal_id,
        "effective_agent": effective_agent,
        "effective_model": effective_model,
        "effective_reasoning": effective_reasoning,
        "effective_skill": effective_skill,
        "effective_subagents": sorted(set(effective_subagents)),
        "effective_tools": sorted(set(effective_tools)),
        "data_egress": route["data_egress"],
        "network": network,
        "external_mutations": sorted(set(external_mutations)),
        "elapsed_seconds": elapsed_seconds,
        "cost_units": float(cost_units),
        "policy_digest": digest(policy),
        "candidate_tree_digest": candidate_manifest["tree_digest"],
        "result": result,
    }
    result_card = deepcopy(card)
    target = next(item for item in result_card["nodes"] if item["node_id"] == node_id)
    target["attempts"].append(attempt)
    target["status"] = "running"
    if result_card["status"] == "authorized":
        result_card["status"] = "running"
    store.validate(result_card, "run-card.schema.json")
    return result_card


def _loop(registry: Mapping[str, Any], loop_id: str) -> Mapping[str, Any]:
    matches = [item for item in registry["loops"] if item["id"] == loop_id]
    if len(matches) != 1:
        raise RunStateError(f"unknown or duplicate loop {loop_id!r}")
    return matches[0]


def _contract(registry: Mapping[str, Any], contract_id: str) -> Mapping[str, Any]:
    matches = [
        item for item in registry["evidence_contracts"] if item["id"] == contract_id
    ]
    if len(matches) != 1:
        raise RunStateError(f"unknown or duplicate evidence contract {contract_id!r}")
    return matches[0]


def _check_runtime_identity(
    card: Mapping[str, Any],
    registry: Mapping[str, Any],
    policy: Mapping[str, Any],
    candidate_manifest: Mapping[str, Any],
    *,
    schema_store: SchemaStore,
) -> None:
    schema_store.validate(dict(card), "run-card.schema.json")
    schema_store.validate(dict(candidate_manifest), "candidate-manifest.schema.json")
    checks = {
        "registry_digest": digest(registry),
        "policy_digest": digest(policy),
        "candidate_tree_digest": candidate_manifest["tree_digest"],
        "candidate_manifest_digest": digest(candidate_manifest),
    }
    for field, expected in checks.items():
        if card[field] != expected:
            raise RunStateError(f"run card {field} mismatch")


def _matching_attempt(
    evidence: Mapping[str, Any], node: Mapping[str, Any]
) -> Mapping[str, Any]:
    route = evidence["effective_route"]
    matches = [
        attempt
        for attempt in node["attempts"]
        if attempt["id"] == evidence["attempt_id"]
    ]
    if len(matches) != 1:
        raise RunStateError(
            f"evidence must cite exactly one factual attempt {evidence['attempt_id']!r}"
        )
    attempt = matches[0]
    expected = {
        "started_at": evidence["started_at"],
        "finished_at": evidence["finished_at"],
        "effective_principal_id": route["principal_id"],
        "effective_agent": route["agent"],
        "effective_model": route["model"],
        "effective_reasoning": route["reasoning"],
        "effective_skill": route["skill"],
        "result": evidence["result"],
    }
    if any(attempt[key] != value for key, value in expected.items()):
        raise RunStateError(
            "evidence effective route does not match a factual recorded attempt"
        )
    if sorted(attempt["effective_subagents"]) != sorted(route["subagents"]):
        raise RunStateError("evidence subagents do not match the cited attempt")
    if sorted(attempt["effective_tools"]) != sorted(route["tools"]):
        raise RunStateError("evidence tools do not match the cited attempt")
    if attempt["data_egress"] != route["data_egress"]:
        raise RunStateError("evidence data egress does not match the cited attempt")
    return attempt


def _verify_effective_route_policy(
    evidence: Mapping[str, Any],
    card: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> None:
    route = evidence["effective_route"]
    tools = set(route["tools"])
    if tools - set(policy["execution"]["allowed_tools"]):
        raise RunStateError("evidence route used a tool outside the bound policy")

    model_policy = policy["execution"]["model_policy"]
    egress = route["data_egress"]
    provider = egress["provider"]
    paths = egress["path_prefixes"]
    content_classes = set(egress["content_classes"])
    if provider and provider not in model_policy["allowed_providers"]:
        raise RunStateError("evidence route used a provider outside the bound policy")
    allowed_models = {
        (item["provider"], item["model"])
        for item in model_policy["allowed_models"]
    }
    if (provider, route["model"]) not in allowed_models:
        raise RunStateError("evidence route used a model outside the bound policy")
    if model_policy["privacy"] == "local_only" and provider:
        raise RunStateError("local-only model policy forbids provider data egress")
    if not provider and (paths or content_classes):
        raise RunStateError("data-egress scope requires a factual provider")
    if route["model"] == "none" and (provider or paths or content_classes):
        raise RunStateError("a no-model route cannot report model data egress")
    if content_classes - set(model_policy["allowed_content_classes"]):
        raise RunStateError(
            "evidence route used a content class outside the bound model policy"
        )
    if (
        model_policy["privacy"] == "public_data_only"
        and content_classes - set(model_policy["public_content_classes"])
    ):
        raise RunStateError(
            "public-data-only policy rejects unclassified egress content"
        )

    allowed_model_paths = model_policy["allowed_path_prefixes"]
    planned_scope = _route(card, evidence["node_id"])["scope"]
    for path in paths:
        if not any(path_within(path, prefix) for prefix in allowed_model_paths):
            raise RunStateError(
                f"evidence route used a path outside model policy: {path!r}"
            )
        if not any(
            path_within(path, prefix) for prefix in planned_scope["read_paths"]
        ):
            raise RunStateError(
                f"evidence route used a path outside planned node scope: {path!r}"
            )


def _verify_evidence(
    evidence: dict[str, Any],
    card: Mapping[str, Any],
    registry: Mapping[str, Any],
    policy: Mapping[str, Any],
    candidate_manifest: Mapping[str, Any],
    *,
    schema_store: SchemaStore,
) -> Mapping[str, Any]:
    schema_store.validate(evidence, "evidence.schema.json")
    node = _node(card, evidence["node_id"])
    if evidence["run_id"] != card["id"] or evidence["loop_id"] != node["loop_id"]:
        raise RunStateError("evidence run, node, or loop identity mismatch")
    if evidence["binding_digest"] != card["binding_digest"]:
        raise RunStateError("evidence binding digest mismatch")
    if evidence["policy_digest"] != digest(policy):
        raise RunStateError("evidence policy digest mismatch")
    candidate = evidence["candidate"]
    if (
        candidate["tree_digest"] != candidate_manifest["tree_digest"]
        or candidate["manifest_digest"] != digest(candidate_manifest)
    ):
        raise RunStateError("evidence candidate digest mismatch")
    if evidence["effective_route"]["principal_id"] != evidence["producer"]["id"]:
        raise RunStateError("evidence producer and effective principal differ")
    guard(
        card,
        evidence["node_id"],
        principal_id=evidence["producer"]["id"],
        policy=policy,
    )
    _matching_attempt(evidence, node)
    _verify_effective_route_policy(evidence, card, policy)
    contract = _contract(registry, evidence["contract_id"])
    loop_contract_ids = {
        contract_id
        for transition in _loop(registry, evidence["loop_id"])[
            "local_control_flow"
        ]["transitions"]
        for contract_id in transition["evidence_contract_ids"]
    }
    if evidence["contract_id"] not in loop_contract_ids:
        raise RunStateError("evidence contract does not belong to its loop")
    if evidence["result"] not in contract["accepted_results"]:
        raise RunStateError("evidence result is not accepted by its contract")
    if evidence["result"] not in policy["evidence"]["accepted_results"]:
        raise RunStateError("evidence result is not accepted by the bound policy")
    require_actor_capability(
        policy, evidence["producer"], contract["producer_capability"]
    )
    if "reviewer_capability" in contract:
        if contract["reviewer_capability"] not in principal_capabilities(
            policy, evidence["producer"]["id"]
        ):
            raise RunStateError("evidence producer lacks reviewer capability")
    if (
        contract.get("independent_from_capability")
        and evidence["producer"]["id"] in card["candidate_author_principal_ids"]
    ):
        raise RunStateError("candidate author cannot satisfy an independent gate")
    claims = {claim["id"]: claim for claim in evidence["claims"]}
    for claim_id in contract["required_claims"]:
        if claim_id not in claims or claims[claim_id]["result"] != "pass":
            raise RunStateError(f"required passing claim {claim_id!r} is missing")
    return contract


def _verify_payload_bytes(
    evidence: Mapping[str, Any],
    payload_root: str | Path,
) -> None:
    root = Path(payload_root).resolve()
    if not root.is_dir():
        raise RunStateError(f"evidence payload root does not exist: {root}")
    target = _inside(root, str(evidence["payload"]["path"]))
    if target.is_symlink() or not target.is_file():
        raise RunStateError("evidence payload must be a regular non-symlink file")
    try:
        first = target.read_bytes()
        first_stat = target.stat(follow_symlinks=False)
        second = target.read_bytes()
        second_stat = target.stat(follow_symlinks=False)
    except OSError as exc:
        raise RunStateError(f"cannot read evidence payload: {exc}") from exc
    if (
        first != second
        or first_stat.st_size != second_stat.st_size
        or first_stat.st_mtime_ns != second_stat.st_mtime_ns
    ):
        raise RunStateError("evidence payload changed while being verified")
    if _raw_digest(first) != evidence["payload"]["digest"]:
        raise RunStateError("evidence payload digest does not match its bytes")


def record_evidence(
    card: dict[str, Any],
    evidence: dict[str, Any],
    registry: dict[str, Any],
    policy: dict[str, Any],
    candidate_manifest: dict[str, Any],
    *,
    payload_root: str | Path,
    repository: str | Path,
    schema_store: SchemaStore | None = None,
) -> dict[str, Any]:
    store = schema_store or SchemaStore()
    validate_registry(registry, policy, schema_store=store)
    _check_runtime_identity(
        card, registry, policy, candidate_manifest, schema_store=store
    )
    if repository is not None:
        verify_candidate_manifest(repository, candidate_manifest, schema_store=store)
    _verify_payload_bytes(evidence, payload_root)
    _verify_evidence(
        evidence, card, registry, policy, candidate_manifest, schema_store=store
    )
    node = _node(card, evidence["node_id"])
    if node["status"] != "running" or not node["attempts"]:
        raise RunStateError("evidence requires a factual running attempt")
    if evidence["id"] in {item["id"] for item in card["evidence"]}:
        raise RunStateError(f"duplicate evidence id {evidence['id']!r}")
    result = deepcopy(card)
    evidence_digest = digest(evidence)
    result["evidence"].append(
        {
            "id": evidence["id"],
            "path": evidence["payload"]["path"],
            "digest": evidence_digest,
        }
    )
    target = next(
        item for item in result["nodes"] if item["node_id"] == evidence["node_id"]
    )
    target["evidence_ids"].append(evidence["id"])
    store.validate(result, "run-card.schema.json")
    return result


def validate_evidence(
    evidence: dict[str, Any],
    card: dict[str, Any],
    registry: dict[str, Any],
    policy: dict[str, Any],
    candidate_manifest: dict[str, Any],
    *,
    repository: str | Path,
    payload_root: str | Path,
    schema_store: SchemaStore | None = None,
) -> dict[str, Any]:
    """Validate evidence bytes, route, candidate, policy, and cited attempt."""

    store = schema_store or SchemaStore()
    validate_registry(registry, policy, schema_store=store)
    _check_runtime_identity(
        card, registry, policy, candidate_manifest, schema_store=store
    )
    verify_candidate_manifest(repository, candidate_manifest, schema_store=store)
    _verify_payload_bytes(evidence, payload_root)
    _verify_evidence(
        evidence,
        card,
        registry,
        policy,
        candidate_manifest,
        schema_store=store,
    )
    return evidence


def complete_node(
    card: dict[str, Any],
    node_id: str,
    registry: dict[str, Any],
    policy: dict[str, Any],
    candidate_manifest: dict[str, Any],
    evidence_documents: Mapping[str, dict[str, Any]],
    *,
    accepted_by: Mapping[str, Any],
    payload_root: str | Path,
    repository: str | Path,
    outcome: str = "passed",
    schema_store: SchemaStore | None = None,
) -> dict[str, Any]:
    store = schema_store or SchemaStore()
    validate_registry(registry, policy, schema_store=store)
    _check_runtime_identity(
        card, registry, policy, candidate_manifest, schema_store=store
    )
    if repository is not None:
        verify_candidate_manifest(repository, candidate_manifest, schema_store=store)
    node = _node(card, node_id)
    if node["status"] != "running":
        raise RunStateError("only a running node can be completed")
    if outcome not in {"passed", "failed", "blocked"}:
        raise RunStateError(f"unsupported node outcome {outcome!r}")
    loop = _loop(registry, node["loop_id"])
    require_actor_capability(
        policy, accepted_by, loop["authority"]["accept_capability"]
    )
    if outcome == "passed":
        required_contracts = {
            contract_id
            for transition in loop["local_control_flow"]["transitions"]
            if transition["kind"] == "success"
            for contract_id in transition["evidence_contract_ids"]
        }
        receipts_by_contract: dict[str, list[dict[str, Any]]] = {
            contract_id: [] for contract_id in required_contracts
        }
        for evidence_id in node["evidence_ids"]:
            if evidence_id not in evidence_documents:
                raise RunStateError(f"missing evidence document {evidence_id!r}")
            evidence = evidence_documents[evidence_id]
            references = [
                reference
                for reference in card["evidence"]
                if reference["id"] == evidence_id
            ]
            if len(references) != 1:
                raise RunStateError(
                    f"run card must contain one evidence receipt {evidence_id!r}"
                )
            if references[0]["digest"] != digest(evidence):
                raise RunStateError(
                    f"evidence document digest mismatch for {evidence_id!r}"
                )
            if references[0]["path"] != evidence["payload"]["path"]:
                raise RunStateError(
                    f"evidence document path mismatch for {evidence_id!r}"
                )
            _verify_payload_bytes(evidence, payload_root)
            contract = _verify_evidence(
                evidence,
                card,
                registry,
                policy,
                candidate_manifest,
                schema_store=store,
            )
            receipts_by_contract.setdefault(contract["id"], []).append(evidence)
        missing = [
            contract_id
            for contract_id, receipts in receipts_by_contract.items()
            if not receipts
        ]
        if missing:
            raise RunStateError(
                f"node lacks required evidence contracts {sorted(missing)!r}"
            )
        independent = any(
            _contract(registry, contract_id).get("independent_from_capability")
            for contract_id in required_contracts
        )
        if independent and accepted_by["id"] in card["candidate_author_principal_ids"]:
            raise RunStateError("candidate author cannot accept an independent node")
    result = deepcopy(card)
    target = next(item for item in result["nodes"] if item["node_id"] == node_id)
    target["status"] = outcome
    target["accepted_by"] = deepcopy(dict(accepted_by))
    if any(item["status"] == "running" for item in result["nodes"]):
        result["status"] = "running"
    else:
        result["status"] = "review"
    store.validate(result, "run-card.schema.json")
    return result


def complete_run(
    card: dict[str, Any],
    binding: dict[str, Any],
    registry: dict[str, Any],
    policy: dict[str, Any],
    candidate_manifest: dict[str, Any],
    *,
    completed_at: str,
    repository: str | Path,
    schema_store: SchemaStore | None = None,
) -> dict[str, Any]:
    store = schema_store or SchemaStore()
    _check_card_identity(
        card,
        binding,
        registry,
        policy,
        candidate_manifest,
        repository=repository,
        schema_store=store,
    )
    root_nodes = [
        item for item in card["nodes"] if item["loop_id"] == card["root_loop_id"]
    ]
    if len(root_nodes) != 1 or root_nodes[0]["status"] != "passed":
        raise RunStateError("the root loop has not passed")
    incomplete = [
        item["node_id"]
        for item in card["nodes"]
        if item["status"] not in {"passed", "skipped"}
    ]
    if incomplete:
        raise RunStateError(f"run has incomplete nodes {sorted(incomplete)!r}")
    result = deepcopy(card)
    result["status"] = "complete"
    result["completed_at"] = completed_at
    result["root_outcome"] = "succeeded"
    store.validate(result, "run-card.schema.json")
    return result


# Small compatibility names for CLI integrations.
candidate_manifest = build_candidate_manifest
