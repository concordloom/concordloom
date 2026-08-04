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
    ("HOW_TO_HELP", "How to help", "Как помочь"),
    ("REPOSITORY_TRIAL", "Repository trial", "Испытание репозитория"),
    (
        "AI_AGENT_GOVERNANCE",
        "Governing AI coding agents",
        "Управление ИИ-агентами",
    ),
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
LOCALIZED_DOC_INDEXES = {
    "en": SITE / "docs" / "en" / "index.html",
    "ru": SITE / "docs" / "ru" / "index.html",
}
LOCALIZED_DOC_PAGES = {
    language: {
        stem: SITE
        / "docs"
        / language
        / stem.casefold().replace("_", "-")
        / "index.html"
        for stem, _, _ in PUBLIC_DOCS
    }
    for language in ("en", "ru")
}
LOCALIZED_ATLAS_OUTPUTS = {
    language: path.parent / "data" / "atlas.json"
    for language, path in LOCALIZED_INDEXES.items()
}
LOCALIZED_CONTENT_OUTPUTS = {
    language: path.parent / "data" / "content.json"
    for language, path in LOCALIZED_INDEXES.items()
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
            public_stems = {stem for stem, _, _ in PUBLIC_DOCS}
            if relative.suffix == ".md" and relative.stem in public_stems:
                if relative.parent == Path("docs"):
                    language = "en"
                elif relative.parent == Path("docs") / "ru":
                    language = "ru"
                else:
                    language = ""
                if language:
                    slug = relative.stem.casefold().replace("_", "-")
                    href = f"{SITE_BASE_URL}/docs/{language}/{slug}/"
                    return f'<a href="{href}">{label}</a>'
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
                "enUrl": f"{SITE_BASE_URL}/docs/en/{stem.casefold().replace('_', '-')}/",
                "ruUrl": f"{SITE_BASE_URL}/docs/ru/{stem.casefold().replace('_', '-')}/",
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


def index_with_static_reading(content: dict, language: str = "en") -> bytes:
    """Project localized reading content into the no-JS HTML shell."""

    if language not in {"en", "ru"}:
        raise ValueError(f"unsupported site locale: {language}")

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
            f"{content[section][language]['html']}\n"
            f"            {end}"
        )
        source, count = pattern.subn(replacement, source, count=1)
        if count != 1:
            raise ValueError(f"site index lacks one generated {section} block")
    return source.encode("utf-8")


def localized_documentation_index(content: dict, language: str) -> bytes:
    """Build one crawlable documentation URL without relying on JavaScript."""

    if language not in {"en", "ru"}:
        raise ValueError(f"unsupported site locale: {language}")
    copy = {
        "en": {
            "title": "Concord Loom documentation",
            "description": "Quickstart, theory, and reference material for Concord Loom.",
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
            "title": "Документация Concord Loom",
            "description": "Быстрый старт, теория и справочные материалы Concord Loom.",
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
    canonical = f"{SITE_BASE_URL}/docs/{language}/"
    alternate_language = "ru" if language == "en" else "en"
    document_links = "\n".join(
        "          <li>"
        f'<a href="{stem.casefold().replace("_", "-")}/">'
        f"{html.escape(en_title if language == 'en' else ru_title)}"
        "</a></li>"
        for stem, en_title, ru_title in PUBLIC_DOCS
    )
    document = f"""<!doctype html>
<html lang="{language}" style="color-scheme: light" data-design-system="signal-canvas">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="theme-color" content="#f3f0e8">
    <meta name="description" content="{html.escape(copy['description'], quote=True)}">
    <link rel="canonical" href="{canonical}">
    <link rel="alternate" hreflang="en" href="{SITE_BASE_URL}/docs/en/">
    <link rel="alternate" hreflang="ru" href="{SITE_BASE_URL}/docs/ru/">
    <link rel="alternate" hreflang="x-default" href="{SITE_BASE_URL}/docs/en/">
    <meta property="og:title" content="{html.escape(copy['title'], quote=True)}">
    <meta property="og:description" content="{html.escape(copy['description'], quote=True)}">
    <meta property="og:image" content="{SITE_BASE_URL}/assets/concordloom-social-preview.png">
    <meta property="og:url" content="{canonical}">
    <meta property="og:type" content="website">
    <meta property="og:locale" content="{'en_US' if language == 'en' else 'ru_RU'}">
    <title>{html.escape(copy['title'])}</title>
    <link rel="icon" type="image/png" sizes="32x32" href="../../assets/favicon-32.png">
    <link rel="stylesheet" href="../../design-tokens.css">
    <link rel="stylesheet" href="../../design-system.css">
    <link rel="stylesheet" href="../../styles.css">
  </head>
  <body data-design-system="signal-canvas">
    <a class="skip-link" href="#main">{'Skip to content' if language == 'en' else 'Перейти к содержанию'}</a>
    <header class="site-header">
      <a class="brand" href="../../{language}/" aria-label="Concord Loom">
        <img src="../../assets/concordloom-mark.png" width="48" height="48" alt="">
        <span>CONCORD LOOM</span>
      </a>
      <nav class="view-tabs" aria-label="{'Language versions' if language == 'en' else 'Языковые версии'}">
        <a class="view-tab" href="../{alternate_language}/">{html.escape(copy['alternate'])}</a>
        <a class="view-tab is-active" href="../../{language}/">{html.escape(copy['interactive'])}</a>
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
          <h2>{'Reference pages' if language == 'en' else 'Справочные страницы'}</h2>
          <ul>
{document_links}
          </ul>
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


def markdown_summary(source: str, fallback: str) -> str:
    """Return a deterministic, plain-text summary from the first useful paragraph."""

    paragraph: list[str] = []
    in_code = False
    for raw_line in source.splitlines():
        line = raw_line.strip()
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code or line.startswith(("#", "- ", "* ", ">", "|")):
            continue
        if re.match(r"^\d+\.\s", line) or re.fullmatch(r"\[[^]]+\]\([^)]+\)", line):
            continue
        if not line:
            if paragraph:
                break
            continue
        paragraph.append(line)
    value = " ".join(paragraph) or fallback
    value = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", value)
    value = re.sub(r"[`*_]+", "", value)
    value = re.sub(r"\s+", " ", value).strip()
    if len(value) > 157:
        value = value[:157].rsplit(" ", 1)[0].rstrip(".,;:") + "…"
    return value


def localized_document_page(
    stem: str,
    en_title: str,
    ru_title: str,
    language: str,
) -> bytes:
    """Build one crawlable, bilingual-paired public reference page."""

    if language not in {"en", "ru"}:
        raise ValueError(f"unsupported site locale: {language}")
    slug = stem.casefold().replace("_", "-")
    source_path = (
        ROOT / "docs" / f"{stem}.md"
        if language == "en"
        else ROOT / "docs" / "ru" / f"{stem}.md"
    )
    source = source_path.read_text(encoding="utf-8")
    fragment, _ = markdown_fragment(source, source_path=source_path)
    fragment, heading_count = re.subn(
        r"<h1\b[^>]*>.*?</h1>",
        "",
        fragment,
        count=1,
        flags=re.DOTALL,
    )
    if heading_count != 1:
        raise ValueError(f"public document {source_path} must contain one title")
    fragment = fragment.strip()
    title = en_title if language == "en" else ru_title
    description = markdown_summary(
        source,
        "Concord Loom reference documentation."
        if language == "en"
        else "Справочная документация Concord Loom.",
    )
    canonical = f"{SITE_BASE_URL}/docs/{language}/{slug}/"
    alternate_language = "ru" if language == "en" else "en"
    alternate = f"{SITE_BASE_URL}/docs/{alternate_language}/{slug}/"
    index_label = "Documentation" if language == "en" else "Документация"
    alternate_label = "Русская версия" if language == "en" else "English version"
    skip_label = "Skip to content" if language == "en" else "Перейти к содержанию"
    page_label = "CONCORD LOOM REFERENCE" if language == "en" else "СПРАВОЧНИК CONCORD LOOM"
    document = f"""<!doctype html>
<html lang="{language}" style="color-scheme: light" data-design-system="signal-canvas">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="theme-color" content="#f3f0e8">
    <meta name="description" content="{html.escape(description, quote=True)}">
    <link rel="canonical" href="{canonical}">
    <link rel="alternate" hreflang="en" href="{SITE_BASE_URL}/docs/en/{slug}/">
    <link rel="alternate" hreflang="ru" href="{SITE_BASE_URL}/docs/ru/{slug}/">
    <link rel="alternate" hreflang="x-default" href="{SITE_BASE_URL}/docs/en/{slug}/">
    <meta property="og:title" content="{html.escape(title, quote=True)} | Concord Loom">
    <meta property="og:description" content="{html.escape(description, quote=True)}">
    <meta property="og:image" content="{SITE_BASE_URL}/assets/concordloom-social-preview.png">
    <meta property="og:url" content="{canonical}">
    <meta property="og:type" content="article">
    <meta property="og:locale" content="{'en_US' if language == 'en' else 'ru_RU'}">
    <title>{html.escape(title)} | Concord Loom</title>
    <link rel="icon" type="image/png" sizes="32x32" href="../../../assets/favicon-32.png">
    <link rel="stylesheet" href="../../../design-tokens.css">
    <link rel="stylesheet" href="../../../design-system.css">
    <link rel="stylesheet" href="../../../styles.css">
  </head>
  <body data-design-system="signal-canvas">
    <a class="skip-link" href="#main">{skip_label}</a>
    <header class="site-header">
      <a class="brand" href="../../../{language}/" aria-label="Concord Loom">
        <img src="../../../assets/concordloom-mark.png" width="48" height="48" alt="">
        <span>CONCORD LOOM</span>
      </a>
      <nav class="view-tabs" aria-label="{'Document navigation' if language == 'en' else 'Навигация по документу'}">
        <a class="view-tab" href="../">{html.escape(index_label)}</a>
        <a class="view-tab" href="{alternate}">{html.escape(alternate_label)}</a>
      </nav>
    </header>
    <main id="main" class="view is-active">
      <section class="content-hero">
        <p class="kicker">{page_label}</p>
        <h1>{html.escape(title)}</h1>
      </section>
      <section class="reading-layout">
        <article class="reading-copy prose">
          {fragment}
        </article>
      </section>
    </main>
  </body>
</html>
"""
    return document.encode("utf-8")


def _static_language_copy(document: str, language: str) -> str:
    """Select simple bilingual text and metadata for the first HTML paint."""

    element_pattern = re.compile(
        r'(<(?P<tag>[a-z][a-z0-9-]*)\b'
        r'(?=[^>]*\bdata-en="(?P<en>[^"]*)")'
        r'(?=[^>]*\bdata-ru="(?P<ru>[^"]*)")[^>]*>)'
        r'(?P<body>[^<]*)(</(?P=tag)>)',
        flags=re.IGNORECASE,
    )

    def replace_element(match: re.Match[str]) -> str:
        return match.group(1) + match.group(language) + match.group(6)

    document = element_pattern.sub(replace_element, document)
    meta_pattern = re.compile(
        r'<meta\b(?=[^>]*\bdata-en-content="(?P<en>[^"]*)")'
        r'(?=[^>]*\bdata-ru-content="(?P<ru>[^"]*)")[^>]*>',
        flags=re.IGNORECASE,
    )

    def replace_meta(match: re.Match[str]) -> str:
        tag = match.group(0)
        return re.sub(
            r'\bcontent="[^"]*"',
            f'content="{match.group(language)}"',
            tag,
            count=1,
        )

    document = meta_pattern.sub(replace_meta, document)
    localized_attribute_pattern = re.compile(
        r'(?P<attribute>href|placeholder)="[^"]*"'
        r'(?=[^>]*\bdata-en-(?P=attribute)="(?P<en>[^"]*)")'
        r'(?=[^>]*\bdata-ru-(?P=attribute)="(?P<ru>[^"]*)")',
        flags=re.IGNORECASE,
    )

    def replace_localized_attribute(match: re.Match[str]) -> str:
        return f'{match.group("attribute")}="{match.group(language)}"'

    return localized_attribute_pattern.sub(replace_localized_attribute, document)


def localized_index(content: dict, language: str) -> bytes:
    """Build a crawlable localized copy of the complete interactive site."""

    if language not in {"en", "ru"}:
        raise ValueError(f"unsupported site locale: {language}")
    document = index_with_static_reading(content, language).decode("utf-8")
    canonical = f"{SITE_BASE_URL}/{language}/"
    document = document.replace('<html lang="en"', f'<html lang="{language}"', 1)
    document = document.replace(
        '        const language =\n'
        '          (requested === "en" || requested === "ru" ? requested : null)\n'
        '          || (stored === "en" || stored === "ru" ? stored : null)\n'
        '          || "en";',
        f'''        const routeLanguage = "{language}";
        if ((requested === "en" || requested === "ru") && requested !== routeLanguage) {{
          const target = new URL(location.href);
          target.pathname = target.pathname.replace(
            /\\/(?:en|ru)\\/?$/,
            `/${{requested}}/`,
          );
          target.searchParams.delete("lang");
          location.replace(`${{target.pathname}}${{target.search}}${{target.hash}}`);
          return;
        }}
        const language = routeLanguage;''',
        1,
    )
    document = document.replace(
        f'<link rel="canonical" href="{SITE_BASE_URL}/">',
        f'<link rel="canonical" href="{canonical}">',
        1,
    )
    document = document.replace(
        f'<meta property="og:url" content="{SITE_BASE_URL}/">',
        f'<meta property="og:url" content="{canonical}">',
        1,
    )
    for attribute in ("href", "src", "srcset"):
        document = document.replace(f'{attribute}="assets/', f'{attribute}="../assets/')
    document = document.replace('href="styles.css"', 'href="../styles.css"')
    document = document.replace(
        'href="design-tokens.css"', 'href="../design-tokens.css"'
    )
    document = document.replace(
        'href="design-system.css"', 'href="../design-system.css"'
    )
    document = document.replace('src="app.js"', 'src="../app.js"')
    return _static_language_copy(document, language).encode("utf-8")


def robots_txt() -> bytes:
    return (
        "User-agent: *\n"
        "Allow: /\n"
        f"Sitemap: {SITE_BASE_URL}/sitemap.xml\n"
    ).encode("utf-8")


def sitemap_xml() -> bytes:
    groups = [
        {
            "x-default": f"{SITE_BASE_URL}/",
            "en": f"{SITE_BASE_URL}/en/",
            "ru": f"{SITE_BASE_URL}/ru/",
        },
        {
            "x-default": f"{SITE_BASE_URL}/docs/en/",
            "en": f"{SITE_BASE_URL}/docs/en/",
            "ru": f"{SITE_BASE_URL}/docs/ru/",
        },
    ]
    for stem, _, _ in PUBLIC_DOCS:
        slug = stem.casefold().replace("_", "-")
        groups.append(
            {
                "x-default": f"{SITE_BASE_URL}/docs/en/{slug}/",
                "en": f"{SITE_BASE_URL}/docs/en/{slug}/",
                "ru": f"{SITE_BASE_URL}/docs/ru/{slug}/",
            }
        )
    entries: list[str] = []
    for group in groups:
        urls = tuple(dict.fromkeys(group.values()))
        for canonical in urls:
            alternates = "\n".join(
                "    <xhtml:link rel=\"alternate\" "
                f"hreflang=\"{alternate_language}\" href=\"{url}\" />"
                for alternate_language, url in group.items()
            )
            entries.append(
                f"  <url>\n    <loc>{canonical}</loc>\n"
                f"{alternates}\n  </url>"
            )
    entries_text = "\n".join(entries)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
        f"{entries_text}\n"
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
    expected_localized_doc_indexes = {
        language: localized_documentation_index(content, language)
        for language in LOCALIZED_DOC_INDEXES
    }
    expected_localized_doc_pages = {
        language: {
            stem: localized_document_page(stem, en_title, ru_title, language)
            for stem, en_title, ru_title in PUBLIC_DOCS
        }
        for language in LOCALIZED_DOC_PAGES
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
        for path in LOCALIZED_ATLAS_OUTPUTS.values():
            if not check_bytes(path, expected):
                stale.append(str(path.relative_to(ROOT)))
        for path in LOCALIZED_CONTENT_OUTPUTS.values():
            if not check_bytes(path, expected_content):
                stale.append(str(path.relative_to(ROOT)))
        if not check_bytes(TOKEN_OUTPUT, expected_tokens):
            stale.append(str(TOKEN_OUTPUT.relative_to(ROOT)))
        if not check_bytes(INDEX, expected_index):
            stale.append(str(INDEX.relative_to(ROOT)))
        for language, path in LOCALIZED_INDEXES.items():
            if not check_bytes(path, expected_localized_indexes[language]):
                stale.append(str(path.relative_to(ROOT)))
        for language, path in LOCALIZED_DOC_INDEXES.items():
            if not check_bytes(path, expected_localized_doc_indexes[language]):
                stale.append(str(path.relative_to(ROOT)))
        for language, pages in LOCALIZED_DOC_PAGES.items():
            for stem, path in pages.items():
                if not check_bytes(path, expected_localized_doc_pages[language][stem]):
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
    for path in LOCALIZED_ATLAS_OUTPUTS.values():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(expected)
    for path in LOCALIZED_CONTENT_OUTPUTS.values():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(expected_content)
    TOKEN_OUTPUT.write_bytes(expected_tokens)
    INDEX.write_bytes(expected_index)
    for language, path in LOCALIZED_INDEXES.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(expected_localized_indexes[language])
    for language, path in LOCALIZED_DOC_INDEXES.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(expected_localized_doc_indexes[language])
    for language, pages in LOCALIZED_DOC_PAGES.items():
        for stem, path in pages.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(expected_localized_doc_pages[language][stem])
    ROBOTS.write_bytes(expected_robots)
    SITEMAP.write_bytes(expected_sitemap)
    for source, target in assets.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    print(f"SITE_BUILT {binding['binding_digest']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
