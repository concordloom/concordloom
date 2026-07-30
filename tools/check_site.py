#!/usr/bin/env python3
"""Fail-closed checks for the bilingual static site and Atlas projection."""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import hashlib
import json
import re
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
            if "alt" not in values:
                self.errors.append("img is missing alt text")
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


def has_raw_font_stack(authored_css: str) -> bool:
    return any(
        "var(--" not in match.group(1)
        for match in re.finditer(r"font-family:\s*([^;]+)", authored_css)
    )


def has_forbidden_patch_panel_background(authored_css: str) -> bool:
    return (
        "linear-gradient(" in authored_css
        or "radial-gradient(" in authored_css
        or re.search(
            r"background(?:-image)?\s*:[^;{}]*url\(",
            authored_css,
            flags=re.IGNORECASE,
        )
        is not None
    )


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
    token_styles = (SITE / "design-tokens.css").read_text(encoding="utf-8")
    design_styles = (SITE / "design-system.css").read_text(encoding="utf-8")
    all_styles = styles + "\n" + token_styles + "\n" + design_styles
    script = (SITE / "app.js").read_text(encoding="utf-8")
    if "prefers-reduced-motion" not in all_styles:
        errors.append("site lacks reduced-motion handling")
    if "focus-visible" not in all_styles:
        errors.append("site lacks visible keyboard focus")
    if "localStorage" not in script or "document.documentElement.lang" not in script:
        errors.append("language preference or document language is not maintained")
    if '|| "en";' not in script or "navigator.languages" in script:
        errors.append("first visit must default to English without locale inference")
    if 'url.searchParams.set("lang", language)' not in script:
        errors.append("language switch does not persist the locale in the URL")
    for marker in (
        'data-atlas-binding data-en="Loading…" data-ru="Загрузка…"',
        'data-atlas-root data-en="Loading…" data-ru="Загрузка…"',
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
        if f'id="{view}" data-view="{view}"' not in index.read_text(encoding="utf-8"):
            errors.append(f"site lacks a no-JS target for {view}")
    for marker in (
        "<noscript>",
        "<!-- GENERATED:article:start -->",
        "<!-- GENERATED:quickstart:start -->",
        ".view:target",
    ):
        if marker not in index.read_text(encoding="utf-8") + design_styles:
            errors.append(f"site lacks no-JS reading contract: {marker}")
    for section in ("article", "quickstart"):
        block = re.search(
            rf"<!-- GENERATED:{section}:start -->(.*?)"
            rf"<!-- GENERATED:{section}:end -->",
            index.read_text(encoding="utf-8"),
            flags=re.DOTALL,
        )
        if not block or len(block.group(1).strip()) < 4_000:
            errors.append(f"site lacks substantial static {section} content")
    if "#atlas/" not in script or "atlas-breadcrumbs" not in styles:
        errors.append("Atlas lacks reloadable drill-down paths or breadcrumbs")
    for marker in (
        'href="design-system.css"',
        'href="design-tokens.css"',
        'data-design-system="patch-panel"',
        'class="system-rail"',
        'class="atlas-commandbar"',
        "data-atlas-graph",
        "data-atlas-history",
        'class="atlas-inspector"',
    ):
        if marker not in index.read_text(encoding="utf-8"):
            errors.append(f"Patch Panel surface is missing {marker}")
    for marker in (
        "--cl-navy-1000",
        "--cl-mint-500",
        "--cl-font-display",
        "--cl-font-mono",
        "--cl-type-title",
        "--cl-leading-reading",
        "--cl-measure-reading",
        "--surface-page",
        "--surface-panel",
        "--surface-module",
        "--surface-void",
        "--type-display",
        "--panel-background",
        "--atlas-node-active",
        "--reading-measure",
        "--cl-duration-level",
        ".atlas-graph",
        ".atlas-history",
        ".atlas-inspector",
        '.atlas-stage[data-motion="forward"]',
        '.atlas-stage[data-motion="back"]',
        "prefers-reduced-motion",
    ):
        if marker not in token_styles + design_styles:
            errors.append(f"design system is missing {marker}")
    if not token_styles.startswith(
        "/* Generated from design-tokens.json. Do not edit. */"
    ):
        errors.append("design token CSS is not a declared generated projection")
    for marker in ("--cl-black-1000:", "--cl-font-display:", "--control-min-size:"):
        if marker in design_styles:
            errors.append(f"component CSS redefines canonical token {marker}")
    authored_css = styles + "\n" + design_styles
    if re.search(r"#[0-9a-fA-F]{3,8}\b|rgba?\(", authored_css):
        errors.append("authored CSS contains a raw color outside design-tokens.json")
    if has_raw_font_stack(authored_css):
        errors.append("authored CSS contains a raw font stack outside design tokens")
    token_source = json.loads(
        (SITE / "design-tokens.json").read_text(encoding="utf-8")
    )
    if tuple(token_source.get("layers", {})) != (
        "primitive",
        "semantic",
        "component",
        "compatibility",
    ):
        errors.append("design token source lacks the four-level authority chain")
    if set(token_source.get("modes", {})) != {"compact", "high-contrast"}:
        errors.append("design token source lacks compact and high-contrast modes")
    if token_source.get("version") != "3.0.0":
        errors.append("Patch Panel requires design-token contract 3.0.0")
    if has_forbidden_patch_panel_background(authored_css):
        errors.append("Patch Panel authored CSS contains forbidden background art or gradient")
    if 'window.addEventListener("scroll"' in script:
        errors.append("site must not run continuous JavaScript on scroll")
    if "offsetWidth" in script or "getBoundingClientRect" in script:
        errors.append("site must not force synchronous layout reads")
    if "IntersectionObserver" not in script:
        errors.append("site reveal effects must use IntersectionObserver")
    for marker in (
        "font-variant-numeric: tabular-nums",
        "touch-action: manipulation",
        "env(safe-area-inset-top)",
        "text-wrap: balance",
    ):
        if marker not in all_styles:
            errors.append(f"web-interface contract is missing {marker}")
    catalog = json.loads(
        (ROOT / "framework" / "concordloom" / "catalog.json").read_text(
            encoding="utf-8"
        )
    )
    active_entry = next(
        (
            entry
            for entry in catalog["entries"]
            if entry["binding_digest"] == catalog["active_binding_digest"]
        ),
        None,
    )
    if active_entry is None:
        errors.append("active binding digest has no catalog entry")
        active_entry = catalog["entries"][-1]
    active_binding = json.loads(
        (ROOT / active_entry["path"]).read_text(encoding="utf-8")
    )
    registry_artifact = next(
        artifact
        for artifact in active_binding["artifacts"]
        if artifact["role"] == "cycle_registry"
    )
    active_registry = json.loads(
        (ROOT / registry_artifact["path"]).read_text(encoding="utf-8")
    )
    frontend_cycle_ids = {
        edge["child_loop_id"]
        for edge in active_registry["containment_graph"]["edges"]
        if edge["parent_loop_id"] == "design-site-experience"
    }
    design_contracts = {
        "en": (ROOT / "docs" / "DESIGN_SYSTEM.md").read_text(encoding="utf-8"),
        "ru": (ROOT / "docs" / "ru" / "DESIGN_SYSTEM.md").read_text(
            encoding="utf-8"
        ),
    }
    for locale, design_contract in design_contracts.items():
        for loop_id in {"design-site-experience", *frontend_cycle_ids}:
            if design_contract.count(f"`{loop_id}`") != 1:
                errors.append(
                    "design-system cycle ownership must appear exactly once "
                    f"in {locale} for {loop_id}"
                )

    social = SITE / "assets" / "concordloom-social-preview.png"
    if png_dimensions(social) != (1280, 640):
        errors.append("social preview must be exactly 1280x640")
    if social.stat().st_size >= 1_000_000:
        errors.append("social preview must stay below GitHub's 1 MB upload limit")
    visual_contract = json.loads(
        (ROOT / "design" / "frontend" / "visual-contract.json").read_text(
            encoding="utf-8"
        )
    )
    if (
        visual_contract.get("id") != "patch-panel-v1"
        or visual_contract.get("status") != "accepted"
        or visual_contract.get("reference", {}).get("variant") != 4
    ):
        errors.append("Patch Panel visual contract is not the accepted variant 4")
    for reference in visual_contract.get("reference", {}).get("files", []):
        reference_path = ROOT / reference["path"]
        if not reference_path.is_file():
            errors.append(f"missing Patch Panel reference: {reference['path']}")
            continue
        if hashlib.sha256(reference_path.read_bytes()).hexdigest() != reference["sha256"]:
            errors.append(f"Patch Panel reference bytes changed: {reference['path']}")

    atlas = json.loads((SITE / "data" / "atlas.json").read_text(encoding="utf-8"))
    loop_ids = {loop["id"] for loop in atlas["loops"]}
    roots = set(atlas["binding"]["rootLoopIds"])
    if atlas.get("product", {}).get("release") != "0.1.5":
        errors.append("Atlas does not distinguish product release 0.1.5")
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
    expected_loop_count = len(active_registry["loops"])
    if len(loop_ids) != expected_loop_count:
        errors.append(
            "Atlas must expose every active development cycle: "
            f"expected {expected_loop_count}, found {len(loop_ids)}"
        )
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
        elif profile.get("mcp", {}).get("status") not in {
            "not-declared",
            "not-required",
            "not-used-as-oracle",
            "optional-adapter",
        }:
            errors.append(
                f"Atlas profile {loop['profile']} has an unsupported MCP status"
            )
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
            elif route["mcp_servers"]:
                errors.append(
                    f"Atlas profile {loop['profile']} invents an MCP assignment"
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
    if len(content.get("documents", [])) != 13:
        errors.append("Docs hub must expose all 13 bilingual document pairs")
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
