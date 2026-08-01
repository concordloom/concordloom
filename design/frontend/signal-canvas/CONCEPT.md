# Signal Canvas

Status: implementation candidate

Signal Canvas is the proposed visual direction for the whole Concord Loom
public site. It replaces the rejected Patch Panel direction.

## Product feeling

The interface should feel like a small, confident product studio:

- serious enough for engineering and governance;
- informal enough to invite exploration;
- tactile without looking like a game;
- expressive without hiding the product behind decoration.

## One visual idea

Every page is a warm canvas. Work appears as bordered, movable pieces connected
by clear lines. Mint marks the current route. Cobalt marks information, coral
marks a boundary, and yellow marks a pending choice. Color never replaces text.

The Atlas is the product demonstration, not a dashboard inside the product. It
uses the full available viewport, one breadcrumb path, one graph, and an
on-demand detail sheet.

## Non-negotiable rules

1. The first viewport explains the product and shows a working graph.
2. The Atlas never reserves permanent width for history or details.
3. A selected cycle is clearly larger than its direct children.
4. Node labels remain readable at every accepted viewport.
5. Entering a child preserves spatial direction; going back reverses it.
6. Mobile uses a vertical map with one child per row, never a squeezed desktop
   constellation.
7. All controls have visible hover, focus, pressed, loading, empty, and error
   states.
8. Long-form pages use the same canvas, type, borders, buttons, and colors.
9. Technical identifiers stay behind optional details.
10. Decorative elements may support hierarchy but may not compete with content.

## Anti-patterns

- no permanent lifecycle rail in the site header;
- no tiny diagram floating inside a mostly empty panel;
- no duplicated navigation panes;
- no background illustration behind the Atlas;
- no monochrome card dashboard;
- no fantasy, stone, metal, neon, glass, or HUD treatment;
- no screenshot gate that proves only that bytes exist.

## Reference

[`index.html`](index.html) is the compact interactive reference. Production
screens may contain more content, but they must preserve its hierarchy,
material, color roles, control feedback, and graph readability.
