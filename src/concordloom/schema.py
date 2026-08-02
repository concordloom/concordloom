"""Fail-closed validation for Concord Loom's public JSON Schemas.

The portable core intentionally implements only the declarative Draft 2020-12
subset used by the shipped schemas.  Unknown validation keywords are rejected
instead of being silently ignored.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import math
import os
from pathlib import Path
import re
import sysconfig
from typing import Any

from .canonical import CanonicalizationError, canonical_bytes


ANNOTATIONS = {"$schema", "$id", "title", "description", "$defs"}
VALIDATION_KEYWORDS = {
    "$ref",
    "type",
    "const",
    "enum",
    "properties",
    "required",
    "additionalProperties",
    "minProperties",
    "maxProperties",
    "items",
    "minItems",
    "maxItems",
    "uniqueItems",
    "minLength",
    "maxLength",
    "pattern",
    "format",
    "minimum",
    "maximum",
    "allOf",
    "anyOf",
    "oneOf",
    "not",
    "if",
    "then",
    "else",
}
KNOWN_KEYWORDS = ANNOTATIONS | VALIDATION_KEYWORDS

PUBLIC_SCHEMAS = {
    "concordloom.binding": "binding.schema.json",
    "concordloom.binding-proposal": "binding-proposal.schema.json",
    "concordloom.catalog": "catalog.schema.json",
    "concordloom.candidate-manifest": "candidate-manifest.schema.json",
    "concordloom.cycle-registry": "cycle-registry.schema.json",
    "concordloom.decision-log": "decision-log.schema.json",
    "concordloom.decision-record": "decision-record.schema.json",
    "concordloom.evidence": "evidence.schema.json",
    "concordloom.evolution-proposal": "evolution-proposal.schema.json",
    "concordloom.evolution-signal": "evolution-signal.schema.json",
    "concordloom.loop-design-manifest": "loop-design-manifest.schema.json",
    "concordloom.loop-design-proposal": "loop-design-proposal.schema.json",
    "concordloom.policy": "policy.schema.json",
    "concordloom.project-graph": "project-graph.schema.json",
    "concordloom.question-set": "question-set.schema.json",
    "concordloom.route-preview": "route-preview.schema.json",
    "concordloom.run-card": "run-card.schema.json",
}


class SchemaError(RuntimeError):
    """A schema cannot be loaded or uses an unsupported construct."""


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


class ValidationError(ValueError):
    """A document does not satisfy its selected schema."""

    def __init__(self, issues: list[ValidationIssue]):
        self.issues = tuple(issues)
        summary = "; ".join(str(issue) for issue in self.issues[:8])
        if len(self.issues) > 8:
            summary += f"; and {len(self.issues) - 8} more"
        super().__init__(summary)


def _default_schema_dirs() -> list[Path]:
    result: list[Path] = []
    configured = os.environ.get("CONCORDLOOM_SCHEMA_DIR")
    if configured:
        result.append(Path(configured))
    # Editable/source checkout.
    result.append(Path(__file__).resolve().parents[2] / "schemas")
    # Wheel data-files installation.
    data_root = Path(sysconfig.get_paths()["data"])
    result.append(data_root / "share" / "concordloom" / "schemas")
    # Deliberately last: convenient for an unpacked release, never implicit
    # network or package discovery.
    result.append(Path.cwd() / "schemas")
    return result


def discover_schema_dir() -> Path:
    """Return the first complete local schema directory."""

    for candidate in _default_schema_dirs():
        if (candidate / "common.schema.json").is_file():
            return candidate.resolve()
    searched = ", ".join(str(path) for path in _default_schema_dirs())
    raise SchemaError(f"cannot find Concord Loom schemas; searched: {searched}")


def _join(path: str, token: str | int) -> str:
    escaped = str(token).replace("~", "~0").replace("/", "~1")
    return path.rstrip("/") + "/" + escaped if path != "/" else "/" + escaped


def _json_type(value: Any, expected: str) -> bool:
    if expected == "null":
        return value is None
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and (not isinstance(value, float) or math.isfinite(value))
        )
    raise SchemaError(f"unsupported JSON Schema type {expected!r}")


def _date_time(value: str) -> bool:
    if not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
        r"(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})",
        value,
    ):
        return False
    try:
        parsed = value[:-1] + "+00:00" if value.endswith("Z") else value
        datetime.fromisoformat(parsed)
    except ValueError:
        return False
    return True


class SchemaStore:
    """A closed, local store of the schemas shipped with one release."""

    def __init__(
        self,
        schema_dir: str | Path | None = None,
        *,
        require_common: bool = True,
    ):
        self.schema_dir = (
            Path(schema_dir).resolve() if schema_dir is not None else discover_schema_dir()
        )
        if not self.schema_dir.is_dir():
            raise SchemaError(f"schema directory does not exist: {self.schema_dir}")
        self._schemas: dict[str, dict[str, Any]] = {}
        self._ids: dict[str, str] = {}
        for path in sorted(self.schema_dir.glob("*.schema.json")):
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise SchemaError(f"cannot load schema {path}: {exc}") from exc
            if not isinstance(value, dict):
                raise SchemaError(f"schema {path} must be an object")
            self._schemas[path.name] = value
            identifier = value.get("$id")
            if isinstance(identifier, str):
                self._ids[identifier] = path.name
            self._check_schema(value, path.name, "#")
        if require_common and "common.schema.json" not in self._schemas:
            raise SchemaError(f"{self.schema_dir} has no common.schema.json")

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._schemas))

    def schema(self, name: str) -> dict[str, Any]:
        resolved = self._ids.get(name, Path(name).name)
        try:
            return self._schemas[resolved]
        except KeyError as exc:
            raise SchemaError(f"unknown schema {name!r}") from exc

    def _check_schema(self, schema: Any, name: str, location: str) -> None:
        if isinstance(schema, bool):
            return
        if not isinstance(schema, dict):
            raise SchemaError(f"{name}{location} must be an object or boolean")
        unknown = set(schema) - KNOWN_KEYWORDS
        if unknown:
            raise SchemaError(
                f"{name}{location} uses unsupported keywords: "
                + ", ".join(sorted(unknown))
            )
        for key in ("properties", "$defs"):
            values = schema.get(key, {})
            if not isinstance(values, dict):
                raise SchemaError(f"{name}{location}/{key} must be an object")
            for child_name, child in values.items():
                self._check_schema(child, name, f"{location}/{key}/{child_name}")
        for key in ("items", "additionalProperties", "not", "if", "then", "else"):
            if key in schema:
                self._check_schema(schema[key], name, f"{location}/{key}")
        for key in ("allOf", "anyOf", "oneOf"):
            if key in schema:
                children = schema[key]
                if not isinstance(children, list):
                    raise SchemaError(f"{name}{location}/{key} must be an array")
                for index, child in enumerate(children):
                    self._check_schema(child, name, f"{location}/{key}/{index}")

    def _pointer(self, document: Any, fragment: str, ref: str) -> Any:
        if fragment in ("", "/"):
            return document
        if not fragment.startswith("/"):
            raise SchemaError(f"unsupported non-pointer schema reference {ref!r}")
        current = document
        for encoded in fragment[1:].split("/"):
            token = encoded.replace("~1", "/").replace("~0", "~")
            try:
                current = current[int(token)] if isinstance(current, list) else current[token]
            except (KeyError, IndexError, ValueError, TypeError) as exc:
                raise SchemaError(f"unresolved schema reference {ref!r}") from exc
        return current

    def _resolve(self, ref: str, base_name: str) -> tuple[Any, str]:
        external, separator, fragment = ref.partition("#")
        if external:
            resolved_name = self._ids.get(external, Path(external).name)
            if resolved_name not in self._schemas:
                raise SchemaError(f"schema reference leaves local store: {ref!r}")
        else:
            resolved_name = base_name
        if resolved_name not in self._schemas:
            raise SchemaError(f"cannot resolve {ref!r} from inline schema")
        root = self._schemas[resolved_name]
        return self._pointer(root, fragment if separator else "", ref), resolved_name

    def _issues(
        self,
        instance: Any,
        schema: Any,
        *,
        base_name: str,
        path: str,
    ) -> list[ValidationIssue]:
        if schema is True:
            return []
        if schema is False:
            return [ValidationIssue(path, "value is forbidden by schema")]
        if not isinstance(schema, dict):
            raise SchemaError("schema node must be an object or boolean")

        issues: list[ValidationIssue] = []
        if "$ref" in schema:
            target, target_base = self._resolve(schema["$ref"], base_name)
            issues.extend(
                self._issues(instance, target, base_name=target_base, path=path)
            )

        expected = schema.get("type")
        if expected is not None:
            expected_types = [expected] if isinstance(expected, str) else expected
            if not isinstance(expected_types, list) or not all(
                isinstance(item, str) for item in expected_types
            ):
                raise SchemaError("type must be a string or string array")
            if not any(_json_type(instance, item) for item in expected_types):
                return issues + [
                    ValidationIssue(
                        path,
                        "expected " + " or ".join(expected_types),
                    )
                ]

        if "const" in schema and instance != schema["const"]:
            issues.append(ValidationIssue(path, f"expected constant {schema['const']!r}"))
        if "enum" in schema and instance not in schema["enum"]:
            issues.append(ValidationIssue(path, "value is not in the allowed enumeration"))

        if isinstance(instance, dict):
            if "minProperties" in schema and len(instance) < schema["minProperties"]:
                issues.append(
                    ValidationIssue(
                        path, f"needs at least {schema['minProperties']} properties"
                    )
                )
            if "maxProperties" in schema and len(instance) > schema["maxProperties"]:
                issues.append(
                    ValidationIssue(
                        path, f"allows at most {schema['maxProperties']} properties"
                    )
                )
            required = schema.get("required", [])
            if not isinstance(required, list) or not all(
                isinstance(item, str) for item in required
            ):
                raise SchemaError("required must be a string array")
            for key in required:
                if key not in instance:
                    issues.append(ValidationIssue(path, f"missing required property {key!r}"))
            properties = schema.get("properties", {})
            for key, child in properties.items():
                if key in instance:
                    issues.extend(
                        self._issues(
                            instance[key],
                            child,
                            base_name=base_name,
                            path=_join(path, key),
                        )
                    )
            extras = sorted(set(instance) - set(properties))
            additional = schema.get("additionalProperties", True)
            if additional is False:
                for key in extras:
                    issues.append(
                        ValidationIssue(_join(path, key), "additional property is forbidden")
                    )
            elif isinstance(additional, dict):
                for key in extras:
                    issues.extend(
                        self._issues(
                            instance[key],
                            additional,
                            base_name=base_name,
                            path=_join(path, key),
                        )
                    )
            elif additional is not True:
                raise SchemaError("additionalProperties must be a schema or boolean")

        if isinstance(instance, list):
            if "minItems" in schema and len(instance) < schema["minItems"]:
                issues.append(
                    ValidationIssue(path, f"needs at least {schema['minItems']} items")
                )
            if "maxItems" in schema and len(instance) > schema["maxItems"]:
                issues.append(
                    ValidationIssue(path, f"allows at most {schema['maxItems']} items")
                )
            if schema.get("uniqueItems"):
                seen: set[bytes] = set()
                for index, item in enumerate(instance):
                    try:
                        key = canonical_bytes(item)
                    except CanonicalizationError as exc:
                        issues.append(ValidationIssue(_join(path, index), str(exc)))
                        continue
                    if key in seen:
                        issues.append(ValidationIssue(_join(path, index), "duplicate item"))
                    seen.add(key)
            if "items" in schema:
                for index, item in enumerate(instance):
                    issues.extend(
                        self._issues(
                            item,
                            schema["items"],
                            base_name=base_name,
                            path=_join(path, index),
                        )
                    )

        if isinstance(instance, str):
            if "minLength" in schema and len(instance) < schema["minLength"]:
                issues.append(
                    ValidationIssue(path, f"needs at least {schema['minLength']} characters")
                )
            if "maxLength" in schema and len(instance) > schema["maxLength"]:
                issues.append(
                    ValidationIssue(path, f"allows at most {schema['maxLength']} characters")
                )
            if "pattern" in schema:
                try:
                    matched = re.search(schema["pattern"], instance)
                except re.error as exc:
                    raise SchemaError(f"invalid schema pattern: {exc}") from exc
                if matched is None:
                    issues.append(
                        ValidationIssue(path, f"does not match {schema['pattern']!r}")
                    )
            if "format" in schema:
                if schema["format"] != "date-time":
                    raise SchemaError(f"unsupported format {schema['format']!r}")
                if not _date_time(instance):
                    issues.append(ValidationIssue(path, "is not an RFC 3339 date-time"))

        if isinstance(instance, (int, float)) and not isinstance(instance, bool):
            if "minimum" in schema and instance < schema["minimum"]:
                issues.append(
                    ValidationIssue(path, f"must be at least {schema['minimum']}")
                )
            if "maximum" in schema and instance > schema["maximum"]:
                issues.append(
                    ValidationIssue(path, f"must be at most {schema['maximum']}")
                )

        for child in schema.get("allOf", []):
            issues.extend(self._issues(instance, child, base_name=base_name, path=path))
        if "anyOf" in schema:
            branches = [
                self._issues(instance, child, base_name=base_name, path=path)
                for child in schema["anyOf"]
            ]
            if all(branch for branch in branches):
                issues.append(ValidationIssue(path, "does not satisfy any anyOf branch"))
        if "oneOf" in schema:
            branches = [
                self._issues(instance, child, base_name=base_name, path=path)
                for child in schema["oneOf"]
            ]
            if sum(not branch for branch in branches) != 1:
                issues.append(
                    ValidationIssue(path, "must satisfy exactly one oneOf branch")
                )
        if "not" in schema and not self._issues(
            instance, schema["not"], base_name=base_name, path=path
        ):
            issues.append(ValidationIssue(path, "matches a forbidden schema"))
        if "if" in schema:
            condition = self._issues(
                instance, schema["if"], base_name=base_name, path=path
            )
            branch = "then" if not condition else "else"
            if branch in schema:
                issues.extend(
                    self._issues(
                        instance,
                        schema[branch],
                        base_name=base_name,
                        path=path,
                    )
                )
        return issues

    def validate(self, instance: Any, schema: str | dict[str, Any]) -> Any:
        """Validate and return *instance*, raising on the first invalid document."""

        if isinstance(schema, str):
            name = self._ids.get(schema, Path(schema).name)
            selected = self.schema(name)
        elif isinstance(schema, dict):
            name = "<inline>"
            selected = schema
            self._check_schema(selected, name, "#")
            # Inline schemas can still reference shipped external schemas, but
            # cannot use local # pointers because they have no store identity.
        else:
            raise SchemaError("schema selector must be a name or object")
        issues = self._issues(instance, selected, base_name=name, path="/")
        if issues:
            raise ValidationError(issues)
        return instance

    def validate_public(self, instance: Any) -> Any:
        if not isinstance(instance, dict) or not isinstance(instance.get("kind"), str):
            raise ValidationError([ValidationIssue("/", "public artifact needs kind")])
        try:
            name = PUBLIC_SCHEMAS[instance["kind"]]
        except KeyError as exc:
            raise ValidationError(
                [ValidationIssue("/kind", "unknown public artifact kind")]
            ) from exc
        if (
            instance["kind"] == "concordloom.run-card"
            and instance.get("schema_version") == "0.2"
        ):
            name = "run-card-v0.2.schema.json"
        if (
            instance["kind"] == "concordloom.route-preview"
            and instance.get("schema_version") == "0.2"
        ):
            name = "route-preview-v0.2.schema.json"
        return self.validate(instance, name)


def validate(
    instance: Any,
    schema: str | dict[str, Any],
    *,
    schema_dir: str | Path | None = None,
) -> Any:
    return SchemaStore(schema_dir).validate(instance, schema)


def validate_named(
    instance: Any,
    schema_name: str | None = None,
    *,
    schema_dir: str | Path | None = None,
) -> Any:
    store = SchemaStore(schema_dir)
    return store.validate_public(instance) if schema_name is None else store.validate(
        instance, schema_name
    )
