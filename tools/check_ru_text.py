#!/usr/bin/env python3
"""Check objective Russian editorial invariants in public human-facing text.

This is deliberately a narrow linter. It catches deterministic typography
errors, project-banned assistant openers, and known onboarding jargon. It does
not replace contextual review with the pinned ru-text skill.
"""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from typing import Iterable, Iterator


ROOT = Path(__file__).resolve().parents[1]
CYRILLIC = re.compile(r"[А-Яа-яЁё]")
INLINE_CODE = re.compile(r"`+[^`\n]*`+")
MARKDOWN_LINK = re.compile(r"!?\[([^\]]*)\]\((?:[^()]|\([^)]*\))*\)")
URL = re.compile(r"(?:https?://|mailto:)\S+")
HTML_TAG = re.compile(r"<[^>]+>")
HTML_ATTRIBUTE = re.compile(
    r"""\b(?:alt|aria-label|data-ru|placeholder|title)=
    (?P<quote>["'])(?P<value>.*?)(?P=quote)""",
    re.IGNORECASE | re.VERBOSE,
)
ASCII_QUOTE = re.compile(r'"[^"\n]*[А-Яа-яЁё][^"\n]*"')
THREE_DOTS = re.compile(r"\.\.\.")
HYPHEN_AS_DASH = re.compile(
    r"(?<=[А-Яа-яЁё0-9)\]])[ \u00a0]+-[ \u00a0]+"
    r"(?=[А-Яа-яЁё0-9(\[])"
)
LEADING_MARKUP = re.compile(r"^\s*(?:#{1,6}|>|[-*+]|\d+[.)])\s*")
IGNORE_BEGIN = "<!-- ru-text: ignore-begin -->"
IGNORE_END = "<!-- ru-text: ignore-end -->"

ASSISTANT_OPENERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "assistant-praise",
        re.compile(
            r"^(?:Отличный|Хороший|Прекрасный)\s+вопрос[!.]?",
            re.IGNORECASE,
        ),
    ),
    (
        "assistant-praise",
        re.compile(r"^Прекрасная\s+идея[!.]?", re.IGNORECASE),
    ),
    (
        "assistant-praise",
        re.compile(r"^Вы\s+абсолютно\s+правы\b", re.IGNORECASE),
    ),
    (
        "assistant-signoff",
        re.compile(
            r"^(?:Надеюсь,\s+(?:это|было)\s+(?:полезно|понятно|полезным)|"
            r"Готов\s+помочь\b|Обращайтесь,\s+если\s+что\b)",
            re.IGNORECASE,
        ),
    ),
    (
        "hollow-opener",
        re.compile(
            r"^(?:Давайте\s+(?:разберёмся|погрузимся)|"
            r"Важно\s+понимать,\s+что|Здесь\s+важно\s+понять|"
            r"Нужно\s+понимать,\s+что|В\s+современном\s+мире\b|"
            r"Не\s+секрет,\s+что|Стоит\s+отметить,\s+что)",
            re.IGNORECASE,
        ),
    ),
)

RAW_JARGON: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "onboarding-jargon",
        re.compile(r"\bgoverned\s+delivery\s+boundary\b", re.IGNORECASE),
    ),
    (
        "onboarding-jargon",
        re.compile(r"\bunresolved[-\s]решени\w*\b", re.IGNORECASE),
    ),
    (
        "onboarding-jargon",
        re.compile(
            r"\b(?:epistemic\s+state|graph\s+delta|raw\s+impact|"
            r"nodes/edges|project\s+intent)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "operator-placeholder",
        re.compile(r"\b(?:current|example)-operator\b", re.IGNORECASE),
    ),
)


@dataclass(frozen=True)
class Segment:
    line: int
    text: str


@dataclass(frozen=True)
class Finding:
    path: Path
    line: int
    code: str
    message: str
    fragment: str


def default_paths() -> list[Path]:
    """Return the deterministic public Russian-text inventory."""

    paths: set[Path] = set()
    direct = (
        ROOT / "README.ru.md",
        ROOT / "site" / "index.html",
        ROOT / "site" / "app.js",
    )
    paths.update(path for path in direct if path.is_file())
    patterns = (
        "docs/ru/**/*.md",
        "docs/*.ru.md",
        "examples/**/*.ru.md",
        "plugins/**/*.ru.md",
        "site/data/*.json",
    )
    for pattern in patterns:
        paths.update(path for path in ROOT.glob(pattern) if path.is_file())
    return sorted(paths)


def _strip_markdown_prose(line: str) -> str:
    line = INLINE_CODE.sub("", line)
    line = MARKDOWN_LINK.sub(r"\1", line)
    line = URL.sub("", line)
    line = HTML_ATTRIBUTE.sub(r"\g<value>", line)
    line = HTML_TAG.sub("", line)
    return line


def markdown_segments(text: str) -> Iterator[Segment]:
    in_fence = False
    ignored = False
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped == IGNORE_BEGIN:
            ignored = True
            continue
        if stripped == IGNORE_END:
            ignored = False
            continue
        if stripped.startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if in_fence or ignored:
            continue
        prose = _strip_markdown_prose(line)
        if CYRILLIC.search(prose):
            yield Segment(line_number, prose)


class _HumanHTMLParser(HTMLParser):
    """Collect visible text and human-readable attributes, excluding code."""

    HUMAN_ATTRIBUTES = {"alt", "aria-label", "data-ru", "placeholder", "title"}
    SKIPPED_ELEMENTS = {"code", "pre", "script", "style"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.segments: list[Segment] = []
        self._skip_depth = 0
        self._ignored = False

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if tag in self.SKIPPED_ELEMENTS:
            self._skip_depth += 1
        if self._skip_depth:
            return
        for name, value in attrs:
            if (
                name in self.HUMAN_ATTRIBUTES
                and value
                and CYRILLIC.search(value)
            ):
                self.segments.append(Segment(self.getpos()[0], value))

    def handle_endtag(self, tag: str) -> None:
        if tag in self.SKIPPED_ELEMENTS and self._skip_depth:
            self._skip_depth -= 1

    def handle_comment(self, data: str) -> None:
        marker = f"<!--{data}-->"
        if marker.strip() == IGNORE_BEGIN:
            self._ignored = True
        elif marker.strip() == IGNORE_END:
            self._ignored = False

    def handle_data(self, data: str) -> None:
        if self._skip_depth or self._ignored or not CYRILLIC.search(data):
            return
        self.segments.append(Segment(self.getpos()[0], data))


def html_segments(text: str) -> Iterator[Segment]:
    parser = _HumanHTMLParser()
    parser.feed(text)
    yield from parser.segments


def _json_strings(value: object) -> Iterator[str]:
    if isinstance(value, str):
        if CYRILLIC.search(value):
            yield value
        return
    if isinstance(value, list):
        for item in value:
            yield from _json_strings(item)
        return
    if isinstance(value, dict):
        for item in value.values():
            yield from _json_strings(item)


def json_segments(text: str) -> Iterator[Segment]:
    document = json.loads(text)
    for value in _json_strings(document):
        position = text.find(value)
        line = 1 if position < 0 else text.count("\n", 0, position) + 1
        if "<" in value and ">" in value:
            for segment in html_segments(value):
                yield Segment(line + segment.line - 1, segment.text)
        else:
            yield Segment(line, value)


JS_STRING = re.compile(
    r"(?P<quote>['\"`])(?P<body>(?:\\.|(?!\1).)*?)(?P=quote)",
    re.DOTALL,
)


def javascript_segments(text: str) -> Iterator[Segment]:
    for match in JS_STRING.finditer(text):
        body = match.group("body")
        if (
            match.group("quote") == "`"
            and "<" in body
            and ">" in body
        ):
            continue
        if CYRILLIC.search(body):
            line = text.count("\n", 0, match.start()) + 1
            yield Segment(line, body)


def segments_for(path: Path, text: str) -> Iterable[Segment]:
    if path.suffix == ".md":
        return markdown_segments(text)
    if path.suffix == ".html":
        return html_segments(text)
    if path.suffix == ".json":
        return json_segments(text)
    if path.suffix == ".js":
        return javascript_segments(text)
    return ()


def _short_fragment(text: str) -> str:
    compact = " ".join(text.split())
    return compact if len(compact) <= 120 else f"{compact[:117]}…"


def lint_segment(path: Path, segment: Segment) -> list[Finding]:
    text = segment.text
    findings: list[Finding] = []
    checks: tuple[tuple[str, re.Pattern[str], str], ...] = (
        (
            "ascii-quotes",
            ASCII_QUOTE,
            "use Russian guillemets in human-facing prose",
        ),
        (
            "three-dot-ellipsis",
            THREE_DOTS,
            "use the single ellipsis character",
        ),
        (
            "hyphen-as-dash",
            HYPHEN_AS_DASH,
            "use an em dash in a sentence",
        ),
    )
    for code, pattern, message in checks:
        if pattern.search(text):
            findings.append(
                Finding(
                    path,
                    segment.line,
                    code,
                    message,
                    _short_fragment(text),
                )
            )

    normalized = LEADING_MARKUP.sub("", text).strip()
    for code, pattern in ASSISTANT_OPENERS:
        if pattern.search(normalized):
            findings.append(
                Finding(
                    path,
                    segment.line,
                    code,
                    "remove the assistant-style preamble and lead with the point",
                    _short_fragment(text),
                )
            )

    for code, pattern in RAW_JARGON:
        if pattern.search(text):
            findings.append(
                Finding(
                    path,
                    segment.line,
                    code,
                    "replace internal onboarding jargon with plain Russian",
                    _short_fragment(text),
                )
            )
    return findings


def lint_path(path: Path) -> list[Finding]:
    text = path.read_text(encoding="utf-8")
    findings: list[Finding] = []
    for segment in segments_for(path, text):
        findings.extend(lint_segment(path, segment))
    return findings


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    paths = [Path(item).resolve() for item in arguments] if arguments else default_paths()
    findings: list[Finding] = []
    for path in paths:
        if not path.is_file():
            print(f"RU_TEXT_ERROR missing file: {path}", file=sys.stderr)
            return 2
        findings.extend(lint_path(path))

    if findings:
        for finding in findings:
            try:
                label = finding.path.relative_to(ROOT)
            except ValueError:
                label = finding.path
            print(
                f"RU_TEXT_ERROR {label}:{finding.line} "
                f"[{finding.code}] {finding.message}: {finding.fragment}"
            )
        return 1

    print(f"RU_TEXT_OK files={len(paths)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
