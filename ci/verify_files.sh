#!/usr/bin/env bash
# Verify that every file listed in manifest.toml exists. With --tracked, also
# require each file to be tracked in Git. Git commit identity and review are
# the integrity boundary; this package intentionally has no checksum file.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

tracked=0
case "${1:-}" in
    "") ;;
    --tracked) tracked=1 ;;
    *) printf 'usage: %s [--tracked]\n' "${0##*/}" >&2; exit 2 ;;
esac

mapfile -t files < <(PYTHONPATH="$ROOT" /usr/bin/python3 - <<'PY'
from src import manifest
for item in manifest.OWNED_FILES:
    print(item)
PY
)
[[ ${#files[@]} -gt 0 ]] || { printf 'STOP: manifest owned_files is empty.\n' >&2; exit 1; }

if (( tracked )); then
    git rev-parse --is-inside-work-tree >/dev/null 2>&1 || {
        printf 'STOP: --tracked requires a Git work tree.\n' >&2
        exit 1
    }
elif git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    tracked=1
fi

status=0
for file in "${files[@]}"; do
    if [[ ! -f "$file" ]]; then
        printf 'MISSING: %s\n' "$file" >&2
        status=1
        continue
    fi
    if (( tracked )) && ! git ls-files --error-unmatch -- "$file" >/dev/null 2>&1; then
        printf 'UNTRACKED: %s\n' "$file" >&2
        status=1
    fi
done

(( status == 0 )) || { printf 'STOP: shipped-file inventory check failed.\n' >&2; exit 1; }
if (( tracked )); then
    printf 'OK: %s shipped files exist and are tracked.\n' "${#files[@]}"
else
    printf 'OK: %s shipped files exist.\n' "${#files[@]}"
fi
