#!/usr/bin/env python3
"""Propose, then separately activate, self-binding v7 metadata authority."""

from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path
import re

from authorize_source_publication import (
    EXTERNAL_MUTATIONS,
    NODES,
    OPERATOR,
    containment,
    development_model,
    loop_specs,
)
from concordloom.canonical import canonical_bytes, digest, load, save
from concordloom.catalog import append_binding
from concordloom.compiler import (
    accept_loop_design,
    activate_binding,
    compile_registry,
    create_binding_proposal,
    propose_loop_design,
)
from concordloom.evolution import propose_evolution
from concordloom.loops import (
    principal_capabilities,
    validate_policy,
    validate_registry,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "framework" / "concordloom"
PREDECESSOR_DIR = SOURCE / "v6"
GRAPH_DIR = SOURCE / "v3"
TARGET = SOURCE / "v7"
STAMP = "2026-07-27T19:00:00Z"
METADATA_PATHS = ["CITATION.cff", "pyproject.toml"]
TRACKED_SOURCE_ROOTS = [
    ".agents",
    ".concord/research",
    ".github",
    ".gitignore",
    "AGENTS.md",
    "CITATION.cff",
    "LICENSE",
    "NOTICE",
    "README.md",
    "README.ru.md",
    "concord",
    "docs",
    "examples",
    "framework",
    "plugins",
    "pyproject.toml",
    "schemas",
    "site",
    "src",
    "tests",
    "tools",
]
ALLOWED_EXTERNAL_MUTATIONS = sorted(
    set(
        EXTERNAL_MUTATIONS
        + [
            "github-release-assets",
            "github-repository-security-settings",
            "github-version-tag",
        ]
    )
)
GOVERNANCE_READS = [
    "AGENTS.md",
    "framework/concordloom/catalog.json",
    "schemas",
]
PUBLICATION_EFFECTS = {
    "distribute-package": [
        "github-release-assets",
        "github-version-tag",
    ],
    "publish-site": ["github-pages"],
    "maintain-repository-presence": [
        "github-repository-homepage",
        "github-repository-security-settings",
        "github-repository-social-preview",
    ],
    "publish-source-change": [
        "github-pull-request",
        "github-repository-source",
    ],
    "accept-source-change": ["github-pull-request-merge"],
    "maintain-organization-presence": ["github-organization-profile"],
}
PUBLICATION_READS = {
    "distribute-package": [
        ".concord/runs",
        "CITATION.cff",
        "LICENSE",
        "NOTICE",
        "README.md",
        "framework/concordloom/catalog.json",
        "pyproject.toml",
        "src",
    ],
    "publish-site": ["site"],
    "maintain-repository-presence": [
        "docs/assets/concordloom-mark.png",
        "docs/assets/concordloom-social-preview.png",
    ],
    "publish-source-change": TRACKED_SOURCE_ROOTS,
    "accept-source-change": [
        ".concord/runs",
        "framework/concordloom/catalog.json",
    ],
    "maintain-organization-presence": [
        "docs/assets/concordloom-mark.png",
        "site",
    ],
}

LEAF_WRITE_PATHS = {
    "discover-product-needs": [".concord/research", "docs/research"],
    "maintain-product-boundary": [
        "LICENSE", "NOTICE",
        "README.md", "README.ru.md", "docs/CONCEPTS.md",
        "docs/ru/CONCEPTS.md", "docs/SPEC_V0.1.md", "docs/ru/SPEC_V0.1.md",
    ],
    "decide-product": ["docs/DECISIONS.md", "docs/ru/DECISIONS.md"],
    "prioritize-roadmap": ["docs/DECISIONS.md", "docs/ru/DECISIONS.md"],
    "observe-landscape": ["docs/research", "docs/ru/research"],
    "formalize-theory": [
        "docs/ARTICLE.md", "docs/ru/ARTICLE.md",
        "docs/CONCEPTS.md", "docs/ru/CONCEPTS.md",
    ],
    "test-applicability": ["docs/research", "docs/ru/research", "examples", "tests"],
    "maintain-article": ["docs/ARTICLE.md", "docs/ru/ARTICLE.md"],
    "define-artifact-semantics": [
        "schemas", "src/concordloom/canonical.py",
        "docs/CONCEPTS.md", "docs/ru/CONCEPTS.md", "tests",
    ],
    "design-graphs-policies": [
        "schemas", "src/concordloom/compiler.py", "src/concordloom/loops.py",
        "docs/ARCHITECTURE.md", "docs/ru/ARCHITECTURE.md", "tests",
    ],
    "evolve-schemas": ["schemas", "src", "tests"],
    "maintain-compiler-core": [
        "src/concordloom/canonical.py", "src/concordloom/catalog.py",
        "src/concordloom/compiler.py", "src/concordloom/evolution.py",
        "src/concordloom/loops.py", "tests",
    ],
    "operate-run-lifecycle": [
        "schemas", "src/concordloom/run.py", "tests",
    ],
    "maintain-cli": ["src/concordloom/cli.py", "tests"],
    "maintain-automation": [
        ".github/dependabot.yml", ".github/workflows", "tools", "plugins", "tests",
    ],
    "model-threats": [
        "docs/TRUST_MODEL.md", "docs/ru/TRUST_MODEL.md",
    ],
    "validate-invariants": ["tests", "tools/check.sh"],
    "maintain-self-binding": [
        ".agents", ".concord/research", ".gitignore", "AGENTS.md", "concord",
        "framework/concordloom", "tools", "tests",
    ],
    "maintain-evidence-adapters": [
        "src/concordloom/inspection.py", "src/concordloom/interview.py", "tests",
    ],
    "maintain-execution-adapters": [
        "src/concordloom/run.py", "plugins", "tests",
    ],
    "maintain-reference-bindings": [
        "examples", "framework/generic-sdlc", "plugins", "tests",
    ],
    "design-information-architecture": ["docs", "site"],
    "author-documentation": ["README.md", "README.ru.md", "docs"],
    "localize-content": [
        "README.ru.md", "docs/ru", "site", "tools/build_site.py",
        "tools/check_docs.py", "tools/check_language.py", "tools/check_site.py",
        "tests",
    ],
    "design-site-experience": ["docs/assets", "site", "tools/build_site.py", "tools/check_site.py", "tests"],
    "project-atlas": [
        "docs/ATLAS.html", "docs/ATLAS.md", "docs/ru/ATLAS.html",
        "docs/ru/ATLAS.md", "site/data", "src/concordloom/atlas.py",
        "src/concordloom/cli.py", "tools/build_site.py", "tests",
    ],
    "plan-release": [
        "CITATION.cff", "pyproject.toml", "README.md", "README.ru.md",
        "docs/RELEASE.md", "docs/ru/RELEASE.md",
    ],
    "distribute-package": [],
    "observe-onboarding": [
        "README.md", "README.ru.md", "docs/QUICKSTART.md",
        "docs/ru/QUICKSTART.md", "docs/research", "docs/ru/research",
    ],
    "validate-use-cases": ["docs/research", "docs/ru/research", "examples", "tests"],
    "collect-friction": [".concord/research", "docs/research", "docs/ru/research"],
    "synthesize-feedback": ["docs/research", "docs/ru/research"],
    "collect-evolution-signals": [".concord/research", "docs/research", "docs/ru/research"],
    "propose-successor": ["framework/concordloom", "tools", "tests"],
    "observe-migration": ["docs/research", "docs/ru/research", "site/data", "tests"],
}

LEAF_READ_PATHS = {
    "assure-compatibility": ["framework", "schemas", "src", "tests"],
    "review-candidate": TRACKED_SOURCE_ROOTS,
    "assure-release": [
        ".concord/runs",
        "framework/concordloom/catalog.json",
        "site",
    ],
    "review-comprehension": [
        "README.md",
        "README.ru.md",
        "docs",
        "site",
    ],
    "review-successor": [
        "framework/concordloom",
        "schemas",
        "tests",
        "tools",
    ],
    "activate-successor": [
        ".concord/runs",
        "framework/concordloom",
    ],
    "verify-live-release": ["site"],
    **PUBLICATION_READS,
}


OPERATOR_CAPABILITIES = {
    "steward-concordloom": "authorize-run",
    "product-direction": "accept-intent",
    "decide-product": "accept-intent",
    "system-evolution": "decide-evolution",
    "activate-successor": "activate-binding",
}
RECEIPT_SCHEMA = "concordloom://activation-receipt/0.1"
RECEIPT_KINDS = {
    "review": {
        "kind": "concordloom.review-recommendation-receipt",
        "capability": "review-candidate",
        "extra_fields": set(),
    },
    "evolution": {
        "kind": "concordloom.evolution-decision-receipt",
        "capability": "decide-evolution",
        "extra_fields": {"decision_id", "review_recommendation_digest"},
    },
    "activation": {
        "kind": "concordloom.activation-evidence-receipt",
        "capability": "activate-binding",
        "extra_fields": {
            "decision_id",
            "evolution_decision_digest",
            "review_recommendation_digest",
        },
    },
}
COMMON_RECEIPT_FIELDS = {
    "schema",
    "schema_version",
    "kind",
    "id",
    "receipt_digest",
    "principal",
    "capability",
    "verdict",
    "proposal_digest",
    "proposal_tree_digest",
    "base_binding_digest",
    "candidate_tree_digest",
    "candidate_author_principal_ids",
}
IDENTIFIER = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*")
DIGEST = re.compile(r"sha256:[0-9a-f]{64}")


def _activation_requirements() -> dict:
    return {
        "kind": "concordloom.activation-requirements",
        "schema_version": "0.1",
        "id": "concordloom-self-binding-v7-activation-requirements",
        "review_successor": {
            "outcome": "recommendation",
            "capability": "review-candidate",
            "receipt_kind": RECEIPT_KINDS["review"]["kind"],
            "exact_receipt_digest_required": True,
            "may_decide_evolution": False,
        },
        "evolution_decision": {
            "capability": "decide-evolution",
            "receipt_kind": RECEIPT_KINDS["evolution"]["kind"],
            "exact_receipt_digest_required": True,
            "decision_id_required": True,
            "separate_from_activation_decision": True,
        },
        "activation": {
            "capability": "activate-binding",
            "receipt_kind": RECEIPT_KINDS["activation"]["kind"],
            "exact_receipt_digest_required": True,
            "decision_id_required": True,
        },
        "digest_contract": {
            "canonicalization": "rfc8785",
            "algorithm": "sha256",
            "receipt_digest_excludes": ["/receipt_digest"],
            "exact_binding_proposal_digest_required": True,
            "exact_proposal_tree_digest_required": True,
            "candidate_tree_is_proposal_artifact_tree": True,
            "one_candidate_tree_digest_across_all_receipts": True,
        },
    }


def _load_receipt(
    path: Path,
    receipt_type: str,
    *,
    proposal_digest: str,
    proposal_tree_digest: str,
    base_binding_digest: str,
    policy: dict,
) -> tuple[dict, str]:
    specification = RECEIPT_KINDS[receipt_type]
    document = load(path)
    if not isinstance(document, dict):
        raise SystemExit(f"{receipt_type} receipt must be a JSON object")
    expected_fields = (
        COMMON_RECEIPT_FIELDS | specification["extra_fields"]
    )
    if set(document) != expected_fields:
        missing = sorted(expected_fields - set(document))
        unexpected = sorted(set(document) - expected_fields)
        raise SystemExit(
            f"{receipt_type} receipt schema mismatch: "
            f"missing={missing!r} unexpected={unexpected!r}"
        )
    try:
        source_bytes = path.read_bytes()
    except OSError as exc:
        raise SystemExit(f"cannot read {receipt_type} receipt: {exc}") from exc
    if source_bytes != canonical_bytes(document) + b"\n":
        raise SystemExit(
            f"{receipt_type} receipt is not canonical newline-terminated JSON"
        )
    if document["schema"] != RECEIPT_SCHEMA:
        raise SystemExit(f"{receipt_type} receipt uses the wrong schema")
    if document["schema_version"] != "0.1":
        raise SystemExit(f"{receipt_type} receipt uses the wrong schema version")
    if document["kind"] != specification["kind"]:
        raise SystemExit(f"{receipt_type} receipt uses the wrong kind")
    if not isinstance(document["id"], str) or not IDENTIFIER.fullmatch(
        document["id"]
    ):
        raise SystemExit(f"{receipt_type} receipt id is invalid")
    payload = deepcopy(document)
    claimed_digest = payload.pop("receipt_digest")
    computed_digest = digest(payload)
    if claimed_digest != computed_digest:
        raise SystemExit(f"{receipt_type} receipt digest mismatch")
    if document["capability"] != specification["capability"]:
        raise SystemExit(f"{receipt_type} receipt uses the wrong capability")
    if document["verdict"] != "pass":
        raise SystemExit(f"{receipt_type} receipt verdict is not pass")
    if document["proposal_digest"] != proposal_digest:
        raise SystemExit(f"{receipt_type} receipt pins the wrong proposal")
    if document["proposal_tree_digest"] != proposal_tree_digest:
        raise SystemExit(
            f"{receipt_type} receipt pins the wrong proposal tree"
        )
    if document["base_binding_digest"] != base_binding_digest:
        raise SystemExit(f"{receipt_type} receipt pins a stale base binding")
    if not isinstance(document["candidate_tree_digest"], str) or not DIGEST.fullmatch(
        document["candidate_tree_digest"]
    ):
        raise SystemExit(f"{receipt_type} receipt candidate tree is invalid")
    if document["candidate_tree_digest"] != proposal_tree_digest:
        raise SystemExit(
            f"{receipt_type} receipt candidate tree does not match "
            "the exact proposal artifact tree"
        )
    principal = document["principal"]
    if (
        not isinstance(principal, dict)
        or set(principal) != {"id", "kind"}
        or not isinstance(principal["id"], str)
        or not isinstance(principal["kind"], str)
    ):
        raise SystemExit(f"{receipt_type} receipt principal is invalid")
    bound_principals = {
        item["id"]: item for item in policy["authority"]["principals"]
    }
    bound = bound_principals.get(principal["id"])
    if bound is None or bound["kind"] != principal["kind"]:
        raise SystemExit(f"{receipt_type} receipt principal is not bound")
    if specification["capability"] not in principal_capabilities(
        policy, principal["id"]
    ):
        raise SystemExit(
            f"{receipt_type} receipt principal lacks "
            f"{specification['capability']}"
        )
    authors = document["candidate_author_principal_ids"]
    if (
        not isinstance(authors, list)
        or not authors
        or not all(isinstance(item, str) for item in authors)
        or len(authors) != len(set(authors))
    ):
        raise SystemExit(
            f"{receipt_type} receipt candidate authors are invalid"
        )
    if receipt_type == "review" and principal["id"] in authors:
        raise SystemExit("review receipt principal authored the candidate")
    for field in specification["extra_fields"]:
        value = document[field]
        if field.endswith("_digest"):
            if not isinstance(value, str) or not DIGEST.fullmatch(value):
                raise SystemExit(
                    f"{receipt_type} receipt {field} is invalid"
                )
        elif field == "decision_id" and (
            not isinstance(value, str) or not IDENTIFIER.fullmatch(value)
        ):
            raise SystemExit(f"{receipt_type} receipt decision id is invalid")
    return document, computed_digest


def _validate_activation_receipts(
    *,
    review_path: Path,
    evolution_path: Path,
    activation_path: Path,
    proposal_digest: str,
    proposal_tree_digest: str,
    base_binding_digest: str,
    policy: dict,
) -> dict:
    review, review_digest = _load_receipt(
        review_path,
        "review",
        proposal_digest=proposal_digest,
        proposal_tree_digest=proposal_tree_digest,
        base_binding_digest=base_binding_digest,
        policy=policy,
    )
    evolution, evolution_digest = _load_receipt(
        evolution_path,
        "evolution",
        proposal_digest=proposal_digest,
        proposal_tree_digest=proposal_tree_digest,
        base_binding_digest=base_binding_digest,
        policy=policy,
    )
    activation, activation_digest = _load_receipt(
        activation_path,
        "activation",
        proposal_digest=proposal_digest,
        proposal_tree_digest=proposal_tree_digest,
        base_binding_digest=base_binding_digest,
        policy=policy,
    )
    if evolution["review_recommendation_digest"] != review_digest:
        raise SystemExit(
            "evolution decision does not pin the exact review recommendation"
        )
    if activation["review_recommendation_digest"] != review_digest:
        raise SystemExit(
            "activation evidence does not pin the exact review recommendation"
        )
    if activation["evolution_decision_digest"] != evolution_digest:
        raise SystemExit(
            "activation evidence does not pin the exact evolution decision"
        )
    tree_digests = {
        review["candidate_tree_digest"],
        evolution["candidate_tree_digest"],
        activation["candidate_tree_digest"],
    }
    if len(tree_digests) != 1:
        raise SystemExit("activation receipts pin different candidate trees")
    author_sets = {
        tuple(review["candidate_author_principal_ids"]),
        tuple(evolution["candidate_author_principal_ids"]),
        tuple(activation["candidate_author_principal_ids"]),
    }
    if len(author_sets) != 1:
        raise SystemExit("activation receipts pin different candidate authors")
    if review["principal"]["id"] in {
        evolution["principal"]["id"],
        activation["principal"]["id"],
    }:
        raise SystemExit(
            "independent reviewer cannot decide or activate evolution"
        )
    if evolution["decision_id"] == activation["decision_id"]:
        raise SystemExit(
            "evolution and activation decision ids must be distinct"
        )
    if len({review["id"], evolution["id"], activation["id"]}) != 3:
        raise SystemExit("activation receipt ids must be distinct")
    return {
        "review": review,
        "review_digest": review_digest,
        "evolution": evolution,
        "evolution_digest": evolution_digest,
        "activation": activation,
        "activation_digest": activation_digest,
        "candidate_tree_digest": review["candidate_tree_digest"],
        "proposal_tree_digest": review["proposal_tree_digest"],
    }


def _v7_loop_specs() -> list[dict[str, object]]:
    specs = deepcopy(loop_specs())
    by_id = {spec["id"]: spec for spec in specs}
    by_id["review-successor"]["output_outcome"] = (
        "An independent recommendation with evidence; never an evolution "
        "decision or activation."
    )
    by_id["activate-successor"]["input_outcome"] = (
        "An exact binding proposal, an independent review recommendation, "
        "a separate decide-evolution decision, and activation evidence."
    )
    return specs


def _descendants() -> dict[str, list[str]]:
    children: dict[str, list[str]] = {node[0]: [] for node in NODES}
    for node_id, parent, *_rest in NODES:
        if parent is not None:
            children[parent].append(node_id)
    result: dict[str, list[str]] = {}

    def visit(node_id: str) -> list[str]:
        nested = [node_id]
        for child_id in children[node_id]:
            nested.extend(visit(child_id))
        result[node_id] = nested
        return nested

    visit("steward-concordloom")
    return result


def _write_paths(node_id: str) -> list[str]:
    if node_id in LEAF_WRITE_PATHS:
        return sorted(set(LEAF_WRITE_PATHS[node_id]))
    descendants = _descendants()[node_id]
    return sorted(
        {
            path
            for descendant in descendants
            for path in LEAF_WRITE_PATHS.get(descendant, [])
        }
    )


def _local_scope(node_id: str) -> dict:
    write_paths = _write_paths(node_id)
    descendants = _descendants()[node_id]
    explicit_reads = [
        path
        for descendant in descendants
        for path in LEAF_READ_PATHS.get(descendant, [])
    ]
    return {
        "read_paths": sorted(
            set(write_paths + explicit_reads + GOVERNANCE_READS)
        ),
        "write_paths": write_paths,
        "network": "none",
        "external_mutations": [],
    }


def _configure_registry(
    registry: dict,
    policy: dict,
) -> tuple[dict, dict, dict]:
    execute_capabilities = {
        **OPERATOR_CAPABILITIES,
        "publish-site": "publish-release",
        "maintain-repository-presence": "publish-release",
        "publish-source-change": "publish-release",
        "accept-source-change": "accept-source-publication",
        "maintain-organization-presence": "publish-release",
        "distribute-package": "publish-release",
        "review-successor": "review-candidate",
    }
    loops = {loop["id"]: loop for loop in registry["loops"]}
    contracts = {
        contract["id"]: contract for contract in registry["evidence_contracts"]
    }
    for loop_id, capability in execute_capabilities.items():
        loops[loop_id]["authority"]["execute_capability"] = capability
        if loop_id != "review-successor":
            contracts[f"{loop_id}-acceptance"][
                "producer_capability"
            ] = capability
    contracts["review-successor-acceptance"]["required_claims"] = [
        "review-successor-recommendation"
    ]
    contracts["activate-successor-acceptance"]["required_claims"] = [
        "review-successor-recommendation",
        "decide-evolution-decision",
        "activate-successor-outcome",
    ]
    for edge in registry["containment_graph"]["edges"]:
        child_id = edge["child_loop_id"]
        capability = execute_capabilities.get(child_id)
        if capability and capability not in edge["grant"]["capabilities"]:
            edge["grant"]["capabilities"].append(capability)
            edge["grant"]["capabilities"].sort()
        if child_id == "activate-successor":
            edge["grant"]["capabilities"] = sorted(
                set(
                    edge["grant"]["capabilities"]
                    + ["decide-evolution", "activate-binding"]
                )
            )

    root_scope = _local_scope("steward-concordloom")
    read_only_scope = deepcopy(root_scope)
    read_only_scope["write_paths"] = []
    metadata_scope = _local_scope("plan-release")
    for edge in registry["containment_graph"]["edges"]:
        child_id = edge["child_loop_id"]
        edge["grant"]["scope"] = _local_scope(child_id)
        if child_id == "release-distribution":
            edge["grant"]["scope"] = {
                "read_paths": sorted(
                    {
                        path
                        for paths in PUBLICATION_READS.values()
                        for path in paths
                    }
                    | set(_local_scope(child_id)["read_paths"])
                ),
                "write_paths": _write_paths(child_id),
                "network": "write",
                "external_mutations": sorted(
                    {
                        effect
                        for effects in PUBLICATION_EFFECTS.values()
                        for effect in effects
                    }
                ),
            }
        elif child_id == "plan-release":
            edge["grant"]["scope"] = deepcopy(metadata_scope)
        elif child_id in PUBLICATION_EFFECTS:
            edge["grant"]["scope"] = {
                "read_paths": sorted(
                    set(PUBLICATION_READS[child_id] + GOVERNANCE_READS)
                ),
                "write_paths": [],
                "network": "write",
                "external_mutations": PUBLICATION_EFFECTS[child_id],
            }
        elif child_id == "verify-live-release":
            edge["grant"]["scope"] = {
                "read_paths": ["site"],
                "write_paths": [],
                "network": "read",
                "external_mutations": [],
            }
    return read_only_scope, metadata_scope, root_scope


def _publication_route(registry: dict) -> list[dict]:
    edges = {
        edge["child_loop_id"]: edge
        for edge in registry["containment_graph"]["edges"]
    }
    route_specs = [
        (
            "steward-concordloom",
            "operator",
            "authorize only the exact publication handoff",
            "record the operator publication decision",
            {
                "read_paths": GOVERNANCE_READS,
                "write_paths": [],
                "network": "none",
                "external_mutations": [],
            },
        ),
        (
            "distribute-package",
            "publisher",
            "publish only the pinned tag and GitHub release assets",
            "publish the checked wheel, sdist and checksums",
            edges["distribute-package"]["grant"]["scope"],
        ),
        (
            "publish-site",
            "publisher",
            "perform only the Pages effect",
            "publish the pinned static site",
            edges["publish-site"]["grant"]["scope"],
        ),
        (
            "maintain-repository-presence",
            "publisher",
            "perform only the repository presence effects",
            "publish the pinned repository brand metadata",
            edges["maintain-repository-presence"]["grant"]["scope"],
        ),
        (
            "publish-source-change",
            "publisher",
            "publish only the pinned branch and pull request",
            "github:yeet",
            edges["publish-source-change"]["grant"]["scope"],
        ),
        (
            "accept-source-change",
            "operator",
            "merge only the independently reviewed candidate",
            "record the exact operator merge decision",
            edges["accept-source-change"]["grant"]["scope"],
        ),
        (
            "maintain-organization-presence",
            "publisher",
            "perform only the organization profile effect",
            "publish the approved organization identity",
            edges["maintain-organization-presence"]["grant"]["scope"],
        ),
    ]
    return [
        {
            "loop_id": loop_id,
            "node_id": loop_id,
            "role": role,
            "scope": deepcopy(scope),
            "model_intent": "none",
            "reasoning_intent": reasoning,
            "skill_intent": skill,
            "subagent_intent": [],
        }
        for loop_id, role, reasoning, skill, scope in route_specs
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--activate", action="store_true")
    parser.add_argument("--accepted-proposal-digest")
    parser.add_argument("--review-recommendation", type=Path)
    parser.add_argument("--evolution-decision", type=Path)
    parser.add_argument("--activation-evidence", type=Path)
    args = parser.parse_args()
    if args.activate and (
        not args.accepted_proposal_digest
        or args.review_recommendation is None
        or args.evolution_decision is None
        or args.activation_evidence is None
    ):
        raise SystemExit(
            "activation requires --accepted-proposal-digest, "
            "--review-recommendation, --evolution-decision, and "
            "--activation-evidence"
        )

    graph = load(GRAPH_DIR / "accepted-project-graph.json")
    decisions = load(GRAPH_DIR / "decision-log.json")
    old_policy = load(PREDECESSOR_DIR / "policy.json")
    predecessor = load(PREDECESSOR_DIR / "binding.json")
    base_digest = predecessor["binding_digest"]

    policy = deepcopy(old_policy)
    policy["id"] = "concordloom-self-policy-v7"
    policy["execution"]["default_scope"]["read_paths"] = _local_scope(
        "steward-concordloom"
    )["read_paths"]
    policy["execution"]["default_scope"]["write_paths"] = _write_paths(
        "steward-concordloom"
    )
    policy["execution"]["default_scope"][
        "external_mutations"
    ] = ALLOWED_EXTERNAL_MUTATIONS
    operator_role = next(
        role
        for role in policy["authority"]["roles"]
        if role["id"] == "operator"
    )
    operator_role["capabilities"] = sorted(
        set(
            operator_role["capabilities"]
            + [
                "accept-intent",
                "activate-binding",
                "authorize-run",
                "decide-evolution",
            ]
        )
    )
    validate_policy(policy)

    design_proposal = propose_loop_design(
        graph,
        decisions,
        policy,
        proposal_id="concordloom-development-system-v7-proposal",
        loop_specs=_v7_loop_specs(),
        containment=containment(),
    )
    design = accept_loop_design(
        design_proposal,
        decisions,
        policy,
        accepted_graph=graph,
        decision_id="accept-concordloom-development-system-v7",
        actor=OPERATOR,
        accepted_at=STAMP,
        authority_ref="operator",
        rationale=(
            "Keep all 58 cycles and grant project metadata maintenance only "
            "to the release branch that owns package distribution."
        ),
    )
    registry = compile_registry(
        graph,
        decisions,
        design,
        policy,
        loop_design_proposal=design_proposal,
        registry_id="concordloom-development-registry-v7",
    )
    read_only_scope, metadata_scope, _root_scope = _configure_registry(
        registry, policy
    )
    validate_registry(registry, policy)

    model = development_model(base_digest)
    model["id"] = "concordloom-development-system-v7"
    model_nodes = {node["id"]: node for node in model["nodes"]}
    model_nodes["review-successor"]["contract"]["en"]["output"] = (
        "An independent recommendation with evidence, not an evolution "
        "decision."
    )
    model_nodes["review-successor"]["contract"]["ru"]["output"] = (
        "Независимая рекомендация с доказательствами, а не решение об "
        "эволюции."
    )
    model_nodes["review-successor"]["artifacts"] = [
        "review",
        "recommendation",
    ]
    model_nodes["activate-successor"]["contract"]["en"]["input"] = (
        "An exact binding proposal, independent recommendation, separate "
        "operator evolution decision and activation evidence."
    )
    model_nodes["activate-successor"]["contract"]["ru"]["input"] = (
        "Точное предложение привязки, независимая рекомендация, отдельное "
        "решение оператора об эволюции и доказательство активации."
    )
    model["activation_requirements"] = _activation_requirements()
    signals = [
        {
            "kind": "concordloom.evolution-signal",
            "schema_version": "0.1",
            "id": "organization-migration-left-stale-package-metadata",
            "base_binding_digest": base_digest,
            "category": "coverage",
            "severity": "warning",
            "occurrences": 3,
            "summary": (
                "The organization migration left pyproject.toml and "
                "CITATION.cff stale because no accepted cycle could write them."
            ),
            "source_digest": digest(
                {"source": "self-use:2026-07-27:root-metadata-gap"}
            ),
            "provenance": [{"kind": "evidence", "ref": "self-use-run-audit"}],
        },
        {
            "kind": "concordloom.evolution-signal",
            "schema_version": "0.1",
            "id": "russian-article-exposed-english-atlas-copy",
            "base_binding_digest": base_digest,
            "category": "friction",
            "severity": "warning",
            "occurrences": 2,
            "summary": (
                "A reader found English Atlas wording and obsolete self-binding "
                "copy in the Russian theory page."
            ),
            "source_digest": digest(
                {"source": "conversation:2026-07-27:russian-article-gap"}
            ),
            "provenance": [{"kind": "evidence", "ref": "reader-screenshot"}],
        },
    ]
    evolution = propose_evolution(
        base_digest,
        signals,
        [
            {
                "op": "add",
                "target_kind": "policy",
                "target_id": "concordloom-self-policy-v7",
                "value": {
                    "unchanged_cycle_count": len(NODES),
                    "metadata_owner_loop_id": "plan-release",
                    "exact_write_paths": METADATA_PATHS,
                    "language_gate": "reject-English-Atlas-in-Russian-prose",
                },
            }
        ],
        proposed_by={"id": "example-orchestrator", "kind": "orchestrator"},
        decision_authority_ref="operator",
        expected_effect=(
            "Keep the 58-cycle graph unchanged, authorize release metadata "
            "authoring separately from exact tag and GitHub release asset "
            "publication, and fail generated Russian copy on known leaks."
        ),
        risk={
            "level": "low",
            "failure_modes": [
                "Metadata authority could leak outside package distribution.",
                "The language gate could treat a machine identifier as prose.",
            ],
            "rollback": (
                "Reactivate the v6 predecessor if exact metadata scope or the "
                "language gate fails independent review."
            ),
        },
        generated_at=STAMP,
        policy=old_policy,
        proposal_id="authorize-project-metadata-maintenance",
    )

    paths = {
        "accepted_project_graph": (
            "framework/concordloom/v3/accepted-project-graph.json"
        ),
        "decision_log": "framework/concordloom/v3/decision-log.json",
        "loop_design_proposal": (
            "framework/concordloom/v7/loop-design-proposal.json"
        ),
        "accepted_loop_design": "framework/concordloom/v7/loop-design.json",
        "cycle_registry": "framework/concordloom/v7/cycle-registry.json",
        "policy": "framework/concordloom/v7/policy.json",
    }
    extras = {
        "atlas_input": (
            "framework/concordloom/v7/development-model.json",
            model,
        ),
        "evolution_history": (
            "framework/concordloom/v7/evolution-proposal.json",
            evolution,
        ),
    }
    proposal = create_binding_proposal(
        graph,
        decisions,
        design,
        registry,
        policy,
        loop_design_proposal=design_proposal,
        artifact_paths=paths,
        proposal_id="concordloom-self-binding-v7-proposal",
        created_at=STAMP,
        predecessor_binding_digest=base_digest,
        extra_artifacts=extras,
    )
    publication_route = _publication_route(registry)
    documents = {
        "loop-design-proposal.json": design_proposal,
        "loop-design.json": design,
        "cycle-registry.json": registry,
        "policy.json": policy,
        "development-model.json": model,
        "evolution-proposal.json": evolution,
        "binding-proposal.json": proposal,
        "publication-route.json": publication_route,
    }
    if not args.activate:
        for name, document in documents.items():
            save(TARGET / name, document)
        print(
            "METADATA_MAINTENANCE_V7_PROPOSED "
            f"nodes={len(NODES)} proposal={proposal['proposal_digest']}"
        )
        return
    if args.accepted_proposal_digest != proposal["proposal_digest"]:
        raise SystemExit("accepted proposal digest does not match exact v7 proposal")
    receipts = _validate_activation_receipts(
        review_path=args.review_recommendation,
        evolution_path=args.evolution_decision,
        activation_path=args.activation_evidence,
        proposal_digest=proposal["proposal_digest"],
        proposal_tree_digest=digest(proposal["artifacts"]),
        base_binding_digest=base_digest,
        policy=old_policy,
    )
    for name, document in documents.items():
        save(TARGET / name, document)

    binding = activate_binding(
        proposal,
        graph,
        decisions,
        design_proposal,
        design,
        registry,
        policy,
        activation_decision={
            "decision_id": receipts["activation"]["decision_id"],
            "actor": {
                **OPERATOR,
                "id": receipts["activation"]["principal"]["id"],
            },
            "authority_ref": "operator",
            "accepted_at": "2026-07-27T19:01:00Z",
            "rationale": (
                "Activate the exact metadata-maintenance successor accepted by "
                "the operator after independent recommendation "
                f"{receipts['review_digest']}, separate evolution decision "
                f"{receipts['evolution']['decision_id']} "
                f"({receipts['evolution_digest']}), and activation evidence "
                f"{receipts['activation_digest']}. The evolution "
                "proposal did not activate itself."
            ),
        },
        binding_id="concordloom-self-binding-v7",
        extra_artifacts=extras,
    )
    catalog = append_binding(
        load(SOURCE / "catalog.json"),
        binding,
        path="framework/concordloom/v7/binding.json",
    )
    save(TARGET / "binding.json", binding)
    save(
        TARGET / "activation-receipt.json",
        {
            "kind": "concordloom.activation-receipt",
            "schema_version": "0.1",
            "id": "activate-concordloom-self-binding-v7-receipt",
            "binding_digest": binding["binding_digest"],
            "binding_proposal_digest": proposal["proposal_digest"],
            "candidate_tree_digest": receipts["candidate_tree_digest"],
            "proposal_tree_digest": receipts["proposal_tree_digest"],
            "review_recommendation_id": receipts["review"]["id"],
            "review_recommendation_digest": receipts["review_digest"],
            "evolution_decision_id": receipts["evolution"]["decision_id"],
            "evolution_decision_digest": receipts["evolution_digest"],
            "activation_decision_id": receipts["activation"]["decision_id"],
            "activation_evidence_id": receipts["activation"]["id"],
            "activation_evidence_digest": receipts["activation_digest"],
            "activated_at": "2026-07-27T19:01:00Z",
        },
    )
    save(SOURCE / "catalog.json", catalog)
    print(
        "METADATA_MAINTENANCE_V7_ACTIVATED "
        f"nodes={len(NODES)} binding={binding['binding_digest']}"
    )


if __name__ == "__main__":
    main()
