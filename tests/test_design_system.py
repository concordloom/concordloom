from __future__ import annotations

import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"


class DesignSystemAuthorityTests(unittest.TestCase):
    def test_normative_contract_and_machine_source_are_linked(self) -> None:
        english = (ROOT / "docs" / "DESIGN_SYSTEM.md").read_text(encoding="utf-8")
        russian = (ROOT / "docs" / "ru" / "DESIGN_SYSTEM.md").read_text(
            encoding="utf-8"
        )
        for text in (english, russian):
            self.assertIn("2.0.0", text)
            self.assertIn("design-tokens.json", text)
            self.assertIn("design-tokens.css", text)
            self.assertIn("design-system.css", text)
            self.assertIn("signal-constellation-reference.png", text)
        self.assertIn("Status: **normative**", english)
        self.assertIn("Статус: **нормативный документ**", russian)

    def test_token_authority_has_every_required_domain_and_mode(self) -> None:
        tokens = json.loads(
            (SITE / "design-tokens.json").read_text(encoding="utf-8")
        )
        self.assertEqual("concordloom.design-tokens", tokens["kind"])
        self.assertEqual("2.0.0", tokens["version"])
        self.assertEqual(
            ["primitive", "semantic", "component", "compatibility"],
            list(tokens["layers"]),
        )
        self.assertEqual({"compact", "high-contrast"}, set(tokens["modes"]))
        flattened = {
            name for layer in tokens["layers"].values() for name in layer
        }
        for required in (
            "cl-acid-500",
            "cl-font-display",
            "cl-type-display",
            "cl-space-4",
            "cl-control",
            "cl-duration-level",
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
        for value in re.findall(r"font-family:\s*([^;]+)", authored):
            self.assertIn("var(--", value)

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

    def test_signal_constellation_reference_lock_is_enforced(self) -> None:
        reference = ROOT / "docs" / "assets" / "signal-constellation-reference.png"
        self.assertTrue(reference.is_file())
        self.assertGreater(reference.stat().st_size, 100_000)
        index = (SITE / "index.html").read_text(encoding="utf-8")
        script = (SITE / "app.js").read_text(encoding="utf-8")
        styles = (SITE / "design-system.css").read_text(encoding="utf-8")
        for marker in ("system-rail", "atlas-commandbar"):
            self.assertIn(marker, index)
        for marker in ("parent-constellation", 'motion = "forward"'):
            self.assertIn(marker, script)
        for marker in (
            "signal-constellation-stage.png",
            ".parent-constellation",
            '.atlas-stage[data-motion="forward"]',
            '.atlas-stage[data-motion="back"]',
            ".view:target",
            ".node-label",
        ):
            self.assertIn(marker, styles)
        self.assertIn("<noscript>", index)
        self.assertNotIn('data-view="theory" hidden', index)
        self.assertNotIn('data-view="quickstart" hidden', index)


if __name__ == "__main__":
    unittest.main()
