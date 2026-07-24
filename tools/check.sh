#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHONPATH=src python3 -m compileall -q src tests tools
PYTHONPATH=src python3 -m unittest discover -s tests -v

while IFS= read -r -d '' file; do
  python3 -m json.tool "$file" >/dev/null
done < <(find schemas concord framework examples plugins .agents .concord \
  -type f -name '*.json' -print0 2>/dev/null | sort -z)

PYTHONPATH=src python3 -m concordloom --help >/dev/null
PYTHONPATH=src python3 tools/generate_generic_example.py --check
PYTHONPATH=src python3 -m concordloom atlas \
  --binding framework/generic-sdlc/binding.json \
  --registry framework/generic-sdlc/cycle-registry.json \
  --policy framework/generic-sdlc/policy.json \
  --output docs/ATLAS.html \
  --check

PLUGIN_VALIDATOR="${CODEX_PLUGIN_VALIDATOR:-}"
if [[ -n "$PLUGIN_VALIDATOR" && -f "$PLUGIN_VALIDATOR" ]]; then
  python3 "$PLUGIN_VALIDATOR" plugins/concordloom
fi

SKILL_VALIDATOR="${CODEX_SKILL_VALIDATOR:-}"
if [[ -n "$SKILL_VALIDATOR" && -f "$SKILL_VALIDATOR" ]]; then
  python3 "$SKILL_VALIDATOR" plugins/concordloom/skills/design-project-loops
fi

git diff --check
printf '%s\n' 'CHECK_OK'
