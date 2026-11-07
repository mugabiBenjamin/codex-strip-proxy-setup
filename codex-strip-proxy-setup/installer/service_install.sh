#!/usr/bin/env bash
# Clone/validate the pinned proxy, render and install its user service.
set -euo pipefail

fail() { printf 'STOP: %s\n' "$*" >&2; exit 1; }
for name in PORT UPSTREAM COMMIT SHA256 REPO DIR UNIT RUN TEMPLATE; do
    [[ -n "${!name:-}" ]] || fail "service_install.sh requires $name."
done

PACKAGE_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$(dirname -- "$DIR")" "$(dirname -- "$UNIT")"

if [[ -e "$DIR" || -L "$DIR" ]]; then
    [[ -d "$DIR/.git" && ! -L "$DIR" ]] || fail 'Proxy directory already exists and is not a regular Git checkout.'
    [[ "$(git -C "$DIR" config --get remote.origin.url)" == "$REPO" ]] || fail 'Existing checkout has a different origin.'
    [[ -z "$(git -C "$DIR" status --porcelain --untracked-files=all)" ]] || fail 'Existing checkout has local changes; preserve/review them first.'
    [[ "$(git -C "$DIR" rev-parse HEAD)" == "$COMMIT" ]] || fail 'Existing checkout is at another revision; it was not changed.'
else
    git clone --quiet "$REPO" "$DIR"
    git -c advice.detachedHead=false -C "$DIR" checkout --quiet --detach "$COMMIT"
fi
[[ "$(git -C "$DIR" rev-parse HEAD)" == "$COMMIT" ]] || fail 'Commit verification failed.'
printf '%s  %s\n' "$SHA256" "$DIR/codex_strip_proxy.py" | sha256sum --check
git -C "$DIR" log -1 --format='%H %s' | tee "$RUN/revision.txt"
printf '\nRead the entire script below before continuing:\n'
cat "$DIR/codex_strip_proxy.py"
printf '\nThis installs a user service, then changes only the selected provider URL after the proxy passes a forwarding test.\n'
read -r -p 'Continue with this reviewed script? [y/N] ' answer
[[ "$answer" == y || "$answer" == Y ]] || fail 'Cancelled before service/config changes.'

PYTHONPATH="$PACKAGE_ROOT" /usr/bin/python3 - "$TEMPLATE" "$RUN/codex-strip-proxy.service" "$PORT" "$UPSTREAM" <<'PY'
from pathlib import Path
import sys
from src.template import render
Path(sys.argv[2]).write_text(render(Path(sys.argv[1]), {'PORT': int(sys.argv[3]), 'UPSTREAM': sys.argv[4]}))
PY

if [[ -e "$UNIT" || -L "$UNIT" ]]; then
    [[ -f "$UNIT" && ! -L "$UNIT" ]] || fail 'Existing service file is not a regular file.'
    # Ignore only ExecStart quoting added for home directories containing spaces.
    /usr/bin/python3 - "$UNIT" "$RUN/codex-strip-proxy.service" <<'PY'
from pathlib import Path
import sys
def normalized(path):
    return Path(path).read_text().replace('"%h/.local/share/codex-strip-proxy/codex_strip_proxy.py"', '%h/.local/share/codex-strip-proxy/codex_strip_proxy.py')
if normalized(sys.argv[1]) != normalized(sys.argv[2]):
    sys.exit('STOP: Existing unit differs; it was not overwritten. Review it manually.')
PY
fi
[[ -z "$(systemctl --user show codex-strip-proxy -p DropInPaths --value)" ]] || fail 'Service drop-ins exist; review them before running this installer.'
listeners="$(ss -H -ltnp "sport = :$PORT")"
if [[ -n "$listeners" ]]; then
    systemctl --user is-active --quiet codex-strip-proxy || fail "Port $PORT is occupied; no process was stopped."
    pid="$(systemctl --user show codex-strip-proxy -p MainPID --value)"
    [[ -f "$UNIT" && "$pid" != 0 && "$listeners" == *"pid=$pid,"* ]] || fail 'Listener is not owned by the expected service.'
    # The final health check will validate its address, command and environment.
fi
systemd-analyze --user verify "$RUN/codex-strip-proxy.service"
if [[ ! -e "$UNIT" ]]; then
    (set -o noclobber; cat "$RUN/codex-strip-proxy.service" > "$UNIT")
fi
systemctl --user daemon-reload
systemctl --user enable --now codex-strip-proxy

ready=false
for attempt in {1..30}; do
    if systemctl --user is-active --quiet codex-strip-proxy &&
       /usr/bin/python3 - "$PORT" <<'PY'
import socket, sys
try:
    with socket.create_connection(('127.0.0.1', int(sys.argv[1])), timeout=1):
        pass
except OSError:
    sys.exit(1)
PY
    then ready=true; break; fi
    sleep 1
done
[[ "$ready" == true ]] || fail 'Proxy did not become ready within 30 attempts. Check its journal.'
