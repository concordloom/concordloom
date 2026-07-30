from __future__ import annotations

import unittest

from tools.build_site import markdown_fragment
from tools.check_site import (
    has_forbidden_patch_panel_background,
    has_raw_font_stack,
)


class SiteContentProjectionTests(unittest.TestCase):
    def test_markdown_projection_preserves_author_approved_dashes(self) -> None:
        fragment, _ = markdown_fragment(
            "Проверка — отдельное решение. Диапазон 2025–2026.\n"
        )

        self.assertIn("Проверка — отдельное решение.", fragment)
        self.assertIn("2025–2026", fragment)
        self.assertNotIn("Проверка - отдельное решение.", fragment)

    def test_patch_panel_css_rejects_raw_fonts_and_background_art(self) -> None:
        self.assertTrue(has_raw_font_stack("main { font-family: Arial, sans-serif; }"))
        self.assertFalse(has_raw_font_stack("main { font-family: var(--type-reading); }"))
        self.assertTrue(
            has_forbidden_patch_panel_background(
                ".atlas { background-image: url(assets/fantasy-map.png); }"
            )
        )
        self.assertTrue(
            has_forbidden_patch_panel_background(
                ".atlas { background: linear-gradient(red, blue); }"
            )
        )
        self.assertFalse(
            has_forbidden_patch_panel_background(
                ".atlas { background: var(--surface-page); }"
            )
        )


if __name__ == "__main__":
    unittest.main()
