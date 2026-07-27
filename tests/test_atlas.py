from __future__ import annotations

from copy import deepcopy
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from concordloom.atlas import (
    AtlasError,
    AtlasStaleError,
    _atlas_model,
    _reachable_loop_ids,
    _route_drift,
    _runtime_projection,
    _script_safe_json,
    _validate_run_identity,
    generate_atlas,
    render_atlas,
)
from concordloom.canonical import digest, load
from concordloom.run import build_candidate_manifest, create_run_card


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "framework" / "generic-sdlc"


def artifacts() -> tuple[dict, dict, dict]:
    return (
        load(EXAMPLE / "binding.json"),
        load(EXAMPLE / "cycle-registry.json"),
        load(EXAMPLE / "policy.json"),
    )


def active_self_artifacts() -> tuple[dict, dict, dict]:
    catalog = load(ROOT / "framework" / "concordloom" / "catalog.json")
    active = next(
        entry
        for entry in catalog["entries"]
        if entry["binding_digest"] == catalog["active_binding_digest"]
    )
    binding = load(ROOT / active["path"])
    by_role = {artifact["role"]: artifact for artifact in binding["artifacts"]}
    return (
        binding,
        load(ROOT / by_role["cycle_registry"]["path"]),
        load(ROOT / by_role["policy"]["path"]),
    )


class AtlasTests(unittest.TestCase):
    def test_render_is_deterministic_offline_and_accessible(self) -> None:
        binding, registry, policy = artifacts()
        first = render_atlas(binding=binding, registry=registry, policy=policy)
        second = render_atlas(binding=binding, registry=registry, policy=policy)

        self.assertEqual(first, second)
        self.assertTrue(first.startswith("<!doctype html>"))
        self.assertIn("No run attached", first)
        self.assertIn("Content-Security-Policy", first)
        self.assertIn("script-src 'sha256-", first)
        self.assertNotIn("'unsafe-inline'", first)
        self.assertNotIn('src="http', first)
        self.assertNotIn('href="http', first)
        self.assertNotIn("transition: all", first)
        self.assertNotIn("user-scalable", first)
        self.assertNotIn("—", first)
        self.assertNotIn("–", first)
        for marker in (
            'href="#atlas-main"',
            'aria-live="polite"',
            ":focus-visible",
            "prefers-reduced-motion",
            "Planned",
            "Actual",
            "Verified",
            "Drift",
            "Containment",
            "Local flow",
            "ArrowDown",
            "history.pushState",
            "Not revalidated",
            "max_traversals",
            "Candidate binding",
        ):
            self.assertIn(marker, first)

    def test_russian_render_localizes_static_dynamic_and_accessible_ui(self) -> None:
        binding, registry, policy = artifacts()
        first = render_atlas(
            binding=binding,
            registry=registry,
            policy=policy,
            locale="ru",
        )
        second = render_atlas(
            binding=binding,
            registry=registry,
            policy=policy,
            locale="ru",
        )

        self.assertEqual(first, second)
        for marker in (
            '<html lang="ru">',
            "<title>Атлас Concord Loom</title>",
            'aria-label="Путь по циклам"',
            'aria-label="Состояния сведений"',
            'aria-label="Условные обозначения"',
            'aria-live="polite"',
            "Карточка запуска не подключена",
            "Вложенность",
            "Локальные переходы",
            "Выбран цикл: {label}",
            "const ATLAS_COPY=",
        ):
            self.assertIn(marker, first)
        for unresolved in (
            "No run attached",
            "Loop path:",
            "Selected loop:",
            ">Containment<",
            ">Local flow<",
            'aria-label="Map key"',
        ):
            self.assertNotIn(unresolved, first)
        with self.assertRaisesRegex(AtlasError, "unsupported Atlas locale"):
            render_atlas(
                binding=binding,
                registry=registry,
                policy=policy,
                locale="de",
            )

    def test_checked_in_atlases_are_exact_english_and_russian_outputs(self) -> None:
        binding, registry, policy = active_self_artifacts()
        expected = {
            ROOT / "docs" / "ATLAS.html": render_atlas(
                binding=binding,
                registry=registry,
                policy=policy,
                locale="en",
            ),
            ROOT / "docs" / "ru" / "ATLAS.html": render_atlas(
                binding=binding,
                registry=registry,
                policy=policy,
                locale="ru",
            ),
        }
        for path, rendered in expected.items():
            with self.subTest(path=path):
                self.assertTrue(path.exists())
                self.assertEqual(path.read_text(encoding="utf-8"), rendered)

    def test_cli_accepts_explicit_atlas_locale(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "atlas.ru.html"
            environment = dict(os.environ)
            environment["PYTHONPATH"] = str(ROOT / "src")
            result = subprocess.run(
                [
                    "python3",
                    "-m",
                    "concordloom",
                    "atlas",
                    "--binding",
                    str(EXAMPLE / "binding.json"),
                    "--registry",
                    str(EXAMPLE / "cycle-registry.json"),
                    "--policy",
                    str(EXAMPLE / "policy.json"),
                    "--locale",
                    "ru",
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('<html lang="ru">', output.read_text(encoding="utf-8"))

    def test_repository_text_is_safe_inside_the_script_element(self) -> None:
        encoded = _script_safe_json(
            {"label": "</script><script>alert('unsafe')</script>&"}
        )
        self.assertNotIn("</script>", encoded)
        self.assertNotIn("<script>", encoded)
        self.assertIn("\\u003c", encoded)
        self.assertIn("\\u0026", encoded)

    def test_projection_preserves_accepted_containment_order(self) -> None:
        binding, registry, policy = artifacts()
        model = _atlas_model(binding, registry, policy, None)
        expected = [
            edge["id"] for edge in registry["containment_graph"]["edges"]
        ]
        self.assertEqual(
            [edge["id"] for edge in model["containment"]["edges"]],
            expected,
        )
        delivery = next(loop for loop in model["loops"] if loop["id"] == "delivery")
        self.assertEqual(
            [edge["id"] for edge in delivery["child_invocations"]],
            [
                edge["id"]
                for edge in registry["containment_graph"]["edges"]
                if edge["parent_loop_id"] == "delivery"
            ],
        )
        self.assertEqual(
            model["containment"]["roots"],
            binding["active_root_loop_ids"],
        )
        self.assertEqual(
            model["containment"]["default_root"],
            binding["active_root_loop_ids"][0],
        )

    def test_active_reachability_excludes_an_unbound_root(self) -> None:
        registry = {
            "containment_graph": {
                "roots": ["active", "inactive"],
                "edges": [
                    {
                        "parent_loop_id": "active",
                        "child_loop_id": "active-child",
                    },
                    {
                        "parent_loop_id": "inactive",
                        "child_loop_id": "inactive-child",
                    },
                ],
            }
        }
        self.assertEqual(
            _reachable_loop_ids(registry, ["active"]),
            {"active", "active-child"},
        )

    def test_attached_run_cannot_cross_between_active_roots(self) -> None:
        class NoOpSchemaStore:
            def validate(self, value: dict, schema_name: str) -> None:
                del value, schema_name

        registry = {
            "loops": [{"id": "alpha"}, {"id": "beta"}],
            "containment_graph": {"roots": ["alpha", "beta"], "edges": []},
        }
        policy = {"id": "policy"}
        binding = {
            "binding_digest": "sha256:" + "a" * 64,
            "active_root_loop_ids": ["alpha", "beta"],
        }
        run_card = {
            "binding_digest": binding["binding_digest"],
            "registry_digest": digest(registry),
            "policy_digest": digest(policy),
            "root_loop_id": "alpha",
            "planned_route": [{"loop_id": "alpha"}],
            "nodes": [{"loop_id": "beta", "evidence_ids": []}],
            "evidence": [],
        }

        with self.assertRaisesRegex(AtlasError, "selected run root subtree"):
            _validate_run_identity(
                run_card,
                binding,
                registry,
                policy,
                schema_store=NoOpSchemaStore(),
            )

    def test_runtime_uses_root_outcome_and_projects_reference_metadata(self) -> None:
        _, _, policy = artifacts()
        card = {
            "id": "complete-run",
            "status": "complete",
            "root_outcome": "succeeded",
            "candidate_tree_digest": "sha256:" + "a" * 64,
            "planned_route": [
                {
                    "node_id": "delivery",
                    "loop_id": "delivery",
                }
            ],
            "evidence": [
                {
                    "id": "delivery-evidence",
                    "path": "evidence/delivery.json",
                    "digest": "sha256:" + "b" * 64,
                }
            ],
            "nodes": [
                {
                    "node_id": "delivery",
                    "loop_id": "delivery",
                    "status": "passed",
                    "attempts": [],
                    "evidence_ids": ["delivery-evidence"],
                }
            ],
        }
        runtime = _runtime_projection(card, {"delivery"}, policy)
        self.assertEqual(runtime["outcome"], "succeeded")
        self.assertEqual(
            runtime["loops"]["delivery"]["evidence"][0]["path"],
            "evidence/delivery.json",
        )
        self.assertEqual(
            runtime["verification"],
            "recorded-references-not-revalidated",
        )

    def test_generate_and_check_compare_exact_bytes(self) -> None:
        binding, registry, policy = artifacts()
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "atlas.html"
            generate_atlas(
                binding=binding,
                registry=registry,
                policy=policy,
                output=output,
            )
            expected = output.read_bytes()
            generate_atlas(
                binding=binding,
                registry=registry,
                policy=policy,
                output=output,
                check=True,
            )
            self.assertEqual(output.read_bytes(), expected)

            output.write_text("stale\n", encoding="utf-8")
            with self.assertRaisesRegex(AtlasStaleError, "stale"):
                generate_atlas(
                    binding=binding,
                    registry=registry,
                    policy=policy,
                    output=output,
                    check=True,
                )

    def test_check_rejects_a_missing_output(self) -> None:
        binding, registry, policy = artifacts()
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(AtlasStaleError, "missing"):
                generate_atlas(
                    binding=binding,
                    registry=registry,
                    policy=policy,
                    output=Path(temporary) / "missing.html",
                    check=True,
                )

    def test_optional_run_is_identity_bound_and_factual(self) -> None:
        binding, registry, policy = artifacts()
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary) / "repository"
            repository.mkdir()
            subprocess.run(
                ["git", "init", "-b", "main"],
                cwd=repository,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Atlas Test"],
                cwd=repository,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "atlas@example.invalid"],
                cwd=repository,
                check=True,
            )
            (repository / "service.py").write_text(
                "answer = 42\n", encoding="utf-8"
            )
            subprocess.run(
                ["git", "add", "service.py"],
                cwd=repository,
                check=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "seed"],
                cwd=repository,
                check=True,
                capture_output=True,
            )
            candidate = build_candidate_manifest(
                repository, generated_at="2026-07-24T10:00:00Z"
            )
            card = create_run_card(
                binding,
                registry,
                policy,
                candidate,
                run_id="atlas-test-run",
                root_loop_id="delivery",
                candidate_author_principal_ids=["example-executor"],
            )

            rendered = render_atlas(
                binding=binding,
                registry=registry,
                policy=policy,
                run_card=card,
            )
            self.assertIn("<strong>run atlas-test-run: draft</strong>", rendered)
            self.assertIn('"attached":true', rendered)
            self.assertIn('"status":"pending"', rendered)

            mismatched = deepcopy(card)
            mismatched["binding_digest"] = "sha256:" + "0" * 64
            with self.assertRaisesRegex(AtlasError, "binding_digest"):
                render_atlas(
                    binding=binding,
                    registry=registry,
                    policy=policy,
                    run_card=mismatched,
                )

            dangling = deepcopy(card)
            dangling["nodes"][0]["evidence_ids"] = ["missing-evidence"]
            with self.assertRaisesRegex(AtlasError, "dangling evidence"):
                render_atlas(
                    binding=binding,
                    registry=registry,
                    policy=policy,
                    run_card=dangling,
                )

    def test_drift_reports_policy_or_scope_violation_not_intent_wording(self) -> None:
        _, _, policy = artifacts()
        planned = {
            "role": "executor",
            "model_intent": "select within bound model policy",
            "skill_intent": "select at execution",
            "reasoning_intent": "proportionate",
            "subagent_intent": [],
            "scope": {
                "read_paths": ["."],
                "write_paths": ["src"],
                "network": "none",
                "external_mutations": [],
            },
        }
        card = {
            "policy_digest": digest(policy),
            "candidate_tree_digest": "sha256:" + "a" * 64,
        }
        attempt = {
            "effective_principal_id": "example-executor",
            "effective_model": "none",
            "effective_tools": ["python"],
            "data_egress": {
                "provider": "",
                "path_prefixes": [],
                "content_classes": [],
            },
            "network": "none",
            "external_mutations": [],
            "policy_digest": card["policy_digest"],
            "candidate_tree_digest": card["candidate_tree_digest"],
        }
        self.assertEqual(_route_drift(planned, attempt, card, policy), [])

        broadened = deepcopy(attempt)
        broadened["network"] = "write"
        self.assertEqual(
            _route_drift(planned, broadened, card, policy)[0]["field"],
            "network scope",
        )

    def test_cli_generates_and_checks_the_same_projection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "atlas.html"
            base = [
                "python3",
                "-m",
                "concordloom",
                "atlas",
                "--binding",
                str(EXAMPLE / "binding.json"),
                "--registry",
                str(EXAMPLE / "cycle-registry.json"),
                "--policy",
                str(EXAMPLE / "policy.json"),
                "--output",
                str(output),
            ]
            environment = {"PYTHONPATH": str(ROOT / "src")}
            generated = subprocess.run(
                base,
                cwd=ROOT,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(generated.returncode, 0, generated.stderr)
            checked = subprocess.run(
                [*base, "--check"],
                cwd=ROOT,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(checked.returncode, 0, checked.stderr)


if __name__ == "__main__":
    unittest.main()
