#!/usr/bin/env python3
"""Propose the v9 evidence-driven frontend development system."""

from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path

from concordloom.canonical import digest, load, save
from concordloom.compiler import compile_registry, create_binding_proposal
from concordloom.evolution import propose_evolution
from concordloom.loops import validate_policy, validate_registry


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "framework" / "concordloom"
PREDECESSOR = SOURCE / "v8"
TARGET = SOURCE / "v9"
STAMP = "2026-07-28T22:30:00Z"

FRONTEND_LOOPS = [
    {
        "id": "define-frontend-concept",
        "label": ("Lock Visual Contract", "Зафиксировать визуальный контракт"),
        "purpose": (
            "Turn an approved concept into exact visual, responsive, motion and state constraints.",
            "Превращать принятую концепцию в точные правила композиции, адаптивности, движения и состояний.",
        ),
        "contract": (
            "Concept art, product truth and target user tasks.",
            "A digest-bound visual contract, state inventory and viewport matrix.",
            "Концепт-арт, факты о продукте и задачи пользователя.",
            "Визуальный контракт с точным хешем, список состояний и матрица экранов.",
        ),
        "artifacts": ["concept-reference", "visual-contract", "viewport-matrix"],
        "role": ("visual design author", "автор визуальной концепции"),
        "profile": "frontend-author",
    },
    {
        "id": "accept-frontend-concept",
        "label": ("Accept Visual Contract", "Принять визуальный контракт"),
        "purpose": (
            "Accept or reject the exact visual contract as a separate human decision.",
            "Отдельным решением принять или отклонить точный визуальный контракт.",
        ),
        "contract": (
            "A digest-bound visual contract.",
            "An operator decision bound to the exact contract digest.",
            "Визуальный контракт с точным хешем.",
            "Решение оператора, привязанное к точному хешу контракта.",
        ),
        "artifacts": ["visual-contract-decision"],
        "role": ("operator", "оператор"),
        "profile": "operator",
    },
    {
        "id": "maintain-component-workshop",
        "label": ("Build Interface Workshop", "Собрать мастерскую интерфейса"),
        "purpose": (
            "Expose real production components in every consequential state.",
            "Показывать настоящие компоненты продукта во всех важных состояниях.",
        ),
        "contract": (
            "An accepted visual contract and production component boundaries.",
            "A local workshop covering normal, long-copy, loading, empty, error and stale states.",
            "Принятый визуальный контракт и границы компонентов продукта.",
            "Локальная мастерская с компонентами в обычном состоянии, с длинным текстом, при загрузке, без данных, с ошибкой и с устаревшими данными.",
        ),
        "artifacts": ["frontend-workshop", "state-fixtures"],
        "role": ("frontend implementer", "разработчик интерфейса"),
        "profile": "frontend-author",
    },
    {
        "id": "implement-frontend-surface",
        "label": ("Implement Frontend Candidate", "Реализовать интерфейс"),
        "purpose": (
            "Build the site and Atlas from the accepted visual contract and production components.",
            "Собирать сайт и Атлас из принятого визуального контракта и компонентов продукта.",
        ),
        "contract": (
            "Accepted visual contract, content, Atlas data and workshop fixtures.",
            "A pinned responsive bilingual frontend candidate.",
            "Принятый визуальный контракт, материалы, данные Атласа и примеры состояний.",
            "Зафиксированная адаптивная двуязычная версия интерфейса.",
        ),
        "artifacts": ["site", "atlas-interface", "component-modules"],
        "role": ("frontend implementer", "разработчик интерфейса"),
        "profile": "frontend-author",
    },
    {
        "id": "maintain-frontend-verification",
        "label": ("Maintain Browser Harness", "Развивать браузерные проверки"),
        "purpose": (
            "Keep deterministic browser, layout, accessibility and visual-regression checks exact.",
            "Поддерживать точные браузерные проверки вёрстки, доступности и визуальных регрессий.",
        ),
        "contract": (
            "Accepted visual contract and supported browser matrix.",
            "A pinned Playwright and axe harness with immutable approved baselines.",
            "Принятый визуальный контракт и поддерживаемая матрица браузеров.",
            "Зафиксированный набор Playwright и axe с отдельно принятыми эталонными снимками.",
        ),
        "artifacts": ["playwright-harness", "layout-contract", "visual-baselines"],
        "role": ("test author", "автор проверок"),
        "profile": "frontend-author",
    },
    {
        "id": "verify-frontend-candidate",
        "label": ("Verify Frontend Runtime", "Проверить интерфейс в браузере"),
        "purpose": (
            "Measure the exact candidate across locale, viewport, zoom, motion and browser states.",
            "Измерять точную версию во всех языках, размерах, масштабах, режимах движения и браузерах.",
        ),
        "contract": (
            "A pinned candidate, visual contract, harness and approved baselines.",
            "A deterministic report with screenshots, diffs, geometry, accessibility and runtime evidence.",
            "Зафиксированная версия, визуальный контракт, проверки и принятые эталонные снимки.",
            "Детерминированный отчёт со снимками, сравнением, геометрией, доступностью и данными исполнения.",
        ),
        "artifacts": ["playwright-report", "screenshots", "layout-evidence", "axe-report"],
        "role": ("deterministic verifier", "детерминированная проверка"),
        "profile": "frontend-verification",
    },
    {
        "id": "critique-frontend-experience",
        "label": ("Review Visual Fidelity", "Проверить визуальное соответствие"),
        "purpose": (
            "Independently reject candidates that pass mechanics but miss the accepted concept.",
            "Независимо отклонять версии, которые формально работают, но не соответствуют принятой концепции.",
        ),
        "contract": (
            "Exact concept, candidate, browser report and screenshots.",
            "An independent pass, revise or indeterminate visual and comprehension verdict.",
            "Точные концепция, версия, браузерный отчёт и снимки.",
            "Независимый вердикт о визуальном соответствии и понятности.",
        ),
        "artifacts": ["visual-review", "reference-comparison", "critic-receipt"],
        "role": ("independent visual critic", "независимый визуальный критик"),
        "profile": "frontend-critique",
    },
]

ORDER = [item["id"] for item in FRONTEND_LOOPS]


def route(model: str, reasoning: str, *, tools: list[str], skills: list[dict] | None = None,
          mcp: list[dict] | None = None) -> dict:
    return {
        "model_provider": "" if model == "none" else "openai",
        "model": model,
        "reasoning": reasoning,
        "skills": deepcopy(skills or []),
        "mcp_servers": deepcopy(mcp or []),
        "resources": [],
        "tool_capabilities": sorted(set(tools)),
        "subagent_identities": [],
    }


def add_frontend_design(base: dict, *, proposal: bool) -> dict:
    document = deepcopy(base)
    document["id"] = (
        "concordloom-development-system-v9-proposal"
        if proposal else "concordloom-development-system-v9-manifest"
    )
    for item in FRONTEND_LOOPS:
        document["loops"].append(
            {
                "id": item["id"],
                "purpose": item["purpose"][0],
                "input_outcome": item["contract"][0],
                "output_outcome": item["contract"][1],
                "basis": [
                    {"kind": "decision", "ref": "accepted-project-graph"}
                ],
                "decision_ids": ["accept-universal-loop-system"],
            }
        )
        document["containment"].append(
            {
                "id": f"design-site-experience.{item['id']}",
                "parent_loop_id": "design-site-experience",
                "child_loop_id": item["id"],
                "decision_id": "accept-universal-loop-system",
            }
        )
    return document


def add_frontend_model(base: dict, base_digest: str) -> dict:
    model = deepcopy(base)
    model["id"] = "concordloom-development-system-v9"
    model["base_binding_digest"] = base_digest
    by_id = {node["id"]: node for node in model["nodes"]}
    by_id["design-site-experience"]["children"] = ORDER
    by_id["design-site-experience"]["artifacts"] = [
        "visual-contract", "frontend-workshop", "site", "atlas",
        "browser-report", "visual-review",
    ]
    by_id["design-site-experience"]["route_materialization"] = route(
        "none", "deterministic", tools=["route-child-receipts"]
    )
    model["profiles"]["frontend-author"] = {
        "model_intent": {
            "en": "concept-faithful frontend design and implementation",
            "ru": "проектирование и реализация интерфейса по принятой концепции",
        },
        "skills": ["impeccable", "design-system-patterns", "ui-animation"],
        "tools": ["browser", "repository", "image-generation", "test-runner"],
        "mcp": {"status": "optional-adapter", "source": "pinned run route"},
        "truth_layer": "planned",
        "route_materialization": route(
            "gpt-5.6-terra",
            "medium",
            tools=["browser", "repository", "image-generation", "test-runner"],
            skills=[{"id": "impeccable", "version": "4.0.3"}],
        ),
    }
    model["profiles"]["frontend-harness"] = {
        "model_intent": {
            "en": "bounded browser-harness engineering",
            "ru": "разработка ограниченного набора браузерных проверок",
        },
        "skills": [],
        "tools": ["playwright-test", "axe", "layout-assertions", "repository"],
        "mcp": {"status": "not-required", "source": "active binding"},
        "truth_layer": "planned",
        "route_materialization": route(
            "gpt-5.6-terra",
            "low",
            tools=["playwright-test", "axe", "layout-assertions", "repository"],
        ),
    }
    model["profiles"]["frontend-verification"] = {
        "model_intent": {
            "en": "deterministic browser and accessibility verification",
            "ru": "детерминированная браузерная проверка и проверка доступности",
        },
        "skills": [],
        "tools": ["playwright-test", "axe", "layout-assertions"],
        "mcp": {"status": "not-used-as-oracle", "source": "active binding"},
        "truth_layer": "planned",
        "route_materialization": route(
            "none", "deterministic",
            tools=["playwright-test", "axe", "layout-assertions"],
        ),
    }
    model["profiles"]["frontend-critique"] = {
        "model_intent": {
            "en": "fresh independent multimodal comparison against the accepted concept",
            "ru": "независимое визуальное сравнение с принятой концепцией в новом контексте",
        },
        "skills": ["impeccable", "web-design-guidelines"],
        "tools": ["browser", "playwright-mcp", "screenshots"],
        "mcp": {"status": "not-declared", "source": "active binding"},
        "truth_layer": "planned",
        "route_materialization": route(
            "gpt-5.6-sol",
            "high",
            tools=["browser", "screenshots"],
            skills=[{"id": "impeccable", "version": "4.0.3"}],
        ),
    }
    for item in FRONTEND_LOOPS:
        profile = item["profile"]
        node = {
            "id": item["id"],
            "parent_id": "design-site-experience",
            "children": [],
            "copy": {
                "en": {"label": item["label"][0], "purpose": item["purpose"][0]},
                "ru": {"label": item["label"][1], "purpose": item["purpose"][1]},
            },
            "responsible_role": {"en": item["role"][0], "ru": item["role"][1]},
            "execution_profile": profile,
            "contract": {
                "en": {"input": item["contract"][0], "output": item["contract"][1]},
                "ru": {"input": item["contract"][2], "output": item["contract"][3]},
            },
            "artifacts": item["artifacts"],
        }
        if item["id"] == "maintain-frontend-verification":
            node["execution_profile"] = "frontend-harness"
            node["route_materialization"] = deepcopy(
                model["profiles"]["frontend-harness"]["route_materialization"]
            )
        elif profile == "operator":
            node["route_materialization"] = route(
                "none", "human-decision", tools=["decision-log"]
            )
        else:
            node["route_materialization"] = deepcopy(
                model["profiles"][profile]["route_materialization"]
            )
        if item["id"] == "define-frontend-concept":
            node["route_materialization"] = route(
                "gpt-5.6-terra", "medium",
                tools=["browser", "image-generation", "repository"],
                skills=[{"id": "impeccable", "version": "4.0.3"}],
            )
        elif item["id"] in (
            "maintain-component-workshop", "implement-frontend-surface"
        ):
            node["route_materialization"] = route(
                "gpt-5.6-terra", "medium",
                tools=["browser", "repository", "test-runner"],
                skills=[{"id": "impeccable", "version": "4.0.3"}],
            )
        model["nodes"].append(node)
    return model


def scope(read: list[str], write: list[str]) -> dict:
    return {
        "read_paths": sorted(set(read)),
        "write_paths": sorted(set(write)),
        "network": "none",
        "external_mutations": [],
    }


def frontend_evolution(base_digest: str, predecessor_policy: dict) -> dict:
    old_parent = next(
        loop for loop in load(PREDECESSOR / "cycle-registry.json")["loops"]
        if loop["id"] == "design-site-experience"
    )
    signals = [
        {
            "kind": "concordloom.evolution-signal",
            "schema_version": "0.1",
            "id": "frontend-source-checks-missed-live-layout-failure",
            "base_binding_digest": base_digest,
            "category": "friction",
            "severity": "critical",
            "occurrences": 4,
            "summary": (
                "Committed and deployed pages passed string-based gates while "
                "headings, controls and Atlas panels visibly overlapped."
            ),
            "source_digest": digest({"source": "operator:2026-07-28:live-layout-rejection"}),
            "provenance": [{"kind": "evidence", "ref": "operator-screenshots"}],
        },
        {
            "kind": "concordloom.evolution-signal",
            "schema_version": "0.1",
            "id": "frontend-implementation-drifted-from-accepted-concept",
            "base_binding_digest": base_digest,
            "category": "coverage",
            "severity": "critical",
            "occurrences": 2,
            "summary": (
                "The Atlas preserved colors and texture but lost the accepted "
                "concept's immersive parent-current-inspector composition."
            ),
            "source_digest": digest({"source": "audit:2026-07-28:reference-fidelity-no-go"}),
            "provenance": [{"kind": "evidence", "ref": "independent-visual-audit"}],
        },
    ]
    operations = [
        {
            "op": "replace",
            "target_kind": "loop",
            "target_id": "design-site-experience",
            "path": "/purpose",
            "precondition_digest": digest(old_parent["purpose"]),
            "value": (
                "Turn an accepted visual contract into a browser-verified, "
                "independently critiqued interface."
            ),
        }
    ]
    operations.extend(
        {
            "op": "add",
            "target_kind": "loop",
            "target_id": item["id"],
            "value": {
                "parent_loop_id": "design-site-experience",
                "purpose": item["purpose"][0],
                "input_outcome": item["contract"][0],
                "output_outcome": item["contract"][1],
            },
        }
        for item in FRONTEND_LOOPS
    )
    operations.extend(
        {
            "op": "add",
            "target_kind": "containment",
            "target_id": f"design-site-experience.{item['id']}",
            "value": {
                "parent_loop_id": "design-site-experience",
                "child_loop_id": item["id"],
            },
        }
        for item in FRONTEND_LOOPS
    )
    return propose_evolution(
        base_digest,
        signals,
        operations,
        proposed_by={"id": "example-orchestrator", "kind": "orchestrator"},
        decision_authority_ref="operator",
        expected_effect=(
            "Make an accepted visual contract, production-state workshop, "
            "deterministic Playwright evidence and an independent visual critic "
            "mandatory before the site experience can pass."
        ),
        risk={
            "level": "medium",
            "failure_modes": [
                "Visual baselines may be accepted from an already broken candidate.",
                "Browser dependencies may increase repository maintenance cost.",
            ],
            "rollback": "Reject v9 and retain active v8.",
        },
        generated_at=STAMP,
        policy=predecessor_policy,
        proposal_id="add-evidence-driven-frontend-system",
        base_targets={"loop": {"design-site-experience": old_parent}},
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--design-decision", type=Path)
    args = parser.parse_args()

    graph = load(SOURCE / "v3" / "accepted-project-graph.json")
    decisions = load(SOURCE / "v3" / "decision-log.json")
    predecessor = load(PREDECESSOR / "binding.json")
    base_digest = predecessor["binding_digest"]

    policy = deepcopy(load(PREDECESSOR / "policy.json"))
    policy["id"] = "concordloom-self-policy-v9"
    frontend_paths = [
        "design/frontend",
        "frontend-workshop",
        "package.json",
        "package-lock.json",
        "playwright.config.js",
        "tests/frontend",
        ".github/workflows/frontend.yml",
    ]
    for key in ("read_paths", "write_paths"):
        policy["execution"]["default_scope"][key] = sorted(set(
            policy["execution"]["default_scope"][key] + frontend_paths
        ))
    operator_role = next(
        role for role in policy["authority"]["roles"] if role["id"] == "operator"
    )
    operator_role["capabilities"] = sorted(set(
        operator_role["capabilities"] + ["accept-frontend-concept"]
    ))
    separation = policy["authority"]["separation_rules"][0]["applies_to_loop_ids"]
    separation.extend([
        "design-site-experience",
        "verify-frontend-candidate",
        "critique-frontend-experience",
    ])
    policy["authority"]["separation_rules"][0]["applies_to_loop_ids"] = sorted(set(separation))
    policy["authority"]["separation_rules"].append(
        {
            "id": "frontend-concept-author-acceptance-separation",
            "subject_capability": "execute-work",
            "review_capability": "accept-frontend-concept",
            "disallow_same_principal": True,
            "applies_to_loop_ids": ["accept-frontend-concept"],
        }
    )
    validate_policy(policy)

    design_proposal = add_frontend_design(
        load(PREDECESSOR / "loop-design-proposal.json"), proposal=True
    )
    design_proposal["authority_policy_digest"] = digest(policy)
    design = add_frontend_design(load(PREDECESSOR / "loop-design.json"), proposal=False)
    design["authority_policy_digest"] = digest(policy)
    design["proposal_digest"] = digest(design_proposal)
    evolution = frontend_evolution(base_digest, load(PREDECESSOR / "policy.json"))
    if args.design_decision is None:
        design_proposal_document = {
            "loop-design-proposal.json": design_proposal,
            "policy.json": policy,
            "evolution-proposal.json": evolution,
        }
        for name, document in design_proposal_document.items():
            save(TARGET / name, document)
        for stale_name in (
            "loop-design.json", "cycle-registry.json", "development-model.json",
            "binding-proposal.json", "publication-route.json", "binding.json",
            "activation-receipt.json",
        ):
            (TARGET / stale_name).unlink(missing_ok=True)
        print(
            "FRONTEND_SYSTEM_V9_DESIGN_PROPOSED "
            f"design={digest(design_proposal)}"
        )
        return
    decision = load(args.design_decision)
    decision_payload = deepcopy(decision)
    claimed_decision_digest = decision_payload.pop("receipt_digest", None)
    expected_decision = {
        "kind": "concordloom.frontend-design-decision",
        "schema_version": "0.1",
        "id": "accept-frontend-verification-system",
        "proposal_digest": digest(design_proposal),
        "verdict": "accepted",
        "principal": {"id": "example-operator", "kind": "human"},
        "capability": "accept-loop-design",
        "decided_at": STAMP,
    }
    if decision_payload != expected_decision or claimed_decision_digest != digest(
        decision_payload
    ):
        raise SystemExit("frontend design decision does not accept the exact proposal")
    design["accepted_by"] = {
        "decision_id": decision["id"],
        "actor": {
            "id": decision["principal"]["id"],
            "kind": "operator",
            "display_name": "User-confirmed operator",
        },
        "authority_ref": "operator",
        "accepted_at": decision["decided_at"],
        "rationale": (
            "Accept a dedicated frontend system that makes concept fidelity, "
            "browser geometry and independent visual critique release gates."
        ),
    }
    registry = compile_registry(
        graph, decisions, design, policy,
        loop_design_proposal=design_proposal,
        registry_id="concordloom-development-registry-v9",
    )
    registry["policy_digest"] = digest(policy)
    registry["source_loop_design_digest"] = digest(design)
    previous_registry = load(PREDECESSOR / "cycle-registry.json")
    previous_edges = {
        edge["id"]: edge for edge in previous_registry["containment_graph"]["edges"]
    }
    for edge in registry["containment_graph"]["edges"]:
        if edge["id"] in previous_edges:
            edge["grant"] = deepcopy(previous_edges[edge["id"]]["grant"])
    previous_loops = {loop["id"]: loop for loop in previous_registry["loops"]}
    for loop in registry["loops"]:
        previous = previous_loops.get(loop["id"])
        if previous is not None:
            loop["authority"] = deepcopy(previous["authority"])
            loop["budgets"] = deepcopy(previous["budgets"])
    previous_contracts = {
        item["id"]: item for item in previous_registry["evidence_contracts"]
    }
    for contract in registry["evidence_contracts"]:
        if contract["id"] in previous_contracts:
            contract.update(deepcopy(previous_contracts[contract["id"]]))

    common_read = [
        "AGENTS.md", "docs/DESIGN_SYSTEM.md", "docs/ru/DESIGN_SYSTEM.md",
        "design/frontend", "frontend-workshop", "package.json", "package-lock.json",
        "playwright.config.js", "site", "tests/frontend", "tools/build_site.py",
    ]
    scopes = {
        "define-frontend-concept": scope(common_read, ["design/frontend"]),
        "accept-frontend-concept": scope(
            ["design/frontend", "framework/concordloom/catalog.json"], []
        ),
        "maintain-component-workshop": scope(
            common_read, ["frontend-workshop"]
        ),
        "implement-frontend-surface": scope(
            common_read, ["site", "docs/assets", "tools/build_site.py"]
        ),
        "maintain-frontend-verification": scope(
            common_read + [".github/workflows"],
            [".github/workflows/frontend.yml", "package.json", "package-lock.json",
             "playwright.config.js", "tests/frontend"],
        ),
        "verify-frontend-candidate": scope(common_read, []),
        "critique-frontend-experience": scope(common_read, []),
    }
    edges = {edge["child_loop_id"]: edge for edge in registry["containment_graph"]["edges"]}
    loops = {loop["id"]: loop for loop in registry["loops"]}
    for loop_id, exact_scope in scopes.items():
        edges[loop_id]["grant"]["scope"] = exact_scope
    loops["accept-frontend-concept"]["authority"] = {
        "execute_capability": "accept-frontend-concept",
        "accept_capability": "accept-parent",
        "escalate_capability": "escalate",
    }
    edges["accept-frontend-concept"]["grant"]["capabilities"] = [
        "accept-frontend-concept", "accept-parent", "escalate",
    ]
    for loop_id in ("verify-frontend-candidate", "critique-frontend-experience"):
        loops[loop_id]["authority"] = {
            "execute_capability": "review-candidate",
            "accept_capability": "accept-gate",
            "escalate_capability": "escalate",
        }
        edges[loop_id]["grant"]["capabilities"] = [
            "accept-gate", "escalate", "produce-evidence", "review-candidate",
        ]
    frontend_read = sorted({
        path for exact_scope in scopes.values()
        for path in exact_scope["read_paths"]
    })
    frontend_write = sorted({
        path for exact_scope in scopes.values()
        for path in exact_scope["write_paths"]
    })
    edges["design-site-experience"]["grant"]["scope"] = scope(
        frontend_read, frontend_write
    )
    knowledge_scope = deepcopy(policy["execution"]["default_scope"])
    knowledge_scope["network"] = "none"
    knowledge_scope["external_mutations"] = []
    edges["knowledge-experience"]["grant"]["scope"] = knowledge_scope
    contracts = {item["id"]: item for item in registry["evidence_contracts"]}
    contracts["accept-frontend-concept-acceptance"]["producer_capability"] = (
        "accept-frontend-concept"
    )
    for loop_id in ("verify-frontend-candidate", "critique-frontend-experience"):
        contracts[f"{loop_id}-acceptance"]["producer_capability"] = "review-candidate"
    frontend_parent = loops["design-site-experience"]
    for transition in frontend_parent["local_control_flow"]["transitions"]:
        for child_id in ORDER:
            if transition["id"] == f"design-site-experience.{child_id}-success":
                transition["evidence_contract_ids"] = [
                    f"{child_id}-acceptance"
                ]
    required_frontend_claims = [f"{child_id}-outcome" for child_id in ORDER]
    contracts["design-site-experience-acceptance"]["required_claims"] = (
        required_frontend_claims + ["design-site-experience-outcome"]
    )
    for release_contract_id in (
        "assure-release-acceptance", "publish-site-acceptance"
    ):
        contracts[release_contract_id]["required_claims"] = sorted(set(
            contracts[release_contract_id]["required_claims"] + [
                "design-site-experience-outcome",
                "verify-frontend-candidate-outcome",
                "critique-frontend-experience-outcome",
            ]
        ))
    validate_registry(registry, policy)

    model = add_frontend_model(load(PREDECESSOR / "development-model.json"), base_digest)
    paths = {
        "accepted_project_graph": "framework/concordloom/v3/accepted-project-graph.json",
        "decision_log": "framework/concordloom/v3/decision-log.json",
        "loop_design_proposal": "framework/concordloom/v9/loop-design-proposal.json",
        "accepted_loop_design": "framework/concordloom/v9/loop-design.json",
        "cycle_registry": "framework/concordloom/v9/cycle-registry.json",
        "policy": "framework/concordloom/v9/policy.json",
    }
    extras = {
        "atlas_input": ("framework/concordloom/v9/development-model.json", model),
        "evolution_history": ("framework/concordloom/v9/evolution-proposal.json", evolution),
    }
    proposal = create_binding_proposal(
        graph, decisions, design, registry, policy,
        loop_design_proposal=design_proposal,
        artifact_paths=paths,
        proposal_id="concordloom-self-binding-v9-proposal",
        created_at=STAMP,
        predecessor_binding_digest=base_digest,
        extra_artifacts=extras,
    )
    publication_route = deepcopy(load(PREDECESSOR / "publication-route.json"))
    verification_entries = []
    for loop_id, role, intent in (
        (
            "verify-frontend-candidate",
            "reviewer",
            "run deterministic browser, layout and accessibility checks",
        ),
        (
            "critique-frontend-experience",
            "reviewer",
            "independently compare the exact candidate with the accepted concept",
        ),
    ):
        materialized = next(
            node["route_materialization"]
            for node in model["nodes"]
            if node["id"] == loop_id
        )
        verification_entries.append(
            {
                "node_id": loop_id,
                "loop_id": loop_id,
                "role": role,
                "model_provider": materialized["model_provider"],
                "model": materialized["model"],
                "model_intent": materialized["model"],
                "reasoning": materialized["reasoning"],
                "reasoning_intent": intent,
                "skill_intent": "verify the accepted visual contract",
                "skills": materialized["skills"],
                "mcp_servers": materialized["mcp_servers"],
                "resources": materialized["resources"],
                "tool_capabilities": materialized["tool_capabilities"],
                "subagent_identities": [],
                "subagent_intent": [],
                "scope": edges[loop_id]["grant"]["scope"],
                "required_evidence_contract_ids": [
                    f"{loop_id}-acceptance"
                ],
            }
        )
    publish_index = next(
        index for index, item in enumerate(publication_route)
        if item["loop_id"] == "publish-site"
    )
    publication_route[publish_index:publish_index] = verification_entries
    publish_item = next(
        item for item in publication_route if item["loop_id"] == "publish-site"
    )
    publish_item["required_evidence_contract_ids"] = [
        "design-site-experience-acceptance",
        "verify-frontend-candidate-acceptance",
        "critique-frontend-experience-acceptance",
    ]
    documents = {
        "loop-design-proposal.json": design_proposal,
        "loop-design.json": design,
        "cycle-registry.json": registry,
        "policy.json": policy,
        "development-model.json": model,
        "evolution-proposal.json": evolution,
        "binding-proposal.json": proposal,
        "publication-route.json": publication_route,
    }
    for name, document in documents.items():
        save(TARGET / name, document)
    print(
        f"FRONTEND_SYSTEM_V9_PROPOSED proposal={proposal['proposal_digest']} "
        f"tree={digest(proposal['artifacts'])}"
    )


if __name__ == "__main__":
    main()
