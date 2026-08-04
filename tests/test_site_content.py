from __future__ import annotations

from pathlib import Path
import unittest

from tools.build_site import localized_index, markdown_fragment, robots_txt, sitemap_xml
from tools.check_site import (
    has_forbidden_signal_canvas_background,
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

    def test_public_document_links_stay_inside_the_crawlable_site(self) -> None:
        fragment, _ = markdown_fragment(
            "Read the [trial](REPOSITORY_TRIAL.md).\n",
            source_path=Path("docs/HOW_TO_HELP.md").resolve(),
        )

        self.assertIn(
            'href="https://concordloom.github.io/concordloom/docs/en/repository-trial/"',
            fragment,
        )

    def test_signal_canvas_css_rejects_raw_fonts_and_background_art(self) -> None:
        self.assertTrue(has_raw_font_stack("main { font-family: Arial, sans-serif; }"))
        self.assertFalse(has_raw_font_stack("main { font-family: var(--type-reading); }"))
        self.assertTrue(
            has_forbidden_signal_canvas_background(
                ".atlas { background-image: url(assets/fantasy-map.png); }"
            )
        )
        self.assertTrue(
            has_forbidden_signal_canvas_background(
                ".atlas { background: linear-gradient(red, blue); }"
            )
        )
        self.assertFalse(
            has_forbidden_signal_canvas_background(
                ".atlas { background: var(--surface-page); }"
            )
        )

    def test_localized_indexes_have_canonical_and_language_alternates(self) -> None:
        content = {
            "article": {
                "en": {"html": "<p>English article</p>"},
                "ru": {"html": "<p>Русская статья</p>"},
            },
            "quickstart": {
                "en": {"html": "<p>English quickstart</p>"},
                "ru": {"html": "<p>Русский быстрый старт</p>"},
            },
        }
        russian = localized_index(content, "ru").decode("utf-8")
        self.assertIn('<html lang="ru"', russian)
        self.assertIn(
            'rel="canonical" href="https://concordloom.github.io/concordloom/ru/"',
            russian,
        )
        self.assertIn('hreflang="en"', russian)
        self.assertIn('hreflang="x-default"', russian)
        self.assertIn(
            'href="https://concordloom.github.io/concordloom/docs/ru/how-to-help/"',
            russian,
        )

    def test_crawler_files_name_every_public_language_url(self) -> None:
        robots = robots_txt().decode("utf-8")
        sitemap = sitemap_xml().decode("utf-8")
        self.assertIn("Sitemap: https://concordloom.github.io/concordloom/sitemap.xml", robots)
        for suffix in ("/", "/en/", "/ru/"):
            self.assertIn(
                f"<loc>https://concordloom.github.io/concordloom{suffix}</loc>",
                sitemap,
            )


if __name__ == "__main__":
    unittest.main()
