#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHONPATH=src python3 -m compileall -q src tests tools
PYTHONPATH=src python3 -m unittest discover -s tests -v

while IFS= read -r -d '' file; do
  python3 -m json.tool "$file" >/dev/null
done < <(find schemas concord framework examples plugins .agents .concord \
  docs/.concord-transition site/data \
  -type f -name '*.json' -print0 2>/dev/null | sort -z)

PYTHONPATH=src python3 -m concordloom --help >/dev/null
PYTHONPATH=src python3 tools/generate_generic_example.py --check
PYTHONPATH=src python3 tools/build_site.py --check
PYTHONPATH=src python3 tools/check_site.py
PYTHONPATH=src python3 tools/check_docs.py
PYTHONPATH=src python3 tools/check_language.py
PYTHONPATH=src python3 tools/check_ru_text.py
PYTHONPATH=src python3 -m concordloom validate \
  --input framework/concordloom/cycle-registry.json \
  --graph framework/concordloom/accepted-project-graph.json \
  --decisions framework/concordloom/decision-log.json \
  --proposal framework/concordloom/loop-design-proposal.json \
  --design framework/concordloom/loop-design.json \
  --policy framework/concordloom/policy.json
PYTHONPATH=src python3 -m concordloom validate \
  --input framework/concordloom/evolution-proposal.json \
  --policy framework/concordloom/policy.json \
  --base-binding docs/.concord-transition/binding.json
PYTHONPATH=src python3 -m concordloom validate \
  --input framework/concordloom/v3/cycle-registry.json \
  --graph framework/concordloom/v3/accepted-project-graph.json \
  --decisions framework/concordloom/v3/decision-log.json \
  --proposal framework/concordloom/v3/loop-design-proposal.json \
  --design framework/concordloom/v3/loop-design.json \
  --policy framework/concordloom/v3/policy.json
PYTHONPATH=src python3 -m concordloom validate \
  --input framework/concordloom/v3/evolution-proposal.json \
  --policy framework/concordloom/policy.json \
  --base-binding framework/concordloom/binding.json
PYTHONPATH=src python3 -m concordloom validate \
  --input framework/concordloom/v4/cycle-registry.json \
  --graph framework/concordloom/v3/accepted-project-graph.json \
  --decisions framework/concordloom/v3/decision-log.json \
  --proposal framework/concordloom/v4/loop-design-proposal.json \
  --design framework/concordloom/v4/loop-design.json \
  --policy framework/concordloom/v4/policy.json
PYTHONPATH=src python3 -m concordloom validate \
  --input framework/concordloom/v4/evolution-proposal.json \
  --policy framework/concordloom/v3/policy.json \
  --base-binding framework/concordloom/v3/binding.json
PYTHONPATH=src python3 -m concordloom validate \
  --input framework/concordloom/v5/cycle-registry.json \
  --graph framework/concordloom/v3/accepted-project-graph.json \
  --decisions framework/concordloom/v3/decision-log.json \
  --proposal framework/concordloom/v5/loop-design-proposal.json \
  --design framework/concordloom/v5/loop-design.json \
  --policy framework/concordloom/v5/policy.json
PYTHONPATH=src python3 -m concordloom validate \
  --input framework/concordloom/v5/evolution-proposal.json \
  --policy framework/concordloom/v4/policy.json \
  --base-binding framework/concordloom/v4/binding.json
PYTHONPATH=src python3 -m concordloom validate \
  --input framework/concordloom/v6/cycle-registry.json \
  --graph framework/concordloom/v3/accepted-project-graph.json \
  --decisions framework/concordloom/v3/decision-log.json \
  --proposal framework/concordloom/v6/loop-design-proposal.json \
  --design framework/concordloom/v6/loop-design.json \
  --policy framework/concordloom/v6/policy.json
PYTHONPATH=src python3 -m concordloom validate \
  --input framework/concordloom/v6/evolution-proposal.json \
  --policy framework/concordloom/v5/policy.json \
  --base-binding framework/concordloom/v5/binding.json
PYTHONPATH=src python3 -m concordloom validate \
  --input framework/concordloom/catalog.json \
  --artifact-root .

mapfile -t ACTIVE_ATLAS_PATHS < <(
  PYTHONPATH=src python3 - <<'PY'
from concordloom.canonical import load

catalog = load("framework/concordloom/catalog.json")
entry = next(
    item
    for item in catalog["entries"]
    if item["binding_digest"] == catalog["active_binding_digest"]
)
binding = load(entry["path"])
artifacts = {item["role"]: item["path"] for item in binding["artifacts"]}
print(entry["path"])
print(artifacts["cycle_registry"])
print(artifacts["policy"])
PY
)

if [[ "${#ACTIVE_ATLAS_PATHS[@]}" -ne 3 ]]; then
  printf '%s\n' 'active Atlas inputs did not resolve exactly' >&2
  exit 1
fi

PYTHONPATH=src python3 -m concordloom atlas \
  --binding "${ACTIVE_ATLAS_PATHS[0]}" \
  --registry "${ACTIVE_ATLAS_PATHS[1]}" \
  --policy "${ACTIVE_ATLAS_PATHS[2]}" \
  --output docs/ATLAS.html \
  --locale en \
  --check
PYTHONPATH=src python3 -m concordloom atlas \
  --binding "${ACTIVE_ATLAS_PATHS[0]}" \
  --registry "${ACTIVE_ATLAS_PATHS[1]}" \
  --policy "${ACTIVE_ATLAS_PATHS[2]}" \
  --output docs/ru/ATLAS.html \
  --locale ru \
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
