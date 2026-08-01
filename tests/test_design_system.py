from __future__ import annotations

import json
from pathlib import Path
import re
import hashlib
import unittest


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"


class DesignSystemAuthorityTests(unittest.TestCase):
    def test_normative_contract_and_machine_source_are_linked(self) -> None:
        english = (ROOT / "docs" / "DESIGN_SYSTEM.md").read_text(encoding="utf-8")
        russian = (ROOT / "docs" / "ru" / "DESIGN_SYSTEM.md").read_text(
            encoding="utf-8"
        )
        english_version = re.search(
            r"^Version: \*\*(\d+\.\d+\.\d+)\*\*$",
            english,
            flags=re.MULTILINE,
        )
        russian_version = re.search(
            r"^Версия: \*\*(\d+\.\d+\.\d+)\*\*$",
            russian,
            flags=re.MULTILINE,
        )
        self.assertIsNotNone(english_version)
        self.assertIsNotNone(russian_version)
        self.assertEqual(english_version.group(1), russian_version.group(1))
        for text in (english, russian):
            self.assertIn("Signal Canvas", text)
            self.assertIn("PRODUCT.md", text)
            self.assertIn("design-tokens.json", text)
            self.assertIn("design-tokens.css", text)
            self.assertIn("design-system.css", text)
            self.assertIn("visual-contract.json", text)
        self.assertIn("Status: **normative**", english)
        self.assertIn("Статус: **нормативный документ**", russian)

    def test_token_authority_has_every_required_domain_and_mode(self) -> None:
        tokens = json.loads(
            (SITE / "design-tokens.json").read_text(encoding="utf-8")
        )
        self.assertEqual("concordloom.design-tokens", tokens["kind"])
        self.assertEqual("4.0.0", tokens["version"])
        self.assertEqual(
            ["primitive", "semantic", "component", "compatibility"],
            list(tokens["layers"]),
        )
        self.assertEqual({"compact", "high-contrast"}, set(tokens["modes"]))
        flattened = {
            name for layer in tokens["layers"].values() for name in layer
        }
        for required in (
            "cl-canvas",
            "cl-mint",
            "cl-blue",
            "cl-coral",
            "cl-yellow",
            "cl-font-display",
            "cl-type-title",
            "cl-space-4",
            "cl-radius-md",
            "cl-control",
            "cl-duration-level",
            "surface-page",
            "surface-panel",
            "surface-module",
            "surface-void",
            "type-reading",
            "panel-background",
            "atlas-node-active",
            "reading-measure",
        ):
            self.assertIn(required, flattened)

    def test_authored_css_cannot_bypass_color_or_font_authority(self) -> None:
        authored = "\n".join(
            (SITE / name).read_text(encoding="utf-8")
            for name in ("styles.css", "design-system.css")
        )
        self.assertIsNone(re.search(r"#[0-9a-fA-F]{3,8}\b|rgba?\(", authored))
        authored_rules = re.sub(
            r"@font-face\s*\{.*?\}",
            "",
            authored,
            flags=re.DOTALL,
        )
        for value in re.findall(r"font-family:\s*([^;]+)", authored_rules):
            self.assertIn("var(--", value)

    def test_visual_baseline_manifest_binds_every_candidate_screenshot(
        self,
    ) -> None:
        manifest = json.loads(
            (
                ROOT
                / "design"
                / "frontend"
                / "baselines"
                / "manifest.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            "concordloom.visual-baseline-manifest",
            manifest["kind"],
        )
        self.assertEqual("candidate-evidence", manifest["status"])
        self.assertEqual(112, manifest["count"])
        self.assertEqual(112, len(manifest["files"]))
        self.assertEqual(
            "signal-canvas-v1",
            manifest["contract"]["id"],
        )
        for item in manifest["files"]:
            path = ROOT / item["path"]
            self.assertTrue(path.is_file(), item["path"])
            data = path.read_bytes()
            self.assertEqual(item["bytes"], len(data))
            self.assertEqual(
                item["sha256"],
                f"sha256:{hashlib.sha256(data).hexdigest()}",
            )

    def test_responsible_cycles_exist_in_the_active_binding(self) -> None:
        catalog = json.loads(
            (ROOT / "framework" / "concordloom" / "catalog.json").read_text(
                encoding="utf-8"
            )
        )
        entry = next(
            item
            for item in catalog["entries"]
            if item["binding_digest"] == catalog["active_binding_digest"]
        )
        binding = json.loads((ROOT / entry["path"]).read_text(encoding="utf-8"))
        model_path = next(
            item["path"]
            for item in binding["artifacts"]
            if item["role"] == "atlas_input"
        )
        model = json.loads((ROOT / model_path).read_text(encoding="utf-8"))
        cycle_ids = {node["id"] for node in model["nodes"]}
        self.assertTrue(
            {
                "design-information-architecture",
                "review-comprehension",
                "design-site-experience",
                "project-atlas",
                "system-evolution",
            }
            <= cycle_ids
        )

    def test_signal_canvas_reference_lock_is_enforced(self) -> None:
        contract = json.loads(
            (ROOT / "design" / "frontend" / "visual-contract.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual("signal-canvas-v1", contract["id"])
        self.assertEqual("implementation-candidate", contract["status"])
        self.assertEqual("interactive-html-concept", contract["reference"]["type"])
        self.assertEqual("Signal Canvas", contract["design_direction"]["name"])
        self.assertEqual("entire public site", contract["design_direction"]["scope"])
        self.assertTrue(contract["acceptance"]["atlas"]["no_background_art"])
        self.assertTrue(
            contract["acceptance"]["interaction"][
                "no_js_status_message_fully_visible_on_direct_entry"
            ]
        )
        self.assertTrue(
            contract["acceptance"]["interaction"]["stale_data_state_required"]
        )
        self.assertTrue(
            contract["acceptance"]["localization"][
                "direct_locale_first_paint_matches_request"
            ]
        )
        self.assertTrue(
            contract["acceptance"]["localization"][
                "localized_loop_titles_preserve_whole_words"
            ]
        )
        self.assertTrue(
            contract["verification"][
                "all_localized_titles_all_viewports_required"
            ]
        )
        self.assertIn(
            "decorative gradient",
            contract["design_direction"]["forbidden"],
        )
        for reference in contract["reference"]["files"]:
            path = ROOT / reference["path"]
            self.assertTrue(path.is_file(), reference["path"])
            self.assertEqual(
                reference["sha256"],
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )

        index = (SITE / "index.html").read_text(encoding="utf-8")
        script = (SITE / "app.js").read_text(encoding="utf-8")
        styles = "\n".join(
            (SITE / name).read_text(encoding="utf-8")
            for name in ("styles.css", "design-system.css")
        )
        for marker in (
            'data-design-system="signal-canvas"',
            "view-tabs",
            "atlas-commandbar",
        ):
            self.assertIn(marker, index)
        self.assertNotIn('data-design-system="patch-panel"', index)
        self.assertNotIn('class="system-rail"', index)
        for marker in ("graph-node", 'motion = "forward"'):
            self.assertIn(marker, script)
        for marker in (
            '[data-motion="forward"] .level-constellation',
            '[data-motion="back"] .level-constellation',
            ".view:target",
            ".node-label",
        ):
            self.assertIn(marker, styles)
        for forbidden in (
            "signal-constellation-stage.png",
            "linear-gradient(",
            "radial-gradient(",
        ):
            self.assertNotIn(forbidden, styles)
        self.assertIn("<noscript>", index)
        self.assertNotIn('data-view="theory" hidden', index)
        self.assertNotIn('data-view="quickstart" hidden', index)


if __name__ == "__main__":
    unittest.main()
