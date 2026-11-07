#!/usr/bin/env bash
# Hash every file listed in manifest.toml's owned_files, in order. This script
# is the only writer of SHA256SUMS.txt; never edit that file by hand.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

mapfile -t files < <(PYTHONPATH="$ROOT" /usr/bin/python3 - <<'PY'
from src import manifest
for item in manifest.OWNED_FILES:
    print(item)
PY
)
[[ ${#files[@]} -gt 0 ]] || { printf 'STOP: manifest owned_files is empty.\n' >&2; exit 1; }
for file in "${files[@]}"; do
    [[ -f "$file" ]] || { printf 'STOP: owned file is missing: %s\n' "$file" >&2; exit 1; }
done

sha256sum "${files[@]}" > SHA256SUMS.txt
printf 'Wrote %s entries to %s.\n' "${#files[@]}" "$ROOT/SHA256SUMS.txt"
