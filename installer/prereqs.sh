#!/usr/bin/env bash
# Read-only prerequisite checks for the codex-strip-proxy setup package.
set -euo pipefail

fail() { printf 'STOP: %s\n' "$*" >&2; exit 1; }

for cmd in git curl ss systemctl systemd-analyze sha256sum cmp; do
    command -v "$cmd" >/dev/null || fail "Missing prerequisite: $cmd. See README.md."
done
/usr/bin/python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' \
    || fail 'This package needs /usr/bin/python3 3.11+ (Ubuntu 24.04+).'
/usr/bin/python3 -c 'import tomllib' \
    || fail 'The standard-library tomllib module is unavailable.'
systemctl --user show-environment >/dev/null \
    || fail 'Cannot reach your user systemd manager. Run in a logged-in desktop terminal.'
