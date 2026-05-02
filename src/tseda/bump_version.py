"""bump_version — increment the version string in pyproject.toml.

Usage
-----
    bump-version          # bumps patch  (0.1.7 -> 0.1.8)
    bump-version patch    # same
    bump-version minor    # bumps minor  (0.1.7 -> 0.2.0)
    bump-version major    # bumps major  (0.1.7 -> 1.0.0)

The script edits pyproject.toml in-place and prints the old and new version.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_PYPROJECT = Path(__file__).parent.parent.parent / "pyproject.toml"
_VERSION_RE = re.compile(r'^(version\s*=\s*")(\d+)\.(\d+)\.(\d+)(")', re.MULTILINE)


def _bump(major: int, minor: int, patch: int, part: str) -> tuple[int, int, int]:
    if part == "major":
        return major + 1, 0, 0
    if part == "minor":
        return major, minor + 1, 0
    return major, minor, patch + 1


def main() -> None:
    part = sys.argv[1].lower() if len(sys.argv) > 1 else "patch"
    if part not in {"major", "minor", "patch"}:
        print(f"error: unknown part '{part}'. Choose major, minor, or patch.", file=sys.stderr)
        sys.exit(1)

    text = _PYPROJECT.read_text(encoding="utf-8")
    match = _VERSION_RE.search(text)
    if not match:
        print("error: could not find version = \"x.y.z\" in pyproject.toml", file=sys.stderr)
        sys.exit(1)

    prefix, maj, min_, pat, suffix = match.groups()
    old_version = f"{maj}.{min_}.{pat}"
    new_maj, new_min, new_pat = _bump(int(maj), int(min_), int(pat), part)
    new_version = f"{new_maj}.{new_min}.{new_pat}"

    new_text = _VERSION_RE.sub(rf'\g<1>{new_version}\5', text)
    _PYPROJECT.write_text(new_text, encoding="utf-8")
    print(f"Bumped {part}: {old_version} → {new_version}")


if __name__ == "__main__":
    main()
