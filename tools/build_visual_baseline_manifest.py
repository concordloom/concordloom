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


def renderer_source(relative_path: object) -> tuple[str, Path]:
    if not isinstance(relative_path, str) or not relative_path:
        raise SystemExit("renderer source path must be a non-empty string")
    declared = Path(relative_path)
    if declared.is_absolute() or ".." in declared.parts:
        raise SystemExit(f"renderer source escapes repository: {relative_path}")
    normalized = declared.as_posix()
    if normalized != relative_path or normalized.startswith("./"):
        raise SystemExit(f"renderer source path is not canonical: {relative_path}")
    source = (ROOT / declared).resolve()
    if not source.is_relative_to(ROOT.resolve()):
        raise SystemExit(f"renderer source escapes repository: {relative_path}")
    return normalized, source


def build_manifest() -> dict[str, object]:
    contract_data = json.loads(CONTRACT.read_text(encoding="utf-8"))
    renderer = contract_data["baseline_policy"]["canonical_renderer"]
    rendering_sources: list[dict[str, str]] = []
    for declared_path in renderer["source_files"]:
        relative_path, source = renderer_source(declared_path)
        if not source.is_file():
            raise SystemExit(f"missing renderer source: {relative_path}")
        rendering_sources.append(
            {
                "path": relative_path,
                "sha256": digest(source.read_bytes()),
            }
        )

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
        "renderer": {
            "browser": renderer["browser"],
            "browser_revision": renderer["browser_revision"],
            "browser_version": renderer["browser_version"],
            "container_image": renderer["container_image"],
            "generation_command": renderer["generation_command"],
            "playwright_version": renderer["playwright_version"],
            "source_files": rendering_sources,
        },
        "schema_version": "0.2",
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
