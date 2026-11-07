#!/usr/bin/env bash
# Keyless forwarding check: direct upstream and local proxy must agree.
set -euo pipefail

fail() { printf 'STOP: %s\n' "$*" >&2; exit 1; }
for name in PORT UPSTREAM RUN; do
    [[ -n "${!name:-}" ]] || fail "probe.sh requires $name."
done

# Deliberately send no key. Do not use curl --fail: the expected 401 is an HTTP result.
direct_code="$(curl --silent --show-error --connect-timeout 10 --max-time 45 \
    --output "$RUN/direct-body.json" --write-out '%{http_code}' \
    --header 'Content-Type: application/json' --data '{}' "$UPSTREAM/v1/responses")"
proxy_code="$(curl --silent --show-error --noproxy '*' --connect-timeout 10 --max-time 45 \
    --output "$RUN/proxy-body.json" --write-out '%{http_code}' \
    --header 'Content-Type: application/json' --data '{}' "http://127.0.0.1:$PORT/v1/responses")"
printf 'Unauthenticated direct=%s proxy=%s\n' "$direct_code" "$proxy_code" | tee "$RUN/probe-status.txt"
[[ "$direct_code" == 401 && "$proxy_code" == 401 ]] || fail 'Expected 401 from both probes. Config unchanged; inspect the saved results.'
cmp -s "$RUN/direct-body.json" "$RUN/proxy-body.json" || fail 'Probe bodies differ. Config unchanged; inspect results before proceeding.'
