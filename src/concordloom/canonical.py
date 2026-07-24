"""Deterministic JSON serialization and content addressing.

Concord Loom digests JSON values rather than presentation files.  The encoder
implements the RFC 8785 rules needed by public artifacts: UTF-16 key ordering,
minimal JSON string escaping, finite IEEE-754 numbers, and no insignificant
whitespace.  Integers outside the interoperable IEEE-754 range are rejected.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from hashlib import sha256
import json
import math
import os
from pathlib import Path
from typing import Any


class CanonicalizationError(ValueError):
    """Raised when a value cannot be represented by canonical JSON."""


def _valid_unicode(value: str) -> None:
    for character in value:
        if 0xD800 <= ord(character) <= 0xDFFF:
            raise CanonicalizationError("JSON strings may not contain lone surrogates")


def _string(value: str) -> str:
    _valid_unicode(value)
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


def _float(value: float) -> str:
    if not math.isfinite(value):
        raise CanonicalizationError("canonical JSON does not permit NaN or infinity")
    if value == 0:
        return "0"

    negative = value < 0
    text = repr(abs(value)).lower()
    coefficient, marker, exponent_text = text.partition("e")
    exponent = int(exponent_text) if marker else 0
    whole, dot, fraction = coefficient.partition(".")
    raw_digits = whole + (fraction if dot else "")
    first_significant = len(raw_digits) - len(raw_digits.lstrip("0"))
    digits = raw_digits.lstrip("0").rstrip("0")
    if not digits:
        return "0"
    decimal_exponent = exponent + len(whole) - first_significant - 1

    if -6 <= decimal_exponent < 21:
        decimal_position = decimal_exponent + 1
        if decimal_position <= 0:
            result = "0." + ("0" * -decimal_position) + digits
        elif decimal_position >= len(digits):
            result = digits + ("0" * (decimal_position - len(digits)))
        else:
            result = digits[:decimal_position] + "." + digits[decimal_position:]
    else:
        result = digits[0]
        if len(digits) > 1:
            result += "." + digits[1:]
        result += "e" + ("+" if decimal_exponent >= 0 else "") + str(decimal_exponent)
    return ("-" if negative else "") + result


def _encode(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        return _string(value)
    if isinstance(value, int):
        if abs(value) > 9_007_199_254_740_991:
            raise CanonicalizationError(
                "integers outside the interoperable IEEE-754 range are unsupported"
            )
        return str(value)
    if isinstance(value, float):
        return _float(value)
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(_encode(item) for item in value) + "]"
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise CanonicalizationError("JSON object keys must be strings")
        for key in value:
            _valid_unicode(key)
        keys = sorted(value, key=lambda key: key.encode("utf-16-be"))
        return "{" + ",".join(
            _string(key) + ":" + _encode(value[key]) for key in keys
        ) + "}"
    raise CanonicalizationError(
        f"{type(value).__name__} is not a supported canonical JSON value"
    )


def dumps(value: Any) -> str:
    """Return the canonical JSON representation of *value*."""

    return _encode(value)


def canonical_bytes(value: Any) -> bytes:
    """Return UTF-8 encoded canonical JSON bytes."""

    return dumps(value).encode("utf-8")


def digest(value: Any) -> str:
    """Return a prefixed SHA-256 digest of a JSON value."""

    return "sha256:" + sha256(canonical_bytes(value)).hexdigest()


def without_pointers(value: Any, pointers: Iterable[str]) -> Any:
    """Copy *value* while removing the listed top-level JSON pointers.

    v0.1 intentionally supports only top-level exclusions.  This makes digest
    contracts small and auditable and is sufficient for ``/binding_digest``.
    """

    result = json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))
    if not isinstance(result, dict):
        if tuple(pointers):
            raise CanonicalizationError("digest exclusions require an object")
        return result
    for pointer in pointers:
        if not pointer.startswith("/") or "/" in pointer[1:]:
            raise CanonicalizationError(
                f"unsupported digest exclusion pointer: {pointer!r}"
            )
        key = pointer[1:].replace("~1", "/").replace("~0", "~")
        result.pop(key, None)
    return result


def document_digest(
    value: Any, *, excluded_fields: Iterable[str] = ()
) -> str:
    """Digest a document after applying its explicit digest exclusions."""

    return digest(without_pointers(value, tuple(excluded_fields)))


def load(path: str | Path) -> Any:
    """Load one UTF-8 JSON document."""

    source = Path(path)
    try:
        return json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CanonicalizationError(f"cannot load JSON {source}: {exc}") from exc


def save(path: str | Path, value: Any, *, pretty: bool = True) -> None:
    """Atomically save deterministic, UTF-8, newline-terminated JSON."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if pretty:
        # Validate through the canonical encoder before creating a file.
        canonical_bytes(value)
        payload = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
            sort_keys=True,
        ) + "\n"
    else:
        payload = dumps(value) + "\n"
    temporary = target.with_name(target.name + ".tmp")
    temporary.write_text(payload, encoding="utf-8", newline="\n")
    os.replace(temporary, target)


# Explicit aliases make the digest contract easy to discover from callers.
bytes_for = canonical_bytes
sha256_digest = digest
