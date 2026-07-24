"""Append-only catalog invariants for activated Concord Loom bindings."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from .canonical import digest, load
from .schema import SchemaStore


class CatalogError(ValueError):
    """A catalog is not an append-only binding chain."""


def _catalog_path(root: Path, raw: str) -> Path:
    path = PurePosixPath(raw)
    if path.is_absolute() or "\\" in raw or ".." in path.parts:
        raise CatalogError(f"unsafe catalog binding path {raw!r}")
    target = root.joinpath(*path.parts)
    try:
        target.parent.resolve().relative_to(root)
    except ValueError as exc:
        raise CatalogError(f"catalog binding path escapes root: {raw!r}") from exc
    return target


def validate_catalog(
    catalog: dict[str, Any],
    *,
    artifact_root: str | Path | None = None,
    schema_store: SchemaStore | None = None,
) -> dict[str, Any]:
    """Validate order, predecessor links, and optionally exact binding bytes."""

    store = schema_store or SchemaStore()
    store.validate(catalog, "catalog.schema.json")
    entries = catalog["entries"]
    ids: set[str] = set()
    digests: set[str] = set()
    paths: set[str] = set()
    previous: str | None = None
    root = Path(artifact_root).resolve() if artifact_root is not None else None
    for index, entry in enumerate(entries):
        if entry["binding_id"] in ids:
            raise CatalogError(f"duplicate binding id {entry['binding_id']!r}")
        if entry["binding_digest"] in digests:
            raise CatalogError("catalog repeats a binding digest")
        if entry["path"] in paths:
            raise CatalogError(f"catalog repeats path {entry['path']!r}")
        ids.add(entry["binding_id"])
        digests.add(entry["binding_digest"])
        paths.add(entry["path"])
        declared_previous = entry.get("previous_binding_digest")
        if index == 0 and declared_previous is not None:
            raise CatalogError("the first catalog entry cannot have a predecessor")
        if index > 0 and declared_previous != previous:
            raise CatalogError("catalog predecessor chain is not append-only")
        previous = entry["binding_digest"]

        if root is not None:
            binding = load(_catalog_path(root, entry["path"]))
            if not isinstance(binding, dict) or binding.get("kind") != "concordloom.binding":
                raise CatalogError("catalog path does not contain a binding")
            store.validate(binding, "binding.schema.json")
            if binding["id"] != entry["binding_id"]:
                raise CatalogError("catalog binding id does not match its bytes")
            if binding["binding_digest"] != entry["binding_digest"]:
                raise CatalogError("catalog binding digest does not match its bytes")
            if binding.get("predecessor_binding_digest") != declared_previous:
                raise CatalogError("binding predecessor differs from catalog chain")
            if digest(binding["accepted_by"]) != entry[
                "activated_by_decision_digest"
            ]:
                raise CatalogError("catalog activation decision digest mismatch")
    if catalog["active_binding_digest"] != entries[-1]["binding_digest"]:
        raise CatalogError("active binding must be the final catalog entry")
    return catalog


def append_binding(
    catalog: Mapping[str, Any] | None,
    binding: Mapping[str, Any],
    *,
    path: str,
    catalog_id: str = "binding-catalog",
    schema_store: SchemaStore | None = None,
) -> dict[str, Any]:
    """Return a new catalog value without mutating or replacing prior entries."""

    store = schema_store or SchemaStore()
    store.validate(dict(binding), "binding.schema.json")
    previous = (
        catalog["active_binding_digest"]
        if catalog is not None
        else None
    )
    if binding.get("predecessor_binding_digest") != previous:
        raise CatalogError("binding predecessor does not match active catalog head")
    result = (
        deepcopy(dict(catalog))
        if catalog is not None
        else {
            "kind": "concordloom.catalog",
            "schema_version": "0.1",
            "id": catalog_id,
            "active_binding_digest": binding["binding_digest"],
            "entries": [],
        }
    )
    entry = {
        "binding_id": binding["id"],
        "binding_digest": binding["binding_digest"],
        "path": path,
        "activated_by_decision_digest": digest(binding["accepted_by"]),
    }
    if previous is not None:
        entry["previous_binding_digest"] = previous
    result["entries"].append(entry)
    result["active_binding_digest"] = binding["binding_digest"]
    validate_catalog(result, schema_store=store)
    return result
