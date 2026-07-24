# Release verification

Concord Loom v0.1 releases bind source, package, independent reviews, and a
durable bootstrap receipt.

## Verify source

```bash
git clone https://github.com/PullDakar/concordloom.git
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

## Maintainer release sequence

1. Finish authoring and documentation.
2. Generate and inspect the offline Atlas.
3. Commit a clean candidate and pin it once.
4. Run independent reference, visual, quality, and release reviews.
5. Publish the exact commit and annotated `v0.1.0` tag.
6. Smoke-test a fresh public clone and installed wheel.
7. Record proposal-only evolution signals.
8. Complete the bootstrap run and export its receipt bundle.
9. Attach the bundle and final checksums to the GitHub release.

If source bytes change after the candidate is pinned, start a new run.
