#!/usr/bin/env python3
"""Build deterministic GitHub Pages data from the active accepted binding."""

from __future__ import annotations

import argparse
import html
from pathlib import Path
import re
import shutil
import sys
import tomllib

from concordloom.canonical import canonical_bytes, load, save


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
TRANSITION_CATALOG = ROOT / "docs" / ".concord-transition" / "catalog.json"
PUBLIC_CATALOG = ROOT / "framework" / "concordloom" / "catalog.json"
CONTENT_SOURCES = {
    "article": {
        "en": ROOT / "docs" / "ARTICLE.md",
        "ru": ROOT / "docs" / "ru" / "ARTICLE.md",
    },
    "quickstart": {
        "en": ROOT / "docs" / "QUICKSTART.md",
        "ru": ROOT / "docs" / "ru" / "QUICKSTART.md",
    },
}
PUBLIC_DOCS = [
    ("CONCEPTS", "Foundations", "Основания"),
    ("ARCHITECTURE", "Architecture", "Архитектура"),
    ("SPEC_V0.1", "Specification", "Спецификация"),
    ("TRUST_MODEL", "Trust model", "Модель доверия"),
    ("QUICKSTART", "Quickstart", "Быстрый старт"),
    ("ARTICLE", "Theory paper", "Теоретическая статья"),
    ("ATLAS", "Atlas", "Атлас"),
    ("CODEX_PLUGIN", "Codex plugin", "Плагин Codex"),
    ("DECISIONS", "Decisions", "Решения"),
    ("RELEASE", "Release", "Релиз"),
    ("WRITING", "Writing for humans", "Как писать для людей"),
    ("DESIGN_SYSTEM", "Design system", "Дизайн-система"),
    (
        "FRONTEND_CYCLE_PROPOSAL",
        "Frontend cycle proposal",
        "Предложение по фронтенд-циклу",
    ),
]
TOKEN_SOURCE = SITE / "design-tokens.json"
TOKEN_OUTPUT = SITE / "design-tokens.css"
INDEX = SITE / "index.html"
SITE_BASE_URL = "https://concordloom.github.io/concordloom"
LOCALIZED_INDEXES = {
    "en": SITE / "en" / "index.html",
    "ru": SITE / "ru" / "index.html",
}
ROBOTS = SITE / "robots.txt"
SITEMAP = SITE / "sitemap.xml"
TOKEN_LAYERS = ("primitive", "semantic", "component", "compatibility")


def design_tokens_css() -> bytes:
    document = load(TOKEN_SOURCE)
    if document.get("kind") != "concordloom.design-tokens":
        raise ValueError("design token source has the wrong kind")
    layers = document.get("layers")
    if not isinstance(layers, dict) or tuple(layers) != TOKEN_LAYERS:
        raise ValueError("design token layers must be ordered primitive to compatibility")
    names: set[str] = set()
    lines = ["/* Generated from design-tokens.json. Do not edit. */", ":root {"]
    for layer in TOKEN_LAYERS:
        tokens = layers[layer]
        if not isinstance(tokens, dict) or not tokens:
            raise ValueError(f"design token layer {layer} must not be empty")
        lines.append(f"  /* {layer} */")
        for name, value in tokens.items():
            if not re.fullmatch(r"[a-z][a-z0-9-]*", name):
                raise ValueError(f"invalid design token name: {name}")
            if name in names:
                raise ValueError(f"duplicate design token name: {name}")
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"design token {name} has no value")
            names.add(name)
            lines.append(f"  --{name}: {value};")
    lines.append("}")
    modes = document.get("modes")
    if not isinstance(modes, dict) or not modes:
        raise ValueError("design tokens must declare responsive or preference modes")
    for mode, definition in modes.items():
        query = definition.get("query")
        overrides = definition.get("tokens")
        if not isinstance(query, str) or not isinstance(overrides, dict):
            raise ValueError(f"invalid design token mode: {mode}")
        lines.extend([f"@media {query} {{", "  :root {"])
        for name, value in overrides.items():
            if name not in names:
                raise ValueError(f"design token mode {mode} overrides unknown {name}")
            lines.append(f"    --{name}: {value};")
        lines.extend(["  }", "}"])
    lines.append("")
    payload = "\n".join(lines).encode("utf-8")
    for reference in re.findall(rb"var\\(--([a-z][a-z0-9-]*)\\)", payload):
        name = reference.decode("ascii")
        if name not in names:
            raise ValueError(f"design token references unknown token: {name}")
    return payload


def slugify(value: str) -> str:
    slug = re.sub(r"[^\w]+", "-", value.casefold(), flags=re.UNICODE).strip("-")
    return slug or "section"


def inline_markup(value: str, source_path: Path | None = None) -> str:
    parts = re.split(r"(`[^`]+`)", value)
    rendered: list[str] = []
    for part in parts:
        if part.startswith("`") and part.endswith("`"):
            rendered.append(f"<code>{html.escape(part[1:-1])}</code>")
            continue
        escaped = html.escape(part)
        def render_link(match: re.Match[str]) -> str:
            label, target = match.groups()
            if target.startswith(("https://", "http://")):
                return f'<a href="{target}" rel="noreferrer">{label}</a>'
            if target.startswith("#"):
                return f'<a href="{target}">{label}</a>'
            if source_path is None:
                return label
            resolved = (source_path.parent / target).resolve()
            try:
                relative = resolved.relative_to(ROOT)
            except ValueError:
                return label
            href = (
                "https://github.com/concordloom/concordloom/blob/main/"
                + html.escape(relative.as_posix(), quote=True)
            )
            return f'<a href="{href}" rel="noreferrer">{label}</a>'

        escaped = re.sub(
            r"\[([^\]]+)\]\(([^)\s]+)\)",
            render_link,
            escaped,
        )
        escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
        escaped = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", escaped)
        rendered.append(escaped)
    return "".join(rendered)


def markdown_fragment(
    source: str,
    *,
    source_path: Path | None = None,
    anchor_prefix: str = "",
) -> tuple[str, list[dict[str, str]]]:
    # Keep author-approved typography intact. In particular, Russian prose
    # uses the em dash as punctuation; replacing it with a hyphen makes the
    # generated public copy both incorrect and harder to read.
    lines = source.splitlines()
    output: list[str] = []
    toc: list[dict[str, str]] = []
    paragraph: list[str] = []
    list_kind = ""
    index = 0
    section_index = 0
    detail_index = 0

    def render_inline(value: str) -> str:
        return inline_markup(value, source_path)

    def flush_paragraph() -> None:
        if paragraph:
            output.append(f"<p>{render_inline(' '.join(paragraph))}</p>")
            paragraph.clear()

    def close_list() -> None:
        nonlocal list_kind
        if list_kind:
            output.append(f"</{list_kind}>")
            list_kind = ""

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if stripped.startswith("```"):
            flush_paragraph()
            close_list()
            language = stripped[3:].strip()
            code: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code.append(lines[index])
                index += 1
            class_name = (
                f' class="language-{html.escape(language)}"' if language else ""
            )
            output.append(
                f'<pre tabindex="0"><code{class_name}>{html.escape(chr(10).join(code))}</code></pre>'
            )
        elif not stripped:
            flush_paragraph()
            close_list()
        elif match := re.match(r"^(#{1,4})\s+(.+)$", stripped):
            flush_paragraph()
            close_list()
            level = len(match.group(1))
            title = match.group(2).strip()
            if level == 1:
                anchor = "document-title"
            elif level == 2:
                section_index += 1
                detail_index = 0
                anchor = f"section-{section_index:02d}"
            else:
                detail_index += 1
                anchor = f"section-{section_index:02d}-detail-{detail_index:02d}"
            anchor = f"{anchor_prefix}{anchor}"
            if level <= 2:
                toc.append({"id": anchor, "title": re.sub(r"[*`]", "", title)})
            output.append(
                f'<h{level} id="{html.escape(anchor)}">{render_inline(title)}</h{level}>'
            )
        elif (
            stripped.startswith("|")
            and index + 1 < len(lines)
            and re.match(r"^\|?[\s:|-]+\|?$", lines[index + 1].strip())
        ):
            flush_paragraph()
            close_list()
            rows: list[list[str]] = []
            rows.append([cell.strip() for cell in stripped.strip("|").split("|")])
            index += 2
            while index < len(lines) and lines[index].strip().startswith("|"):
                rows.append(
                    [cell.strip() for cell in lines[index].strip().strip("|").split("|")]
                )
                index += 1
            index -= 1
            output.append("<div class=\"content-table-wrap\"><table>")
            output.append(
                "<thead><tr>"
                + "".join(f"<th>{render_inline(cell)}</th>" for cell in rows[0])
                + "</tr></thead><tbody>"
            )
            for row in rows[1:]:
                output.append(
                    "<tr>"
                    + "".join(f"<td>{render_inline(cell)}</td>" for cell in row)
                    + "</tr>"
                )
            output.append("</tbody></table></div>")
        elif match := re.match(r"^([-*]|\d+\.)\s+(.+)$", stripped):
            flush_paragraph()
            kind = "ol" if match.group(1)[0].isdigit() else "ul"
            if list_kind != kind:
                close_list()
                output.append(f"<{kind}>")
                list_kind = kind
            output.append(f"<li>{render_inline(match.group(2))}</li>")
        elif stripped.startswith(">"):
            flush_paragraph()
            close_list()
            quote: list[str] = []
            while index < len(lines) and lines[index].strip().startswith(">"):
                quote.append(lines[index].strip().lstrip(">").strip())
                index += 1
            index -= 1
            output.append(
                f"<blockquote>{render_inline(' '.join(quote))}</blockquote>"
            )
        elif re.match(r"^[-*_]{3,}$", stripped):
            flush_paragraph()
            close_list()
            output.append("<hr>")
        else:
            close_list()
            paragraph.append(stripped)
        index += 1

    flush_paragraph()
    close_list()
    return "\n".join(output), toc


def site_content() -> dict:
    sections: dict[str, dict] = {}
    for section, languages in CONTENT_SOURCES.items():
        sections[section] = {}
        for language, path in languages.items():
            fragment, toc = markdown_fragment(
                path.read_text(encoding="utf-8"),
                source_path=path,
                anchor_prefix=f"{section}-",
            )
            sections[section][language] = {"html": fragment, "toc": toc}

    documents = []
    for stem, en_title, ru_title in PUBLIC_DOCS:
        documents.append(
            {
                "id": stem.casefold().replace("_", "-"),
                "enTitle": en_title,
                "ruTitle": ru_title,
                "enUrl": (
                    f"https://github.com/concordloom/concordloom/blob/main/docs/{stem}.md"
                ),
                "ruUrl": (
                    "https://github.com/concordloom/concordloom/blob/main/"
                    f"docs/ru/{stem}.md"
                ),
            }
        )
    documents.append(
        {
            "id": "research-landscape",
            "enTitle": "Observed landscape",
            "ruTitle": "Обзор ландшафта",
            "enUrl": (
                "https://github.com/concordloom/concordloom/blob/main/"
                "docs/research/OBSERVED_LANDSCAPE.md"
            ),
            "ruUrl": (
                "https://github.com/concordloom/concordloom/blob/main/"
                "docs/ru/research/OBSERVED_LANDSCAPE.md"
            ),
        }
    )
    sections["documents"] = documents
    return sections


def index_with_static_reading(content: dict) -> bytes:
    """Project default-English reading content into the no-JS HTML shell."""

    source = INDEX.read_text(encoding="utf-8")
    for section in ("article", "quickstart"):
        start = f"<!-- GENERATED:{section}:start -->"
        end = f"<!-- GENERATED:{section}:end -->"
        pattern = re.compile(
            rf"{re.escape(start)}.*?{re.escape(end)}",
            flags=re.DOTALL,
        )
        replacement = (
            f"{start}\n"
            f"{content[section]['en']['html']}\n"
            f"            {end}"
        )
        source, count = pattern.subn(replacement, source, count=1)
        if count != 1:
            raise ValueError(f"site index lacks one generated {section} block")
    return source.encode("utf-8")


def localized_index(content: dict, language: str) -> bytes:
    """Build one crawlable language URL without relying on JavaScript."""

    if language not in {"en", "ru"}:
        raise ValueError(f"unsupported site locale: {language}")
    copy = {
        "en": {
            "title": "Concord Loom — governed systems of development loops",
            "description": (
                "Discover, negotiate, execute, verify, and evolve bounded systems "
                "of development loops with explicit human authority."
            ),
            "label": "ENGLISH DOCUMENTATION",
            "intro": (
                "Concord Loom maps how work is accepted, executed, verified, and "
                "allowed to change. Start with the practical guide, then read the "
                "complete argument."
            ),
            "quickstart": "Quickstart",
            "article": "Cycles of Cycles",
            "interactive": "Open the interactive site",
            "alternate": "Русская версия",
        },
        "ru": {
            "title": "Concord Loom — управляемые системы циклов разработки",
            "description": (
                "Исследуйте, согласуйте, выполняйте, проверяйте и развивайте "
                "ограниченные системы циклов с явными решениями человека."
            ),
            "label": "РУССКАЯ ДОКУМЕНТАЦИЯ",
            "intro": (
                "Concord Loom показывает, как работа принимается, выполняется, "
                "проверяется и получает право на изменение. Начните с практического "
                "руководства, затем прочитайте полное обоснование."
            ),
            "quickstart": "Быстрый старт",
            "article": "Циклы циклов",
            "interactive": "Открыть интерактивный сайт",
            "alternate": "English version",
        },
    }[language]
    canonical = f"{SITE_BASE_URL}/{language}/"
    alternate_language = "ru" if language == "en" else "en"
    document = f"""<!doctype html>
<html lang="{language}" style="color-scheme: light" data-design-system="signal-canvas">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="theme-color" content="#f3f0e8">
    <meta name="description" content="{html.escape(copy['description'], quote=True)}">
    <link rel="canonical" href="{canonical}">
    <link rel="alternate" hreflang="en" href="{SITE_BASE_URL}/en/">
    <link rel="alternate" hreflang="ru" href="{SITE_BASE_URL}/ru/">
    <link rel="alternate" hreflang="x-default" href="{SITE_BASE_URL}/">
    <meta property="og:title" content="{html.escape(copy['title'], quote=True)}">
    <meta property="og:description" content="{html.escape(copy['description'], quote=True)}">
    <meta property="og:image" content="{SITE_BASE_URL}/assets/concordloom-social-preview.png">
    <meta property="og:url" content="{canonical}">
    <meta property="og:type" content="website">
    <meta property="og:locale" content="{'en_US' if language == 'en' else 'ru_RU'}">
    <title>{html.escape(copy['title'])}</title>
    <link rel="icon" type="image/png" sizes="32x32" href="../assets/favicon-32.png">
    <link rel="stylesheet" href="../design-tokens.css">
    <link rel="stylesheet" href="../design-system.css">
    <link rel="stylesheet" href="../styles.css">
  </head>
  <body data-design-system="signal-canvas">
    <a class="skip-link" href="#main">{'Skip to content' if language == 'en' else 'Перейти к содержанию'}</a>
    <header class="site-header">
      <a class="brand" href="../?lang={language}" aria-label="Concord Loom">
        <img src="../assets/concordloom-mark.png" width="48" height="48" alt="">
        <span>CONCORD LOOM</span>
      </a>
      <nav class="view-tabs" aria-label="{'Language versions' if language == 'en' else 'Языковые версии'}">
        <a class="view-tab" href="../{alternate_language}/">{html.escape(copy['alternate'])}</a>
        <a class="view-tab is-active" href="../?lang={language}">{html.escape(copy['interactive'])}</a>
      </nav>
    </header>
    <main id="main" class="view is-active">
      <section class="content-hero">
        <p class="kicker">{html.escape(copy['label'])}</p>
        <h1>{html.escape(copy['title'])}</h1>
        <p>{html.escape(copy['intro'])}</p>
      </section>
      <section class="reading-layout">
        <article class="reading-copy">
          <h2>{html.escape(copy['quickstart'])}</h2>
          {content['quickstart'][language]['html']}
          <h2>{html.escape(copy['article'])}</h2>
          {content['article'][language]['html']}
        </article>
      </section>
    </main>
  </body>
</html>
"""
    return document.encode("utf-8")


def robots_txt() -> bytes:
    return (
        "User-agent: *\n"
        "Allow: /\n"
        f"Sitemap: {SITE_BASE_URL}/sitemap.xml\n"
    ).encode("utf-8")


def sitemap_xml() -> bytes:
    urls = (f"{SITE_BASE_URL}/", f"{SITE_BASE_URL}/en/", f"{SITE_BASE_URL}/ru/")
    entries = "\n".join(f"  <url><loc>{url}</loc></url>" for url in urls)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{entries}\n"
        "</urlset>\n"
    ).encode("utf-8")


def active_documents() -> tuple[dict, dict, dict]:
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
    model_path = next(
        artifact["path"]
        for artifact in binding["artifacts"]
        if artifact["role"] == "atlas_input"
    )
    return binding, load(ROOT / registry_path), load(ROOT / model_path)


def atlas_projection(binding: dict, registry: dict, model: dict) -> dict:
    contracts = {
        contract["id"]: contract for contract in registry["evidence_contracts"]
    }
    registry_loops = {loop["id"]: loop for loop in registry["loops"]}
    child_scopes = {
        edge["child_loop_id"]: edge["grant"]["scope"]
        for edge in registry["containment_graph"]["edges"]
    }
    loops = []
    for node in model["nodes"]:
        loop = registry_loops[node["id"]]
        contract_id = f"{loop['id']}-acceptance"
        contract = contracts[contract_id]
        loops.append(
            {
                "id": loop["id"],
                "parentId": node["parent_id"],
                "children": node["children"],
                "copy": node["copy"],
                "role": node["responsible_role"],
                "profile": node["execution_profile"],
                "route_materialization": node.get(
                    "route_materialization",
                    model["profiles"][node["execution_profile"]][
                        "route_materialization"
                    ],
                ),
                "contract": node["contract"],
                "artifacts": node["artifacts"],
                "acceptedResults": contract["accepted_results"],
                "requiredClaims": contract["required_claims"],
                "independentReview": "reviewer_capability" in contract,
                "prospectiveEffects": {
                    "network": (
                        "none"
                        if node["children"]
                        else child_scopes.get(loop["id"], {}).get("network", "none")
                    ),
                    "externalMutations": (
                        []
                        if node["children"]
                        else child_scopes.get(loop["id"], {}).get(
                            "external_mutations", []
                        )
                    ),
                },
            }
        )
    package = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return {
        "kind": "concordloom.atlas-projection",
        "schemaVersion": "0.2",
        "product": {
            "name": "Concord Loom",
            "release": package["project"]["version"],
        },
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
        "profiles": model["profiles"],
        "sharedRunGrammar": model["shared_run_grammar"],
        "evolutionCircuit": model["evolution_circuit"],
        "activationBoundary": model["activation_boundary"],
        "resourceSemantics": model["resource_semantics"],
    }


def check_bytes(path: Path, expected: bytes) -> bool:
    return path.exists() and path.read_bytes() == expected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    binding, registry, model = active_documents()
    projection = atlas_projection(binding, registry, model)
    output = SITE / "data" / "atlas.json"
    expected = canonical_bytes(projection) + b"\n"
    content_output = SITE / "data" / "content.json"
    content = site_content()
    expected_content = canonical_bytes(content) + b"\n"
    expected_index = index_with_static_reading(content)
    expected_localized_indexes = {
        language: localized_index(content, language)
        for language in LOCALIZED_INDEXES
    }
    expected_robots = robots_txt()
    expected_sitemap = sitemap_xml()
    expected_tokens = design_tokens_css()
    assets = {
        ROOT / "docs" / "assets" / "concordloom-hero.webp": (
            SITE / "assets" / "concordloom-hero.webp"
        ),
        ROOT / "docs" / "assets" / "concordloom-social-preview.png": (
            SITE / "assets" / "concordloom-social-preview.png"
        ),
        ROOT / "docs" / "assets" / "signal-constellation-stage.png": (
            SITE / "assets" / "signal-constellation-stage.png"
        ),
        ROOT / "docs" / "assets" / "concordloom-mark.png": (
            SITE / "assets" / "concordloom-mark.png"
        ),
        ROOT / "docs" / "assets" / "concordloom-mark-512.png": (
            SITE / "assets" / "concordloom-mark-512.png"
        ),
        ROOT / "docs" / "assets" / "concordloom-mark-192.png": (
            SITE / "assets" / "concordloom-mark-192.png"
        ),
        ROOT / "docs" / "assets" / "favicon-32.png": (
            SITE / "assets" / "favicon-32.png"
        ),
    }

    if args.check:
        stale = []
        if not check_bytes(output, expected):
            stale.append(str(output.relative_to(ROOT)))
        if not check_bytes(content_output, expected_content):
            stale.append(str(content_output.relative_to(ROOT)))
        if not check_bytes(TOKEN_OUTPUT, expected_tokens):
            stale.append(str(TOKEN_OUTPUT.relative_to(ROOT)))
        if not check_bytes(INDEX, expected_index):
            stale.append(str(INDEX.relative_to(ROOT)))
        for language, path in LOCALIZED_INDEXES.items():
            if not check_bytes(path, expected_localized_indexes[language]):
                stale.append(str(path.relative_to(ROOT)))
        if not check_bytes(ROBOTS, expected_robots):
            stale.append(str(ROBOTS.relative_to(ROOT)))
        if not check_bytes(SITEMAP, expected_sitemap):
            stale.append(str(SITEMAP.relative_to(ROOT)))
        for source, target in assets.items():
            if not target.exists() or source.read_bytes() != target.read_bytes():
                stale.append(str(target.relative_to(ROOT)))
        if stale:
            print("STALE_SITE_OUTPUT " + " ".join(stale))
            return 1
        print("SITE_OUTPUT_OK")
        return 0

    save(output, projection, pretty=False)
    content_output.parent.mkdir(parents=True, exist_ok=True)
    content_output.write_bytes(expected_content)
    TOKEN_OUTPUT.write_bytes(expected_tokens)
    INDEX.write_bytes(expected_index)
    for language, path in LOCALIZED_INDEXES.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(expected_localized_indexes[language])
    ROBOTS.write_bytes(expected_robots)
    SITEMAP.write_bytes(expected_sitemap)
    for source, target in assets.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    print(f"SITE_BUILT {binding['binding_digest']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
