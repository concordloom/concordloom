#!/usr/bin/env python3
"""Activate the exact independently reviewed v9 frontend-system proposal."""

from __future__ import annotations

import argparse
from pathlib import Path

from concordloom.canonical import digest, load, save
from concordloom.catalog import append_binding
from concordloom.compiler import activate_binding
from authorize_metadata_maintenance import _validate_activation_receipts


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "framework" / "concordloom"
V8 = SOURCE / "v8"
V9 = SOURCE / "v9"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--accepted-proposal-digest", required=True)
    parser.add_argument("--review-recommendation", type=Path, required=True)
    parser.add_argument("--evolution-decision", type=Path, required=True)
    parser.add_argument("--activation-evidence", type=Path, required=True)
    args = parser.parse_args()

    graph = load(SOURCE / "v3" / "accepted-project-graph.json")
    decisions = load(SOURCE / "v3" / "decision-log.json")
    design_proposal = load(V9 / "loop-design-proposal.json")
    design = load(V9 / "loop-design.json")
    registry = load(V9 / "cycle-registry.json")
    policy = load(V9 / "policy.json")
    model = load(V9 / "development-model.json")
    evolution = load(V9 / "evolution-proposal.json")
    proposal = load(V9 / "binding-proposal.json")
    base_digest = load(V8 / "binding.json")["binding_digest"]

    if args.accepted_proposal_digest != proposal["proposal_digest"]:
        raise SystemExit("accepted proposal digest does not match exact v9 proposal")
    receipts = _validate_activation_receipts(
        review_path=args.review_recommendation,
        evolution_path=args.evolution_decision,
        activation_path=args.activation_evidence,
        proposal_digest=proposal["proposal_digest"],
        proposal_tree_digest=digest(proposal["artifacts"]),
        base_binding_digest=base_digest,
        policy=load(V8 / "policy.json"),
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
            "accepted_at": "2026-07-28T23:00:00Z",
            "rationale": (
                "Activate the exact independently reviewed frontend system "
                "through a distinct operator decision."
            ),
        },
        binding_id="concordloom-self-binding-v9",
        extra_artifacts={
            "atlas_input": (
                "framework/concordloom/v9/development-model.json",
                model,
            ),
            "evolution_history": (
                "framework/concordloom/v9/evolution-proposal.json",
                evolution,
            ),
        },
    )
    save(V9 / "binding.json", binding)
    save(
        V9 / "activation-receipt.json",
        {
            "kind": "concordloom.activation-receipt",
            "schema_version": "0.1",
            "id": "activate-concordloom-self-binding-v9-receipt",
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
            "activated_at": "2026-07-28T23:00:00Z",
        },
    )
    save(
        SOURCE / "catalog.json",
        append_binding(
            load(SOURCE / "catalog.json"),
            binding,
            path="framework/concordloom/v9/binding.json",
        ),
    )
    print(f"FRONTEND_SYSTEM_V9_ACTIVATED binding={binding['binding_digest']}")


if __name__ == "__main__":
    main()
