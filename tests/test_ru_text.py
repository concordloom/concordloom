from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.check_ru_text import lint_path


class RussianTextCheckTests(unittest.TestCase):
    def lint(self, suffix: str, text: str) -> set[str]:
        with TemporaryDirectory() as directory:
            path = Path(directory) / f"sample{suffix}"
            path.write_text(text, encoding="utf-8")
            return {finding.code for finding in lint_path(path)}

    def test_objective_typography_errors_fail(self) -> None:
        codes = self.lint(
            ".md",
            'Он назвал это "картой"... Проект - один процесс.\n',
        )
        self.assertEqual(
            {"ascii-quotes", "three-dot-ellipsis", "hyphen-as-dash"},
            codes,
        )

    def test_code_paths_links_and_fences_are_excluded(self) -> None:
        codes = self.lint(
            ".md",
            """
Команда `tool --label "русский"` находится в `scripts/tool.py`.

[Открыть "русский" пример](https://example.test/"русский")

<img
  src="preview.webp"
  alt="Понятная карта проекта"
>

```text
Проект - один процесс...
governed delivery boundary
```
""",
        )
        self.assertEqual({"ascii-quotes"}, codes)

    def test_ignore_block_is_local(self) -> None:
        codes = self.lint(
            ".md",
            """
<!-- ru-text: ignore-begin -->
Намеренная "ошибка"...
<!-- ru-text: ignore-end -->
Обычный текст - снова проверяется.
""",
        )
        self.assertEqual({"hyphen-as-dash"}, codes)

    def test_assistant_openers_fail_but_direct_copy_passes(self) -> None:
        codes = self.lint(
            ".md",
            """
Отличный вопрос!

Давайте разберёмся.

Карта показывает циклы проекта. Откройте Атлас.
""",
        )
        self.assertEqual({"assistant-praise", "hollow-opener"}, codes)

    def test_known_onboarding_jargon_fails_outside_code(self) -> None:
        codes = self.lint(
            ".md",
            """
Самое важное unresolved-решение определяет governed delivery boundary.

Точное поле `project intent` остаётся машинным идентификатором.
""",
        )
        self.assertEqual({"onboarding-jargon"}, codes)

    def test_html_checks_visible_copy_and_skips_script(self) -> None:
        codes = self.lint(
            ".html",
            """
<button aria-label='Открыть "Атлас"'>Проект - карта</button>
<script>const ignored = 'Ошибка...';</script>
""",
        )
        self.assertEqual({"ascii-quotes", "hyphen-as-dash"}, codes)

    def test_json_and_javascript_human_strings_are_checked(self) -> None:
        json_codes = self.lint(".json", '{"ru": "Карта..."}\n')
        js_codes = self.lint(".js", 'const label = "Проект - карта";\n')
        self.assertEqual({"three-dot-ellipsis"}, json_codes)
        self.assertEqual({"hyphen-as-dash"}, js_codes)


if __name__ == "__main__":
    unittest.main()
