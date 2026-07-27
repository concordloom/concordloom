#!/usr/bin/env python3
"""Check English/Russian public-document parity and positioning invariants."""

from __future__ import annotations

from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
CYRILLIC = re.compile(r"[А-Яа-яЁё]")


def public_pairs() -> list[tuple[Path, Path]]:
    pairs = [(ROOT / "README.md", ROOT / "README.ru.md")]
    for english in sorted((ROOT / "docs").glob("*.md")):
        pairs.append((english, ROOT / "docs" / "ru" / english.name))
    for english in sorted((ROOT / "docs" / "research").glob("*.md")):
        pairs.append(
            (
                english,
                ROOT / "docs" / "ru" / "research" / english.name,
            )
        )
    pairs.append(
        (
            ROOT / "examples" / "generic-sdlc" / "README.md",
            ROOT / "examples" / "generic-sdlc" / "README.ru.md",
        )
    )
    references = (
        ROOT
        / "plugins"
        / "concordloom"
        / "skills"
        / "design-project-loops"
        / "references"
    )
    for english in sorted(references.glob("*.md")):
        if english.name.endswith(".ru.md"):
            continue
        pairs.append((english, english.with_name(f"{english.stem}.ru.md")))
    return pairs


def main() -> int:
    errors: list[str] = []
    pairs = public_pairs()
    for english, russian in pairs:
        label = str(english.relative_to(ROOT))
        if not english.exists():
            errors.append(f"missing English source {label}")
            continue
        if not russian.exists():
            errors.append(f"missing Russian peer for {label}")
            continue
        en_text = english.read_text(encoding="utf-8")
        ru_text = russian.read_text(encoding="utf-8")
        if not en_text.endswith("\n") or not ru_text.endswith("\n"):
            errors.append(f"document pair is not newline-terminated: {label}")
        if "# " not in en_text or "# " not in ru_text:
            errors.append(f"document pair lacks an H1: {label}")
        if len(ru_text.strip()) < 120 or not CYRILLIC.search(ru_text):
            errors.append(f"Russian peer is not substantial: {label}")
        ratio = len(ru_text) / max(len(en_text), 1)
        if not 0.45 <= ratio <= 1.8:
            errors.append(f"document pair length drift {ratio:.2f}: {label}")

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    article = (ROOT / "docs" / "ARTICLE.md").read_text(encoding="utf-8")
    if "docs/assets/concordloom-hero.webp" not in readme:
        errors.append("README does not render the authored hero image")
    if "This is not an SDLC framework" not in readme:
        errors.append("README does not state the domain-neutral product boundary")
    if "Governed Software Delivery Systems" in article.splitlines()[0]:
        errors.append("article title still presents software delivery as product identity")

    if errors:
        for error in errors:
            print(f"DOCS_CHECK_ERROR {error}")
        return 1
    print(f"DOCS_CHECK_OK pairs={len(pairs)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
