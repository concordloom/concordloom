#!/usr/bin/env python3
"""Record one plain onboarding answer without reconstructing CLI internals."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import re
import subprocess
import sys


def _identifier(value: str) -> str:
    result = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return result or f"person-{hashlib.sha256(value.encode()).hexdigest()[:8]}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Record a confirmed or rejected onboarding question."
    )
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--question", required=True)
    parser.add_argument("--answer", choices=("confirm", "reject"), required=True)
    parser.add_argument("--person-name", required=True)
    parser.add_argument("--rationale", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    verdict = "confirmed" if args.answer == "confirm" else "rejected"
    launcher = Path(__file__).with_name("concordloom_cli.py")
    command = [
        sys.executable,
        str(launcher),
        "decide",
        "--questions",
        str(args.questions),
        "--question",
        args.question,
        "--verdict",
        verdict,
        "--actor-id",
        _identifier(args.person_name),
        "--actor-kind",
        "operator",
        "--actor-display-name",
        args.person_name,
        "--authority-ref",
        "bootstrap-operator",
        "--rationale",
        args.rationale,
        "--decided-at",
        datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "--output",
        str(args.output),
    ]
    completed = subprocess.run(
        command,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode:
        print(
            "Could not record the answer. The repository is unchanged.",
            file=sys.stderr,
        )
        return completed.returncode
    print(str(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
