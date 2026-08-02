from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import subprocess
import tempfile
import unittest

from concordloom.canonical import digest, document_digest, load
from concordloom.route import (
    RoutePreviewError,
    create_route_preview,
    validate_route_preview,
)
from concordloom.run import (
    RunStateError,
    authorize_run,
    build_candidate_manifest,
    create_run_card,
    guard,
    migrate_run_card_v0_1,
    record_attempt,
    validate_run_card,
)
from concordloom.schema import SchemaStore, ValidationError


ROOT = Path(__file__).resolve().parents[1]
V9 = ROOT / "framework" / "concordloom" / "v9"
V10 = ROOT / "framework" / "concordloom" / "v10"
NOW = "2026-08-02T12:00:00Z"
REQUEST_DIGEST = "sha256:" + ("a" * 64)


def fixture(name: str) -> dict:
    return load(V9 / name)


def v10_fixture(name: str) -> dict:
    return load(V10 / name)


def manifest() -> dict:
    return {
        "kind": "concordloom.candidate-manifest",
        "schema_version": "0.1",
        "id": "route-preview-candidate",
        "generated_at": NOW,
        "revision": "b" * 40,
        "tree_digest": "sha256:" + ("c" * 64),
        "dirty": False,
        "files": [],
    }


class RoutePreviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.binding = fixture("binding.json")
        self.registry = fixture("cycle-registry.json")
        self.policy = fixture("policy.json")
        self.model = fixture("development-model.json")
        self.candidate = manifest()

    def create(self, *targets: str, **overrides: object) -> dict:
        arguments: dict[str, object] = {
            "preview_id": "preview-route",
            "request_digest": REQUEST_DIGEST,
            "request_ref": "request.user.1",
            "root_loop_id": "steward-concordloom",
            "target_loop_ids": targets or ("maintain-cli",),
            "created_at": NOW,
        }
        arguments.update(overrides)
        return create_route_preview(
            self.binding,
            self.registry,
            self.policy,
            self.candidate,
            self.model,
            **arguments,
        )

    def repin(self, preview: dict) -> dict:
        preview["preview_digest"] = document_digest(
            preview,
            excluded_fields=preview["digest_contract"]["excluded_fields"],
        )
        return preview

    def repository_candidate(self, parent: Path) -> tuple[Path, dict]:
        repository = parent / "repository"
        repository.mkdir()
        for command in (
            ("init", "-b", "main"),
            ("config", "user.name", "Route Preview Test"),
            ("config", "user.email", "route@example.invalid"),
        ):
            subprocess.run(
                ["git", *command],
                cwd=repository,
                check=True,
                capture_output=True,
            )
        (repository / "service.py").write_text("answer = 42\n", encoding="utf-8")
        subprocess.run(
            ["git", "add", "service.py"],
            cwd=repository,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "seed"],
            cwd=repository,
            check=True,
            capture_output=True,
        )
        return repository, build_candidate_manifest(
            repository,
            manifest_id="route-preview-candidate",
            generated_at=NOW,
        )

    def test_preview_is_public_pinned_exact_and_non_authorizing(self) -> None:
        preview = self.create("maintain-cli")

        self.assertEqual("concordloom.route-preview", preview["kind"])
        self.assertEqual("proposed", preview["status"])
        self.assertFalse(preview["execution_allowed"])
        self.assertTrue(preview["confirmation_required"])
        self.assertEqual(
            {
                "read_paths": [],
                "write_paths": [],
                "network": "none",
                "external_mutations": [],
            },
            preview["preview_scope"],
        )
        self.assertNotIn("request_text", preview)
        self.assertNotIn("authorization", preview)
        self.assertEqual(
            self.binding["binding_digest"], preview["binding_digest"]
        )
        self.assertEqual(digest(self.registry), preview["registry_digest"])
        self.assertEqual(digest(self.policy), preview["policy_digest"])
        self.assertEqual(digest(self.model), preview["development_model_digest"])
        self.assertEqual(
            digest(self.candidate), preview["candidate_manifest_digest"]
        )
        self.assertEqual(
            ["steward-concordloom", "runtime-tooling", "maintain-cli"],
            [item["loop_id"] for item in preview["proposed_route"]],
        )
        self.assertEqual(
            preview["preview_digest"],
            document_digest(preview, excluded_fields=["/preview_digest"]),
        )
        SchemaStore().validate_public(preview)

    def test_target_order_does_not_change_route_or_digest(self) -> None:
        left = self.create("maintain-cli", "project-atlas")
        right = self.create("project-atlas", "maintain-cli")

        self.assertEqual(left, right)
        self.assertEqual(
            ["maintain-cli", "project-atlas"],
            left["target_loop_ids"],
        )

    def test_unknown_duplicate_and_out_of_root_targets_fail_closed(self) -> None:
        with self.assertRaisesRegex(RoutePreviewError, "at least one"):
            self.create(target_loop_ids=[])
        with self.assertRaisesRegex(RoutePreviewError, "unique"):
            self.create("maintain-cli", "maintain-cli")
        with self.assertRaisesRegex(RoutePreviewError, "unknown target loops"):
            self.create("not-a-loop")

        registry = deepcopy(self.registry)
        registry["containment_graph"]["roots"].append("knowledge-experience")
        registry["containment_graph"]["edges"] = [
            edge
            for edge in registry["containment_graph"]["edges"]
            if not (
                edge["parent_loop_id"] == "steward-concordloom"
                and edge["child_loop_id"] == "knowledge-experience"
            )
        ]
        root_loop = next(
            loop
            for loop in registry["loops"]
            if loop["id"] == "steward-concordloom"
        )
        detached_state = "invoke-steward-concordloom.knowledge-experience"
        flow = root_loop["local_control_flow"]
        flow["states"] = [
            state for state in flow["states"] if state["id"] != detached_state
        ]
        flow["transitions"] = [
            transition
            for transition in flow["transitions"]
            if transition["from"] != detached_state
        ]
        predecessor = next(
            transition
            for transition in flow["transitions"]
            if transition["id"]
            == "steward-concordloom.bindings-adapters-success"
        )
        predecessor["to"] = "invoke-steward-concordloom.release-distribution"
        predecessor_edge = next(
            edge
            for edge in registry["containment_graph"]["edges"]
            if edge["id"] == "steward-concordloom.bindings-adapters"
        )
        predecessor_edge["success_state"] = (
            "invoke-steward-concordloom.release-distribution"
        )
        binding = deepcopy(self.binding)
        for artifact in binding["artifacts"]:
            if artifact["role"] == "cycle_registry":
                artifact["digest"] = digest(registry)
        binding["active_root_loop_ids"].append("knowledge-experience")
        binding["binding_digest"] = document_digest(
            binding,
            excluded_fields=binding["digest_contract"]["excluded_fields"],
        )
        with self.assertRaisesRegex(RoutePreviewError, "leave.*root subtree"):
            create_route_preview(
                binding,
                registry,
                self.policy,
                self.candidate,
                self.model,
                preview_id="outside-root",
                request_digest=REQUEST_DIGEST,
                request_ref="request.user.1",
                root_loop_id="steward-concordloom",
                target_loop_ids=["project-atlas"],
                created_at=NOW,
            )

    def test_missing_or_non_exact_development_model_is_rejected(self) -> None:
        with self.assertRaisesRegex(RoutePreviewError, "required"):
            create_route_preview(
                self.binding,
                self.registry,
                self.policy,
                self.candidate,
                None,  # type: ignore[arg-type]
                preview_id="missing-model",
                request_digest=REQUEST_DIGEST,
                request_ref="request.user.1",
                root_loop_id="steward-concordloom",
                target_loop_ids=["maintain-cli"],
                created_at=NOW,
            )

        with self.assertRaisesRegex(RoutePreviewError, "unexpected kind"):
            create_route_preview(
                self.binding,
                self.registry,
                self.policy,
                self.candidate,
                {},
                preview_id="missing-model",
                request_digest=REQUEST_DIGEST,
                request_ref="request.user.1",
                root_loop_id="steward-concordloom",
                target_loop_ids=["maintain-cli"],
                created_at=NOW,
            )

        changed = deepcopy(self.model)
        changed["nodes"][0]["copy"]["en"]["purpose"] += " Changed."
        with self.assertRaisesRegex(RoutePreviewError, "exact atlas input"):
            create_route_preview(
                self.binding,
                self.registry,
                self.policy,
                self.candidate,
                changed,
                preview_id="changed-model",
                request_digest=REQUEST_DIGEST,
                request_ref="request.user.1",
                root_loop_id="steward-concordloom",
                target_loop_ids=["maintain-cli"],
                created_at=NOW,
            )

    def test_route_and_candidate_drift_are_rejected(self) -> None:
        preview = self.create("maintain-cli")
        shuffled = deepcopy(preview)
        shuffled["proposed_route"].reverse()
        self.repin(shuffled)
        with self.assertRaisesRegex(RoutePreviewError, "exact deterministic route"):
            validate_route_preview(
                shuffled,
                self.binding,
                self.registry,
                self.policy,
                self.candidate,
                self.model,
            )

        changed_candidate = deepcopy(self.candidate)
        changed_candidate["tree_digest"] = "sha256:" + ("d" * 64)
        with self.assertRaisesRegex(RoutePreviewError, "candidate tree"):
            validate_route_preview(
                preview,
                self.binding,
                self.registry,
                self.policy,
                changed_candidate,
                self.model,
            )

    def test_raw_request_and_noncanonical_targets_are_rejected(self) -> None:
        preview = self.create("maintain-cli", "project-atlas")
        with_raw_text = deepcopy(preview)
        with_raw_text["request_text"] = "change the CLI"
        self.repin(with_raw_text)
        with self.assertRaises(ValidationError):
            validate_route_preview(
                with_raw_text,
                self.binding,
                self.registry,
                self.policy,
                self.candidate,
                self.model,
            )

        reordered = deepcopy(preview)
        reordered["target_loop_ids"].reverse()
        self.repin(reordered)
        with self.assertRaisesRegex(RoutePreviewError, "canonically ordered"):
            validate_route_preview(
                reordered,
                self.binding,
                self.registry,
                self.policy,
                self.candidate,
                self.model,
            )

    def test_correction_replaces_only_targets_and_requires_exact_predecessor(
        self,
    ) -> None:
        first = self.create("maintain-cli")
        corrected = self.create(
            "project-atlas",
            preview_id="preview-route-correction",
            replaces_preview=first,
        )

        self.assertEqual(
            first["preview_digest"],
            corrected["replaces_preview_digest"],
        )
        for field in (
            "request_digest",
            "request_ref",
            "binding_digest",
            "registry_digest",
            "policy_digest",
            "development_model_digest",
            "candidate_tree_digest",
            "candidate_manifest_digest",
            "root_loop_id",
        ):
            self.assertEqual(first[field], corrected[field])
        validate_route_preview(
            corrected,
            self.binding,
            self.registry,
            self.policy,
            self.candidate,
            self.model,
            replaced_preview=first,
        )
        with self.assertRaisesRegex(RoutePreviewError, "exact preview"):
            validate_route_preview(
                corrected,
                self.binding,
                self.registry,
                self.policy,
                self.candidate,
                self.model,
            )
        with self.assertRaisesRegex(RoutePreviewError, "must replace"):
            self.create("maintain-cli", replaces_preview=first)
        with self.assertRaisesRegex(
            RoutePreviewError, "cannot replace another correction"
        ):
            self.create("maintain-article", replaces_preview=corrected)

        forged_predecessor = deepcopy(first)
        forged_predecessor["replaces_preview_digest"] = "sha256:" + ("9" * 64)
        self.repin(forged_predecessor)
        forged_successor = self.create("maintain-article")
        forged_successor["replaces_preview_digest"] = forged_predecessor[
            "preview_digest"
        ]
        self.repin(forged_successor)
        with self.assertRaisesRegex(
            RoutePreviewError, "cannot replace another correction"
        ):
            validate_route_preview(
                forged_successor,
                self.binding,
                self.registry,
                self.policy,
                self.candidate,
                self.model,
                replaced_preview=forged_predecessor,
            )

        changed_request = deepcopy(corrected)
        changed_request["request_digest"] = "sha256:" + ("e" * 64)
        self.repin(changed_request)
        with self.assertRaisesRegex(RoutePreviewError, "request_digest"):
            validate_route_preview(
                changed_request,
                self.binding,
                self.registry,
                self.policy,
                self.candidate,
                self.model,
                replaced_preview=first,
            )

    def test_digest_tampering_is_rejected(self) -> None:
        preview = self.create("maintain-cli")
        preview["preview_digest"] = "sha256:" + ("f" * 64)
        with self.assertRaisesRegex(RoutePreviewError, "digest contract"):
            validate_route_preview(
                preview,
                self.binding,
                self.registry,
                self.policy,
                self.candidate,
                self.model,
            )

    def test_corrected_preview_requires_exact_predecessor_before_run(self) -> None:
        first = self.create("maintain-cli")
        corrected = self.create(
            "project-atlas",
            preview_id="preview-route-correction",
            replaces_preview=first,
        )
        common = {
            "binding": self.binding,
            "registry": self.registry,
            "policy": self.policy,
            "candidate_manifest": self.candidate,
            "root_loop_id": "steward-concordloom",
            "candidate_author_principal_ids": ["example-executor"],
            "development_model": self.model,
        }

        card = create_run_card(
            **common,
            run_id="corrected-preview-run",
            route_preview=corrected,
            replaced_route_preview=first,
        )
        self.assertEqual(
            corrected["preview_digest"], card["route_preview_digest"]
        )
        self.assertEqual(corrected["proposed_route"], card["planned_route"])

        with self.assertRaisesRegex(RunStateError, "provided together"):
            create_run_card(
                **common,
                run_id="missing-predecessor",
                route_preview=corrected,
            )
        with self.assertRaisesRegex(RunStateError, "provided together"):
            create_run_card(
                **common,
                run_id="unexpected-predecessor",
                route_preview=first,
                replaced_route_preview=first,
            )
        with self.assertRaisesRegex(RunStateError, "requires a route preview"):
            create_run_card(
                **common,
                run_id="predecessor-only",
                replaced_route_preview=first,
            )
        wrong_predecessor = self.create("maintain-article")
        with self.assertRaisesRegex(RoutePreviewError, "link digest mismatch"):
            create_run_card(
                **common,
                run_id="wrong-predecessor",
                route_preview=corrected,
                replaced_route_preview=wrong_predecessor,
            )

    def test_legacy_run_card_is_read_only_until_explicit_migration(self) -> None:
        current = create_run_card(
            self.binding,
            self.registry,
            self.policy,
            self.candidate,
            run_id="legacy-read-only-run",
            root_loop_id="steward-concordloom",
            candidate_author_principal_ids=["example-executor"],
            target_loop_ids=["maintain-cli"],
            development_model=self.model,
        )
        legacy = deepcopy(current)
        legacy["schema_version"] = "0.1"
        legacy["status"] = "authorized"
        legacy["authorization"] = {
            "actor": {"id": "example-operator", "kind": "operator"},
            "capability": "authorize-run",
            "authorized_at": NOW,
            "binding_digest": self.binding["binding_digest"],
            "scope_digest": digest(legacy["scope"]),
        }
        SchemaStore().validate(legacy, "run-card.schema.json")

        with self.assertRaisesRegex(RunStateError, "legacy read-only"):
            validate_run_card(
                legacy,
                self.binding,
                self.registry,
                self.policy,
                self.candidate,
                repository=None,
                development_model=self.model,
            )
        self.assertIs(
            legacy,
            validate_run_card(
                legacy,
                self.binding,
                self.registry,
                self.policy,
                self.candidate,
                repository=None,
                development_model=self.model,
                legacy_read_only=True,
            ),
        )
        with self.assertRaisesRegex(RunStateError, "legacy read-only"):
            guard(legacy, "steward-concordloom", policy=self.policy)

        migrated = migrate_run_card_v0_1(legacy)
        self.assertEqual(migrated["schema_version"], "0.2")
        self.assertEqual(migrated["status"], "draft")
        self.assertNotIn("authorization", migrated)
        SchemaStore().validate(migrated, "run-card-v0.2.schema.json")

    def test_authorization_binds_exact_preview_plan_and_guard_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository, candidate = self.repository_candidate(Path(temporary))
            first = create_route_preview(
                self.binding,
                self.registry,
                self.policy,
                candidate,
                self.model,
                preview_id="authorized-preview-a",
                request_digest=REQUEST_DIGEST,
                request_ref="request.user.1",
                root_loop_id="steward-concordloom",
                target_loop_ids=["maintain-cli"],
                created_at=NOW,
            )
            second = create_route_preview(
                self.binding,
                self.registry,
                self.policy,
                candidate,
                self.model,
                preview_id="authorized-preview-b",
                request_digest=REQUEST_DIGEST,
                request_ref="request.user.1",
                root_loop_id="steward-concordloom",
                target_loop_ids=["project-atlas"],
                created_at=NOW,
            )
            draft = create_run_card(
                self.binding,
                self.registry,
                self.policy,
                candidate,
                run_id="preview-authorization-run",
                root_loop_id="steward-concordloom",
                candidate_author_principal_ids=["example-executor"],
                development_model=self.model,
                route_preview=first,
            )
            with self.assertRaisesRegex(RunStateError, "exact route preview"):
                validate_run_card(
                    draft,
                    self.binding,
                    self.registry,
                    self.policy,
                    candidate,
                    repository=repository,
                    development_model=self.model,
                )
            authorized = authorize_run(
                draft,
                self.binding,
                self.registry,
                self.policy,
                candidate,
                actor={"id": "example-operator", "kind": "operator"},
                authority_ref="operator",
                authorized_at=NOW,
                repository=repository,
                development_model=self.model,
                route_preview=first,
            )
            self.assertEqual(
                first["preview_digest"],
                authorized["authorization"]["route_preview_digest"],
            )
            guard(
                authorized,
                "steward-concordloom",
                binding=self.binding,
                registry=self.registry,
                policy=self.policy,
                candidate_manifest=candidate,
                repository=repository,
                development_model=self.model,
                route_preview=first,
            )

            tampered_plans = []
            changed_authors = deepcopy(authorized)
            changed_authors["candidate_author_principal_ids"] = [
                "example-reviewer"
            ]
            tampered_plans.append(changed_authors)
            changed_root = deepcopy(authorized)
            changed_root["root_loop_id"] = "runtime-tooling"
            tampered_plans.append(changed_root)
            changed_budgets = deepcopy(authorized)
            changed_budgets["budgets"]["max_attempts"] = 999999
            tampered_plans.append(changed_budgets)
            for tampered in tampered_plans:
                with self.assertRaisesRegex(
                    RunStateError, "authorization plan digest mismatch"
                ):
                    validate_run_card(
                        tampered,
                        self.binding,
                        self.registry,
                        self.policy,
                        candidate,
                        repository=repository,
                        development_model=self.model,
                        route_preview=first,
                    )
                with self.assertRaisesRegex(
                    RunStateError, "authorization plan digest mismatch"
                ):
                    guard(
                        tampered,
                        "steward-concordloom",
                        binding=self.binding,
                        registry=self.registry,
                        policy=self.policy,
                        candidate_manifest=candidate,
                        repository=repository,
                        development_model=self.model,
                        route_preview=first,
                    )

            swapped = deepcopy(authorized)
            swapped["route_preview_digest"] = second["preview_digest"]
            swapped["planned_route"] = deepcopy(second["proposed_route"])
            swapped["nodes"] = [
                {
                    "node_id": item["node_id"],
                    "loop_id": item["loop_id"],
                    "status": "pending",
                    "attempts": [],
                    "evidence_ids": [],
                }
                for item in second["proposed_route"]
            ]
            with self.assertRaises((ValidationError, RunStateError)):
                guard(
                    swapped,
                    "steward-concordloom",
                    binding=self.binding,
                    registry=self.registry,
                    policy=self.policy,
                    candidate_manifest=candidate,
                    repository=repository,
                    development_model=self.model,
                    route_preview=second,
                )
            with self.assertRaisesRegex(
                RunStateError, "authorization plan digest mismatch"
            ):
                record_attempt(
                    swapped,
                    self.policy,
                    candidate,
                    node_id="steward-concordloom",
                    attempt_id="swapped-attempt",
                    started_at=NOW,
                    finished_at=NOW,
                    effective_principal_id="example-orchestrator",
                    effective_agent="orchestrator",
                    effective_model="none",
                    effective_reasoning="deterministic",
                    effective_skill="orchestration",
                    token_accounting="not-applicable",
                    result="pass",
                    repository=repository,
                    binding=self.binding,
                    registry=self.registry,
                    development_model=self.model,
                    route_preview=second,
                )

            downgraded = deepcopy(authorized)
            del downgraded["route_preview_digest"]
            for field in (
                "route_preview_digest",
                "planned_route_digest",
                "planned_nodes_digest",
                "authorization_plan_digest",
            ):
                downgraded["authorization"].pop(field, None)
            downgraded["planned_route"] = deepcopy(second["proposed_route"])
            downgraded["nodes"] = [
                {
                    "node_id": item["node_id"],
                    "loop_id": item["loop_id"],
                    "status": "pending",
                    "attempts": [],
                    "evidence_ids": [],
                }
                for item in second["proposed_route"]
            ]
            with self.assertRaises((ValidationError, RunStateError)):
                validate_run_card(
                    downgraded,
                    self.binding,
                    self.registry,
                    self.policy,
                    candidate,
                    repository=repository,
                    development_model=self.model,
                )
            with self.assertRaises((ValidationError, RunStateError)):
                guard(
                    downgraded,
                    "steward-concordloom",
                    policy=self.policy,
                )

            (repository / "service.py").write_text(
                "answer = 43\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(RunStateError, "candidate"):
                guard(
                    authorized,
                    "steward-concordloom",
                    binding=self.binding,
                    registry=self.registry,
                    policy=self.policy,
                    candidate_manifest=candidate,
                    repository=repository,
                    development_model=self.model,
                    route_preview=first,
                )


class CompositeRoutePreviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.binding = v10_fixture("binding.json")
        self.registry = v10_fixture("cycle-registry.json")
        self.policy = v10_fixture("policy.json")
        self.model = v10_fixture("development-model.json")
        self.candidate = manifest()

    def create(self, *targets: str, **overrides: object) -> dict:
        arguments: dict[str, object] = {
            "preview_id": "composite-preview",
            "request_digest": REQUEST_DIGEST,
            "request_ref": "request.user.1",
            "root_loop_id": "steward-concordloom",
            "target_loop_ids": targets or ("maintain-cli",),
            "created_at": NOW,
        }
        arguments.update(overrides)
        return create_route_preview(
            self.binding,
            self.registry,
            self.policy,
            self.candidate,
            self.model,
            **arguments,
        )

    def repin_registry(self, registry: dict) -> dict:
        binding = deepcopy(self.binding)
        registry_digest = digest(registry)
        artifact = next(
            item
            for item in binding["artifacts"]
            if item["role"] == "cycle_registry"
        )
        artifact["digest"] = registry_digest
        binding["binding_digest"] = document_digest(
            binding,
            excluded_fields=binding["digest_contract"]["excluded_fields"],
        )
        return binding

    def test_leaf_is_one_action_and_composite_expands_success_flow(self) -> None:
        leaf = self.create("maintain-cli")
        self.assertEqual("0.2", leaf["schema_version"])
        self.assertEqual(
            [
                {
                    "target_loop_id": "maintain-cli",
                    "action_loop_ids": ["maintain-cli"],
                    "branch_choices": [],
                    "retry_choices": [],
                }
            ],
            leaf["target_plans"],
        )
        self.assertEqual(
            ["steward-concordloom", "runtime-tooling", "maintain-cli"],
            [item["loop_id"] for item in leaf["proposed_route"]],
        )
        self.assertFalse(leaf["execution_allowed"])
        self.assertNotIn("authorization", leaf)
        SchemaStore().validate_public(leaf)

        composite = self.create("runtime-tooling")
        self.assertEqual(
            [
                "runtime-tooling",
                "maintain-compiler-core",
                "plan-task-route",
                "operate-run-lifecycle",
                "maintain-cli",
                "maintain-automation",
            ],
            composite["target_plans"][0]["action_loop_ids"],
        )
        self.assertEqual(
            [
                "steward-concordloom",
                "runtime-tooling",
                "maintain-compiler-core",
                "plan-task-route",
                "operate-run-lifecycle",
                "maintain-cli",
                "maintain-automation",
            ],
            [item["loop_id"] for item in composite["proposed_route"]],
        )

    def test_nested_composite_expands_recursively(self) -> None:
        preview = self.create("knowledge-experience")
        actions = preview["target_plans"][0]["action_loop_ids"]
        self.assertEqual("knowledge-experience", actions[0])
        self.assertEqual(
            [
                "design-site-experience",
                "define-frontend-concept",
                "accept-frontend-concept",
                "maintain-component-workshop",
                "implement-frontend-surface",
                "maintain-frontend-verification",
                "verify-frontend-candidate",
                "critique-frontend-experience",
                "project-atlas",
            ],
            actions[-9:],
        )

    def test_ambiguous_success_requires_exact_branch_choice(self) -> None:
        registry = deepcopy(self.registry)
        runtime = next(
            loop for loop in registry["loops"] if loop["id"] == "runtime-tooling"
        )
        runtime["local_control_flow"]["transitions"].insert(
            1,
            {
                "evidence_contract_ids": [],
                "from": "start",
                "guard": "operator selected the shorter accepted path",
                "id": "enter-runtime-tooling.operate-run-lifecycle",
                "kind": "progress",
                "to": "invoke-runtime-tooling.operate-run-lifecycle",
            },
        )
        binding = self.repin_registry(registry)

        common = {
            "preview_id": "branch-preview",
            "request_digest": REQUEST_DIGEST,
            "request_ref": "request.user.1",
            "root_loop_id": "steward-concordloom",
            "target_loop_ids": ["runtime-tooling"],
            "created_at": NOW,
        }
        with self.assertRaisesRegex(RoutePreviewError, "explicit branch choice"):
            create_route_preview(
                binding,
                registry,
                self.policy,
                self.candidate,
                self.model,
                **common,
            )
        preview = create_route_preview(
            binding,
            registry,
            self.policy,
            self.candidate,
            self.model,
            branch_choices={
                "runtime-tooling:start": (
                    "enter-runtime-tooling.operate-run-lifecycle"
                )
            },
            **common,
        )
        self.assertEqual(
            {
                "loop_id": "runtime-tooling",
                "state_id": "start",
                "transition_id": "enter-runtime-tooling.operate-run-lifecycle",
            },
            preview["target_plans"][0]["branch_choices"][0],
        )
        self.assertEqual(
            [
                "runtime-tooling",
                "operate-run-lifecycle",
                "maintain-cli",
                "maintain-automation",
            ],
            preview["target_plans"][0]["action_loop_ids"],
        )
        with self.assertRaisesRegex(RoutePreviewError, "unused or non-ambiguous"):
            self.create(
                "maintain-cli",
                branch_choices={"maintain-cli:start": "begin"},
            )

    def test_retries_are_explicit_bounded_and_digest_bound(self) -> None:
        preview = self.create(
            "maintain-cli",
            retry_choices={"maintain-cli:retry": 2},
        )
        self.assertEqual(
            [
                {
                    "loop_id": "maintain-cli",
                    "transition_id": "retry",
                    "traversals": 2,
                }
            ],
            preview["target_plans"][0]["retry_choices"],
        )
        self.assertEqual(
            ["maintain-cli"], preview["target_plans"][0]["action_loop_ids"]
        )
        with self.assertRaisesRegex(RoutePreviewError, "exceeds max_traversals"):
            self.create(
                "maintain-cli",
                retry_choices={"maintain-cli:retry": 3},
            )
        with self.assertRaisesRegex(RoutePreviewError, "unknown or unreachable"):
            self.create(
                "maintain-cli",
                retry_choices={"maintain-cli:not-a-transition": 1},
            )

        tampered = deepcopy(preview)
        tampered["target_plans"][0]["action_loop_ids"].append("maintain-cli")
        tampered["preview_digest"] = document_digest(
            tampered,
            excluded_fields=tampered["digest_contract"]["excluded_fields"],
        )
        with self.assertRaises((ValidationError, RoutePreviewError)):
            validate_route_preview(
                tampered,
                self.binding,
                self.registry,
                self.policy,
                self.candidate,
                self.model,
            )

    def test_correction_can_replace_choices_without_changing_request(self) -> None:
        first = self.create("maintain-cli")
        corrected = self.create(
            "maintain-cli",
            preview_id="retry-correction",
            retry_choices={"maintain-cli:retry": 1},
            replaces_preview=first,
        )
        self.assertEqual(
            first["preview_digest"], corrected["replaces_preview_digest"]
        )
        self.assertEqual(first["request_digest"], corrected["request_digest"])
        self.assertNotEqual(first["target_plans"], corrected["target_plans"])


if __name__ == "__main__":
    unittest.main()
