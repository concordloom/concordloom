# Visual contract pointer

There is one normative visual contract:
[`visual-contract.json`](visual-contract.json).

This page is only a human-readable pointer. It does not define another visual
direction.

The current implementation candidate is **Signal Canvas**. Its reference files
live under [`signal-canvas/`](signal-canvas/). Production tokens live in
[`../../site/design-tokens.json`](../../site/design-tokens.json). The component
workshop and every public route consume those production tokens.

The candidate is not accepted merely because it renders or because screenshots
exist. Acceptance requires:

1. deterministic geometry, accessibility, interaction, language, and reflow
   checks for the exact candidate;
2. pixel comparisons against baselines that CI cannot update;
3. an independent critic comparing the exact candidate with the exact
   reference and returning `PASS`; and
4. an explicit visual-contract decision before baseline changes or
   publication.

The geometry gate checks every localized cycle title at every accepted viewport.
Words may wrap only at word boundaries. The no-JavaScript status message must
also remain fully visible after direct navigation.

The factual source of the Atlas remains the active Concord Loom binding. The
visual contract governs presentation only.
