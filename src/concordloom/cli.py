"""Stable, local-only command line interface for Concord Loom v0.1.

The CLI is deliberately a thin adapter over the portable core.  Artifact
commands always name their input and output paths, never contact a remote
service, and report failures as one compact JSON object on stderr.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
import json
from pathlib import Path
import sys
from typing import Any

from . import __version__
from .canonical import digest, load, save


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

        validate_run_card(
            artifact,
            _object(args.binding),
            _object(args.registry),
            _object(args.policy),
            _object(args.candidate),
            repository=args.repository,
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

        validate_evidence(
            artifact,
            _object(args.card),
            _object(args.registry),
            _object(args.policy),
            _object(args.candidate),
            repository=args.repository,
            payload_root=args.payload_root,
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


def _cmd_run_new(args: argparse.Namespace) -> None:
    from .run import create_run_card

    binding = _object(args.binding, "binding")
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
    )
    _save_outputs({"run_card": (args.output, result)})


def _cmd_run_authorize(args: argparse.Namespace) -> None:
    from .run import authorize_run

    card = authorize_run(
        _object(args.card, "run card"),
        _object(args.binding, "binding"),
        _object(args.registry, "cycle registry"),
        _object(args.policy, "policy"),
        _object(args.candidate, "candidate manifest"),
        actor=_actor(args),
        authority_ref=args.authority_ref,
        authorized_at=args.authorized_at,
        repository=args.repository,
    )
    _save_outputs({"run_card": (args.output, card)})


def _cmd_run_attempt(args: argparse.Namespace) -> None:
    from .run import record_attempt

    attempt = _object(args.attempt, "attempt")
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
    )
    _save_outputs({"run_card": (args.output, card)})


def _cmd_run_evidence(args: argparse.Namespace) -> None:
    from .run import record_evidence

    card = record_evidence(
        _object(args.card, "run card"),
        _object(args.evidence, "evidence"),
        _object(args.registry, "cycle registry"),
        _object(args.policy, "policy"),
        _object(args.candidate, "candidate manifest"),
        payload_root=args.payload_root,
        repository=args.repository,
    )
    _save_outputs({"run_card": (args.output, card)})


def _cmd_run_guard(args: argparse.Namespace) -> None:
    from .run import guard

    guard(
        _object(args.card, "run card"),
        args.node,
        read_paths=args.read_path,
        write_paths=args.write_path,
        principal_id=args.principal_id,
        policy=(
            _object(args.policy, "policy")
            if args.policy
            else None
        ),
    )
    _emit({"node": args.node, "ok": True})


def _cmd_run_complete(args: argparse.Namespace) -> None:
    from .run import complete_node, complete_run

    card_input = _object(args.card, "run card")
    registry = _object(args.registry, "cycle registry")
    policy = _object(args.policy, "policy")
    candidate = _object(args.candidate, "candidate manifest")
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
        )
    else:
        if not args.binding:
            raise ValueError("run completion requires --binding")
        card = complete_run(
            card_input,
            _object(args.binding, "binding"),
            registry,
            policy,
            candidate,
            completed_at=args.completed_at,
            repository=args.repository,
        )
    _save_outputs({"run_card": (args.output, card)})


def _cmd_atlas(args: argparse.Namespace) -> None:
    try:
        from .atlas import generate_atlas
    except ImportError as exc:
        raise RuntimeError(
            "Atlas support is unavailable in this installation"
        ) from exc

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

    run = commands.add_parser("run", help="govern a bound run-card lifecycle")
    run_commands = run.add_subparsers(dest="run_command", required=True)

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
    _set_handler(run_guard, _cmd_run_guard)

    run_complete = run_commands.add_parser(
        "complete", help="complete a run only after all required gates"
    )
    run_complete.add_argument("--card", required=True)
    run_complete.add_argument("--binding")
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
