#!/usr/bin/env python3
"""Build deterministic GitHub Pages data from the active accepted binding."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sys

from concordloom.canonical import canonical_bytes, load, save


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
TRANSITION_CATALOG = ROOT / "docs" / ".concord-transition" / "catalog.json"
PUBLIC_CATALOG = ROOT / "framework" / "concordloom" / "catalog.json"


def active_documents() -> tuple[dict, dict]:
    catalog_path = PUBLIC_CATALOG if PUBLIC_CATALOG.exists() else TRANSITION_CATALOG
    catalog = load(catalog_path)
    active_digest = catalog["active_binding_digest"]
    active_entry = next(
        entry for entry in catalog["entries"] if entry["binding_digest"] == active_digest
    )
    binding = load(ROOT / active_entry["path"])
    registry_path = next(
        artifact["path"]
        for artifact in binding["artifacts"]
        if artifact["role"] == "cycle_registry"
    )
    return binding, load(ROOT / registry_path)


def atlas_projection(binding: dict, registry: dict) -> dict:
    contracts = {
        contract["id"]: contract for contract in registry["evidence_contracts"]
    }
    loops = []
    for loop in registry["loops"]:
        contract_id = f"{loop['id']}-acceptance"
        contract = contracts[contract_id]
        loops.append(
            {
                "id": loop["id"],
                "label": loop["label"],
                "purpose": loop["purpose"],
                "input": loop["inputs"][0]["description"],
                "output": loop["outputs"][0]["description"],
                "acceptedResults": contract["accepted_results"],
                "requiredClaims": contract["required_claims"],
                "independentReview": "reviewer_capability" in contract,
            }
        )
    return {
        "kind": "concordloom.atlas-projection",
        "schemaVersion": "0.2",
        "binding": {
            "id": binding["id"],
            "digest": binding["binding_digest"],
            "predecessorDigest": binding.get("predecessor_binding_digest"),
            "acceptedAt": binding["accepted_by"]["accepted_at"],
            "acceptedBy": binding["accepted_by"]["actor"]["id"],
            "rootLoopIds": binding["active_root_loop_ids"],
        },
        "loops": loops,
        "containment": registry["containment_graph"],
    }


def check_bytes(path: Path, expected: bytes) -> bool:
    return path.exists() and path.read_bytes() == expected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    binding, registry = active_documents()
    projection = atlas_projection(binding, registry)
    output = SITE / "data" / "atlas.json"
    expected = canonical_bytes(projection) + b"\n"
    assets = {
        ROOT / "docs" / "assets" / "concordloom-hero.webp": (
            SITE / "assets" / "concordloom-hero.webp"
        ),
        ROOT / "docs" / "assets" / "concordloom-social-preview.png": (
            SITE / "assets" / "concordloom-social-preview.png"
        ),
    }

    if args.check:
        stale = []
        if not check_bytes(output, expected):
            stale.append(str(output.relative_to(ROOT)))
        for source, target in assets.items():
            if not target.exists() or source.read_bytes() != target.read_bytes():
                stale.append(str(target.relative_to(ROOT)))
        if stale:
            print("STALE_SITE_OUTPUT " + " ".join(stale))
            return 1
        print("SITE_OUTPUT_OK")
        return 0

    save(output, projection, pretty=False)
    for source, target in assets.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    print(f"SITE_BUILT {binding['binding_digest']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
