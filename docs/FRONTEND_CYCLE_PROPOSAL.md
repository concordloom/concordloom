# Frontend cycle proposal

Language: **English** | [Русский](ru/FRONTEND_CYCLE_PROPOSAL.md)

Status: **proposal only — not activated**

Base: active Concord Loom self-binding v9

## Decision requested

Approve strengthening the existing frontend cycle without adding or removing
loops.

The current topology is sufficient. The failure was in its acceptance
contracts: a page could work mechanically while remaining visibly unlike the
accepted concept. The successor should make that impossible to call complete.

## What the user should receive

Every frontend change should end with one exact candidate that:

- follows the accepted visual contract on every public route;
- works at 360×800, 390×844, 844×390, 768×1024, 1024×768, 1440×900,
  and 1920×1080;
- works in English and Russian, with English as the deterministic default;
- stays understandable with JavaScript disabled;
- has honest loading, empty, stale, and error states;
- supports keyboard use, 200% zoom, and reduced motion;
- preserves URLs, browser Back and Forward, language, and Atlas location;
- has no overlaps, clipped labels, accidental horizontal scrolling, duplicate
  navigation, dead controls, or targets smaller than 44×44 CSS pixels;
- has a readable text or tree alternative for every interactive graph;
- is reviewed visually by an independent critic against the accepted concept,
  not only against its previous screenshot.

## Existing cycle, stronger contracts

### 1. Define frontend concept

Turn product intent and references into one visual contract. The contract names
the composition, hierarchy, responsive changes, component states, motion,
forbidden patterns, supported viewports, and evidence required for acceptance.

Use `ui-ux-pro-max`, the Concord Loom design system, and relevant design skills
as pinned resources. A generated recommendation is input, not a second source
of truth.

### 2. Accept frontend concept

An operator accepts or rejects the exact contract digest. Screenshots and prose
that are not bound to that digest cannot substitute for this decision.

### 3. Maintain interface workshop

The workshop must use production tokens and production component CSS. It must
show normal, hover, focus, pressed, disabled, loading, empty, error, stale,
long-copy, English, and Russian states. A mock component that does not share
production styles is not evidence.

Storybook is optional. The dependency-free workshop remains the default until
component count or collaboration needs justify the additional runtime and
maintenance cost.

### 4. Implement frontend candidate

Build only from the accepted contract and workshop components. Route state,
Atlas selection, language, and overlays must be addressable and restorable.
Technical data stays available without dominating the main interface.

### 5. Maintain browser harness

The harness must test the exact viewport and locale matrix, no-JavaScript
rendering, loading and failure paths, keyboard focus, modal isolation, minimum
target size, graph geometry, label collisions, browser history, zoom, reduced
motion, and accessibility rules.

The Playwright MCP may help an author inspect the interface, but deterministic
Playwright tests and exact artifacts remain the verification source.

### 6. Verify frontend candidate

A model-free verifier runs the pinned harness against the exact candidate. It
produces screenshots, geometry results, accessibility results, runtime state
evidence, and a SHA-256 manifest of the visual baselines. It cannot update its
own baselines and cannot make a taste judgment.

### 7. Critique frontend experience

A fresh high-reasoning critic compares the exact concept, contract, candidate,
and full screenshot matrix. The critic checks visual fidelity, hierarchy,
clarity, Russian copy, and whether the interface feels like one product.

Its verdict is `PASS`, `REVISE`, or `INDETERMINATE`. A mechanical pass cannot
override `REVISE`.

## Revision boundary

`REVISE` returns the candidate to implementation, then verification and
independent critique run again on a new digest. After three failed revisions,
the run stops and asks the operator whether the concept, the implementation, or
the acceptance contract should change.

No agent may silently weaken the visual contract, update golden screenshots to
hide a regression, or accept work it authored.

## Model and resource budget

| Work | Default route |
|---|---|
| Concept, workshop, implementation | Terra, medium reasoning |
| Harness maintenance | Terra, low reasoning |
| Deterministic browser and manifest checks | No model |
| Routine failure triage | Luna, low reasoning where a model is useful |
| Final independent visual critique | Sol, high reasoning |
| Russian interface and documentation review | `ru-text`; escalate to Sol only for unresolved high-impact copy |

This keeps expensive reasoning at the judgment boundary instead of spending it
on every CSS or test change.

## Exact evidence required

One candidate digest must bind:

1. the accepted visual-contract digest;
2. the source tree and generated site bytes;
3. the production workshop;
4. the browser harness;
5. screenshots for all accepted routes, locales, states, and viewports;
6. the visual-baseline manifest;
7. deterministic verification results;
8. an independent critic receipt.

Publication remains a separate publisher action. A passing frontend candidate
is not deployment authority.

## Proposed successor delta

If this proposal is approved, a future self-binding successor should:

- keep the current `design-site-experience` topology;
- bind `ui-ux-pro-max`, `ru-text`, design-system guidance, and the browser
  adapter as versioned resources where they are used;
- replace broad prose outputs with the exact evidence above;
- make the three-revision boundary and return path explicit;
- require negative geometry, interaction, and language assertions;
- reject a critic receipt from the candidate author;
- document the public guard command consistently as
  `python3 -m concordloom run guard`.

Activation must remain a separate operator decision. This document does not
change the active binding.
