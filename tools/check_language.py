#!/usr/bin/env python3
"""Check the public entry path for known literal-translation failures."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
ENTRY_DOCUMENTS = [
    ROOT / "README.ru.md",
    ROOT / "docs" / "ru" / "QUICKSTART.md",
]
RAW_PROSE_TERMS = [
    "binding",
    "candidate",
    "containment",
    "runtime",
    "self-binding",
    "scope",
    "workflow",
    "successor",
    "digest",
    "registry",
    "manifest",
    "governance",
    "attestations",
    "read-only",
    "checkout",
]


def prose_lines(source: str) -> list[tuple[int, str]]:
    """Return Markdown prose while ignoring code and machine identifiers."""

    result: list[tuple[int, str]] = []
    in_fence = False
    for number, raw_line in enumerate(source.splitlines(), 1):
        if raw_line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        line = re.sub(r"`[^`]*`", "", raw_line)
        line = re.sub(r"https?://\S+", "", line)
        result.append((number, line))
    return result


def main() -> int:
    errors: list[str] = []
    terminology_path = ROOT / "docs" / "terminology.json"
    terminology = json.loads(terminology_path.read_text(encoding="utf-8"))
    concepts = {entry["concept"] for entry in terminology["terms"]}
    required = {
        "loop",
        "loop_system",
        "containment_graph",
        "binding",
        "candidate",
        "authority",
        "successor",
        "activation",
    }
    missing = required - concepts
    if missing:
        errors.append(f"terminology manifest misses {sorted(missing)}")

    for path in ENTRY_DOCUMENTS:
        for number, line in prose_lines(path.read_text(encoding="utf-8")):
            for term in RAW_PROSE_TERMS:
                pattern = rf"(?i)(?<![\w-]){re.escape(term)}(?![\w-])"
                if re.search(pattern, line):
                    errors.append(
                        f"{path.relative_to(ROOT)}:{number}: "
                        f"unexplained English term {term!r}"
                    )

    site_source = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    if "data-ru=" not in site_source:
        errors.append("site has no Russian copy")
    if "активация остаётся" in site_source.casefold():
        errors.append("site still uses the rejected literal activation copy")

    if errors:
        for error in errors:
            print(f"LANGUAGE_CHECK_ERROR {error}")
        return 1
    print(
        "LANGUAGE_CHECK_OK "
        f"entry_docs={len(ENTRY_DOCUMENTS)} terms={len(terminology['terms'])}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
