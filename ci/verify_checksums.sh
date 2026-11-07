#!/usr/bin/env bash
# Verify SHA256SUMS.txt and fail fast, naming the first mismatching file.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
[[ -f SHA256SUMS.txt ]] || { printf 'STOP: SHA256SUMS.txt is missing.\n' >&2; exit 1; }

if ! output="$(sha256sum --check --strict SHA256SUMS.txt 2>&1)"; then
    printf '%s\n' "$output" >&2
    first="$(printf '%s\n' "$output" | awk '/FAILED/ { print $1; exit }')"
    printf 'STOP: checksum verification failed%s\n' "${first:+ for $first}" >&2
    exit 1
fi
printf '%s\n' "$output"
