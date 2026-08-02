# Release and public-site verification

Concord Loom v0.1 releases bind source, package, independent reviews, and a
durable bootstrap receipt.

The `v0.1.0` instructions below are historical verification for that immutable
tag. Current development additionally carries the accepted, domain-neutral
Concord Loom self-binding and a bilingual Pages candidate. Do not use current
working-tree files to revise claims about the tagged release.

## Verify source

```bash
git clone https://github.com/concordloom/concordloom.git
cd concordloom
git fetch --tags
git checkout --detach v0.1.0
git status --short
./tools/check.sh
```

The checkout should be clean and the gate should end with `CHECK_OK`.

## Verify release assets

Download the wheel, source archive, `SHA256SUMS`, and bootstrap receipt bundle
from the `v0.1.0` GitHub release. Then run:

```bash
sha256sum --check SHA256SUMS
python3 -m venv /tmp/concordloom-release-check
/tmp/concordloom-release-check/bin/python -m pip install \
  --no-deps concordloom-0.1.0-py3-none-any.whl
/tmp/concordloom-release-check/bin/concordloom --version
/tmp/concordloom-release-check/bin/python -m pip check
```

The wheel is expected to have no runtime Python dependencies. Its inventory
contains the portable package, seventeen public schemas, and the generic SDLC
artifact chain.

## Verify the bootstrap receipt

The release receipt bundle embeds:

- the completed bootstrap run card;
- the exact bootstrap cycle and compute policy;
- the pinned candidate commit and tree digest;
- factual node attempts;
- independent R, L, Q, and M evidence; and
- its own canonical SHA-256 digest.

The runner exports it only from a complete run and revalidates the candidate,
all nodes, review bindings, and author/reviewer separation. The release
`SHA256SUMS` anchors the exported bytes next to the tagged candidate.

A self-digest alone is not authentication. Verify the release/tag provenance
appropriate to your environment, and add signed attestations when
cryptographic identity is required.

## Evidence levels

Do not collapse these claims:

- Unit and integration tests prove deterministic code paths.
- An installed-wheel smoke proves packaging and command availability.
- Browser inspection proves the rendered Atlas states and viewports examined.
- Independent quality review evaluates the exact pinned candidate.
- A public-clone smoke proves the published tag and assets are retrievable.

None of these alone proves product value, complete test oracles, or
cryptographic reviewer identity.

## Verify the accepted self-binding

Validate the exact binding, registry, policy, predecessor link, and append-only
catalog rather than relying on the label “current.” The accepted root is
`steward-concordloom`; the active development model contains ten responsibility
areas and 66 cycles. Observe, negotiate, bind, execute, verify, publish, and
evolve are run phases, not the top-level containment graph.

The binding was activated through a decision separate from the evolution
proposal. The proposal retains `activation_allowed: false`, and the predecessor
binding remains addressable in the catalog. This is the evidence for governed
self-binding; a generated Atlas or website copy is not.

## Verify the bilingual Pages candidate

From a checkout containing the current candidate:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 tools/build_site.py --check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 tools/check_site.py
```

The checks bind `site/data/atlas.json` to the active accepted binding, require
substantial English/Russian copy, verify local assets and accessibility hooks,
and require the social preview to be exactly 1280 × 640 pixels. The hero and
social-preview files under `docs/assets/` are source communication assets; the
copies under `site/assets/` must match the deterministic site build.

The Pages workflow is scoped publication machinery. Review its trigger,
artifact path, `contents: read`, `pages: write`, and `id-token: write`
permissions, plus the separate `github-pages` deployment environment. A
successful local check or workflow build proves neither that Pages was
authorized nor that a public URL is live.

Live verification requires the deployment record and URL for the exact
candidate, followed by a fresh fetch that checks the bilingual switch, local
assets, social metadata, and accepted Atlas digest. Until that evidence exists,
describe the site as a Pages candidate, not as deployed.

## Maintainer release sequence

For the immutable v0.1 release:

1. Finish authoring and documentation.
2. Generate and inspect the offline Atlas.
3. Commit a clean candidate and pin it once.
4. Run independent reference, visual, quality, and release reviews.
5. Publish the exact commit and annotated `v0.1.0` tag.
6. Smoke-test a fresh public clone and installed wheel.
7. Record proposal-only evolution signals.
8. Complete the bootstrap run and export its receipt bundle.
9. Attach the bundle and final checksums to the GitHub release.

For a successor and Pages publication:

1. Pin the candidate under the active predecessor binding.
2. Validate bilingual docs, site output, social assets, and Atlas provenance.
3. Obtain independent verification of the exact candidate.
4. Record a separate capable operator decision for any successor activation.
5. Append the activated binding without replacing predecessor history.
6. Let the scoped publisher deploy only the verified `site/` artifact.
7. Capture the deployment receipt and smoke-test the live URL.
8. Record later friction as signals; never auto-activate their proposal.

If source bytes change after the candidate is pinned, start a new run.
