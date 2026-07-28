#!/usr/bin/env python3
"""Create a read-only, human-reviewable Atlas draft from one Git repository."""

from __future__ import annotations

import argparse
from collections import Counter
from html import escape
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any


COPY = {
    "en": {
        "draft": "DRAFT · NOTHING HAS BEEN ACTIVATED",
        "title": "Project Atlas",
        "for": "Prepared for {name}",
        "summary": "A first map built from repository evidence",
        "root_purpose": "The whole project and the recurring work found around it.",
        "observed": "Seen in the repository",
        "inferred": "Suggested by the analysis",
        "evidence": "Why this appears on the map",
        "children": "Open a nested cycle",
        "leaf": "No smaller cycle was inferred here.",
        "review": "Does this map describe the project correctly?",
        "review_hint": "Tell Concord Loom what to rename, move, add, or remove.",
        "files": "{count} matching file(s)",
        "dirty": "The working tree contains local changes.",
        "truncated": "Some evidence was limited during inspection: {items}.",
    },
    "ru": {
        "draft": "ЧЕРНОВИК · НИЧЕГО НЕ ВКЛЮЧЕНО",
        "title": "Атлас проекта",
        "for": "Подготовлено для: {name}",
        "summary": "Первая карта, построенная по данным репозитория",
        "root_purpose": "Весь проект и найденная в нём повторяющаяся работа.",
        "observed": "Найдено в репозитории",
        "inferred": "Предложено по результатам анализа",
        "evidence": "Почему этот цикл появился на карте",
        "children": "Открыть вложенный цикл",
        "leaf": "Здесь пока не найдено вложенных циклов.",
        "review": "Эта карта правильно описывает проект?",
        "review_hint": "Скажите Concord Loom, что переименовать, переместить, добавить или убрать.",
        "files": "Подходящих файлов: {count}",
        "dirty": "В рабочем дереве есть локальные изменения.",
        "truncated": "Часть данных была ограничена при анализе: {items}.",
    },
}

CYCLES = {
    "decision": ("Decide direction", "Определять направление"),
    "source": ("Develop the product", "Развивать продукт"),
    "test": ("Verify changes", "Проверять изменения"),
    "documentation": ("Explain the product", "Объяснять продукт"),
    "build": ("Build deliverables", "Собирать результат"),
    "ci": ("Integrate changes", "Интегрировать изменения"),
    "operations": ("Operate the product", "Эксплуатировать продукт"),
    "governance": ("Govern changes", "Управлять изменениями"),
    "other": ("Maintain the repository", "Поддерживать репозиторий"),
}

PURPOSES = {
    "decision": ("Turn product choices into recorded direction.", "Превращать продуктовые решения в зафиксированное направление."),
    "source": ("Change the product implementation.", "Изменять реализацию продукта."),
    "test": ("Check that a change behaves as expected.", "Проверять, что изменения работают ожидаемым образом."),
    "documentation": ("Keep explanations aligned with the product.", "Поддерживать объяснения в соответствии с продуктом."),
    "build": ("Turn source material into usable outputs.", "Превращать исходные материалы в готовый результат."),
    "ci": ("Run repeatable checks around incoming changes.", "Запускать повторяемые проверки для входящих изменений."),
    "operations": ("Observe and maintain the running product.", "Наблюдать за работающим продуктом и поддерживать его."),
    "governance": ("Keep project-wide change rules explicit.", "Поддерживать понятные правила изменений проекта."),
    "other": ("Maintain supporting repository material.", "Поддерживать вспомогательные материалы репозитория."),
}

STYLE = """
:root{color-scheme:dark;--bg:#080a09;--panel:#111411;--ink:#f4f4ef;--muted:#a5ada5;--acid:#baff00;--line:#303630}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 ui-monospace,SFMono-Regular,Consolas,monospace}
header{padding:28px clamp(22px,5vw,72px);border-bottom:1px solid var(--line);display:flex;gap:24px;justify-content:space-between;align-items:end}
.eyebrow{color:var(--acid);font-weight:800}.meta{color:var(--muted);text-align:right}h1{margin:.2rem 0;font:800 clamp(2.4rem,7vw,6rem)/.92 Arial,sans-serif;letter-spacing:-.06em}
main{display:grid;grid-template-columns:minmax(260px,34%) 1fr;min-height:72vh}.tree{padding:28px;border-right:1px solid var(--line)}
.tree button{width:100%;padding:14px 16px;margin:0 0 8px;text-align:left;background:transparent;color:var(--muted);border:1px solid var(--line);font:inherit;cursor:pointer}
.tree button:hover,.tree button[aria-current=true]{color:#091006;background:var(--acid);border-color:var(--acid)}.detail{padding:clamp(28px,6vw,88px)}
.state{color:var(--acid);text-transform:uppercase;font-weight:800}.detail h2{font:800 clamp(2rem,5vw,5rem)/.95 Arial,sans-serif;letter-spacing:-.05em;margin:.35em 0}
.purpose{font:clamp(1.1rem,2vw,1.6rem)/1.45 Arial,sans-serif;max-width:62ch}.evidence{margin-top:34px;padding:22px;border-left:2px solid var(--acid);background:var(--panel)}
.children{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px;margin-top:28px}.children button{padding:18px;background:var(--panel);border:1px solid var(--line);color:var(--ink);text-align:left;cursor:pointer}
.review{padding:28px clamp(22px,5vw,72px);background:var(--acid);color:#081006}.review strong{font:800 clamp(1.4rem,3vw,2.6rem)/1 Arial,sans-serif}.review p{margin:.5rem 0 0}
code{color:var(--acid)}@media(max-width:760px){header{display:block}.meta{text-align:left;margin-top:16px}main{display:block}.tree{border-right:0;border-bottom:1px solid var(--line)}}
"""

SCRIPT = r"""
const model=JSON.parse(document.getElementById("model").textContent),copy=JSON.parse(document.getElementById("copy").textContent);
const byId=new Map(model.loops.map(x=>[x.id,x])),tree=document.getElementById("tree"),detail=document.getElementById("detail");
const esc=value=>String(value).replace(/[&<>"']/g,char=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));
function select(id,push=true){const item=byId.get(id)||model.loops[0];if(push)history.pushState(null,"","#"+item.id);
[...tree.querySelectorAll("button")].forEach(b=>b.setAttribute("aria-current",String(b.dataset.id===item.id)));
const kids=model.loops.filter(x=>x.parent_id===item.id);
detail.innerHTML=`<span class="state">${esc(item.state==="observed"?copy.observed:copy.inferred)}</span><h2>${esc(item.label)}</h2><p class="purpose">${esc(item.purpose)}</p>
<section class="evidence"><strong>${esc(copy.evidence)}</strong><p>${item.evidence.map(esc).join("<br>")}</p></section>
<section class="children">${kids.length?kids.map(x=>`<button data-child="${esc(x.id)}">${esc(copy.children)}<br><strong>${esc(x.label)}</strong></button>`).join(""):`<p>${esc(copy.leaf)}</p>`}</section>`;
detail.querySelectorAll("[data-child]").forEach(b=>b.onclick=()=>select(b.dataset.child));}
model.loops.forEach(x=>{const b=document.createElement("button");b.dataset.id=x.id;b.textContent=(x.parent_id?"↳ ":"")+x.label;b.onclick=()=>select(x.id);tree.appendChild(b)});
addEventListener("popstate",()=>select(location.hash.slice(1),false));select(location.hash.slice(1)||model.loops[0].id,false);
"""


def _identifier(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "project"


def _model(graph: dict[str, Any], locale: str, person_name: str) -> dict[str, Any]:
    copy = COPY[locale]
    project_name = str(graph["repository"]["id"])
    nodes = [item for item in graph["nodes"] if isinstance(item, dict)]
    categories = Counter(str(item.get("category", "other")) for item in nodes)
    root_id = f"{_identifier(project_name)}-project"
    loops = [{
        "id": root_id, "parent_id": None, "label": project_name,
        "purpose": copy["root_purpose"], "state": "observed",
        "evidence": [copy["files"].format(count=len(nodes))],
    }]
    for category in CYCLES:
        count = categories.get(category, 0)
        if not count:
            continue
        examples = sorted(
            str(item.get("path", item.get("label", "")))
            for item in nodes if item.get("category") == category
        )[:4]
        loops.append({
            "id": f"{root_id}-{category}", "parent_id": root_id,
            "label": CYCLES[category][0 if locale == "en" else 1],
            "purpose": PURPOSES[category][0 if locale == "en" else 1],
            "state": "inferred",
            "evidence": [copy["files"].format(count=count), *examples],
        })
    warnings = []
    if graph["repository"].get("dirty"):
        warnings.append(copy["dirty"])
    truncated = graph.get("coverage", {}).get("truncated", [])
    if truncated:
        warnings.append(copy["truncated"].format(items=", ".join(truncated)))
    return {
        "project": project_name, "person_name": person_name,
        "revision": graph["repository"]["revision"], "warnings": warnings,
        "loops": loops,
    }


def _safe_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True).replace("<", "\\u003c")


def _validate_model(model: Any) -> dict[str, Any]:
    if not isinstance(model, dict):
        raise ValueError("Atlas model must be an object")
    for field in ("project", "person_name", "revision"):
        if not isinstance(model.get(field), str) or not model[field].strip():
            raise ValueError(f"Atlas model field {field!r} must be a non-empty string")
    warnings = model.get("warnings")
    if not isinstance(warnings, list) or not all(
        isinstance(item, str) for item in warnings
    ):
        raise ValueError("Atlas model warnings must be a list of strings")
    loops = model.get("loops")
    if not isinstance(loops, list) or not loops:
        raise ValueError("Atlas model must contain at least one loop")
    identifiers: set[str] = set()
    parents: dict[str, str | None] = {}
    for loop in loops:
        if not isinstance(loop, dict):
            raise ValueError("Every Atlas loop must be an object")
        identifier = loop.get("id")
        if not isinstance(identifier, str) or not re.fullmatch(
            r"[a-z0-9][a-z0-9-]*", identifier
        ):
            raise ValueError("Atlas loop IDs must use lowercase letters, digits, and hyphens")
        if identifier in identifiers:
            raise ValueError(f"Duplicate Atlas loop ID: {identifier}")
        identifiers.add(identifier)
        parent = loop.get("parent_id")
        if parent is not None and not isinstance(parent, str):
            raise ValueError(f"Invalid parent for Atlas loop: {identifier}")
        parents[identifier] = parent
        if loop.get("state") not in {"observed", "inferred"}:
            raise ValueError(f"Invalid state for Atlas loop: {identifier}")
        for field in ("label", "purpose"):
            if not isinstance(loop.get(field), str) or not loop[field].strip():
                raise ValueError(f"Atlas loop {identifier} needs {field}")
        if not isinstance(loop.get("evidence"), list) or not all(
            isinstance(item, str) for item in loop["evidence"]
        ):
            raise ValueError(f"Atlas loop {identifier} needs string evidence")
    roots = [identifier for identifier, parent in parents.items() if parent is None]
    if len(roots) != 1:
        raise ValueError("Atlas model must contain exactly one root loop")
    for identifier, parent in parents.items():
        if parent is not None and parent not in identifiers:
            raise ValueError(f"Unknown parent {parent!r} for Atlas loop {identifier}")
        seen: set[str] = set()
        current: str | None = identifier
        while current is not None:
            if current in seen:
                raise ValueError("Atlas containment must be acyclic")
            seen.add(current)
            current = parents.get(current)
    return model


def _render(model: dict[str, Any], locale: str) -> str:
    copy = COPY[locale]
    warning = " ".join(escape(item) for item in model["warnings"])
    return f"""<!doctype html>
<html lang="{locale}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none';style-src 'unsafe-inline';script-src 'unsafe-inline'">
<title>{escape(copy["title"])} · {escape(model["project"])}</title><style>{STYLE}</style></head>
<body><header><div><div class="eyebrow">{escape(copy["draft"])}</div><h1>{escape(copy["title"])}</h1><p>{escape(copy["summary"])}</p></div>
<div class="meta">{escape(copy["for"].format(name=model["person_name"]))}<br><code>{escape(model["project"])}</code></div></header>
<main><nav class="tree" id="tree" aria-label="{escape(copy["title"])}"></nav><article class="detail" id="detail"></article></main>
<section class="review"><strong>{escape(copy["review"])}</strong><p>{escape(copy["review_hint"])}</p>{f"<p>{warning}</p>" if warning else ""}</section>
<script type="application/json" id="model">{_safe_json(model)}</script><script type="application/json" id="copy">{_safe_json(copy)}</script><script>{SCRIPT}</script></body></html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a read-only onboarding Atlas draft.")
    parser.add_argument("--repo", type=Path)
    parser.add_argument("--model", type=Path)
    parser.add_argument("--model-output", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--locale", choices=sorted(COPY), required=True)
    parser.add_argument("--person-name", required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if bool(args.repo) == bool(args.model):
        parser.error("provide exactly one of --repo or --model")
    if args.model:
        model = json.loads(args.model.read_text(encoding="utf-8"))
        model["person_name"] = args.person_name
    else:
        launcher = Path(__file__).with_name("concordloom_cli.py")
        with tempfile.TemporaryDirectory(prefix="concordloom-onboarding-") as directory:
            graph_path = Path(directory) / "observed-project-graph.json"
            completed = subprocess.run(
                [os.sys.executable, os.fspath(launcher), "inspect",
                 os.fspath(args.repo), "--output", os.fspath(graph_path)],
                check=False, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                text=True,
            )
            if completed.returncode:
                raise SystemExit(completed.stderr.strip() or "repository inspection failed")
            graph = json.loads(graph_path.read_text(encoding="utf-8"))
            model = _model(graph, args.locale, args.person_name)
    try:
        model = _validate_model(model)
    except ValueError as error:
        parser.error(str(error))
    rendered = _render(model, args.locale)
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding="utf-8") != rendered:
            raise SystemExit("Atlas draft is missing or stale")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    if args.model_output:
        args.model_output.write_text(
            json.dumps(model, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps({
        "atlas": str(args.output),
        "model": str(args.model_output) if args.model_output else None,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
