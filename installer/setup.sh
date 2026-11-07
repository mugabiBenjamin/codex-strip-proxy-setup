#!/usr/bin/env bash
# Orchestration only: sequence the reviewed install phases.
set -euo pipefail
umask 077
trap 'printf "Setup stopped at line %s. Read the error above; partial files are retained.\n" "$LINENO" >&2' ERR

fail() { printf 'STOP: %s\n' "$*" >&2; exit 1; }
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_ROOT="$(cd -- "$HERE/.." && pwd)"
export PACKAGE_ROOT

# Load shared values through src.manifest, the package's only manifest reader.
eval "$(PYTHONPATH="$PACKAGE_ROOT" /usr/bin/python3 - <<'PY'
import shlex
from src import manifest
values = {
    'COMMIT': manifest.COMMIT,
    'SHA256': manifest.SHA256,
    'UPSTREAM': manifest.UPSTREAM,
    'REPO': manifest.REPOSITORY,
    'DEFAULT_PORT': manifest.DEFAULT_PORT,
    'CODEX_HOME_ENV_VAR': manifest.CODEX_HOME_ENV_VAR,
}
for name, value in values.items():
    print(f'export {name}={shlex.quote(str(value))}')
PY
)"

[[ "$EUID" -ne 0 ]] || fail 'Run as your desktop user, without sudo.'
PORT="${STRIP_PROXY_PORT:-$DEFAULT_PORT}"
[[ "$PORT" =~ ^[1-9][0-9]{3,4}$ ]] || fail 'STRIP_PROXY_PORT must be a decimal port from 1024 to 65535.'
(( PORT >= 1024 && PORT <= 65535 )) || fail 'Port is out of range.'

for file in "$HERE/prereqs.sh" "$HERE/service_install.sh" "$HERE/probe.sh" \
            "$PACKAGE_ROOT/bin/proxy-config" "$PACKAGE_ROOT/bin/verify-proxy" \
            "$PACKAGE_ROOT/templates/codex-strip-proxy.service.tmpl"; do
    [[ -f "$file" ]] || fail "Missing package file: $file"
done

DIR="$HOME/.local/share/codex-strip-proxy"
STATE="$HOME/.local/state/codex-strip-proxy"
UNIT="$HOME/.config/systemd/user/codex-strip-proxy.service"
codex_home="${!CODEX_HOME_ENV_VAR:-$HOME/.codex}"
CFG="$codex_home/config.toml"
TEMPLATE="$PACKAGE_ROOT/templates/codex-strip-proxy.service.tmpl"
export PORT UPSTREAM COMMIT SHA256 REPO DIR UNIT TEMPLATE

# Preview before downloading or changing anything. Does not print API keys.
/usr/bin/python3 "$PACKAGE_ROOT/bin/proxy-config" --config "$CFG" --port "$PORT" --mode check

bash "$HERE/prereqs.sh"
bash "$PACKAGE_ROOT/ci/verify_files.sh"

mkdir -p "$STATE" "$(dirname -- "$DIR")" "$(dirname -- "$UNIT")"
RUN="$(mktemp -d "$STATE/setup-XXXXXXXX")"
export RUN
printf 'Setup evidence directory: %s\n' "$RUN"

bash "$HERE/service_install.sh"
bash "$HERE/probe.sh"

/usr/bin/python3 "$PACKAGE_ROOT/bin/verify-proxy" --config "$CFG" --port "$PORT" --service-only \
    | tee "$RUN/service-check.json"
/usr/bin/python3 "$PACKAGE_ROOT/bin/proxy-config" --config "$CFG" --port "$PORT" --mode apply \
    | tee "$RUN/config-change.json"
/usr/bin/python3 "$PACKAGE_ROOT/bin/verify-proxy" --config "$CFG" --port "$PORT" \
    | tee "$RUN/final-check.json"

printf '\nInstalled and locally checked. Saved evidence: %s\n' "$RUN"
printf 'NOT YET VERIFIED: authenticated Codex turns and desktop restart. Complete README.md verification steps.\n'
