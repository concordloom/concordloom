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
    ROOT / "docs" / "ru" / "ATLAS.md",
]
PUBLIC_RUSSIAN_DOCUMENTS = sorted((ROOT / "docs" / "ru").rglob("*.md"))
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
        "runner",
        "run_card",
        "digest",
        "registry",
        "policy",
        "scope",
        "runtime",
        "workflow",
        "skill",
        "observe_phase",
        "negotiate_phase",
        "bind_phase",
        "execute_phase",
        "verify_phase",
        "publish_phase",
        "evolve_phase",
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

    for path in PUBLIC_RUSSIAN_DOCUMENTS:
        for number, line in prose_lines(path.read_text(encoding="utf-8")):
            if re.search(r"(?<![\w-])Atlas(?![\w-])", line):
                errors.append(
                    f"{path.relative_to(ROOT)}:{number}: "
                    "English product-view name 'Atlas' in Russian prose"
                )
            if re.search(r"(?<![\w-])concord-change(?![\w-])", line):
                errors.append(
                    f"{path.relative_to(ROOT)}:{number}: "
                    "obsolete seven-loop self-binding described as current"
                )

    atlas_data = json.loads(
        (ROOT / "site" / "data" / "atlas.json").read_text(encoding="utf-8")
    )
    active_binding_id = atlas_data["binding"]["id"]
    revision_match = re.search(r"-v([0-9]+)$", active_binding_id)
    if revision_match is None:
        errors.append(
            f"cannot derive rules revision from active binding {active_binding_id!r}"
        )
    else:
        revision = revision_match.group(1)
        version_markers = {
            ROOT / "docs" / "QUICKSTART.md": f"Development rules: revision {revision}",
            ROOT / "docs" / "ATLAS.md": f"Development rules: revision {revision}",
            ROOT / "docs" / "ru" / "QUICKSTART.md": (
                f"Правила разработки: редакция {revision}"
            ),
            ROOT / "docs" / "ru" / "ATLAS.md": (
                f"Правила разработки: редакция {revision}"
            ),
        }
        for path, marker in version_markers.items():
            if marker not in path.read_text(encoding="utf-8"):
                errors.append(
                    f"{path.relative_to(ROOT)} misses active rules marker {marker!r}"
                )

    site_source = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    site_script = (ROOT / "site" / "app.js").read_text(encoding="utf-8")
    content_data = json.loads(
        (ROOT / "site" / "data" / "content.json").read_text(encoding="utf-8")
    )
    if "data-ru=" not in site_source:
        errors.append("site has no Russian copy")
    if "активация остаётся" in site_source.casefold():
        errors.append("site still uses the rejected literal activation copy")
    for rejected in (
        'data-ru="Atlas"',
        "На этом Evolve",
        "planned / active binding",
        'skills: "Скиллы"',
    ):
        if rejected in site_source or rejected in site_script:
            errors.append(f"site still exposes mixed-language copy {rejected!r}")
    for required in (
        'data-atlas-binding data-en="Loading…" data-ru="Загрузка…"',
        'data-atlas-root data-en="Loading…" data-ru="Загрузка…"',
        'identifier: "Идентификатор"',
        'childCount: "Вложенных циклов"',
    ):
        if required not in site_source and required not in site_script:
            errors.append(f"site misses Russian dynamic copy {required!r}")
    for section in ("article", "quickstart"):
        russian_html = content_data[section]["ru"]["html"]
        visible_russian = re.sub(r"<[^>]+>", " ", russian_html)
        if re.search(r"(?<![\w-])Atlas(?![\w-])", visible_russian):
            errors.append(
                f"generated Russian {section} still exposes English 'Atlas'"
            )
        if re.search(r"(?<![\w-])concord-change(?![\w-])", visible_russian):
            errors.append(
                f"generated Russian {section} describes the obsolete root as current"
            )

    offline_russian_path = ROOT / "docs" / "ru" / "ATLAS.html"
    if not offline_russian_path.exists():
        errors.append("generated Russian offline Atlas is missing")
    else:
        offline_russian = offline_russian_path.read_text(encoding="utf-8")
        for required in (
            '<html lang="ru">',
            "Перейти к Атласу",
            'aria-label="Путь по циклам"',
            "Выбран цикл: {label}",
        ):
            if required not in offline_russian:
                errors.append(
                    f"generated Russian offline Atlas misses {required!r}"
                )
        for rejected in (
            "No run attached",
            "Selected loop:",
            'aria-label="Map key"',
            ">Containment<",
            ">Local flow<",
        ):
            if rejected in offline_russian:
                errors.append(
                    f"generated Russian offline Atlas exposes {rejected!r}"
                )

    if errors:
        for error in errors:
            print(f"LANGUAGE_CHECK_ERROR {error}")
        return 1
    print(
        "LANGUAGE_CHECK_OK "
        f"entry_docs={len(ENTRY_DOCUMENTS)} "
        f"public_ru_docs={len(PUBLIC_RUSSIAN_DOCUMENTS)} "
        f"terms={len(terminology['terms'])}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
