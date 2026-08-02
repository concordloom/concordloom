#!/usr/bin/env python3
"""Activate the exact independently reviewed v10 task-route successor.

The tool materializes authority that already exists in three external receipts.
It never creates a review, evolution decision, or activation decision.  The
reviewed repository may be a separate exact checkout so adding this tool does
not invalidate the candidate that was reviewed before activation.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from concordloom.canonical import digest, load, save
from concordloom.catalog import append_binding, validate_catalog
from concordloom.compiler import activate_binding
from concordloom.run import verify_candidate_manifest
from authorize_metadata_maintenance import _validate_activation_receipts


ROOT = Path(__file__).resolve().parents[1]
SOURCE_REL = Path("framework/concordloom")
PROPOSAL_REL = SOURCE_REL / "v10" / "binding-proposal.json"
CATALOG_REL = SOURCE_REL / "catalog.json"
V9_BINDING_REL = SOURCE_REL / "v9" / "binding.json"
V10_BINDING_REL = SOURCE_REL / "v10" / "binding.json"
V10_RECEIPT_REL = SOURCE_REL / "v10" / "activation-receipt.json"


@dataclass(frozen=True)
class ActivationExpectations:
    base_binding_digest: str
    proposal_digest: str
    proposal_tree_digest: str
    review_card_digest: str
    reviewed_manifest_digest: str
    reviewed_tree_digest: str


EXPECTATIONS = ActivationExpectations(
    base_binding_digest=(
        "sha256:1940a57ca917d6136c5742048dfccc68d0434c530da2ad3ef3b2ba486f866597"
    ),
    proposal_digest=(
        "sha256:e19ebf34082aaff8f6a52d8f7b9420b60db146ca8b0acb22d2ec7fa7dd3d84bd"
    ),
    proposal_tree_digest=(
        "sha256:7d9cde486f6a73a63862d442713ab910d51e521b567c3d7007da04d8f3bae23e"
    ),
    review_card_digest=(
        "sha256:f422790fcc8e81c5a4bd7c132961d0ba7c0b45a9b04e9860d131bf1e7b8ec097"
    ),
    reviewed_manifest_digest=(
        "sha256:55c53c20e56fd38939d5feff2ccc06cc1e7717ccbb205ef43ff1da205e33a445"
    ),
    reviewed_tree_digest=(
        "sha256:59ec27df3dbe981bee6b91e34bf1725a3215314cdb0d0dbd1f71f894c67e5270"
    ),
)


class ActivationError(ValueError):
    """The exact reviewed successor cannot be activated safely."""


def _raw_digest(path: Path) -> str:
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise ActivationError(f"cannot read exact activation input {path}: {exc}") from exc
    return "sha256:" + sha256(payload).hexdigest()


def _manifest_entries(candidate: dict) -> dict[str, dict]:
    return {item["path"]: item for item in candidate["files"]}


def _require_reviewed_candidate(
    reviewed_repository: Path,
    output_root: Path,
    review_card_path: Path,
    candidate_path: Path,
    expectations: ActivationExpectations,
) -> tuple[dict, dict]:
    review_card = load(review_card_path)
    if digest(review_card) != expectations.review_card_digest:
        raise ActivationError("review card digest does not match the accepted review")
    candidate = load(candidate_path)
    if digest(candidate) != expectations.reviewed_manifest_digest:
        raise ActivationError("reviewed candidate manifest digest changed")
    if candidate.get("tree_digest") != expectations.reviewed_tree_digest:
        raise ActivationError("reviewed candidate declares the wrong tree digest")
    verified_tree = verify_candidate_manifest(reviewed_repository, candidate)
    if verified_tree != expectations.reviewed_tree_digest:
        raise ActivationError("reviewed repository no longer matches the reviewed tree")
    expected_card_fields = {
        "binding_digest": expectations.base_binding_digest,
        "candidate_manifest_digest": expectations.reviewed_manifest_digest,
        "candidate_tree_digest": expectations.reviewed_tree_digest,
        "candidate_author_principal_ids": ["example-executor"],
        "status": "authorized",
    }
    for field, expected in expected_card_fields.items():
        if review_card.get(field) != expected:
            raise ActivationError(f"review card {field} does not match the reviewed candidate")
    if not any(
        node.get("node_id") == "review-successor"
        for node in review_card.get("nodes", [])
    ):
        raise ActivationError("review card does not contain the independent successor review")

    entries = _manifest_entries(candidate)
    proposal_entry = entries.get(PROPOSAL_REL.as_posix())
    if proposal_entry is None:
        raise ActivationError("reviewed candidate omits the exact binding proposal bytes")
    reviewed_proposal = reviewed_repository / PROPOSAL_REL
    output_proposal = output_root / PROPOSAL_REL
    if _raw_digest(reviewed_proposal) != proposal_entry["digest"]:
        raise ActivationError("reviewed proposal bytes differ from the candidate manifest")
    if reviewed_proposal.read_bytes() != output_proposal.read_bytes():
        raise ActivationError("output binding proposal bytes differ from the reviewed candidate")
    return review_card, candidate


def _require_artifact_bytes(
    reviewed_repository: Path,
    output_root: Path,
    candidate: dict,
    proposal: dict,
) -> None:
    entries = _manifest_entries(candidate)
    for artifact in proposal["artifacts"]:
        relative = artifact["path"]
        entry = entries.get(relative)
        if entry is None:
            raise ActivationError(f"reviewed candidate omits binding artifact {relative!r}")
        reviewed_path = reviewed_repository / relative
        output_path = output_root / relative
        if _raw_digest(reviewed_path) != entry["digest"]:
            raise ActivationError(f"reviewed artifact bytes changed for {relative!r}")
        try:
            matches = reviewed_path.read_bytes() == output_path.read_bytes()
        except OSError as exc:
            raise ActivationError(f"cannot compare binding artifact {relative!r}: {exc}") from exc
        if not matches:
            raise ActivationError(f"output artifact differs from reviewed bytes: {relative!r}")


def _require_v9_head(output_root: Path, expectations: ActivationExpectations) -> dict:
    source = output_root / SOURCE_REL
    catalog = load(output_root / CATALOG_REL)
    validate_catalog(catalog, artifact_root=output_root)
    base = load(output_root / V9_BINDING_REL)
    if base.get("binding_digest") != expectations.base_binding_digest:
        raise ActivationError("v9 binding bytes do not match the activation base")
    if catalog.get("active_binding_digest") != expectations.base_binding_digest:
        raise ActivationError("catalog head changed before v10 activation")
    tail = catalog["entries"][-1]
    if (
        tail.get("binding_digest") != expectations.base_binding_digest
        or tail.get("binding_id") != "concordloom-self-binding-v9"
        or tail.get("path") != V9_BINDING_REL.as_posix()
    ):
        raise ActivationError("catalog tail is not the exact v9 predecessor")
    if (source / "v10" / "binding.json").exists() or (
        source / "v10" / "activation-receipt.json"
    ).exists():
        raise ActivationError("v10 activation artifacts already exist")
    return catalog


def materialize_activation(
    *,
    reviewed_repository: Path,
    output_root: Path,
    review_card_path: Path,
    reviewed_candidate_path: Path,
    review_recommendation_path: Path,
    evolution_decision_path: Path,
    activation_evidence_path: Path,
    accepted_proposal_digest: str,
    activated_at: str,
    expectations: ActivationExpectations = EXPECTATIONS,
) -> dict:
    """Validate all authority and reviewed bytes, then append v10 atomically-last."""

    reviewed_repository = reviewed_repository.resolve()
    output_root = output_root.resolve()
    if accepted_proposal_digest != expectations.proposal_digest:
        raise ActivationError("accepted proposal digest is not the exact v10 proposal")
    _review_card, candidate = _require_reviewed_candidate(
        reviewed_repository,
        output_root,
        review_card_path,
        reviewed_candidate_path,
        expectations,
    )

    source = output_root / SOURCE_REL
    v10 = source / "v10"
    proposal = load(v10 / "binding-proposal.json")
    if proposal.get("proposal_digest") != expectations.proposal_digest:
        raise ActivationError("binding proposal digest changed")
    if proposal.get("predecessor_binding_digest") != expectations.base_binding_digest:
        raise ActivationError("binding proposal names the wrong predecessor")
    proposal_tree_digest = digest(proposal["artifacts"])
    if proposal_tree_digest != expectations.proposal_tree_digest:
        raise ActivationError("binding proposal artifact tree changed")
    _require_artifact_bytes(reviewed_repository, output_root, candidate, proposal)
    catalog = _require_v9_head(output_root, expectations)

    predecessor_policy = load(source / "v9" / "policy.json")
    receipts = _validate_activation_receipts(
        review_path=review_recommendation_path,
        evolution_path=evolution_decision_path,
        activation_path=activation_evidence_path,
        proposal_digest=expectations.proposal_digest,
        proposal_tree_digest=expectations.proposal_tree_digest,
        base_binding_digest=expectations.base_binding_digest,
        policy=predecessor_policy,
    )
    if receipts["review"]["principal"]["id"] != "example-reviewer":
        raise ActivationError("review receipt is not from the independent reviewer")
    if receipts["candidate_tree_digest"] != expectations.proposal_tree_digest:
        raise ActivationError("authority receipts pin the wrong proposal artifact tree")

    graph = load(source / "v3" / "accepted-project-graph.json")
    decisions = load(source / "v3" / "decision-log.json")
    design_proposal = load(v10 / "loop-design-proposal.json")
    design = load(v10 / "loop-design.json")
    registry = load(v10 / "cycle-registry.json")
    policy = load(v10 / "policy.json")
    model = load(v10 / "development-model.json")
    evolution_history = load(v10 / "evolution-history.json")
    rationale = (
        "Activate the exact independently reviewed v10 task-route successor "
        f"using review {receipts['review_digest']}, evolution decision "
        f"{receipts['evolution_digest']}, and activation evidence "
        f"{receipts['activation_digest']}."
    )
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
                "id": receipts["activation"]["principal"]["id"],
                "kind": "operator",
                "display_name": "User-confirmed operator",
            },
            "authority_ref": "operator",
            "accepted_at": activated_at,
            "rationale": rationale,
        },
        binding_id="concordloom-self-binding-v10",
        extra_artifacts={
            "atlas_input": (
                "framework/concordloom/v10/development-model.json",
                model,
            ),
            "evolution_history": (
                "framework/concordloom/v10/evolution-history.json",
                evolution_history,
            ),
        },
    )
    next_catalog = append_binding(
        catalog,
        binding,
        path=V10_BINDING_REL.as_posix(),
    )
    validate_catalog(next_catalog)
    activation_receipt = {
        "kind": "concordloom.activation-receipt",
        "schema_version": "0.1",
        "id": "activate-concordloom-self-binding-v10-receipt",
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
        "review_card_digest": expectations.review_card_digest,
        "reviewed_candidate_manifest_digest": expectations.reviewed_manifest_digest,
        "reviewed_candidate_tree_digest": expectations.reviewed_tree_digest,
        "activated_at": activated_at,
    }

    # The active catalog is the commit point.  It is written only after both
    # referenced activation artifacts exist and the future catalog validates.
    save(output_root / V10_BINDING_REL, binding)
    save(output_root / V10_RECEIPT_REL, activation_receipt)
    validate_catalog(next_catalog, artifact_root=output_root)
    save(output_root / CATALOG_REL, next_catalog)
    return {
        "binding": binding,
        "activation_receipt": activation_receipt,
        "catalog": next_catalog,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reviewed-repository", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=ROOT)
    parser.add_argument("--review-card", type=Path, required=True)
    parser.add_argument("--reviewed-candidate", type=Path, required=True)
    parser.add_argument("--review-recommendation", type=Path, required=True)
    parser.add_argument("--evolution-decision", type=Path, required=True)
    parser.add_argument("--activation-evidence", type=Path, required=True)
    parser.add_argument("--accepted-proposal-digest", required=True)
    parser.add_argument("--activated-at", required=True)
    args = parser.parse_args()
    result = materialize_activation(
        reviewed_repository=args.reviewed_repository,
        output_root=args.output_root,
        review_card_path=args.review_card,
        reviewed_candidate_path=args.reviewed_candidate,
        review_recommendation_path=args.review_recommendation,
        evolution_decision_path=args.evolution_decision,
        activation_evidence_path=args.activation_evidence,
        accepted_proposal_digest=args.accepted_proposal_digest,
        activated_at=args.activated_at,
    )
    print(
        "TASK_ROUTE_V10_ACTIVATED "
        f"binding={result['binding']['binding_digest']}"
    )


if __name__ == "__main__":
    main()
