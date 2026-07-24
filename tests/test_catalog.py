from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest

from concordloom.canonical import load
from concordloom.catalog import CatalogError, append_binding, validate_catalog


ROOT = Path(__file__).resolve().parents[1]


class CatalogTests(unittest.TestCase):
    def test_append_and_exact_binding_validation(self) -> None:
        binding = load(ROOT / "framework/generic-sdlc/binding.json")
        catalog = append_binding(
            None,
            binding,
            path="framework/generic-sdlc/binding.json",
            catalog_id="generic-catalog",
        )
        validate_catalog(catalog, artifact_root=ROOT)

    def test_predecessor_and_active_head_are_fail_closed(self) -> None:
        binding = load(ROOT / "framework/generic-sdlc/binding.json")
        catalog = append_binding(
            None,
            binding,
            path="framework/generic-sdlc/binding.json",
        )
        broken = deepcopy(catalog)
        broken["active_binding_digest"] = "sha256:" + ("0" * 64)
        with self.assertRaises(CatalogError):
            validate_catalog(broken)

        successor = deepcopy(binding)
        successor["id"] = "successor-binding"
        successor["predecessor_binding_digest"] = "sha256:" + ("f" * 64)
        with self.assertRaises(CatalogError):
            append_binding(catalog, successor, path="successor.json")


if __name__ == "__main__":
    unittest.main()
