"""Deterministic, self-contained HTML projection of a Concord Loom system."""

from __future__ import annotations

import base64
from copy import deepcopy
import hashlib
from html import escape as html_escape
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping

from .canonical import digest
from .loops import validate_policy, validate_registry
from .run import validate_binding
from .schema import SchemaStore


class AtlasError(ValueError):
    """The supplied artifacts cannot form an honest Atlas projection."""


class AtlasStaleError(AtlasError):
    """Check mode found a missing or stale generated Atlas."""


_STYLE = r"""
:root {
  color-scheme: light;
  --paper: #f1f3f0;
  --paper-strong: #e7eae6;
  --ink: #182221;
  --muted: #586361;
  --line: #b9c1bd;
  --line-soft: #d9dedb;
  --accent: #bd482c;
  --accent-soft: #f1d8d0;
  --focus: #0b6159;
  --radius: 2px;
  --mono: ui-monospace, "SFMono-Regular", Consolas, "Liberation Mono", monospace;
  --sans: "Avenir Next", Avenir, "Segoe UI", Helvetica, Arial, sans-serif;
}

* { box-sizing: border-box; }

html {
  min-width: 300px;
  min-height: 100%;
  background: var(--paper);
  scroll-behavior: smooth;
}

body {
  min-height: 100dvh;
  margin: 0;
  color: var(--ink);
  background:
    linear-gradient(to right, transparent 31px, rgb(24 34 33 / 0.035) 32px),
    linear-gradient(to bottom, transparent 31px, rgb(24 34 33 / 0.035) 32px),
    var(--paper);
  background-size: 32px 32px;
  font-family: var(--sans);
  line-height: 1.5;
}

button, a { touch-action: manipulation; }

button {
  color: inherit;
  font: inherit;
}

a { color: inherit; }

.skip-link {
  position: fixed;
  inset: 8px auto auto 8px;
  z-index: 10;
  padding: 8px 12px;
  border: 2px solid var(--focus);
  background: var(--paper);
  transform: translateY(-160%);
}

.skip-link:focus { transform: translateY(0); }

:focus-visible {
  outline: 3px solid var(--focus);
  outline-offset: 3px;
}

.masthead {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 24px;
  align-items: end;
  min-height: 112px;
  padding: 26px clamp(18px, 3vw, 52px) 20px;
  border-bottom: 1px solid var(--ink);
  background: rgb(241 243 240 / 0.94);
}

.brand {
  display: flex;
  gap: 18px;
  align-items: baseline;
  min-width: 0;
}

.brand h1 {
  margin: 0;
  font-size: clamp(1.65rem, 3vw, 2.75rem);
  font-weight: 670;
  letter-spacing: -0.045em;
  line-height: 1;
  text-wrap: balance;
}

.brand p,
.masthead-meta p {
  margin: 0;
  color: var(--muted);
  font-family: var(--mono);
  font-size: 0.72rem;
}

.masthead-meta {
  display: grid;
  gap: 4px;
  justify-items: end;
  text-align: right;
}

.masthead-meta strong {
  color: var(--accent);
  font-family: var(--mono);
  font-size: 0.76rem;
  font-weight: 720;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.breadcrumbs {
  position: sticky;
  top: 0;
  z-index: 5;
  display: flex;
  gap: 7px;
  align-items: center;
  min-height: 48px;
  padding: 8px clamp(18px, 3vw, 52px);
  overflow-x: auto;
  border-bottom: 1px solid var(--line);
  background: rgb(241 243 240 / 0.97);
  backdrop-filter: blur(8px);
}

.crumb {
  flex: 0 0 auto;
  border: 0;
  border-bottom: 1px solid transparent;
  padding: 3px 1px;
  background: transparent;
  cursor: pointer;
  font-family: var(--mono);
  font-size: 0.76rem;
}

.crumb:hover { border-bottom-color: var(--accent); }
.crumb[aria-current="page"] { color: var(--accent); font-weight: 720; }
.crumb-separator { color: var(--line); user-select: none; }

.truth-bar {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  border-bottom: 1px solid var(--ink);
  background: var(--paper-strong);
}

.truth-cell {
  min-width: 0;
  padding: 12px clamp(12px, 2vw, 26px);
  border-right: 1px solid var(--line);
}

.truth-cell:last-child { border-right: 0; }

.truth-cell h2 {
  margin: 0 0 4px;
  font-family: var(--mono);
  font-size: 0.68rem;
  font-weight: 760;
  letter-spacing: 0.07em;
  text-transform: uppercase;
}

.truth-cell p {
  margin: 0;
  color: var(--muted);
  font-size: 0.78rem;
  overflow-wrap: anywhere;
}

.truth-cell[data-layer="actual"] h2,
.truth-cell[data-layer="verified"] h2 { color: var(--accent); }

.atlas-shell {
  display: grid;
  grid-template-columns: minmax(210px, 0.72fr) minmax(420px, 1.8fr) minmax(290px, 1fr);
  min-height: calc(100dvh - 231px);
}

.panel {
  min-width: 0;
  padding: clamp(18px, 2.4vw, 34px);
  background: rgb(241 243 240 / 0.86);
}

.panel + .panel { border-left: 1px solid var(--ink); }

.panel-heading {
  display: flex;
  gap: 14px;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 24px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--line);
}

.panel-heading h2 {
  margin: 0;
  font-size: 0.92rem;
  font-weight: 760;
  letter-spacing: 0.02em;
}

.panel-heading span {
  color: var(--muted);
  font-family: var(--mono);
  font-size: 0.68rem;
}

.loop-summary {
  margin-bottom: 22px;
}

.loop-summary h3 {
  margin: 0 0 5px;
  font-size: clamp(1.5rem, 2.6vw, 2.35rem);
  font-weight: 650;
  letter-spacing: -0.04em;
  line-height: 1.05;
  text-wrap: balance;
}

.loop-summary p {
  max-width: 64ch;
  margin: 0;
  color: var(--muted);
}

.mono-id {
  display: block;
  margin-top: 8px;
  color: var(--accent);
  font-family: var(--mono);
  font-size: 0.69rem;
  overflow-wrap: anywhere;
}

.level-label {
  margin: 22px 0 8px;
  color: var(--muted);
  font-family: var(--mono);
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.loop-nav {
  display: grid;
  gap: 7px;
}

.loop-button {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
  width: 100%;
  min-height: 47px;
  align-items: center;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 9px 10px;
  background: transparent;
  cursor: pointer;
  text-align: left;
  transition: border-color 140ms ease, background-color 140ms ease, transform 80ms ease;
}

.loop-button:hover { border-color: var(--ink); background: var(--paper-strong); }
.loop-button:active { transform: translateY(1px); }
.loop-button[aria-current="true"] {
  border-color: var(--accent);
  background: var(--accent-soft);
}

.loop-button strong {
  min-width: 0;
  font-size: 0.83rem;
  overflow-wrap: anywhere;
}

.loop-button span {
  color: var(--muted);
  font-family: var(--mono);
  font-size: 0.63rem;
}

.empty {
  border-left: 3px solid var(--line);
  padding: 8px 12px;
  color: var(--muted);
  font-size: 0.82rem;
}

.map-key {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 14px;
  margin-bottom: 18px;
  color: var(--muted);
  font-family: var(--mono);
  font-size: 0.65rem;
}

.key-item { display: inline-flex; gap: 6px; align-items: center; }
.key-mark {
  width: 19px;
  height: 8px;
  border-top: 2px solid var(--ink);
}
.key-mark.feedback { border-top: 2px dashed var(--accent); }
.key-mark.containment { border-top: 4px double var(--muted); }

.state-rail {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(112px, 1fr));
  gap: 9px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.state-node {
  position: relative;
  min-width: 0;
  min-height: 92px;
  border: 1px solid var(--ink);
  border-radius: var(--radius);
  padding: 12px 10px 9px;
  background: var(--paper);
}

.state-node[data-kind="gate"] { border-top: 5px solid var(--accent); }
.state-node[data-kind="child"] { border-style: double; border-width: 4px; }
.state-node[data-kind="terminal"] { background: var(--paper-strong); }

.state-node .kind {
  color: var(--muted);
  font-family: var(--mono);
  font-size: 0.61rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.state-node strong {
  display: block;
  margin-top: 8px;
  font-size: 0.78rem;
  line-height: 1.25;
  overflow-wrap: anywhere;
}

.state-node .state-id {
  display: block;
  margin-top: 6px;
  color: var(--muted);
  font-family: var(--mono);
  font-size: 0.58rem;
  overflow-wrap: anywhere;
}

.transition-section { margin-top: 28px; }

.transition-section h3,
.detail-group h3 {
  margin: 0 0 10px;
  font-size: 0.74rem;
  font-weight: 760;
  letter-spacing: 0.055em;
  text-transform: uppercase;
}

.transition-list {
  display: grid;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.transition {
  display: grid;
  grid-template-columns: minmax(0, 0.8fr) auto minmax(0, 0.8fr) minmax(100px, 1fr);
  gap: 10px;
  align-items: center;
  min-width: 0;
  padding: 9px 0;
  border-bottom: 1px solid var(--line-soft);
  font-size: 0.73rem;
}

.transition:last-child { border-bottom: 0; }
.transition[data-kind="feedback"] { color: var(--accent); }
.transition .route-id { font-family: var(--mono); overflow-wrap: anywhere; }
.transition .arrow { color: var(--muted); font-family: var(--mono); }
.transition .guard { color: var(--muted); overflow-wrap: anywhere; }

.feedback-note {
  margin-top: 14px;
  border-left: 3px solid var(--accent);
  padding: 8px 12px;
  color: var(--muted);
  font-size: 0.75rem;
}

.feedback-note ul {
  display: grid;
  gap: 5px;
  margin: 5px 0 0;
  padding-left: 18px;
}

.detail-stack { display: grid; gap: 26px; }

.detail-group {
  min-width: 0;
  padding-bottom: 18px;
  border-bottom: 1px solid var(--line);
}

.detail-group:last-child { border-bottom: 0; }

.kv {
  display: grid;
  grid-template-columns: minmax(96px, 0.8fr) minmax(0, 1.35fr);
  gap: 7px 12px;
  margin: 0;
  font-size: 0.72rem;
}

.kv dt { color: var(--muted); }
.kv dd {
  min-width: 0;
  margin: 0;
  font-family: var(--mono);
  overflow-wrap: anywhere;
}

.plain-list {
  display: grid;
  gap: 7px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.plain-list li {
  border-left: 2px solid var(--line);
  padding-left: 9px;
  color: var(--muted);
  font-size: 0.72rem;
  overflow-wrap: anywhere;
}

.plain-list strong { color: var(--ink); font-weight: 680; }

.run-status {
  display: inline-block;
  border: 1px solid var(--accent);
  border-radius: var(--radius);
  padding: 3px 6px;
  color: var(--accent);
  font-family: var(--mono);
  font-size: 0.66rem;
  font-weight: 720;
  text-transform: uppercase;
}

.footer {
  display: flex;
  gap: 16px;
  justify-content: space-between;
  padding: 14px clamp(18px, 3vw, 52px);
  border-top: 1px solid var(--ink);
  background: var(--paper-strong);
  color: var(--muted);
  font-family: var(--mono);
  font-size: 0.65rem;
}

.footer span { overflow-wrap: anywhere; }

.selection-live {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: -1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  clip-path: inset(50%);
  white-space: nowrap;
}

@media (max-width: 1050px) {
  .atlas-shell { grid-template-columns: minmax(190px, 0.68fr) minmax(0, 1.5fr); }
  .details-panel { grid-column: 1 / -1; border-top: 1px solid var(--ink); border-left: 0 !important; }
  .detail-stack { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}

@media (max-width: 740px) {
  .masthead { grid-template-columns: 1fr; gap: 12px; align-items: start; }
  .brand { display: grid; gap: 8px; }
  .masthead-meta { justify-items: start; text-align: left; }
  .truth-bar { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .truth-cell:nth-child(2) { border-right: 0; }
  .truth-cell:nth-child(-n + 2) { border-bottom: 1px solid var(--line); }
  .atlas-shell { display: block; }
  .panel + .panel { border-top: 1px solid var(--ink); border-left: 0; }
  .detail-stack { display: grid; grid-template-columns: 1fr; }
  .transition { grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr); }
  .transition .guard { grid-column: 1 / -1; }
  .footer { display: grid; }
}

@media (max-width: 430px) {
  .truth-bar { display: block; }
  .truth-cell { border-right: 0; border-bottom: 1px solid var(--line); }
  .truth-cell:last-child { border-bottom: 0; }
  .state-rail { grid-template-columns: 1fr 1fr; }
}

@media (prefers-reduced-motion: reduce) {
  html { scroll-behavior: auto; }
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
""".strip()


_SCRIPT = r"""
(() => {
  "use strict";
  const model = ATLAS_MODEL;
  const byId = new Map(model.loops.map((loop) => [loop.id, loop]));
  const childEdges = new Map();
  const parentEdge = new Map();
  for (const edge of model.containment.edges) {
    if (!childEdges.has(edge.parent_loop_id)) childEdges.set(edge.parent_loop_id, []);
    childEdges.get(edge.parent_loop_id).push(edge);
    parentEdge.set(edge.child_loop_id, edge);
  }

  const esc = (value) => String(value ?? "").replace(
    /[&<>"']/g,
    (character) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[character])
  );
  const list = (value) => Array.isArray(value) ? value : [];
  const objectText = (value) => {
    if (value && typeof value === "object" && !Array.isArray(value)) {
      if ("name" in value) {
        let result = value.type ? `${value.name}: ${value.type}` : String(value.name);
        if (value.required === true) result += ", required";
        if (value.description) result += `. ${value.description}`;
        return result;
      }
      return Object.entries(value)
        .sort(([left], [right]) => left < right ? -1 : left > right ? 1 : 0)
        .map(([key, item]) => `${key}: ${item}`)
        .join(", ");
    }
    return String(value);
  };
  const text = (value, fallback = "Not declared") => {
    if (Array.isArray(value)) {
      return value.length ? value.map(objectText).join("; ") : fallback;
    }
    if (value && typeof value === "object") return objectText(value);
    if (value === null || value === undefined || value === "") return fallback;
    return String(value);
  };

  const fromHash = () => {
    const match = location.hash.match(/(?:^#|&)loop=([^&]+)/);
    if (!match) return model.containment.default_root;
    try {
      const value = decodeURIComponent(match[1]);
      return byId.has(value) ? value : model.containment.default_root;
    } catch (_) {
      return model.containment.default_root;
    }
  };

  let selectedId = fromHash();

  const ancestors = (loopId) => {
    const values = [];
    const seen = new Set();
    let current = loopId;
    while (current && byId.has(current) && !seen.has(current)) {
      seen.add(current);
      values.unshift(current);
      current = parentEdge.get(current)?.parent_loop_id;
    }
    return values;
  };

  const runtimeFor = (loopId) => model.runtime.loops[loopId] || {
    status: "no-run",
    planned: [],
    attempts: [],
    evidence_ids: [],
    evidence: [],
    drift: []
  };

  const navigate = (loopId, replace = false) => {
    if (!byId.has(loopId)) return;
    if (!replace && loopId === selectedId) return;
    selectedId = loopId;
    const url = `${location.pathname}${location.search}#loop=${encodeURIComponent(loopId)}`;
    if (replace) history.replaceState({loopId}, "", url);
    else history.pushState({loopId}, "", url);
    render();
    document.querySelector(".loop-summary h3")?.focus({preventScroll: true});
  };

  const renderBreadcrumbs = (loop) => {
    const root = document.getElementById("breadcrumbs");
    const chain = ancestors(loop.id);
    root.innerHTML = chain.map((id, index) => {
      const item = byId.get(id);
      const current = index === chain.length - 1;
      return `${index ? '<span class="crumb-separator" aria-hidden="true">/</span>' : ""}
        <button class="crumb" type="button" data-loop="${esc(id)}"
          ${current ? 'aria-current="page"' : ""}>${esc(item.label)}</button>`;
    }).join("");
    root.setAttribute("aria-label", `Loop path: ${chain.map((id) => byId.get(id).label).join(", ")}`);
  };

  const truthSummary = (loop, runtime) => {
    const latest = runtime.attempts.at(-1);
    const planned = runtime.planned.length
      ? `${runtime.planned.length} routed node${runtime.planned.length === 1 ? "" : "s"}`
      : model.runtime.attached ? "No routed node for this loop" : "Accepted loop contract";
    const actual = latest
      ? `${latest.result} by ${latest.effective_agent}`
      : model.runtime.attached ? "No attempt recorded" : "No run attached";
    const verified = runtime.evidence.length
      ? `Not revalidated: ${runtime.evidence.length} recorded evidence reference${runtime.evidence.length === 1 ? "" : "s"}`
      : model.runtime.attached ? "No recorded evidence reference" : "No run attached";
    const drift = !model.runtime.attached
      ? "Not evaluated without a run"
      : !latest ? "Not evaluated without an attempt"
      : runtime.drift.length ? `${runtime.drift.length} planned and actual mismatch${runtime.drift.length === 1 ? "" : "es"}`
      : "No declared scope or policy mismatch";
    return {planned, actual, verified, drift, loop};
  };

  const renderTruth = (loop, runtime) => {
    const value = truthSummary(loop, runtime);
    document.getElementById("truth-planned").textContent = value.planned;
    document.getElementById("truth-actual").textContent = value.actual;
    document.getElementById("truth-verified").textContent = value.verified;
    document.getElementById("truth-drift").textContent = value.drift;
  };

  const renderNavigation = (loop) => {
    const edges = childEdges.get(loop.id) || [];
    const parent = parentEdge.get(loop.id);
    const path = new Set(ancestors(loop.id));
    const rootsMarkup = `<p class="level-label">Active roots</p>
      <div class="loop-nav">${model.containment.roots.map((rootId) => {
        const root = byId.get(rootId);
        const current = rootId === loop.id;
        const state = current ? "current" : path.has(rootId) ? "branch" : "open";
        return `<button class="loop-button" type="button" data-loop="${esc(rootId)}"
          ${current ? 'aria-current="true"' : ""}>
          <strong>${esc(root.label)}</strong><span>${state}</span>
        </button>`;
      }).join("")}</div>`;
    const parentMarkup = parent
      ? `<p class="level-label">Parent loop</p>
         <div class="loop-nav">
           <button class="loop-button" type="button" data-loop="${esc(parent.parent_loop_id)}">
             <strong>${esc(byId.get(parent.parent_loop_id).label)}</strong><span>up</span>
           </button>
         </div>`
      : "";
    const childrenMarkup = edges.length
      ? `<div class="loop-nav" id="child-loop-nav">${edges.map((edge) => {
          const child = byId.get(edge.child_loop_id);
          return `<button class="loop-button" type="button" data-loop="${esc(child.id)}">
            <strong>${esc(child.label)}</strong><span>open</span>
          </button>`;
        }).join("")}</div>`
      : `<p class="empty">This loop contains no child loops. Its feedback stays in the local flow.</p>`;
    document.getElementById("navigation-content").innerHTML = `
      <div class="loop-summary">
        <h3 tabindex="-1">${esc(loop.label)}</h3>
        <p>${esc(loop.purpose)}</p>
        <span class="mono-id" translate="no">${esc(loop.id)}</span>
      </div>
      ${rootsMarkup}
      ${parentMarkup}
      <p class="level-label">Contained loops</p>
      ${childrenMarkup}`;
    document.getElementById("navigation-count").textContent = `${edges.length} child${edges.length === 1 ? "" : "ren"}`;
  };

  const renderFlow = (loop) => {
    const flow = loop.local_control_flow;
    const states = list(flow.states);
    const transitions = list(flow.transitions);
    const feedback = transitions.filter((item) => item.kind === "feedback");
    document.getElementById("flow-title").textContent = `${loop.label} local flow`;
    document.getElementById("flow-count").textContent =
      `${states.length} states, ${transitions.length} transitions`;
    const stateMarkup = states.length
      ? `<ol class="state-rail">${states.map((state) => `
          <li class="state-node" data-kind="${esc(state.kind)}">
            <span class="kind">${esc(state.kind)}</span>
            <strong>${esc(state.label)}</strong>
            <span class="state-id" translate="no">${esc(state.id)}</span>
          </li>`).join("")}</ol>`
      : `<p class="empty">No local states are declared.</p>`;
    const transitionMarkup = transitions.length
      ? `<ol class="transition-list">${transitions.map((transition) => `
          <li class="transition" data-kind="${esc(transition.kind)}">
            <span class="route-id" translate="no">${esc(transition.from)}</span>
            <span class="arrow" aria-label="to">-&gt;</span>
            <span class="route-id" translate="no">${esc(transition.to)}</span>
            <span class="guard">${esc(transition.kind)}: ${esc(transition.guard)}</span>
          </li>`).join("")}</ol>`
      : `<p class="empty">No local transitions are declared.</p>`;
    const feedbackMarkup = feedback.length
      ? `<div class="feedback-note"><strong>Bounded feedback</strong>
          <ul>${feedback.map((item) => {
            const budget = item.feedback_budget || {};
            return `<li>${esc(item.id)}: maximum ${esc(text(budget.max_traversals))} traversal${budget.max_traversals === 1 ? "" : "s"}.
              Exhaustion goes to ${esc(text(budget.on_exhaustion_state))} with outcome ${esc(text(budget.on_exhaustion_outcome))}.</li>`;
          }).join("")}</ul></div>`
      : `<p class="feedback-note">No cyclic feedback route is declared in this local flow.</p>`;
    document.getElementById("flow-content").innerHTML = `
      <div class="loop-summary">
        <h3>${esc(loop.label)}</h3>
        <p>Containment selects the loop. The map below shows only this loop's local control flow.</p>
      </div>
      ${stateMarkup}
      <section class="transition-section" aria-labelledby="transition-heading">
        <h3 id="transition-heading">Transition ledger</h3>
        ${transitionMarkup}
        ${feedbackMarkup}
      </section>`;
  };

  const kvRows = (items) => items.map(([key, value]) =>
    `<dt>${esc(key)}</dt><dd>${esc(text(value))}</dd>`
  ).join("");

  const renderDetails = (loop, runtime) => {
    const budgets = loop.budgets || {};
    const authority = loop.authority || {};
    const contracts = list(loop.evidence_contracts);
    const invocations = list(loop.child_invocations);
    const latest = runtime.attempts.at(-1);
    const plannedList = runtime.planned.length
      ? `<ul class="plain-list">${runtime.planned.map((item) => `
          <li><strong>${esc(item.node_id)}</strong> role ${esc(item.role)}.
          Model: ${esc(item.model_intent)}. Skill: ${esc(item.skill_intent)}.
          Reasoning: ${esc(item.reasoning_intent)}.</li>`).join("")}</ul>`
      : `<p class="empty">${model.runtime.attached ? "No routed node is declared for this loop." : "The accepted loop contract is the only plan layer."}</p>`;
    const runtimeRows = [
      ["Run", model.runtime.attached ? model.runtime.id : "No run attached"],
      ["Loop status", model.runtime.attached ? runtime.status : "planned only"],
      ["Attempts", runtime.attempts.length],
      ["Evidence refs", runtime.evidence_ids.length],
      ["Run outcome", model.runtime.outcome || "Not recorded"]
    ];
    const actualList = latest
      ? `<ul class="plain-list">
          <li><strong>Agent</strong> ${esc(latest.effective_agent)}</li>
          <li><strong>Model</strong> ${esc(latest.effective_model)}</li>
          <li><strong>Skill</strong> ${esc(latest.effective_skill)}</li>
          <li><strong>Result</strong> ${esc(latest.result)}</li>
          <li><strong>Attempt</strong> ${esc(latest.id)}</li>
        </ul>`
      : `<p class="empty">${model.runtime.attached ? "No attempt recorded for this loop." : "Attach a run card to inspect factual attempts."}</p>`;
    const driftList = runtime.drift.length
      ? `<ul class="plain-list">${runtime.drift.map((item) =>
          `<li><strong>${esc(item.field)}</strong> planned ${esc(text(item.planned))}; actual ${esc(text(item.actual))}</li>`
        ).join("")}</ul>`
      : `<p class="empty">${latest ? "No declared scope or policy mismatch." : "Drift is not evaluated without a factual attempt."}</p>`;
    const evidenceList = runtime.evidence.length
      ? `<p class="empty">Recorded reference metadata only. This Atlas does not reload or revalidate payload bytes.</p>
         <ul class="plain-list">${runtime.evidence.map((item) => `
           <li><strong>${esc(item.id)}</strong> ${esc(item.path)}.
           Digest: ${esc(item.digest)}</li>`).join("")}</ul>`
      : `<p class="empty">${model.runtime.attached ? "No evidence reference is recorded for this loop." : "Attach a run card to inspect recorded evidence references."}</p>`;
    const contractList = contracts.length
      ? `<ul class="plain-list">${contracts.map((item) => `
          <li><strong>${esc(item.id)}</strong> ${esc(item.description)}
          Required claims: ${esc(text(item.required_claims, "none"))}.
          Accepted results: ${esc(text(item.accepted_results, "none"))}.
          Producer: ${esc(item.producer_capability)}.
          Candidate binding: ${item.candidate_binding_required ? "required" : "not required"}.
          Policy binding: ${item.policy_binding_required ? "required" : "not required"}.
          Reviewer: ${esc(text(item.reviewer_capability, "not required"))}.
          Independence from: ${esc(text(item.independent_from_capability, "not required"))}.</li>`).join("")}</ul>`
      : `<p class="empty">No evidence contract is referenced by this loop.</p>`;
    const invocationList = invocations.length
      ? `<ul class="plain-list">${invocations.map((item) => `
          <li><strong>${esc(item.child_loop_id)}</strong> at ${esc(item.at_state)}.
          Timeout ${esc(item.timeout_seconds)} seconds; failure goes to ${esc(item.failure_state)}.</li>`).join("")}</ul>`
      : `<p class="empty">No child invocation is declared.</p>`;
    document.getElementById("details-title").textContent = `${loop.label} contract`;
    document.getElementById("details-status").textContent =
      model.runtime.attached ? runtime.status : "planned";
    document.getElementById("details-content").innerHTML = `
      <section class="detail-group">
        <h3>Interface</h3>
        <dl class="kv">${kvRows([
          ["Inputs", loop.inputs],
          ["Outputs", loop.outputs],
          ["Entry state", loop.local_control_flow.entry_state],
          ["Terminal states", loop.local_control_flow.terminal_state_ids]
        ])}</dl>
      </section>
      <section class="detail-group">
        <h3>Budgets</h3>
        <dl class="kv">${kvRows([
          ["Attempts", budgets.max_attempts],
          ["Elapsed seconds", budgets.max_elapsed_seconds],
          ["Cost units", budgets.max_cost_units],
          ["On exhaustion", budgets.on_exhaustion]
        ])}</dl>
      </section>
      <section class="detail-group">
        <h3>Authority</h3>
        <dl class="kv">${kvRows([
          ["Execute", authority.execute_capability],
          ["Accept", authority.accept_capability],
          ["Escalate", authority.escalate_capability]
        ])}</dl>
      </section>
      <section class="detail-group">
        <h3>Run truth</h3>
        <dl class="kv">${kvRows(runtimeRows)}</dl>
      </section>
      <section class="detail-group">
        <h3>Recorded evidence references</h3>
        ${evidenceList}
      </section>
      <section class="detail-group">
        <h3>Planned route</h3>
        ${plannedList}
      </section>
      <section class="detail-group">
        <h3>Latest actual route</h3>
        ${actualList}
      </section>
      <section class="detail-group">
        <h3>Drift</h3>
        ${driftList}
      </section>
      <section class="detail-group">
        <h3>Evidence contracts</h3>
        ${contractList}
      </section>
      <section class="detail-group">
        <h3>Child invocations</h3>
        ${invocationList}
      </section>`;
  };

  const render = () => {
    const loop = byId.get(selectedId) || byId.get(model.containment.default_root);
    if (!loop) return;
    selectedId = loop.id;
    const runtime = runtimeFor(loop.id);
    renderBreadcrumbs(loop);
    renderTruth(loop, runtime);
    renderNavigation(loop);
    renderFlow(loop);
    renderDetails(loop, runtime);
    document.title = `${loop.label} | Concord Loom Atlas`;
    document.getElementById("selection-live").textContent = `Selected loop: ${loop.label}`;
  };

  document.addEventListener("click", (event) => {
    const target = event.target.closest("[data-loop]");
    if (target instanceof HTMLButtonElement) navigate(target.dataset.loop);
  });

  document.getElementById("navigation-content").addEventListener("keydown", (event) => {
    if (!["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) return;
    const buttons = [...event.currentTarget.querySelectorAll("button[data-loop]")];
    if (!buttons.length) return;
    const current = buttons.indexOf(document.activeElement);
    let next = current;
    if (event.key === "ArrowDown") next = Math.min(buttons.length - 1, current + 1);
    if (event.key === "ArrowUp") next = Math.max(0, current - 1);
    if (event.key === "Home") next = 0;
    if (event.key === "End") next = buttons.length - 1;
    event.preventDefault();
    buttons[Math.max(0, next)].focus();
  });

  addEventListener("popstate", () => {
    selectedId = fromHash();
    render();
  });
  addEventListener("hashchange", () => {
    const next = fromHash();
    if (next !== selectedId) {
      selectedId = next;
      render();
    }
  });

  if (!location.hash || !byId.has(selectedId)) {
    selectedId = model.containment.default_root;
    navigate(selectedId, true);
  } else {
    render();
  }
})();
""".strip()


def _copy_objects(values: Any) -> list[dict[str, Any]]:
    if not isinstance(values, list):
        return []
    return [deepcopy(value) for value in values if isinstance(value, dict)]


def _reachable_loop_ids(
    registry: Mapping[str, Any], roots: list[str]
) -> set[str]:
    adjacency: dict[str, list[str]] = {}
    for edge in registry["containment_graph"]["edges"]:
        adjacency.setdefault(edge["parent_loop_id"], []).append(edge["child_loop_id"])
    reachable: set[str] = set()
    pending = list(reversed(roots))
    while pending:
        current = pending.pop()
        if current in reachable:
            continue
        reachable.add(current)
        pending.extend(reversed(adjacency.get(current, [])))
    return reachable


def _validate_run_identity(
    run_card: Mapping[str, Any],
    binding: Mapping[str, Any],
    registry: Mapping[str, Any],
    policy: Mapping[str, Any],
    *,
    schema_store: SchemaStore,
) -> None:
    schema_store.validate(dict(run_card), "run-card.schema.json")
    expected = {
        "binding_digest": binding["binding_digest"],
        "registry_digest": digest(registry),
        "policy_digest": digest(policy),
    }
    for field, value in expected.items():
        if run_card[field] != value:
            raise AtlasError(f"run card {field} does not match Atlas inputs")
    if run_card["root_loop_id"] not in binding["active_root_loop_ids"]:
        raise AtlasError("run card root is not active in the binding")
    loop_ids = {item["id"] for item in registry["loops"]}
    run_loop_ids = _reachable_loop_ids(registry, [run_card["root_loop_id"]])
    if any(item["loop_id"] not in loop_ids for item in run_card["planned_route"]):
        raise AtlasError("run card route refers to an unknown loop")
    if any(item["loop_id"] not in loop_ids for item in run_card["nodes"]):
        raise AtlasError("run card node refers to an unknown loop")
    if any(
        item["loop_id"] not in run_loop_ids
        for item in (*run_card["planned_route"], *run_card["nodes"])
    ):
        raise AtlasError("run card route leaves the selected run root subtree")
    evidence_ids = [item["id"] for item in run_card["evidence"]]
    if len(evidence_ids) != len(set(evidence_ids)):
        raise AtlasError("run card evidence reference ids must be unique")
    known_evidence_ids = set(evidence_ids)
    dangling = {
        evidence_id
        for node in run_card["nodes"]
        for evidence_id in node["evidence_ids"]
        if evidence_id not in known_evidence_ids
    }
    if dangling:
        raise AtlasError(
            f"run card has dangling evidence references: {sorted(dangling)!r}"
        )


def _route_drift(
    planned: Mapping[str, Any],
    attempt: Mapping[str, Any],
    run_card: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    def add(field: str, planned_value: Any, actual_value: Any) -> None:
        findings.append(
            {"field": field, "planned": planned_value, "actual": actual_value}
        )

    network_order = {"none": 0, "read": 1, "write": 2}
    planned_scope = planned.get("scope", {})
    planned_network = planned_scope.get("network")
    actual_network = attempt.get("network")
    if (
        planned_network in network_order
        and actual_network in network_order
        and network_order[actual_network] > network_order[planned_network]
    ):
        add("network scope", planned_network, actual_network)

    planned_mutations = set(planned_scope.get("external_mutations", []))
    actual_mutations = set(attempt.get("external_mutations", []))
    if not actual_mutations.issubset(planned_mutations):
        add(
            "external mutations",
            sorted(planned_mutations),
            sorted(actual_mutations),
        )

    allowed_tools = set(policy["execution"]["allowed_tools"])
    actual_tools = set(attempt.get("effective_tools", []))
    if not actual_tools.issubset(allowed_tools):
        add("tool policy", sorted(allowed_tools), sorted(actual_tools))

    egress = attempt.get("data_egress", {})
    actual_model = (egress.get("provider", ""), attempt.get("effective_model"))
    allowed_models = {
        (item["provider"], item["model"])
        for item in policy["execution"]["model_policy"]["allowed_models"]
    }
    if actual_model not in allowed_models:
        add(
            "model policy",
            [f"{provider}:{model}" for provider, model in sorted(allowed_models)],
            f"{actual_model[0]}:{actual_model[1]}",
        )

    principals = {
        item["id"]: set(item["roles"]) for item in policy["authority"]["principals"]
    }
    principal_roles = principals.get(attempt.get("effective_principal_id"), set())
    if planned.get("role") not in principal_roles:
        add(
            "principal role",
            planned.get("role"),
            sorted(principal_roles) or "unknown principal",
        )

    identity_checks = (
        ("policy digest", run_card["policy_digest"], attempt.get("policy_digest")),
        (
            "candidate digest",
            run_card["candidate_tree_digest"],
            attempt.get("candidate_tree_digest"),
        ),
    )
    for field, planned_value, actual_value in identity_checks:
        if planned_value != actual_value:
            add(field, planned_value, actual_value)
    return findings


def _runtime_projection(
    run_card: Mapping[str, Any] | None,
    loop_ids: set[str],
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    if run_card is None:
        return {
            "attached": False,
            "id": None,
            "status": "no-run",
            "outcome": None,
            "loops": {},
        }
    planned_by_node = {
        item["node_id"]: deepcopy(item) for item in run_card["planned_route"]
    }
    evidence_by_id = {
        item["id"]: deepcopy(item) for item in run_card["evidence"]
    }
    per_loop: dict[str, dict[str, Any]] = {
        loop_id: {
            "status": "pending",
            "planned": [],
            "attempts": [],
            "evidence_ids": [],
            "evidence": [],
            "drift": [],
        }
        for loop_id in loop_ids
    }
    for item in run_card["planned_route"]:
        per_loop[item["loop_id"]]["planned"].append(deepcopy(item))
    for node in run_card["nodes"]:
        target = per_loop[node["loop_id"]]
        target["status"] = node["status"]
        target["attempts"].extend(deepcopy(node["attempts"]))
        target["evidence_ids"].extend(node["evidence_ids"])
        target["evidence"].extend(
            deepcopy(evidence_by_id[evidence_id])
            for evidence_id in node["evidence_ids"]
            if evidence_id in evidence_by_id
        )
        planned = planned_by_node.get(node["node_id"])
        if planned and node["attempts"]:
            target["drift"].extend(
                _route_drift(
                    planned,
                    node["attempts"][-1],
                    run_card,
                    policy,
                )
            )
    for target in per_loop.values():
        target["planned"].sort(key=lambda item: item["node_id"])
        target["attempts"].sort(key=lambda item: (item["finished_at"], item["id"]))
        target["evidence_ids"] = sorted(set(target["evidence_ids"]))
        target["evidence"].sort(key=lambda item: item["id"])
        target["drift"].sort(key=lambda item: item["field"])
    return {
        "attached": True,
        "id": run_card["id"],
        "status": run_card["status"],
        "outcome": run_card.get("root_outcome"),
        "candidate_tree_digest": run_card["candidate_tree_digest"],
        "verification": "recorded-references-not-revalidated",
        "loops": per_loop,
    }


def _atlas_model(
    binding: Mapping[str, Any],
    registry: Mapping[str, Any],
    policy: Mapping[str, Any],
    run_card: Mapping[str, Any] | None,
) -> dict[str, Any]:
    active_roots = list(binding["active_root_loop_ids"])
    reachable_loop_ids = _reachable_loop_ids(registry, active_roots)
    loops = [
        item
        for item in _copy_objects(registry["loops"])
        if item["id"] in reachable_loop_ids
    ]
    contracts = {
        item["id"]: item for item in _copy_objects(registry["evidence_contracts"])
    }
    edges = [
        item
        for item in _copy_objects(registry["containment_graph"]["edges"])
        if item["parent_loop_id"] in reachable_loop_ids
        and item["child_loop_id"] in reachable_loop_ids
    ]
    invocations: dict[str, list[dict[str, Any]]] = {}
    for edge in edges:
        invocations.setdefault(edge["parent_loop_id"], []).append(edge)
    for loop in loops:
        contract_ids = sorted(
            {
                contract_id
                for transition in loop["local_control_flow"]["transitions"]
                for contract_id in transition["evidence_contract_ids"]
            }
        )
        loop["evidence_contracts"] = [
            deepcopy(contracts[contract_id])
            for contract_id in contract_ids
            if contract_id in contracts
        ]
        loop["child_invocations"] = invocations.get(loop["id"], [])
    loops.sort(key=lambda item: item["id"])
    loop_ids = {item["id"] for item in loops}
    runtime = _runtime_projection(run_card, loop_ids, policy)
    return {
        "framework": "Concord Loom",
        "framework_version": binding["framework_version"],
        "binding": {
            "id": binding["id"],
            "digest": binding["binding_digest"],
            "created_at": binding["created_at"],
        },
        "registry_digest": digest(registry),
        "policy": {
            "id": policy["id"],
            "digest": digest(policy),
            "child_receipts_auto_accept_parent": policy["evidence"][
                "child_receipts_auto_accept_parent"
            ],
        },
        "containment": {
            "roots": active_roots,
            "default_root": (
                run_card["root_loop_id"] if run_card is not None else active_roots[0]
            ),
            "edges": edges,
        },
        "loops": loops,
        "runtime": runtime,
    }


def _script_safe_json(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return (
        encoded.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def _csp_hash(value: str) -> str:
    raw = hashlib.sha256(value.encode("utf-8")).digest()
    return base64.b64encode(raw).decode("ascii")


def render_atlas(
    *,
    binding: Mapping[str, Any],
    registry: Mapping[str, Any],
    policy: Mapping[str, Any],
    run_card: Mapping[str, Any] | None = None,
) -> str:
    """Render validated inputs to deterministic standalone HTML."""

    store = SchemaStore()
    binding_value = deepcopy(dict(binding))
    registry_value = deepcopy(dict(registry))
    policy_value = deepcopy(dict(policy))
    validate_policy(policy_value, schema_store=store)
    validate_registry(registry_value, policy_value, schema_store=store)
    validate_binding(
        binding_value,
        registry_value,
        policy_value,
        schema_store=store,
    )
    run_value = deepcopy(dict(run_card)) if run_card is not None else None
    if run_value is not None:
        _validate_run_identity(
            run_value,
            binding_value,
            registry_value,
            policy_value,
            schema_store=store,
        )
    model = _atlas_model(binding_value, registry_value, policy_value, run_value)
    script = "const ATLAS_MODEL=" + _script_safe_json(model) + ";\n" + _SCRIPT
    csp = (
        "default-src 'none'; "
        f"style-src 'sha256-{_csp_hash(_STYLE)}'; "
        f"script-src 'sha256-{_csp_hash(script)}'; "
        "img-src data:; connect-src 'none'; font-src 'none'; "
        "object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
    )
    runtime_label = (
        f"run {run_value['id']}: {run_value['status']}"
        if run_value is not None
        else "No run attached"
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <meta name="theme-color" content="#f1f3f0">
  <meta http-equiv="Content-Security-Policy" content="{csp}">
  <title>Concord Loom Atlas</title>
  <style>{_STYLE}</style>
</head>
<body>
  <a class="skip-link" href="#atlas-main">Skip to Atlas</a>
  <header class="masthead">
    <div class="brand">
      <h1>Concord Loom Atlas</h1>
      <p>Nested loop system</p>
    </div>
    <div class="masthead-meta">
      <strong>{html_escape(runtime_label)}</strong>
      <p translate="no">{html_escape(str(binding_value["id"]))}</p>
    </div>
  </header>
  <nav class="breadcrumbs" id="breadcrumbs" aria-label="Loop path"></nav>
  <section class="truth-bar" aria-label="Truth layers">
    <div class="truth-cell" data-layer="planned">
      <h2>Planned</h2><p id="truth-planned"></p>
    </div>
    <div class="truth-cell" data-layer="actual">
      <h2>Actual</h2><p id="truth-actual"></p>
    </div>
    <div class="truth-cell" data-layer="verified">
      <h2>Verified</h2><p id="truth-verified"></p>
    </div>
    <div class="truth-cell" data-layer="drift">
      <h2>Drift</h2><p id="truth-drift"></p>
    </div>
  </section>
  <main class="atlas-shell" id="atlas-main">
    <aside class="panel navigation-panel" aria-labelledby="navigation-title">
      <div class="panel-heading">
        <h2 id="navigation-title">Containment</h2>
        <span id="navigation-count"></span>
      </div>
      <div id="navigation-content"></div>
    </aside>
    <section class="panel flow-panel" aria-labelledby="flow-title">
      <div class="panel-heading">
        <h2 id="flow-title">Local flow</h2>
        <span id="flow-count"></span>
      </div>
      <div class="map-key" aria-label="Map key">
        <span class="key-item"><span class="key-mark" aria-hidden="true"></span>local transition</span>
        <span class="key-item"><span class="key-mark feedback" aria-hidden="true"></span>bounded feedback</span>
        <span class="key-item"><span class="key-mark containment" aria-hidden="true"></span>child invocation</span>
      </div>
      <div id="flow-content"></div>
    </section>
    <aside class="panel details-panel" aria-labelledby="details-title">
      <div class="panel-heading">
        <h2 id="details-title">Loop contract</h2>
        <span class="run-status" id="details-status"></span>
      </div>
      <div class="detail-stack" id="details-content"></div>
    </aside>
  </main>
  <p id="selection-live" class="selection-live" aria-live="polite"></p>
  <footer class="footer">
    <span>Accepted structure is not runtime verification.</span>
    <span translate="no">{html_escape(str(binding_value["binding_digest"]))}</span>
  </footer>
  <script>{script}</script>
</body>
</html>
"""


def generate_atlas(
    *,
    binding: Mapping[str, Any],
    registry: Mapping[str, Any],
    policy: Mapping[str, Any],
    output: str | Path,
    run_card: Mapping[str, Any] | None = None,
    check: bool = False,
) -> Path:
    """Write an Atlas atomically, or fail when check mode detects drift."""

    target = Path(output)
    rendered = render_atlas(
        binding=binding,
        registry=registry,
        policy=policy,
        run_card=run_card,
    ).encode("utf-8")
    if check:
        try:
            current = target.read_bytes()
        except FileNotFoundError as exc:
            raise AtlasStaleError(f"Atlas output is missing: {target}") from exc
        if current != rendered:
            raise AtlasStaleError(f"Atlas output is stale: {target}")
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o644)
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()
    return target
