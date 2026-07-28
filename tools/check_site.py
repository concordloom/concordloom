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
        for suffix in ("content", "aria-label", "alt"):
            en_key = f"data-en-{suffix}"
            ru_key = f"data-ru-{suffix}"
            if en_key in values or ru_key in values:
                self.localized += 1
                if not values.get(en_key) or not values.get(ru_key):
                    self.errors.append(
                        f"{tag} has incomplete {en_key}/{ru_key} copy"
                    )
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
    compact_styles = "".join(styles.split())
    if (
        "grid-template-columns:minmax(190px,1fr)minmax(0,760px)"
        "minmax(190px,1fr)" not in compact_styles
    ):
        errors.append(
            "wide reading layout must balance equal margins around the prose"
        )
    if 'html[lang="en"].heroh1em{margin-top:0.22em;}' not in compact_styles:
        errors.append("English hero lines must clear descenders")
    if (
        ".stage-readout{display:grid;grid-template-rows:3.5remminmax(0,1fr);"
        "gap:1.25rem;height:200px;" not in compact_styles
        or ".stage-readoutp{max-width:26ch;margin:0;" not in compact_styles
    ):
        errors.append("phase readout must keep its code and copy on stable rows")
    if "localStorage" not in script or "document.documentElement.lang" not in script:
        errors.append("language preference or document language is not maintained")
    if '|| "en";' not in script or "navigator.languages" in script:
        errors.append("first visit must default to English without locale inference")
    if 'url.searchParams.set("lang", language)' not in script:
        errors.append("language switch does not persist the locale in the URL")
    for marker in (
        'data-atlas-binding data-en="Loading" data-ru="Загрузка"',
        'data-atlas-root data-en="Loading" data-ru="Загрузка"',
    ):
        if marker not in index.read_text(encoding="utf-8"):
            errors.append(
                "Russian Atlas first paint lacks a localized loading placeholder"
            )
    for marker in (
        'text("identifier")',
        'text("childCount")',
        'text("noChildCount")',
        'aria-hidden="true"',
        'text("loadError")',
    ):
        if marker not in script:
            errors.append(f"dynamic Atlas localization contract is missing {marker}")
    for forbidden in (
        'data-ru="Atlas"',
        "planned / active binding",
        "На этом Evolve",
        'skills: "Скиллы"',
        "<span>${documentData.id}</span>",
    ):
        if forbidden in index.read_text(encoding="utf-8") or forbidden in script:
            errors.append(f"Russian interface contains unresolved copy: {forbidden}")
    for required in (
        "data-ru-aria-label",
        "data-ru-alt",
        "data-ru-content",
        "technical-details",
        "data-product-release",
    ):
        if required not in index.read_text(encoding="utf-8") and required not in script:
            errors.append(f"site misses localized or progressive UI contract: {required}")
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
    if atlas.get("product", {}).get("release") != "0.1.4":
        errors.append("Atlas does not distinguish product release 0.1.4")
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
    if len(loop_ids) != 58:
        errors.append(f"Atlas must expose all 58 development cycles, found {len(loop_ids)}")
    for required_loop_id in (
        "publish-source-change",
        "accept-source-change",
        "maintain-organization-presence",
    ):
        if required_loop_id not in loop_ids:
            errors.append(f"Atlas is missing active cycle {required_loop_id}")
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
        route = loop.get("route_materialization")
        if not isinstance(route, dict) or not {
            "model_provider",
            "model",
            "reasoning",
            "skills",
            "mcp_servers",
            "resources",
            "tool_capabilities",
            "subagent_identities",
        } <= route.keys():
            errors.append(f"Atlas loop {loop['id']} lacks its exact planned route")
        profile = atlas.get("profiles", {}).get(loop.get("profile"))
        if not profile:
            errors.append(f"Atlas loop {loop['id']} lacks an execution profile")
        elif profile.get("mcp", {}).get("status") != "not-declared":
            errors.append(f"Atlas profile {loop['profile']} invents an MCP assignment")
        else:
            route = profile.get("route_materialization")
            required_route_fields = {
                "model_provider",
                "model",
                "reasoning",
                "skills",
                "mcp_servers",
                "resources",
                "tool_capabilities",
                "subagent_identities",
            }
            if not isinstance(route, dict):
                errors.append(
                    f"Atlas profile {loop['profile']} lacks an exact planned route"
                )
            elif not required_route_fields <= route.keys():
                errors.append(
                    f"Atlas profile {loop['profile']} has an incomplete planned route"
                )
    routes = {
        loop["id"]: loop.get("route_materialization", {})
        for loop in atlas["loops"]
    }
    if (
        routes.get("collect-evolution-signals", {}).get("model")
        != "gpt-5.6-luna"
        or routes.get("collect-evolution-signals", {}).get("reasoning")
        != "medium"
    ):
        errors.append("Atlas drops the Luna/medium evolution-signal override")
    if (
        routes.get("decide-product", {}).get("model") != "none"
        or routes.get("decide-product", {}).get("reasoning")
        != "human-decision"
    ):
        errors.append("Atlas drops the operator-only product decision override")
    evolution_skills = routes.get("collect-evolution-signals", {}).get(
        "skills", []
    )
    if {
        "id": "design-project-loops",
        "version": "0.1.0",
    } not in evolution_skills:
        errors.append("Atlas drops the versioned evolution-analysis skill")
    for edge in atlas["containment"]["edges"]:
        if edge["parent_loop_id"] not in loop_ids or edge["child_loop_id"] not in loop_ids:
            errors.append(f"Atlas edge {edge['id']} references an unknown loop")

    offline_atlases = {
        "en": ROOT / "docs" / "ATLAS.html",
        "ru": ROOT / "docs" / "ru" / "ATLAS.html",
    }
    for locale, path in offline_atlases.items():
        if not path.exists():
            errors.append(f"missing checked-in {locale} offline Atlas")
            continue
        source = path.read_text(encoding="utf-8")
        if f'<html lang="{locale}">' not in source:
            errors.append(f"{locale} offline Atlas declares the wrong locale")
        for marker in (
            'aria-live="polite"',
            "Content-Security-Policy",
            "const ATLAS_COPY=",
        ):
            if marker not in source:
                errors.append(f"{locale} offline Atlas misses {marker}")
    russian_offline = offline_atlases["ru"]
    if russian_offline.exists():
        source = russian_offline.read_text(encoding="utf-8")
        for marker in (
            "Перейти к Атласу",
            'aria-label="Путь по циклам"',
            'aria-label="Состояния сведений"',
            'aria-label="Условные обозначения"',
            "Выбран цикл: {label}",
        ):
            if marker not in source:
                errors.append(f"Russian offline Atlas misses localized UI {marker}")
        for unresolved in (
            "No run attached",
            "Selected loop:",
            'aria-label="Map key"',
            ">Containment<",
            ">Local flow<",
        ):
            if unresolved in source:
                errors.append(
                    f"Russian offline Atlas contains unresolved English UI {unresolved}"
                )

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
