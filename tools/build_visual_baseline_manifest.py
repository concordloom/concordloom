#!/usr/bin/env python3
"""Build or verify the deterministic Signal Canvas screenshot manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASELINES = ROOT / "design" / "frontend" / "baselines"
MANIFEST = BASELINES / "manifest.json"
CONTRACT = ROOT / "design" / "frontend" / "visual-contract.json"

VIEWPORTS = {
    "visual-small-mobile": "360x800",
    "visual-mobile": "390x844",
    "visual-phone-landscape": "844x390",
    "visual-tablet-portrait": "768x1024",
    "visual-tablet-landscape": "1024x768",
    "visual-desktop": "1440x900",
    "visual-wide": "1920x1080",
}

SNAPSHOTS = {
    f"{language}-{name}.png"
    for language in ("en", "ru")
    for name in (
        "concept",
        "theory",
        "quickstart",
        "atlas",
        "docs",
        "atlas-nested",
        "atlas-details",
        "workshop",
    )
}


def digest(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def build_manifest() -> dict[str, object]:
    files: list[dict[str, object]] = []
    for project, viewport in VIEWPORTS.items():
        directory = BASELINES / project / "visual-evidence.spec.js"
        actual = {path.name for path in directory.glob("*.png")}
        if actual != SNAPSHOTS:
            missing = sorted(SNAPSHOTS - actual)
            extra = sorted(actual - SNAPSHOTS)
            raise SystemExit(
                f"invalid baseline inventory for {project}: "
                f"missing={missing} extra={extra}"
            )
        for path in sorted(directory.glob("*.png")):
            data = path.read_bytes()
            files.append(
                {
                    "bytes": len(data),
                    "language": path.name.split("-", 1)[0],
                    "path": path.relative_to(ROOT).as_posix(),
                    "sha256": digest(data),
                    "viewport": viewport,
                }
            )

    aggregate_bytes = json.dumps(
        [(item["path"], item["sha256"]) for item in files],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return {
        "baseline_set_sha256": digest(aggregate_bytes),
        "contract": {
            "id": "signal-canvas-v1",
            "path": CONTRACT.relative_to(ROOT).as_posix(),
            "sha256": digest(CONTRACT.read_bytes()),
        },
        "count": len(files),
        "files": files,
        "kind": "concordloom.visual-baseline-manifest",
        "schema_version": "0.1",
        "status": "candidate-evidence",
    }


def canonical_bytes(value: dict[str, object]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    expected = canonical_bytes(build_manifest())
    if args.check:
        if not MANIFEST.is_file() or MANIFEST.read_bytes() != expected:
            raise SystemExit("STALE_VISUAL_BASELINE_MANIFEST")
        print("VISUAL_BASELINE_MANIFEST_OK")
        return 0

    MANIFEST.write_bytes(expected)
    print(f"VISUAL_BASELINE_MANIFEST_BUILT {digest(expected)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
