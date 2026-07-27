#!/usr/bin/env python3
"""Fail-closed checks for the bilingual static site and Atlas projection."""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import json
import struct
import sys


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"


class SiteParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.local_assets: list[str] = []
        self.errors: list[str] = []
        self.localized = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if identifier := values.get("id"):
            self.ids.append(identifier)
        if "data-en" in values or "data-ru" in values:
            self.localized += 1
            if not values.get("data-en") or not values.get("data-ru"):
                self.errors.append(f"{tag} has incomplete data-en/data-ru copy")
        if tag == "img":
            if not values.get("alt"):
                self.errors.append("img is missing non-empty alt text")
            if not values.get("width") or not values.get("height"):
                self.errors.append("img is missing intrinsic width/height")
        for key in ("src", "href"):
            value = values.get(key)
            if not value or value.startswith(("#", "https://", "mailto:")):
                continue
            if "://" in value:
                self.errors.append(f"unexpected external asset: {value}")
                continue
            self.local_assets.append(value.split("#", 1)[0])


def png_dimensions(path: Path) -> tuple[int, int]:
    payload = path.read_bytes()[:24]
    if payload[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{path} is not a PNG")
    return struct.unpack(">II", payload[16:24])


def main() -> int:
    errors: list[str] = []
    index = SITE / "index.html"
    parser = SiteParser()
    parser.feed(index.read_text(encoding="utf-8"))
    errors.extend(parser.errors)
    if len(parser.ids) != len(set(parser.ids)):
        errors.append("HTML contains duplicate ids")
    if parser.localized < 25:
        errors.append(f"expected substantial bilingual copy, found {parser.localized}")

    for asset in parser.local_assets:
        target = SITE / asset
        if not target.exists():
            errors.append(f"missing local asset: {asset}")

    styles = (SITE / "styles.css").read_text(encoding="utf-8")
    script = (SITE / "app.js").read_text(encoding="utf-8")
    if "prefers-reduced-motion" not in styles:
        errors.append("site lacks reduced-motion handling")
    if "focus-visible" not in styles:
        errors.append("site lacks visible keyboard focus")
    if "localStorage" not in script or "document.documentElement.lang" not in script:
        errors.append("language preference or document language is not maintained")
    if "fallbackAtlas" in script or ".catch(() => renderAtlas())" in script:
        errors.append("site silently falls back when accepted Atlas data is unavailable")
    for view in ("concept", "theory", "quickstart", "atlas", "docs"):
        if f'data-view="{view}"' not in index.read_text(encoding="utf-8"):
            errors.append(f"site misses the {view} destination")
    if "#atlas/" not in script or "atlas-breadcrumbs" not in styles:
        errors.append("Atlas lacks reloadable drill-down paths or breadcrumbs")

    social = SITE / "assets" / "concordloom-social-preview.png"
    if png_dimensions(social) != (1280, 640):
        errors.append("social preview must be exactly 1280x640")
    if social.stat().st_size >= 1_000_000:
        errors.append("social preview must stay below GitHub's 1 MB upload limit")

    atlas = json.loads((SITE / "data" / "atlas.json").read_text(encoding="utf-8"))
    loop_ids = {loop["id"] for loop in atlas["loops"]}
    roots = set(atlas["binding"]["rootLoopIds"])
    if roots != {"steward-concordloom"}:
        errors.append(f"unexpected active Atlas roots: {sorted(roots)}")
    expected_cycles = {
        "product-direction",
        "research-theory",
        "protocol-design",
        "runtime-tooling",
        "trust-assurance",
        "bindings-adapters",
        "knowledge-experience",
        "release-distribution",
        "adoption-feedback",
        "system-evolution",
        "review-comprehension",
        "activate-successor",
    }
    if len(loop_ids) != 55:
        errors.append(f"Atlas must expose all 55 development cycles, found {len(loop_ids)}")
    if not expected_cycles <= loop_ids:
        errors.append("Atlas projection omits required development cycles")
    if atlas.get("evolutionCircuit") != [
        "collect-evolution-signals",
        "propose-successor",
        "review-successor",
        "activate-successor",
        "observe-migration",
    ]:
        errors.append("Atlas does not expose the full evolution circuit")
    if atlas.get("activationBoundary", {}).get("self_activation_allowed") is not False:
        errors.append("Atlas does not expose the non-self-activation boundary")
    for loop in atlas["loops"]:
        if not loop.get("copy", {}).get("en") or not loop.get("copy", {}).get("ru"):
            errors.append(f"Atlas loop {loop['id']} lacks bilingual copy")
        profile = atlas.get("profiles", {}).get(loop.get("profile"))
        if not profile:
            errors.append(f"Atlas loop {loop['id']} lacks an execution profile")
        elif profile.get("mcp", {}).get("status") != "not-declared":
            errors.append(f"Atlas profile {loop['profile']} invents an MCP assignment")
    for edge in atlas["containment"]["edges"]:
        if edge["parent_loop_id"] not in loop_ids or edge["child_loop_id"] not in loop_ids:
            errors.append(f"Atlas edge {edge['id']} references an unknown loop")

    content = json.loads((SITE / "data" / "content.json").read_text(encoding="utf-8"))
    if len(content.get("documents", [])) != 12:
        errors.append("Docs hub must expose all 12 bilingual document pairs")
    for section in ("article", "quickstart"):
        for locale in ("en", "ru"):
            rendered = content.get(section, {}).get(locale, {})
            if not rendered.get("html") or not rendered.get("toc"):
                errors.append(f"missing rendered {locale} {section}")
            ids = [item["id"] for item in rendered.get("toc", [])]
            if len(ids) != len(set(ids)):
                errors.append(f"duplicate stable section id in {locale} {section}")

    if errors:
        for error in errors:
            print(f"SITE_CHECK_ERROR {error}")
        return 1
    print(
        "SITE_CHECK_OK "
        f"localized={parser.localized} loops={len(loop_ids)} assets={len(set(parser.local_assets))}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
