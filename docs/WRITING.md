# Writing for humans

[Русская версия](ru/WRITING.md)

Documentation is part of the product. A schema may be exact and still leave a
reader unable to act. Concord Loom therefore reviews meaning and comprehension,
not only links, headings, and translation length.

## The reader test

Within the first 150 words of a top-level concept, a reader should be able to
answer three questions:

1. What is it?
2. Why does it matter?
3. What is one concrete example?

If the text cannot answer those questions, it is not ready.

## Write the idea before the identifier

Use ordinary words in prose. Introduce a machine identifier only when the
reader needs to recognize it in a command, JSON document, or Atlas view.

Good:

> The active configuration lists the cycles and their authority. The JSON
> artifact calls this configuration a `binding`.

Bad:

> The active binding materializes policy-bound containment semantics.

## Keep fact states separate

Say whether something was observed, proposed, accepted, planned, run, or
verified. Do not use a confident verb to hide a missing decision or missing
evidence.

## Translation preserves meaning

Russian text is edited as Russian prose. It is not an English sentence with
translated nouns. Product identifiers, commands, paths, JSON keys, and code
remain unchanged. Explanatory terms follow
[`terminology.json`](terminology.json).

## Comprehension is an independent cycle

`review-comprehension` checks the candidate after authoring and localization.
Its reviewer looks for unexplained jargon, literal translation, empty claims,
missing examples, and instructions that cannot be followed. The author cannot
close this check by asserting that the text is clear.

Automated checks catch known terminology leaks and structural defects. They do
not replace a reader.
