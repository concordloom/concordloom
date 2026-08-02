"""Stable, local-only command line interface for Concord Loom v0.1.

The CLI is deliberately a thin adapter over the portable core.  Artifact
commands always name their input and output paths, never contact a remote
service, and report failures as one compact JSON object on stderr.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
from hashlib import sha256
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
from typing import Any

from . import __version__
from .canonical import canonical_bytes, digest, load, save


class _ArgumentParser(argparse.ArgumentParser):
    """Argparse variant whose usage failures are machine-readable."""

    def error(self, message: str) -> None:
        _emit_error("usage_error", message)
        raise SystemExit(2)


def _emit(value: Mapping[str, Any], *, stream: Any = sys.stdout) -> None:
    print(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        file=stream,
    )


def _emit_error(code: str, message: str) -> None:
    _emit({"error": {"code": code, "message": message}}, stream=sys.stderr)


def _object(path: str | Path, label: str = "artifact") -> dict[str, Any]:
    value = load(path)
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object: {path}")
    return value


def _read_bounded_regular_file(
    path: str | Path,
    *,
    label: str,
    limit: int,
) -> bytes:
    """Read stable bytes without following links or opening special files."""

    source = Path(path)
    try:
        path_before = source.lstat()
    except OSError as exc:
        raise ValueError(f"cannot inspect {label}: {source}") from exc
    if stat.S_ISLNK(path_before.st_mode) or not stat.S_ISREG(path_before.st_mode):
        raise ValueError(f"{label} must be a regular, non-symbolic-link file")
    if path_before.st_size > limit:
        raise ValueError(f"{label} exceeds the 64 KiB safety limit")

    flags = os.O_RDONLY
    flags |= getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    flags |= getattr(os, "O_NONBLOCK", 0)
    try:
        descriptor = os.open(source, flags)
    except OSError as exc:
        raise ValueError(f"cannot open {label}: {source}") from exc
    try:
        opened_before = os.fstat(descriptor)
        if not stat.S_ISREG(opened_before.st_mode):
            raise ValueError(
                f"{label} must be a regular, non-symbolic-link file"
            )
        if (opened_before.st_dev, opened_before.st_ino) != (
            path_before.st_dev,
            path_before.st_ino,
        ):
            raise ValueError(f"{label} changed while it was being opened")
        if opened_before.st_size > limit:
            raise ValueError(f"{label} exceeds the 64 KiB safety limit")

        chunks: list[bytes] = []
        remaining = limit + 1
        while remaining:
            chunk = os.read(descriptor, min(65_537, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        value = b"".join(chunks)
        opened_after = os.fstat(descriptor)
    finally:
        os.close(descriptor)

    if len(value) > limit:
        raise ValueError(f"{label} exceeds the 64 KiB safety limit")
    stable_fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
    if any(
        getattr(opened_before, field) != getattr(opened_after, field)
        for field in stable_fields
    ) or len(value) != opened_after.st_size:
        raise ValueError(f"{label} changed while it was being read")
    try:
        path_after = source.lstat()
    except OSError as exc:
        raise ValueError(f"{label} changed while it was being read") from exc
    if stat.S_ISLNK(path_after.st_mode) or (
        path_after.st_dev,
        path_after.st_ino,
    ) != (opened_after.st_dev, opened_after.st_ino):
        raise ValueError(f"{label} changed while it was being read")
    return value


def _array(path: str | Path, label: str = "artifact") -> list[Any]:
    value = load(path)
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a JSON array: {path}")
    return value


def _bound_development_model(
    binding: Mapping[str, Any],
    binding_path: str | Path,
    explicit_path: str | Path | None,
) -> dict[str, Any]:
    artifacts = [
        artifact
        for artifact in binding.get("artifacts", [])
        if artifact.get("role") == "atlas_input"
    ]
    if len(artifacts) != 1:
        raise ValueError("binding must declare exactly one atlas_input artifact")
    artifact = artifacts[0]
    if explicit_path is not None:
        model = _object(explicit_path, "development model")
    else:
        relative = Path(str(artifact["path"]))
        candidates = [Path.cwd() / relative]
        resolved_binding = Path(binding_path).resolve()
        candidates.extend(parent / relative for parent in resolved_binding.parents)
        existing = []
        seen: set[Path] = set()
        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved not in seen and resolved.is_file():
                existing.append(resolved)
                seen.add(resolved)
        if len(existing) != 1:
            raise ValueError(
                "cannot resolve the binding's exact atlas_input artifact; "
                "pass --development-model explicitly"
            )
        model = _object(existing[0], "development model")
    if digest(model) != artifact["digest"]:
        raise ValueError(
            "development model digest does not match the binding atlas_input"
        )
    return model


def _save_outputs(outputs: Mapping[str, tuple[str | Path, Any]]) -> None:
    for _, (path, value) in outputs.items():
        save(path, value)
    _emit(
        {
            "ok": True,
            "outputs": {
                name: str(path)
                for name, (path, _) in sorted(outputs.items())
            },
        }
    )


def _save_new_output(name: str, path: str | Path, value: Any) -> None:
    """Atomically create one JSON artifact without replacing existing bytes."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    canonical_bytes(value)
    payload = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=target.parent,
            prefix=".concordloom-output.",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(payload)
            temporary.flush()
            os.fsync(temporary.fileno())
        try:
            os.link(temporary_path, target)
        except FileExistsError as exc:
            raise ValueError(f"output already exists: {target}") from exc
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    _emit({"ok": True, "outputs": {name: str(target)}})


def _reject_output_collisions(
    output: str | Path,
    input_paths: Sequence[str | Path | None],
    *,
    label: str,
) -> None:
    """Reject resolved aliases from a mutable output to immutable inputs."""

    target = Path(output).resolve(strict=False)
    for input_path in input_paths:
        if input_path is None:
            continue
        if target == Path(input_path).resolve(strict=False):
            raise ValueError(f"{label} output cannot replace an input artifact")


def _save_run_card_output(
    card_input: str | Path,
    output: str | Path,
    value: Any,
) -> None:
    """Update the named mutable card or create a distinct output once."""

    input_path = Path(os.path.abspath(card_input))
    output_path = Path(os.path.abspath(output))
    if output_path.resolve(strict=False) == input_path.resolve(strict=False):
        if output_path != input_path or output_path.is_symlink():
            raise ValueError("run-card output cannot replace an input through an alias")
        _save_outputs({"run_card": (output_path, value)})
        return
    _save_new_output("run_card", output_path, value)


def _route_preview_pair(
    args: argparse.Namespace,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    preview_path = getattr(args, "route_preview", None)
    replaced_path = getattr(args, "replaced_route_preview", None)
    if replaced_path and not preview_path:
        raise ValueError("--replaced-route-preview requires --route-preview")
    return (
        _object(preview_path, "route preview") if preview_path else None,
        (
            _object(replaced_path, "replaced route preview")
            if replaced_path
            else None
        ),
    )


def _parse_branch_choices(values: Sequence[str]) -> dict[str, str]:
    """Parse repeatable ``LOOP:STATE=TRANSITION`` route choices."""

    choices: dict[str, str] = {}
    for value in values:
        if (
            value != value.strip()
            or value.count("=") != 1
            or value.partition("=")[0].count(":") != 1
        ):
            raise ValueError(
                "--branch-choice must use LOOP:STATE=TRANSITION"
            )
        source, _, transition_id = value.partition("=")
        loop_id, _, state_id = source.partition(":")
        if not all(
            item and item == item.strip()
            for item in (loop_id, state_id, transition_id)
        ):
            raise ValueError(
                "--branch-choice must use LOOP:STATE=TRANSITION with "
                "non-empty identifiers"
            )
        key = f"{loop_id}:{state_id}"
        if key in choices:
            raise ValueError(
                f"--branch-choice repeats the same loop and state: {key}"
            )
        choices[key] = transition_id
    return choices


def _parse_retry_choices(values: Sequence[str]) -> dict[str, int]:
    """Parse repeatable ``LOOP:TRANSITION=COUNT`` retry choices."""

    choices: dict[str, int] = {}
    for value in values:
        if (
            value != value.strip()
            or value.count("=") != 1
            or value.partition("=")[0].count(":") != 1
        ):
            raise ValueError(
                "--retry-choice must use LOOP:TRANSITION=COUNT"
            )
        source, _, raw_count = value.partition("=")
        loop_id, _, transition_id = source.partition(":")
        if not all(
            item and item == item.strip()
            for item in (loop_id, transition_id, raw_count)
        ):
            raise ValueError(
                "--retry-choice must use LOOP:TRANSITION=COUNT with "
                "non-empty identifiers and a count"
            )
        if not raw_count.isascii() or not raw_count.isdecimal():
            raise ValueError(
                f"--retry-choice count must be a non-negative integer: {raw_count}"
            )
        count = int(raw_count, 10)
        key = f"{loop_id}:{transition_id}"
        if key in choices:
            raise ValueError(
                f"--retry-choice repeats the same loop and transition: {key}"
            )
        choices[key] = count
    return choices


def _safe_route_preview_output(
    repository: str | Path,
    output: str | Path,
    candidate_manifest: Mapping[str, Any],
    *,
    input_paths: Sequence[str | Path] = (),
) -> Path:
    repository_root = Path(repository).resolve()
    if not repository_root.is_dir():
        raise ValueError(f"repository does not exist: {repository_root}")
    lexical = Path(output).absolute()
    resolved = lexical.resolve(strict=False)
    for input_path in input_paths:
        if resolved == Path(input_path).resolve(strict=False):
            raise ValueError("route preview output cannot replace an input artifact")
    if resolved.exists():
        raise ValueError(f"output already exists: {resolved}")

    lexical_inside = False
    resolved_inside = False
    try:
        lexical.relative_to(repository_root)
        lexical_inside = True
    except ValueError:
        pass
    try:
        relative = resolved.relative_to(repository_root)
        resolved_inside = True
    except ValueError:
        relative = None
    if lexical_inside != resolved_inside:
        raise ValueError("route preview output cannot escape through a symlink")
    if not resolved_inside:
        return resolved

    assert relative is not None
    if tuple(relative.parts[:2]) != (".concord", "runs") or len(
        relative.parts
    ) < 3:
        raise ValueError(
            "route preview output inside the repository must be beneath "
            ".concord/runs"
        )
    candidate_paths = {
        Path(str(item["path"])).as_posix()
        for item in candidate_manifest["files"]
    }
    if relative.as_posix() in candidate_paths:
        raise ValueError("route preview output cannot replace a candidate file")
    current = repository_root
    for part in relative.parts[:-1]:
        current /= part
        if current.is_symlink():
            raise ValueError("route preview output cannot use a symlinked directory")
    ignored = subprocess.run(
        [
            "git",
            "-C",
            str(repository_root),
            "check-ignore",
            "--quiet",
            "--no-index",
            "--",
            relative.as_posix(),
        ],
        check=False,
        capture_output=True,
    )
    if ignored.returncode == 1:
        raise ValueError(
            "route preview output inside the repository must be explicitly "
            "ignored by Git"
        )
    if ignored.returncode != 0:
        raise ValueError("cannot verify the route preview output ignore contract")
    return resolved


def _artifact_path(path: str | Path, root: str | Path) -> str:
    resolved_root = Path(root).resolve()
    resolved = Path(path).resolve()
    try:
        relative = resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(
            f"binding artifact is outside --artifact-root: {path}"
        ) from exc
    if not relative.parts:
        raise ValueError(f"binding artifact must name a file beneath --artifact-root: {path}")
    return relative.as_posix()


def _verify_bound_artifact_bytes(
    document: Mapping[str, Any], artifact_root: str | Path
) -> None:
    from .canonical import digest

    root = Path(artifact_root).resolve()
    for artifact in document.get("artifacts", []):
        target = (root / str(artifact["path"])).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise ValueError(
                f"bound artifact escapes --artifact-root: {artifact['path']}"
            ) from exc
        if digest(load(target)) != artifact["digest"]:
            raise ValueError(
                f"bound artifact digest mismatch for role {artifact['role']!r}"
            )


def _actor(args: argparse.Namespace) -> dict[str, str]:
    actor = {"id": args.actor_id, "kind": args.actor_kind}
    if getattr(args, "actor_display_name", None):
        actor["display_name"] = args.actor_display_name
    return actor


def _question(document: Mapping[str, Any], question_id: str) -> dict[str, Any]:
    matches = [
        item
        for item in document.get("questions", [])
        if isinstance(item, dict) and item.get("id") == question_id
    ]
    if len(matches) != 1:
        raise ValueError(
            f"question id must match exactly one question: {question_id!r}"
        )
    return matches[0]


def _decision_records(paths: Sequence[str]) -> list[dict[str, Any]]:
    decisions: list[dict[str, Any]] = []
    for path in paths:
        value = load(path)
        if (
            isinstance(value, dict)
            and value.get("kind") == "concordloom.decision-record"
        ):
            values = [value.get("decision")]
        elif isinstance(value, dict) and isinstance(value.get("decisions"), list):
            values = value["decisions"]
        elif isinstance(value, list):
            values = value
        else:
            values = [value]
        for record in values:
            if not isinstance(record, dict):
                raise ValueError(f"decision record must be an object: {path}")
            decisions.append(record)
    return decisions


def _cmd_inspect(args: argparse.Namespace) -> None:
    from .inspect_repo import InspectionLimits, inspect_repository

    graph = inspect_repository(
        args.repository,
        generated_at=args.generated_at,
        include_untracked=args.include_untracked,
        limits=InspectionLimits(
            max_files=args.max_files,
            max_file_bytes=args.max_file_bytes,
            max_history_commits=args.max_history_commits,
            max_paths_per_commit=args.max_paths_per_commit,
            max_cochange_pairs=args.max_cochange_pairs,
            max_subprocess_bytes=args.max_subprocess_bytes,
            subprocess_timeout_seconds=args.subprocess_timeout_seconds,
        ),
    )
    _save_outputs({"graph": (args.output, graph)})


def _cmd_questions(args: argparse.Namespace) -> None:
    from .interview import generate_questions

    result = generate_questions(_object(args.graph, "project graph"))
    _save_outputs({"questions": (args.output, result)})


def _cmd_decide(args: argparse.Namespace) -> None:
    from .interview import make_decision
    from .canonical import digest
    from .schema import validate_named

    questions = _object(args.questions, "question set")
    graph_delta = None
    if args.graph_delta:
        graph_delta = _array(args.graph_delta, "graph delta")
    decision = make_decision(
        _question(questions, args.question),
        args.verdict,
        actor=_actor(args),
        authority_ref=args.authority_ref,
        rationale=args.rationale,
        decided_at=args.decided_at,
        decision_id=args.decision_id,
        correction=args.correction,
        graph_delta=graph_delta,
    )
    result = {
        "kind": "concordloom.decision-record",
        "schema_version": "0.1",
        "id": decision["id"],
        "question_set_digest": digest(questions),
        "question_id": args.question,
        "decision": decision,
    }
    validate_named(result)
    _save_outputs({"decision": (args.output, result)})


def _cmd_accept(args: argparse.Namespace) -> None:
    policy = _object(args.policy, "authority policy")
    if args.proposal:
        from .compiler import accept_loop_design

        if (
            not args.decisions
            or not args.accepted_graph
            or not args.decision_id
            or not args.rationale
        ):
            raise ValueError(
                "loop-design acceptance requires --accepted-graph, --decisions, "
                "--decision-id, and --rationale"
            )
        accepted_design = accept_loop_design(
            _object(args.proposal, "loop-design proposal"),
            _object(args.decisions, "decision log"),
            policy,
            accepted_graph=_object(args.accepted_graph, "accepted project graph"),
            decision_id=args.decision_id,
            actor=_actor(args),
            accepted_at=args.accepted_at,
            authority_ref=args.authority_ref,
            rationale=args.rationale,
        )
        _save_outputs({"accepted_loop_design": (args.output, accepted_design)})
        return

    from .graph import apply_decisions
    from .interview import make_decision_log
    from .schema import validate_named

    if not args.decision or not args.decision_log_output:
        raise ValueError(
            "project acceptance requires --decision and --decision-log-output"
        )
    graph = _object(args.graph, "observed project graph")
    decision_log = make_decision_log(
        graph,
        policy,
        _decision_records(args.decision),
        log_id=args.log_id,
        acceptance_actor=_actor(args),
        acceptance_authority_ref=args.authority_ref,
        accepted_at=args.accepted_at,
    )
    accepted = apply_decisions(graph, decision_log, policy)
    validate_named(decision_log)
    validate_named(accepted)
    _save_outputs(
        {
            "accepted_graph": (args.output, accepted),
            "decision_log": (args.decision_log_output, decision_log),
        }
    )


def _cmd_propose(args: argparse.Namespace) -> None:
    from .compiler import propose_loop_design

    graph = _object(args.graph, "accepted project graph")
    decisions = _object(args.decisions, "decision log")
    policy = _object(args.policy, "policy")
    proposal = propose_loop_design(
        graph,
        decisions,
        policy,
        proposal_id=args.design_id or "loop-design-proposal",
    )
    _save_outputs({"loop_design_proposal": (args.output, proposal)})


def _cmd_compile(args: argparse.Namespace) -> None:
    graph = _object(args.graph, "accepted project graph")
    decisions = _object(args.decisions, "decision log")
    design_proposal = _object(args.design_proposal, "loop-design proposal")
    design = _object(args.design, "accepted loop design")
    policy = _object(args.policy, "policy")
    if design.get("status") != "accepted":
        raise ValueError(
            "compile requires an operator-accepted loop design; run propose first"
        )
    from .compiler import compile_registry, create_binding_proposal

    registry = compile_registry(
        graph,
        decisions,
        design,
        policy,
        loop_design_proposal=design_proposal,
        registry_id=args.registry_id or "compiled-cycle-registry",
    )
    proposal = create_binding_proposal(
        graph,
        decisions,
        design,
        registry,
        policy,
        loop_design_proposal=design_proposal,
        artifact_paths={
            "accepted_project_graph": _artifact_path(args.graph, args.artifact_root),
            "decision_log": _artifact_path(args.decisions, args.artifact_root),
            "loop_design_proposal": _artifact_path(
                args.design_proposal, args.artifact_root
            ),
            "accepted_loop_design": _artifact_path(args.design, args.artifact_root),
            "cycle_registry": _artifact_path(
                args.registry_output, args.artifact_root
            ),
            "policy": _artifact_path(args.policy, args.artifact_root),
        },
        proposal_id=args.proposal_id or f"{design['id']}-binding-proposal",
        created_at=args.created_at,
        predecessor_binding_digest=args.predecessor_binding_digest,
    )
    _save_outputs(
        {
            "binding_proposal": (args.proposal_output, proposal),
            "registry": (args.registry_output, registry),
        }
    )


def _cmd_activate(args: argparse.Namespace) -> None:
    from .compiler import activate_binding

    binding = activate_binding(
        _object(args.proposal, "binding proposal"),
        _object(args.graph, "accepted project graph"),
        _object(args.decisions, "decision log"),
        _object(args.design_proposal, "loop-design proposal"),
        _object(args.design, "accepted loop design"),
        _object(args.registry, "cycle registry"),
        _object(args.policy, "policy"),
        activation_decision={
            "decision_id": args.decision_id,
            "actor": _actor(args),
            "authority_ref": args.authority_ref,
            "accepted_at": args.accepted_at,
            "rationale": args.rationale,
        },
        binding_id=args.binding_id,
    )
    _save_outputs({"binding": (args.output, binding)})


def _cmd_validate(args: argparse.Namespace) -> None:
    from .graph import validate_project_graph
    from .loops import validate_loop_design, validate_policy, validate_registry
    from .schema import validate_named

    artifact = _object(args.input)
    validate_named(artifact, args.schema)
    kind = artifact.get("kind")
    if kind == "concordloom.project-graph":
        validate_project_graph(artifact)
        if artifact.get("phase") == "accepted":
            if not args.observed_graph or not args.decisions or not args.policy:
                raise ValueError(
                    "accepted graph validation requires --observed-graph, "
                    "--decisions, and --policy"
                )
            from .graph import apply_decisions

            expected = apply_decisions(
                _object(args.observed_graph, "observed project graph"),
                _object(args.decisions, "decision log"),
                _object(args.policy, "policy"),
            )
            if expected != artifact:
                raise ValueError("accepted project graph differs from decision overlay")
    elif kind == "concordloom.question-set":
        if not args.graph:
            raise ValueError("question-set validation requires --graph")
        from .interview import generate_questions

        if generate_questions(_object(args.graph, "observed project graph")) != artifact:
            raise ValueError("question set differs from its source graph")
    elif kind == "concordloom.decision-record":
        if not args.questions:
            raise ValueError("decision-record validation requires --questions")
        from .canonical import digest

        questions = _object(args.questions, "question set")
        if artifact["question_set_digest"] != digest(questions):
            raise ValueError("decision record question-set digest mismatch")
        question = _question(questions, artifact["question_id"])
        if artifact["decision"]["subject_id"] != question["hypothesis_id"]:
            raise ValueError("decision record answers a different hypothesis")
    elif kind == "concordloom.decision-log":
        if not args.graph or not args.policy:
            raise ValueError("decision-log validation requires --graph and --policy")
        from .graph import apply_decisions

        apply_decisions(
            _object(args.graph, "observed project graph"),
            artifact,
            _object(args.policy, "policy"),
        )
    elif kind == "concordloom.policy":
        validate_policy(artifact)
    elif kind == "concordloom.loop-design-proposal":
        if not args.graph or not args.decisions or not args.policy:
            raise ValueError(
                "loop-design proposal validation requires --graph, --decisions, "
                "and --policy"
            )
        from .compiler import validate_loop_design_proposal

        validate_loop_design_proposal(
            artifact,
            _object(args.graph, "accepted project graph"),
            _object(args.decisions, "decision log"),
            _object(args.policy, "policy"),
        )
    elif kind == "concordloom.loop-design-manifest":
        if not args.decisions or not args.policy or not args.proposal:
            raise ValueError(
                "loop-design validation requires --proposal, --decisions, and --policy"
            )
        validate_loop_design(
            artifact,
            _object(args.decisions, "decision log"),
            _object(args.policy, "policy"),
            proposal=_object(args.proposal, "loop-design proposal"),
            accepted_graph=(
                _object(args.graph, "accepted project graph")
                if args.graph
                else None
            ),
        )
    elif kind == "concordloom.cycle-registry":
        if (
            not args.policy
            or not args.graph
            or not args.decisions
            or not args.proposal
            or not args.design
        ):
            raise ValueError(
                "cycle-registry validation requires --graph, --decisions, "
                "--proposal, --design, and --policy"
            )
        policy = _object(args.policy, "policy")
        graph = _object(args.graph, "accepted project graph")
        decisions = _object(args.decisions, "decision log")
        design = _object(args.design, "accepted loop design")
        validate_registry(artifact, policy)
        from .canonical import digest

        expected = {
            "source_graph_digest": digest(graph),
            "source_decisions_digest": digest(decisions),
            "source_loop_design_digest": digest(design),
            "policy_digest": digest(policy),
        }
        if any(artifact[field] != value for field, value in expected.items()):
            raise ValueError("cycle registry source digest mismatch")
        validate_loop_design(
            design,
            decisions,
            policy,
            proposal=_object(args.proposal, "loop-design proposal"),
            accepted_graph=graph,
        )
    elif kind == "concordloom.binding-proposal":
        required = (
            args.graph,
            args.decisions,
            args.proposal,
            args.design,
            args.registry,
            args.policy,
        )
        if not all(required):
            raise ValueError(
                "binding-proposal validation requires --graph, --decisions, "
                "--proposal, --design, --registry, and --policy"
            )
        from .compiler import validate_binding_proposal

        validate_binding_proposal(
            artifact,
            _object(args.graph),
            _object(args.decisions),
            _object(args.proposal),
            _object(args.design),
            _object(args.registry),
            _object(args.policy),
        )
        _verify_bound_artifact_bytes(artifact, args.artifact_root)
    elif kind == "concordloom.binding":
        if not args.binding_proposal or not args.registry or not args.policy:
            raise ValueError(
                "binding validation requires --binding-proposal, --registry, "
                "and --policy"
            )
        from .run import validate_binding

        validate_binding(
            artifact,
            _object(args.registry),
            _object(args.policy),
            binding_proposal=_object(args.binding_proposal),
        )
        _verify_bound_artifact_bytes(artifact, args.artifact_root)
    elif kind == "concordloom.candidate-manifest":
        if not args.repository:
            raise ValueError("candidate validation requires --repository")
        from .run import verify_candidate_manifest

        verify_candidate_manifest(args.repository, artifact)
    elif kind == "concordloom.route-preview":
        required = (
            args.binding,
            args.registry,
            args.policy,
            args.candidate,
            args.development_model,
            args.repository,
        )
        if not all(required):
            raise ValueError(
                "route-preview validation requires --binding, --registry, "
                "--policy, --candidate, --development-model, and --repository"
            )
        from .route import validate_route_preview
        from .run import verify_candidate_manifest

        binding = _object(args.binding, "binding")
        candidate = _object(args.candidate, "candidate manifest")
        verify_candidate_manifest(args.repository, candidate)
        validate_route_preview(
            artifact,
            binding,
            _object(args.registry, "cycle registry"),
            _object(args.policy, "policy"),
            candidate,
            _bound_development_model(
                binding,
                args.binding,
                args.development_model,
            ),
            replaced_preview=(
                _object(args.replaced_route_preview, "replaced route preview")
                if args.replaced_route_preview
                else None
            ),
        )
    elif kind == "concordloom.run-card":
        required = (
            args.binding,
            args.registry,
            args.policy,
            args.candidate,
            args.repository,
        )
        if not all(required):
            raise ValueError(
                "run-card validation requires --binding, --registry, --policy, "
                "--candidate, and --repository"
            )
        from .run import validate_run_card

        binding = _object(args.binding, "binding")
        route_preview, replaced_route_preview = _route_preview_pair(args)

        validate_run_card(
            artifact,
            binding,
            _object(args.registry),
            _object(args.policy),
            _object(args.candidate),
            repository=args.repository,
            development_model=(
                _bound_development_model(
                    binding,
                    args.binding,
                    args.development_model,
                )
                if route_preview is not None
                else None
            ),
            route_preview=route_preview,
            replaced_route_preview=replaced_route_preview,
        )
    elif kind == "concordloom.evidence":
        required = (
            args.card,
            args.registry,
            args.policy,
            args.candidate,
            args.repository,
            args.payload_root,
        )
        if not all(required):
            raise ValueError(
                "evidence validation requires --card, --registry, --policy, "
                "--candidate, --repository, and --payload-root"
            )
        from .run import validate_evidence

        binding = _object(args.binding, "binding") if args.binding else None
        route_preview, replaced_route_preview = _route_preview_pair(args)
        if route_preview is not None and binding is None:
            raise ValueError("preview-backed evidence validation requires --binding")

        validate_evidence(
            artifact,
            _object(args.card),
            _object(args.registry),
            _object(args.policy),
            _object(args.candidate),
            repository=args.repository,
            payload_root=args.payload_root,
            binding=binding,
            development_model=(
                _bound_development_model(
                    binding,
                    args.binding,
                    args.development_model,
                )
                if route_preview is not None and binding is not None
                else None
            ),
            route_preview=route_preview,
            replaced_route_preview=replaced_route_preview,
        )
    elif kind == "concordloom.catalog":
        from .catalog import validate_catalog

        validate_catalog(artifact, artifact_root=args.artifact_root)
    elif kind == "concordloom.evolution-signal":
        if not args.base_binding:
            raise ValueError("evolution-signal validation requires --base-binding")
        if artifact["base_binding_digest"] != _object(args.base_binding)[
            "binding_digest"
        ]:
            raise ValueError("evolution signal is pinned to another binding")
    elif kind == "concordloom.evolution-proposal":
        if not args.policy or not args.base_binding:
            raise ValueError(
                "evolution-proposal validation requires --policy and --base-binding"
            )
        from .evolution import validate_evolution_proposal

        validate_evolution_proposal(
            artifact,
            _object(args.policy),
            base_binding=_object(args.base_binding),
            base_targets=(
                _object(args.base_targets) if args.base_targets else None
            ),
        )
    _emit(
        {
            "kind": kind,
            "ok": True,
            "path": args.input,
            "schema": args.schema or "public-kind",
        }
    )


def _cmd_candidate(args: argparse.Namespace) -> None:
    from .run import build_candidate_manifest

    manifest = build_candidate_manifest(
        args.repository,
        include_untracked=args.include_untracked,
        manifest_id=args.manifest_id or "candidate",
        generated_at=args.generated_at,
    )
    _save_outputs({"candidate_manifest": (args.output, manifest)})


def _cmd_catalog(args: argparse.Namespace) -> None:
    from .catalog import append_binding

    binding = _object(args.binding, "binding")
    catalog = append_binding(
        _object(args.catalog, "binding catalog") if args.catalog else None,
        binding,
        path=_artifact_path(args.binding, args.artifact_root),
        catalog_id=args.catalog_id or "binding-catalog",
    )
    _save_outputs({"catalog": (args.output, catalog)})


def _cmd_route_preview(args: argparse.Namespace) -> None:
    from .route import create_route_preview
    from .run import verify_candidate_manifest

    branch_choices = _parse_branch_choices(getattr(args, "branch_choice", ()))
    retry_choices = _parse_retry_choices(getattr(args, "retry_choice", ()))
    binding = _object(args.binding, "binding")
    candidate = _object(args.candidate, "candidate manifest")
    verify_candidate_manifest(args.repository, candidate)
    if args.request_file:
        request_bytes = _read_bounded_regular_file(
            args.request_file,
            label="task request",
            limit=65_536,
        )
        try:
            request_text = request_bytes.decode("utf-8", "strict")
        except UnicodeDecodeError as exc:
            raise ValueError("task request must be UTF-8") from exc
        if not request_text.strip():
            raise ValueError("task request must not be empty")
        request_digest = "sha256:" + sha256(request_bytes).hexdigest()
    else:
        request_digest = args.request_digest
    previous = (
        _object(args.replaces_preview, "replaced route preview")
        if args.replaces_preview
        else None
    )
    roots = list(binding["active_root_loop_ids"])
    root_loop_id = args.root_loop
    if root_loop_id is None:
        if len(roots) != 1:
            raise ValueError("--root-loop is required when more than one root is active")
        root_loop_id = roots[0]
    result = create_route_preview(
        binding,
        _object(args.registry, "cycle registry"),
        _object(args.policy, "policy"),
        candidate,
        _bound_development_model(
            binding,
            args.binding,
            args.development_model,
        ),
        preview_id=args.preview_id,
        request_digest=request_digest,
        request_ref=args.request_ref,
        root_loop_id=root_loop_id,
        target_loop_ids=args.target_loop,
        branch_choices=branch_choices,
        retry_choices=retry_choices,
        created_at=args.created_at,
        replaces_preview=previous,
    )
    output = _safe_route_preview_output(
        args.repository,
        args.output,
        candidate,
        input_paths=[
            path
            for path in (
                args.binding,
                args.registry,
                args.policy,
                args.candidate,
                args.development_model,
                args.request_file,
                args.replaces_preview,
            )
            if path is not None
        ],
    )
    _save_new_output("route_preview", output, result)


def _cmd_run_new(args: argparse.Namespace) -> None:
    from .run import create_run_card

    _reject_output_collisions(
        args.output,
        (
            args.binding,
            args.registry,
            args.policy,
            args.candidate,
            args.development_model,
            args.route_preview,
            args.replaced_route_preview,
            args.planned_route,
            args.scope,
            args.budgets,
        ),
        label="run-card",
    )
    if args.replaced_route_preview and not args.route_preview:
        raise ValueError("--replaced-route-preview requires --route-preview")
    binding = _object(args.binding, "binding")
    route_preview = (
        _object(args.route_preview, "route preview")
        if args.route_preview
        else None
    )
    replaced_route_preview = (
        _object(args.replaced_route_preview, "replaced route preview")
        if args.replaced_route_preview
        else None
    )
    result = create_run_card(
        binding,
        _object(args.registry, "cycle registry"),
        _object(args.policy, "policy"),
        _object(args.candidate, "candidate manifest"),
        run_id=args.run_id,
        root_loop_id=args.root_loop,
        candidate_author_principal_ids=args.candidate_author,
        planned_route=(
            _array(args.planned_route, "planned route")
            if args.planned_route
            else None
        ),
        scope=_object(args.scope, "run scope") if args.scope else None,
        budgets=_object(args.budgets, "run budgets") if args.budgets else None,
        target_loop_ids=args.target_loop,
        portfolio=args.portfolio,
        development_model=_bound_development_model(
            binding,
            args.binding,
            args.development_model,
        ),
        route_preview=route_preview,
        replaced_route_preview=replaced_route_preview,
    )
    _save_new_output("run_card", args.output, result)


def _cmd_run_migrate(args: argparse.Namespace) -> None:
    from .run import migrate_run_card_v0_1

    _reject_output_collisions(
        args.output,
        (args.card,),
        label="migrated run-card",
    )
    result = migrate_run_card_v0_1(_object(args.card, "legacy run card"))
    _save_new_output("run_card", args.output, result)


def _cmd_run_authorize(args: argparse.Namespace) -> None:
    from .run import authorize_run

    _reject_output_collisions(
        args.output,
        (
            args.binding,
            args.registry,
            args.policy,
            args.candidate,
            args.development_model,
            args.route_preview,
            args.replaced_route_preview,
        ),
        label="run-card",
    )
    binding = _object(args.binding, "binding")
    route_preview, replaced_route_preview = _route_preview_pair(args)
    card = authorize_run(
        _object(args.card, "run card"),
        binding,
        _object(args.registry, "cycle registry"),
        _object(args.policy, "policy"),
        _object(args.candidate, "candidate manifest"),
        actor=_actor(args),
        authority_ref=args.authority_ref,
        authorized_at=args.authorized_at,
        repository=args.repository,
        development_model=(
            _bound_development_model(
                binding,
                args.binding,
                args.development_model,
            )
            if route_preview is not None
            else None
        ),
        route_preview=route_preview,
        replaced_route_preview=replaced_route_preview,
    )
    _save_run_card_output(args.card, args.output, card)


def _cmd_run_attempt(args: argparse.Namespace) -> None:
    from .run import record_attempt

    attempt = _object(args.attempt, "attempt")
    binding_path = getattr(args, "binding", None)
    registry_path = getattr(args, "registry", None)
    development_model_path = getattr(args, "development_model", None)
    _reject_output_collisions(
        args.output,
        (
            args.policy,
            args.candidate,
            args.attempt,
            binding_path,
            registry_path,
            development_model_path,
            getattr(args, "route_preview", None),
            getattr(args, "replaced_route_preview", None),
        ),
        label="run-card",
    )
    binding = _object(binding_path, "binding") if binding_path else None
    registry = _object(registry_path, "cycle registry") if registry_path else None
    route_preview, replaced_route_preview = _route_preview_pair(args)
    if route_preview is not None and (binding is None or registry is None):
        raise ValueError(
            "preview-backed attempt recording requires --binding and --registry"
        )
    card = record_attempt(
        _object(args.card, "run card"),
        _object(args.policy, "policy"),
        _object(args.candidate, "candidate manifest"),
        node_id=args.node,
        attempt_id=str(attempt["id"]),
        started_at=str(attempt["started_at"]),
        finished_at=str(attempt["finished_at"]),
        effective_principal_id=str(attempt["effective_principal_id"]),
        effective_agent=str(attempt["effective_agent"]),
        effective_model=str(attempt["effective_model"]),
        effective_model_provider=(
            str(attempt["effective_model_provider"])
            if "effective_model_provider" in attempt
            else None
        ),
        effective_reasoning=str(attempt["effective_reasoning"]),
        effective_skill=str(attempt["effective_skill"]),
        effective_skills=(
            list(attempt["effective_skills"])
            if "effective_skills" in attempt
            else None
        ),
        effective_mcp_servers=(
            list(attempt["effective_mcp_servers"])
            if "effective_mcp_servers" in attempt
            else None
        ),
        effective_resources=(
            list(attempt["effective_resources"])
            if "effective_resources" in attempt
            else None
        ),
        effective_tool_capabilities=(
            list(attempt["effective_tool_capabilities"])
            if "effective_tool_capabilities" in attempt
            else None
        ),
        effective_subagent_identities=(
            list(attempt["effective_subagent_identities"])
            if "effective_subagent_identities" in attempt
            else None
        ),
        effective_subagents=list(attempt.get("effective_subagents", [])),
        effective_tools=list(attempt.get("effective_tools", [])),
        data_egress=dict(attempt["data_egress"]),
        network=str(attempt["network"]),
        external_mutations=list(attempt["external_mutations"]),
        input_tokens=int(attempt["input_tokens"]),
        output_tokens=int(attempt["output_tokens"]),
        reasoning_tokens=int(attempt["reasoning_tokens"]),
        cached_tokens=int(attempt["cached_tokens"]),
        token_accounting=str(attempt["token_accounting"]),
        cost_units=float(attempt["cost_units"]),
        result=str(attempt["result"]),
        repository=args.repository,
        binding=binding,
        registry=registry,
        development_model=(
            _bound_development_model(
                binding,
                binding_path,
                development_model_path,
            )
            if route_preview is not None and binding is not None
            else None
        ),
        route_preview=route_preview,
        replaced_route_preview=replaced_route_preview,
    )
    _save_run_card_output(args.card, args.output, card)


def _cmd_run_evidence(args: argparse.Namespace) -> None:
    from .run import record_evidence

    _reject_output_collisions(
        args.output,
        (
            args.registry,
            args.policy,
            args.candidate,
            args.evidence,
            args.binding,
            args.development_model,
            args.route_preview,
            args.replaced_route_preview,
        ),
        label="run-card",
    )
    binding = _object(args.binding, "binding") if args.binding else None
    route_preview, replaced_route_preview = _route_preview_pair(args)
    if route_preview is not None and binding is None:
        raise ValueError("preview-backed evidence recording requires --binding")
    card = record_evidence(
        _object(args.card, "run card"),
        _object(args.evidence, "evidence"),
        _object(args.registry, "cycle registry"),
        _object(args.policy, "policy"),
        _object(args.candidate, "candidate manifest"),
        payload_root=args.payload_root,
        repository=args.repository,
        binding=binding,
        development_model=(
            _bound_development_model(
                binding,
                args.binding,
                args.development_model,
            )
            if route_preview is not None and binding is not None
            else None
        ),
        route_preview=route_preview,
        replaced_route_preview=replaced_route_preview,
    )
    _save_run_card_output(args.card, args.output, card)


def _cmd_run_guard(args: argparse.Namespace) -> None:
    from .run import guard

    binding = _object(args.binding, "binding") if args.binding else None
    registry = _object(args.registry, "cycle registry") if args.registry else None
    candidate = _object(args.candidate, "candidate manifest") if args.candidate else None
    policy = _object(args.policy, "policy") if args.policy else None
    route_preview, replaced_route_preview = _route_preview_pair(args)
    if route_preview is not None and any(
        value is None for value in (binding, registry, policy, candidate)
    ):
        raise ValueError(
            "preview-backed guard requires --binding, --registry, --policy, "
            "and --candidate"
        )
    guard(
        _object(args.card, "run card"),
        args.node,
        read_paths=args.read_path,
        write_paths=args.write_path,
        principal_id=args.principal_id,
        policy=policy,
        binding=binding,
        registry=registry,
        candidate_manifest=candidate,
        repository=args.repository,
        development_model=(
            _bound_development_model(
                binding,
                args.binding,
                args.development_model,
            )
            if route_preview is not None and binding is not None
            else None
        ),
        route_preview=route_preview,
        replaced_route_preview=replaced_route_preview,
    )
    _emit({"node": args.node, "ok": True})


def _cmd_run_complete(args: argparse.Namespace) -> None:
    from .run import complete_node, complete_run

    _reject_output_collisions(
        args.output,
        (
            args.binding,
            args.registry,
            args.policy,
            args.candidate,
            args.development_model,
            args.route_preview,
            args.replaced_route_preview,
            *args.evidence_document,
        ),
        label="run-card",
    )
    card_input = _object(args.card, "run card")
    registry = _object(args.registry, "cycle registry")
    policy = _object(args.policy, "policy")
    candidate = _object(args.candidate, "candidate manifest")
    binding = _object(args.binding, "binding") if args.binding else None
    route_preview, replaced_route_preview = _route_preview_pair(args)
    if route_preview is not None and binding is None:
        raise ValueError("preview-backed completion requires --binding")
    development_model = (
        _bound_development_model(
            binding,
            args.binding,
            args.development_model,
        )
        if route_preview is not None and binding is not None
        else None
    )
    if args.node:
        if not args.actor_id or not args.actor_kind:
            raise ValueError(
                "node completion requires --actor-id and --actor-kind"
            )
        evidence_documents = {
            document["id"]: document
            for document in (
                _object(path, "evidence document")
                for path in args.evidence_document
            )
        }
        card = complete_node(
            card_input,
            args.node,
            registry,
            policy,
            candidate,
            evidence_documents,
            accepted_by=_actor(args),
            payload_root=args.payload_root,
            outcome=args.outcome,
            repository=args.repository,
            binding=binding,
            development_model=development_model,
            route_preview=route_preview,
            replaced_route_preview=replaced_route_preview,
        )
    else:
        if binding is None:
            raise ValueError("run completion requires --binding")
        card = complete_run(
            card_input,
            binding,
            registry,
            policy,
            candidate,
            completed_at=args.completed_at,
            repository=args.repository,
            development_model=development_model,
            route_preview=route_preview,
            replaced_route_preview=replaced_route_preview,
        )
    _save_run_card_output(args.card, args.output, card)


def _cmd_atlas(args: argparse.Namespace) -> None:
    try:
        from .atlas import generate_atlas
    except ImportError as exc:
        raise RuntimeError(
            "Atlas support is unavailable in this installation"
        ) from exc

    _reject_output_collisions(
        args.output,
        (
            args.binding,
            args.registry,
            args.policy,
            args.run_card,
            args.route_preview,
            args.replaced_route_preview,
            args.candidate,
            args.development_model,
        ),
        label="Atlas",
    )
    kwargs: dict[str, Any] = {
        "binding": _object(args.binding, "binding"),
        "registry": _object(args.registry, "cycle registry"),
        "policy": _object(args.policy, "policy"),
        "output": args.output,
        "check": args.check,
        "locale": args.locale,
    }
    if args.run_card:
        kwargs["run_card"] = _object(args.run_card, "run card")
    if args.route_preview:
        if not args.candidate:
            raise ValueError("--route-preview requires --candidate")
        binding = kwargs["binding"]
        kwargs["route_preview"] = _object(args.route_preview, "route preview")
        kwargs["candidate_manifest"] = _object(args.candidate, "candidate manifest")
        kwargs["development_model"] = _bound_development_model(
            binding,
            args.binding,
            args.development_model,
        )
        if args.replaced_route_preview:
            kwargs["replaced_route_preview"] = _object(
                args.replaced_route_preview,
                "replaced route preview",
            )
    elif args.replaced_route_preview:
        raise ValueError("--replaced-route-preview requires --route-preview")
    generate_atlas(**kwargs)
    _emit(
        {
            "check": args.check,
            "ok": True,
            "outputs": {"atlas": args.output},
        }
    )


def _cmd_evolve(args: argparse.Namespace) -> None:
    from .evolution import propose_evolution

    binding = _object(args.base_binding, "base binding")
    policy = _object(args.policy, "policy")
    proposal = propose_evolution(
        str(binding["binding_digest"]),
        [_object(path, "evolution signal") for path in args.signal],
        _array(args.operations, "evolution operations"),
        proposed_by={"id": args.proposed_by, "kind": args.proposer_kind},
        decision_authority_ref=args.decision_authority_ref,
        expected_effect=args.expected_effect,
        risk=_object(args.risk, "evolution risk"),
        proposal_id=args.proposal_id,
        generated_at=args.generated_at,
        policy=policy,
        base_targets=(
            _object(args.base_targets, "evolution base targets")
            if args.base_targets
            else None
        ),
    )
    if proposal.get("activation_allowed") is not False:
        raise ValueError("evolution proposals must not self-authorize activation")
    _save_outputs({"evolution_proposal": (args.output, proposal)})


def _add_actor(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--actor-id", required=True)
    parser.add_argument("--actor-kind", required=True)
    parser.add_argument("--actor-display-name")
    parser.add_argument("--authority-ref", required=True)


def _set_handler(parser: argparse.ArgumentParser, handler: Callable[..., None]) -> None:
    parser.set_defaults(_handler=handler)


def build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(
        prog="concordloom",
        description=(
            "Discover, negotiate, compile, execute, visualize, and evolve "
            "evidence-governed systems of development loops."
        ),
    )
    parser.add_argument(
        "--version", action="version", version=f"concordloom {__version__}"
    )
    commands = parser.add_subparsers(dest="command", required=True)

    inspect = commands.add_parser(
        "inspect", help="inspect a local Git repository without executing it"
    )
    inspect.add_argument("repository")
    inspect.add_argument("--output", required=True)
    inspect.add_argument("--generated-at")
    inspect.add_argument("--include-untracked", action="store_true")
    inspect.add_argument("--max-files", type=int, default=5_000)
    inspect.add_argument("--max-file-bytes", type=int, default=1_048_576)
    inspect.add_argument("--max-history-commits", type=int, default=500)
    inspect.add_argument("--max-paths-per-commit", type=int, default=200)
    inspect.add_argument("--max-cochange-pairs", type=int, default=20_000)
    inspect.add_argument("--max-subprocess-bytes", type=int, default=16_777_216)
    inspect.add_argument("--subprocess-timeout-seconds", type=int, default=30)
    _set_handler(inspect, _cmd_inspect)

    questions = commands.add_parser(
        "questions", help="rank unresolved project-intent hypotheses"
    )
    questions.add_argument("--graph", required=True)
    questions.add_argument("--output", required=True)
    _set_handler(questions, _cmd_questions)

    decide = commands.add_parser(
        "decide", help="record one explicit answer and graph delta"
    )
    decide.add_argument("--questions", required=True)
    decide.add_argument("--question", required=True)
    decide.add_argument(
        "--verdict",
        required=True,
        choices=("confirmed", "rejected", "corrected"),
    )
    _add_actor(decide)
    decide.add_argument("--rationale", required=True)
    decide.add_argument("--decided-at", required=True)
    decide.add_argument("--decision-id")
    decide.add_argument("--correction")
    decide.add_argument("--graph-delta")
    decide.add_argument("--output", required=True)
    _set_handler(decide, _cmd_decide)

    accept = commands.add_parser(
        "accept", help="accept project intent or a proposed loop design"
    )
    acceptance_source = accept.add_mutually_exclusive_group(required=True)
    acceptance_source.add_argument("--graph")
    acceptance_source.add_argument("--proposal")
    accept.add_argument("--policy", required=True)
    accept.add_argument("--decision", action="append")
    accept.add_argument("--decisions")
    accept.add_argument("--accepted-graph")
    accept.add_argument("--decision-id")
    accept.add_argument("--rationale")
    _add_actor(accept)
    accept.add_argument("--accepted-at", required=True)
    accept.add_argument("--log-id")
    accept.add_argument("--decision-log-output")
    accept.add_argument("--output", required=True)
    _set_handler(accept, _cmd_accept)

    propose = commands.add_parser(
        "propose", help="propose a reviewable loop design from accepted intent"
    )
    propose.add_argument("--graph", required=True)
    propose.add_argument("--decisions", required=True)
    propose.add_argument("--policy", required=True)
    propose.add_argument("--design-id")
    propose.add_argument("--output", required=True)
    _set_handler(propose, _cmd_propose)

    compile_command = commands.add_parser(
        "compile", help="compile only an operator-accepted loop design"
    )
    compile_command.add_argument("--graph", required=True)
    compile_command.add_argument("--decisions", required=True)
    compile_command.add_argument("--design-proposal", required=True)
    compile_command.add_argument("--design", required=True)
    compile_command.add_argument("--policy", required=True)
    compile_command.add_argument("--registry-id")
    compile_command.add_argument("--proposal-id")
    compile_command.add_argument("--created-at", required=True)
    compile_command.add_argument("--predecessor-binding-digest")
    compile_command.add_argument("--artifact-root", default=".")
    compile_command.add_argument("--registry-output", required=True)
    compile_command.add_argument("--proposal-output", required=True)
    _set_handler(compile_command, _cmd_compile)

    activate = commands.add_parser(
        "activate",
        help="activate one exact binding proposal through a separate decision",
    )
    activate.add_argument("--proposal", required=True)
    activate.add_argument("--graph", required=True)
    activate.add_argument("--decisions", required=True)
    activate.add_argument("--design-proposal", required=True)
    activate.add_argument("--design", required=True)
    activate.add_argument("--registry", required=True)
    activate.add_argument("--policy", required=True)
    activate.add_argument("--binding-id", required=True)
    activate.add_argument("--decision-id", required=True)
    _add_actor(activate)
    activate.add_argument("--accepted-at", required=True)
    activate.add_argument("--rationale", required=True)
    activate.add_argument("--output", required=True)
    _set_handler(activate, _cmd_activate)

    validate = commands.add_parser(
        "validate", help="validate one public artifact and its invariants"
    )
    validate.add_argument("--input", required=True)
    validate.add_argument("--schema")
    validate.add_argument("--graph")
    validate.add_argument("--questions")
    validate.add_argument("--observed-graph")
    validate.add_argument("--decisions")
    validate.add_argument("--policy")
    validate.add_argument("--proposal")
    validate.add_argument("--design")
    validate.add_argument("--registry")
    validate.add_argument("--binding-proposal")
    validate.add_argument("--binding")
    validate.add_argument("--candidate")
    validate.add_argument("--card")
    validate.add_argument("--development-model")
    validate.add_argument("--route-preview")
    validate.add_argument("--replaced-route-preview")
    validate.add_argument("--repository")
    validate.add_argument("--payload-root")
    validate.add_argument("--artifact-root", default=".")
    validate.add_argument("--base-binding")
    validate.add_argument("--base-targets")
    _set_handler(validate, _cmd_validate)

    candidate = commands.add_parser(
        "candidate", help="create a content-addressed candidate manifest"
    )
    candidate.add_argument("repository")
    candidate.add_argument(
        "--include-untracked", action="append", default=[], metavar="PATH"
    )
    candidate.add_argument("--manifest-id")
    candidate.add_argument("--generated-at", required=True)
    candidate.add_argument("--output", required=True)
    _set_handler(candidate, _cmd_candidate)

    catalog = commands.add_parser(
        "catalog", help="append an activated binding to an immutable chain"
    )
    catalog.add_argument("--catalog")
    catalog.add_argument("--binding", required=True)
    catalog.add_argument("--artifact-root", default=".")
    catalog.add_argument("--catalog-id")
    catalog.add_argument("--output", required=True)
    _set_handler(catalog, _cmd_catalog)

    route = commands.add_parser(
        "route", help="preview an exact task route without running it"
    )
    route_commands = route.add_subparsers(dest="route_command", required=True)
    route_preview = route_commands.add_parser(
        "preview", help="create a pinned, non-authorizing route proposal"
    )
    route_preview.add_argument("--binding", required=True)
    route_preview.add_argument("--registry", required=True)
    route_preview.add_argument("--policy", required=True)
    route_preview.add_argument("--candidate", required=True)
    route_preview.add_argument("--repository", required=True)
    route_preview.add_argument("--development-model")
    route_preview.add_argument("--preview-id", required=True)
    route_preview.add_argument("--request-ref", default="task-request")
    request_source = route_preview.add_mutually_exclusive_group(required=True)
    request_source.add_argument("--request-file")
    request_source.add_argument("--request-digest")
    route_preview.add_argument("--root-loop")
    route_preview.add_argument("--target-loop", action="append", required=True)
    route_preview.add_argument(
        "--branch-choice",
        action="append",
        default=[],
        metavar="LOOP:STATE=TRANSITION",
        help="select one successful outgoing transition at a branch state",
    )
    route_preview.add_argument(
        "--retry-choice",
        action="append",
        default=[],
        metavar="LOOP:TRANSITION=COUNT",
        help="select a bounded feedback traversal count",
    )
    route_preview.add_argument("--created-at", required=True)
    route_preview.add_argument("--replaces-preview")
    route_preview.add_argument("--output", required=True)
    _set_handler(route_preview, _cmd_route_preview)

    run = commands.add_parser("run", help="govern a bound run-card lifecycle")
    run_commands = run.add_subparsers(dest="run_command", required=True)

    run_migrate = run_commands.add_parser(
        "migrate",
        help="convert one pristine run-card 0.1 into an unauthorised 0.2 draft",
    )
    run_migrate.add_argument("--card", required=True)
    run_migrate.add_argument("--output", required=True)
    _set_handler(run_migrate, _cmd_run_migrate)

    run_new = run_commands.add_parser("new", help="create a pinned run card")
    run_new.add_argument("--binding", required=True)
    run_new.add_argument("--registry", required=True)
    run_new.add_argument("--policy", required=True)
    run_new.add_argument("--candidate", required=True)
    run_new.add_argument("--run-id", required=True)
    run_new.add_argument("--root-loop", required=True)
    run_new.add_argument("--candidate-author", action="append", required=True)
    route_selection = run_new.add_mutually_exclusive_group()
    route_selection.add_argument("--planned-route")
    route_selection.add_argument("--target-loop", action="append", default=[])
    route_selection.add_argument("--portfolio", action="store_true")
    route_selection.add_argument("--route-preview")
    run_new.add_argument("--replaced-route-preview")
    run_new.add_argument("--development-model")
    run_new.add_argument("--scope")
    run_new.add_argument("--budgets")
    run_new.add_argument("--output", required=True)
    _set_handler(run_new, _cmd_run_new)

    run_authorize = run_commands.add_parser(
        "authorize", help="authorize one ready node"
    )
    run_authorize.add_argument("--card", required=True)
    run_authorize.add_argument("--binding", required=True)
    run_authorize.add_argument("--registry", required=True)
    run_authorize.add_argument("--policy", required=True)
    run_authorize.add_argument("--candidate", required=True)
    run_authorize.add_argument("--development-model")
    run_authorize.add_argument("--route-preview")
    run_authorize.add_argument("--replaced-route-preview")
    _add_actor(run_authorize)
    run_authorize.add_argument("--authorized-at", required=True)
    run_authorize.add_argument("--repository", required=True)
    run_authorize.add_argument("--output", required=True)
    _set_handler(run_authorize, _cmd_run_authorize)

    run_attempt = run_commands.add_parser(
        "attempt", help="record one effective execution route"
    )
    run_attempt.add_argument("--card", required=True)
    run_attempt.add_argument("--policy", required=True)
    run_attempt.add_argument("--candidate", required=True)
    run_attempt.add_argument("--binding")
    run_attempt.add_argument("--registry")
    run_attempt.add_argument("--development-model")
    run_attempt.add_argument("--route-preview")
    run_attempt.add_argument("--replaced-route-preview")
    run_attempt.add_argument("--node", required=True)
    run_attempt.add_argument("--attempt", required=True)
    run_attempt.add_argument("--repository", required=True)
    run_attempt.add_argument("--output", required=True)
    _set_handler(run_attempt, _cmd_run_attempt)

    run_evidence = run_commands.add_parser(
        "evidence", help="record candidate-bound structured evidence"
    )
    run_evidence.add_argument("--card", required=True)
    run_evidence.add_argument("--registry", required=True)
    run_evidence.add_argument("--policy", required=True)
    run_evidence.add_argument("--candidate", required=True)
    run_evidence.add_argument("--binding")
    run_evidence.add_argument("--development-model")
    run_evidence.add_argument("--route-preview")
    run_evidence.add_argument("--replaced-route-preview")
    run_evidence.add_argument("--evidence", required=True)
    run_evidence.add_argument("--payload-root", required=True)
    run_evidence.add_argument("--repository", required=True)
    run_evidence.add_argument("--output", required=True)
    _set_handler(run_evidence, _cmd_run_evidence)

    run_guard = run_commands.add_parser(
        "guard", help="check requested paths against one authorized node"
    )
    run_guard.add_argument("--card", required=True)
    run_guard.add_argument("--node", required=True)
    run_guard.add_argument("--read-path", action="append", default=[])
    run_guard.add_argument("--write-path", action="append", default=[])
    run_guard.add_argument("--principal-id")
    run_guard.add_argument("--policy")
    run_guard.add_argument("--binding")
    run_guard.add_argument("--registry")
    run_guard.add_argument("--candidate")
    run_guard.add_argument("--repository")
    run_guard.add_argument("--development-model")
    run_guard.add_argument("--route-preview")
    run_guard.add_argument("--replaced-route-preview")
    _set_handler(run_guard, _cmd_run_guard)

    run_complete = run_commands.add_parser(
        "complete", help="complete a run only after all required gates"
    )
    run_complete.add_argument("--card", required=True)
    run_complete.add_argument("--binding")
    run_complete.add_argument("--development-model")
    run_complete.add_argument("--route-preview")
    run_complete.add_argument("--replaced-route-preview")
    run_complete.add_argument("--registry", required=True)
    run_complete.add_argument("--policy", required=True)
    run_complete.add_argument("--candidate", required=True)
    run_complete.add_argument("--node")
    run_complete.add_argument("--actor-id")
    run_complete.add_argument("--actor-kind")
    run_complete.add_argument("--actor-display-name")
    run_complete.add_argument("--evidence-document", action="append", default=[])
    run_complete.add_argument(
        "--outcome", choices=("passed", "failed", "blocked"), default="passed"
    )
    run_complete.add_argument("--completed-at", required=True)
    run_complete.add_argument("--payload-root", required=True)
    run_complete.add_argument("--repository", required=True)
    run_complete.add_argument("--output", required=True)
    _set_handler(run_complete, _cmd_run_complete)

    atlas = commands.add_parser(
        "atlas", help="generate or check a self-contained offline Atlas"
    )
    atlas.add_argument("--binding", required=True)
    atlas.add_argument("--registry", required=True)
    atlas.add_argument("--policy", required=True)
    atlas.add_argument("--run-card")
    atlas.add_argument("--route-preview")
    atlas.add_argument("--replaced-route-preview")
    atlas.add_argument("--candidate")
    atlas.add_argument("--development-model")
    atlas.add_argument("--output", required=True)
    atlas.add_argument("--locale", choices=("en", "ru"), default="en")
    atlas.add_argument("--check", action="store_true")
    _set_handler(atlas, _cmd_atlas)

    evolve = commands.add_parser(
        "evolve", help="propose, but never activate, a successor binding"
    )
    evolve.add_argument("--base-binding", required=True)
    evolve.add_argument("--policy", required=True)
    evolve.add_argument("--signal", action="append", required=True)
    evolve.add_argument("--proposed-by", required=True)
    evolve.add_argument("--proposer-kind", required=True)
    evolve.add_argument("--decision-authority-ref", required=True)
    evolve.add_argument("--operations", required=True)
    evolve.add_argument("--expected-effect", required=True)
    evolve.add_argument("--risk", required=True)
    evolve.add_argument("--base-targets")
    evolve.add_argument("--proposal-id")
    evolve.add_argument("--generated-at", required=True)
    evolve.add_argument("--output", required=True)
    _set_handler(evolve, _cmd_evolve)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args._handler(args)
    except (
        ImportError,
        KeyError,
        OSError,
        TypeError,
        UnicodeError,
        ValueError,
        RuntimeError,
    ) as exc:
        _emit_error("command_failed", str(exc))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
