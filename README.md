# codex-strip-proxy on Ubuntu: reproducible setup and verification

This package installs a pinned local workaround for the AgentRouter Responses API error:

```text
The requested item was created under a different Azure OpenAI resource.
Use the same resource that created the item to access it.
```

**Completion means successful Codex conversation replay after restarting the desktop app.** A running service or one HTTP 200 entry is only an intermediate check.

## 1. What the proxy does and does not prove

Azure Responses state can be tied to the resource that created it. Replaying that state through a relay that routes to different Azure resources can produce the error. This guide verifies that the workaround succeeded here; it does not independently prove AgentRouter's internal routing.

For a POST whose path contains `/responses`, the pinned script removes top-level `previous_response_id`, `id` directly on each dictionary in `input`, and keys starting with `encrypted` directly on those items. It preserves message content, tool `call_id`s, arguments, and outputs in tested shapes, but does not recursively remove every nested ID. JSON is serialized again, so byte layout can change. Most request headers, including POST authorization, are forwarded; transport headers are filtered. Responses are streamed with limited headers. The proxy listens on IPv4 loopback, `127.0.0.1`, and does not forward WebSockets.

Keep in mind:

- Encrypted reasoning state is removed; token use, latency, and reasoning behavior may change. Model and reasoning effort are unchanged, and no quality or cost gain is promised.
- AgentRouter still receives the prompts, code/context actually sent, and its authentication credential.
- With dumping disabled, logs contain timestamps, paths, status, strip counts, and sizes, not bodies or authorization headers. They are unbounded; rotate them under a reviewed policy.
- Loopback is not an authentication boundary against other local processes or deliberate port forwarding.

## 2. Package layout

| Path | Purpose |
| --- | --- |
| [`manifest.toml`](manifest.toml) | Pinned commit, checksum, upstream, default port, and owned files; only [`src/manifest.py`](src/manifest.py) reads it. |
| [`installer/`](installer/) | `setup.sh` orchestration, `prereqs.sh`, `service_install.sh`, and `probe.sh`. |
| [`templates/codex-strip-proxy.service.tmpl`](templates/codex-strip-proxy.service.tmpl) | The only unit definition; rendered by [`src/template.py`](src/template.py). |
| [`bin/`](bin/) | `proxy-config` for preview/apply/restore and `verify-proxy` for read-only local checks. |
| [`src/`](src/) | Manifest, path, config I/O, editor, template, service, and sanitizer modules. |
| [`ci/`](ci/) / [`tests/`](tests/) | Checksum generator/verifier and unit tests; tests never touch the live config or service. |

The installer phases and both CLIs run `set -euo pipefail` where applicable. Nothing writes to `manifest.toml`.

## 3. Scope, prerequisites, and provider checks

Use this package when:

1. Codex already sends authenticated requests through AgentRouter. This is not an API-key or account setup guide.
2. The selected provider in the effective user config has `base_url = "https://agentrouter.org/v1"`, or already points at this local proxy.
3. You use an Ubuntu desktop session with a working systemd user manager.
4. `/usr/bin/python3` is Python 3.11 or newer, so the helpers can validate TOML with standard-library `tomllib`.

**Tested:** Ubuntu 26.04.1 LTS, `/usr/bin/python3` 3.14.4, port 8899, an AgentRouter provider using an environment-supplied API key, and HTTP Responses traffic. Ubuntu 24.04 has the required Python baseline but was not tested on a clean machine. Ubuntu 22.04 is not a turnkey target for this installer.

Do not run the installer with `sudo`; it installs a service for your desktop user. Do not change the system's default Python interpreter to satisfy it.

Provider names can differ from `AgentRouter`; the helper uses the selected `model_provider`. It stops on profile tables, unexpected provider URLs, symlinked configs, unsupported inline layouts, or explicitly enabled WebSockets. If you use a profile, `--config` override, another `CODEX_HOME`, project configuration, or app-managed provider settings, identify that effective configuration first. This package is specifically for `agentrouter.org`; changing only the URL in `manifest.toml` is not enough to support another relay.

Check prerequisites from the package directory with `bash ./installer/prereqs.sh`. It verifies the required commands, Python version, `tomllib`, and user systemd. Missing packages map to `git`, `curl`, `python3`, and `iproute2` for `ss`; install only what is needed (for example, `sudo apt install git python3 curl iproute2`). Package installation was **not needed or run** on the tested machine, and there is no `pip install` step.

Check the selected provider without printing secrets:

```bash
/usr/bin/python3 ./bin/proxy-config --mode check
```

The output shows the config path, selected provider, and proposed URL, but not credentials or config contents. The default path is `${CODEX_HOME:-$HOME/.codex}/config.toml`, resolved in [`src/env.py`](src/env.py). Keep the existing credential source; a key available in a terminal may not be available to a separately launched GUI app. Avoid printing secrets or whole configs into shared logs.

## 4. Install using the reviewed scripts

Download or extract the complete package, open a terminal in its directory, and run:

```bash
bash ./installer/setup.sh
```

There is no need to mark scripts executable when invoking them with `bash`; the orchestration also works from a zsh terminal.

The installer:

1. Loads pinned values from `manifest.toml` through [`src/manifest.py`](src/manifest.py), previews the selected provider, runs the prerequisite and checksum checks, and creates an evidence directory under `~/.local/state/codex-strip-proxy/setup-*`.
2. Downloads the proxy into `~/.local/share/codex-strip-proxy`, checks out exactly `f28af95966200a614c671b73aa3e1e581ac2141b`, and verifies `codex_strip_proxy.py` against SHA-256 `422f19081195d5586521e1abce5789b12a709ee60dbc93e19a774a4445965fc4`. This proves byte consistency, not trustworthiness.
3. Prints the entire upstream script and waits for `y`. Read it first. Expected imports are `http.server`, `urllib.request`, `urllib.error`, `json`, `sys`, `os`, and `time`. The reviewed script runs no shell commands; `urllib` may honor proxy environment settings and follow redirects.
4. Renders the unit, refuses to overwrite an unexpected checkout or service, and never kills a process to free the port. It installs and enables the user service, waits for an active service with a reachable socket, and runs the keyless direct-vs-proxy probe. The expected result is the same 401 from both.
5. Runs the verifier, applies `bin/proxy-config --mode apply`, then runs the verifier again including the config check.

If port 8899 is occupied, inspect it first:

```bash
ss -ltnp 'sport = :8899'
```

To use a different unprivileged port in a **new** installation:

```bash
STRIP_PROXY_PORT=9900 bash ./installer/setup.sh
```

Use `--port 9900` with both CLIs and replace 8899 later. Changing an existing installation's port is a coordinated service/config change; the installer stops rather than overwriting a differing service.

### Installed service

The template contains the only copy of the unit:

```ini
[Unit]
Description=codex-strip-proxy (strips Azure resource-bound state for AgentRouter)

[Service]
Environment=LOG=%h/.local/state/codex-strip-proxy/proxy.log
UnsetEnvironment=DUMP_DIR
ExecStart=/usr/bin/python3 -I "%h/.local/share/codex-strip-proxy/codex_strip_proxy.py" {{PORT}} {{UPSTREAM}}
Restart=on-failure
RestartSec=2
NoNewPrivileges=yes
UMask=0077
ProtectSystem=strict
ProtectHome=read-only
PrivateTmp=yes
ReadWritePaths=%h/.local/state/codex-strip-proxy
RestrictAddressFamilies=AF_INET AF_UNIX
CapabilityBoundingSet=
RestrictRealtime=yes
LockPersonality=yes

[Install]
WantedBy=default.target
```

The rendered values are the chosen port and `https://agentrouter.org`. The upstream has **no `/v1` suffix**: Codex supplies `/v1/responses`, which the proxy appends to the upstream origin; the local Codex base URL includes `/v1`.

`-I` isolates Python imports but does not clear environment variables. `UnsetEnvironment=DUMP_DIR` disables request-body dumps, and `UMask=0077` keeps new logs private. The hardening directives make system directories and home read-only, allow writes only under `~/.local/state/codex-strip-proxy`, restrict sockets to IPv4/Unix, and drop capabilities. If you change either install path, update `ReadWritePaths` and retest. Do not start another foreground proxy on the same port while the service runs.

### Config edits and reruns

[`bin/proxy-config`](bin/proxy-config) previews by default. On `--mode apply`, it requires the selected provider's current URL to be the known upstream or target local proxy, then saves a unique mode-0600 backup (`config.toml.bak.strip-proxy.<UTC timestamp>`) before replacement. [`src/config_editor.py`](src/config_editor.py) preserves comments, line endings, and all other bytes, verifies that only the selected provider URL changed, checks for concurrent changes, and replaces the file atomically. There is no portable lock against another application writing immediately afterward, so the post-restart config check remains necessary.

An already-correct URL is a no-op. A rerun reuses a matching checkout and service, creates fresh evidence, and repeats local checks; it does not update the proxy revision or restart a running service, and a deliberate unit change requires a reviewed restart. If setup stops halfway, it leaves files and evidence for inspection and does not automatically undo a useful installation. It changes the Codex URL only after service and forwarding checks pass; later failure is handled by rollback.

## 5. Verify in stages

### A. Service, source, config, and sanitizer

```bash
/usr/bin/python3 ./bin/verify-proxy
systemctl --user status codex-strip-proxy --no-pager
ss -ltnp 'sport = :8899'
```

The verifier sends no API requests. It checks the commit/checksum, sanitizer, running command and private logging, listener PID, and selected provider URL, then prints recent logs and labels the result **local checks only**: old entries do not prove new traffic. Expect `127.0.0.1:8899`, owned by the service Python process, with state `active`/`running` and `enabled`. Record `NRestarts`; a rising number needs investigation, though a nonzero historical count alone does not mean the service is broken.

### B. Forwarding without an API key

The installer saves this comparison. To inspect it manually:

```bash
curl --silent --show-error --include --connect-timeout 10 --max-time 45 \
  --header 'Content-Type: application/json' --data '{}' \
  https://agentrouter.org/v1/responses

curl --silent --show-error --include --noproxy '*' --connect-timeout 10 --max-time 45 \
  --header 'Content-Type: application/json' --data '{}' \
  http://127.0.0.1:8899/v1/responses
```

No API key is sent. On the verified installation, both returned 401 with `unauthorized client detected`; compare status and bodies, not complete headers. The probe stops on a status/body mismatch, and a dynamic upstream error may need manual investigation rather than proving the proxy broken. Do not add `curl --fail` (it treats the expected 401 as failure); a 401 from a **real authenticated Codex request** is different and needs credential/provider investigation. Do not use GET `/v1/models` as a health check: this revision's GET handler forwards no client authorization and maps exceptions to 599, so model-list refresh can fail while Responses works.

### C. Fresh Codex CLI session and replay (optional for desktop-only testing)

CLI testing uses the real model and may incur charges. This block creates harmless fixtures, runs two turns in the same read-only session, and verifies the saved events. It stops on failure; inspect `$VERIFY_DIR` rather than bypassing a check.

```bash
set -euo pipefail
umask 077
STATE="$HOME/.local/state/codex-strip-proxy"
mkdir -p "$STATE"
VERIFY_DIR="$(mktemp -d "$STATE/verification-XXXXXXXX")"
mkdir "$VERIFY_DIR/files"
head -c 17 /dev/zero | tr '\0' x > "$VERIFY_DIR/files/small.txt"
head -c 1024 /dev/zero | tr '\0' x > "$VERIFY_DIR/files/medium.txt"
head -c 4096 /dev/zero | tr '\0' x > "$VERIFY_DIR/files/large.txt"

CODEX_BIN="$(command -v codex || true)"
[ -n "$CODEX_BIN" ] || CODEX_BIN=/usr/lib/chatgpt/resources/codex
test -x "$CODEX_BIN" && "$CODEX_BIN" --version

"$CODEX_BIN" --no-daemon -a never exec -s read-only \
  --skip-git-repo-check --json -C "$VERIFY_DIR/files" \
  -o "$VERIFY_DIR/turn1-answer.txt" \
  'Use a shell tool to list the files in this directory and their byte sizes. Only read this directory; do not modify anything. Give a concise answer.' \
  > "$VERIFY_DIR/turn1-events.jsonl" 2> "$VERIFY_DIR/turn1-stderr.log"

SESSION_ID="$(/usr/bin/python3 - "$VERIFY_DIR/turn1-events.jsonl" <<'PY'
import json, sys
events = [json.loads(line) for line in open(sys.argv[1])]
assert any(e['type'] == 'turn.completed' for e in events)
assert not any(e['type'] == 'turn.failed' for e in events)
commands = [e['item'] for e in events if e['type'] == 'item.completed' and e['item']['type'] == 'command_execution']
assert commands and all(c['exit_code'] == 0 for c in commands)
print(next(e['thread_id'] for e in events if e['type'] == 'thread.started'))
PY
)"

"$CODEX_BIN" --no-daemon -a never exec -s read-only \
  --skip-git-repo-check --json -C "$VERIFY_DIR/files" \
  resume "$SESSION_ID" -o "$VERIFY_DIR/turn2-answer.txt" \
  'Which of those files is the largest? Answer using the files and sizes from our previous turn.' \
  > "$VERIFY_DIR/turn2-events.jsonl" 2> "$VERIFY_DIR/turn2-stderr.log"

/usr/bin/python3 - "$VERIFY_DIR" <<'PY'
from pathlib import Path
import json, sys
d = Path(sys.argv[1])
t = [[json.loads(x) for x in (d / f'turn{i}-events.jsonl').read_text().splitlines()] for i in (1, 2)]
assert all(any(x['type'] == 'turn.completed' for x in e) for e in t)
assert not any(x['type'] == 'turn.failed' for e in t for x in e)
ids = [next(x['thread_id'] for x in e if x['type'] == 'thread.started') for e in t]
assert ids[0] == ids[1]
c = [x['item'] for x in t[0] if x['type'] == 'item.completed' and x['item']['type'] == 'command_execution']
assert c and all(x['exit_code'] == 0 for x in c)
a = (d / 'turn2-answer.txt').read_text()
assert 'large.txt' in a and ('4,096' in a or '4096' in a)
assert all((d / 'files' / n).read_bytes() == b'x' * s for n, s in [('small.txt', 17), ('medium.txt', 1024), ('large.txt', 4096)])
print('PASS: same session, two completed turns, successful tool, correct follow-up, unchanged files')
PY
```

The block uses the exact session ID; do not substitute `resume --last`. The verified machine used `/usr/lib/chatgpt/resources/codex`; if your CLI differs, use its help rather than an approvals/sandbox bypass. The read-only sandbox stays enabled. Check fresh proxy log entries over the same interval.

### D. Full desktop restart and two prompts

1. Finish active work, then use the app's Quit or tray Quit action to exit completely. Closing a window may leave processes alive. Do not use `pkill -f codex`, whose broad match can hit the proxy and other Codex work.
2. Reopen with the same credential environment and provider configuration. Run `bin/proxy-config --mode check` again; current and target URLs should both be the local proxy.
3. In another terminal, show only new log entries:

   ```bash
   date -Is
   tail -n 0 -F "$HOME/.local/state/codex-strip-proxy/proxy.log"
   ```

4. In one desktop chat, ask: “Use a shell tool to list the files in this directory and their byte sizes. Do not modify anything.” After it finishes, ask in **the same chat**: “Which of those files is the largest?”
5. Confirm the tool output, completed answers, and fresh HTTP 200 entries. The follow-up should show a positive strip count when replay contains resource-bound fields. If all counts are zero, requests may be succeeding but state removal is not demonstrated.

`-F` follows the log if it is created later or rotated. Stop the viewer with Ctrl+C; that does not stop the service. Counts and sizes vary; even a first turn can show `stripped > 0`.

### Completion criteria

Call the installation verified only when all applicable items are observed:

- The correct pinned process is enabled, active, and listening only on the chosen loopback port.
- The effective selected provider URL points at it and persists after a full desktop restart.
- A real authenticated prompt completes a tool call and a subsequent prompt completes in the same conversation.
- Fresh log entries correspond to those turns, show HTTP 200, and demonstrate removal of replayed state.
- The returned answers and tool results are correct, with no relevant Azure error.

The proxy logs HTTP status after receiving upstream response headers, **before** streaming the body. A dropped stream can therefore coexist with an HTTP 200 log line, which is why completed client turns are required.

Keep a redacted report: date/time zone, platform and versions, config path and provider (no key), commit/checksum, service status, backup name, session ID, command exits, answers, and fresh log lines.

Save a redacted report with the date/time zone, platform and versions, config path and selected provider (no key), commit/checksum, service status, backup filename, test directory/session ID, command exits, final answers, and relevant fresh log lines.

## 6. Evidence and limitations

The tested installation changed only the selected URL, kept model/reasoning/authentication settings, and used the template service. The sanitizer removed six sample state fields; both CLI turns exited 0, completed, shared a session, listed the fixtures correctly, and left them unchanged. The deliberate keyless probe logged 401; CLI and post-restart desktop replay produced fresh 200 entries with positive strip counts (for example 7, 5, and 79 removed fields). After a full quit/reopen, the config still pointed local, and the service stayed active/enabled with zero restarts. This demonstrates persistence on that machine, not every future payload, relay state, or Codex version.

Limitations:

- Prerequisite installation was skipped because the tools were already present; no `pip install` was used.
- The foreground proxy test was unnecessary; forwarding was tested through the installed service.
- Initial DNS/network and `systemctl`/`ss` checks failed in a restricted agent sandbox but worked with approved host access; this was not evidence the commands were wrong.
- Desktop shutdown was user-performed to avoid interrupting work; completion was withheld until restart and new traffic.
- The hardened unit passes `systemd-analyze --user verify` but has not run against a live service in this revision. The fresh-install orchestration has not reinstalled this machine or been tested on every Ubuntu release; see [VALIDATION.md](VALIDATION.md). The CLI also warned about ignored settings and plugin requests, but both turns completed.

## 7. Troubleshooting

| Observation | Interpretation and next check |
| --- | --- |
| Keyless direct and proxied POST both return matching 401 | Expected forwarding check. Continue with authenticated Codex verification. |
| Actual Codex request returns 401 | Authentication/client acceptance failed. Verify the app's credential source and effective provider; this is not automatically proof that the proxy is at fault. Do not share the key. |
| 400 with the Azure resource or encrypted-content message | Save the error and corresponding metadata line. The request shape may include resource-bound state the pinned sanitizer does not handle. Do not declare success. |
| Other 400 | Inspect the error body; unsupported model parameters or malformed input are different problems. |
| 429 or 5xx | Investigate relay limits or upstream availability. State stripping does not fix those. |
| 599 with `strip-proxy upstream failure` | Python failed before receiving normal upstream headers, for example DNS, TLS, connection, or timeout failure. Such POST failures are returned before the normal metadata log write. |
| No new metadata lines | Check URL/overrides and desktop restart, but also service state, upstream failures, the configured log path, and its permissions. The script silently ignores log-write exceptions. |
| HTTP 200 but turn fails or never completes | Check client output and stream behavior; the status line was recorded before streaming completed. Do not count it as a completed turn. |
| Connection refused | Check service state and the selected port. |
| Address already in use | Inspect `ss`; do not start another copy or kill an unrelated process. |
| `systemctl --user` cannot connect to the bus | Use the logged-in user's desktop terminal. Do not substitute `sudo systemctl --user`. In an agent sandbox, use its ordinary permission/host-access flow. |
| `ss` says operation not permitted | Retry through authorized host access or a normal terminal; do not label the port free from a failed command. |
| `curl: (6) Could not resolve host` | Check whether the execution environment permits network/DNS before changing system DNS settings. |
| Config changes back after reopening the app | Inspect app/provider management and effective configuration. Stop repeatedly overwriting the file until the source of the rewrite is understood. |
| Model-list refresh fails | This revision's GET auth handling is limited. Diagnose Responses conversations separately. |
| Script stops on an existing differing unit/repository | Preserve it and review the differences. The refusal avoids overwriting unrelated work. |

Useful read-only diagnostics:

```bash
systemctl --user status codex-strip-proxy --no-pager
systemctl --user show codex-strip-proxy \
  -p ActiveState -p SubState -p UnitFileState -p MainPID -p NRestarts
journalctl --user -u codex-strip-proxy -n 30 --no-pager
ss -ltnp 'sport = :8899'
tail -n 20 "$HOME/.local/state/codex-strip-proxy/proxy.log"
```

`systemd-analyze --user verify` may warn about another installed unit; one observed warning concerned `spice-vdagent.service`. Read the unit name and exit result. Do not change unrelated services to silence a warning.

## 8. Maintenance and reversible rollback

Keep the proxy pinned; inspect diffs and retest replay after any revision change. `Restart=on-failure` helps after crashes but does not detect stalled requests or guarantee uptime. Enabled user services normally start at login and may stop after logout; `loginctl enable-linger` is an optional separate choice, and no firewall opening is required.

### Rotation, restart, and rollback

The log is unbounded. A reviewed user-level `logrotate` policy can rotate it without dropping evidence:

```text
$HOME/.local/state/codex-strip-proxy/proxy.log {
    weekly
    rotate 8
    compress
    missingok
    notifempty
    copytruncate
}
```

`copytruncate` avoids interrupting active requests; review retention, ownership, and the runner user. Let active requests finish before a restart:

```bash
systemctl --user restart codex-strip-proxy
```

For rollback, restore **only** the selected provider URL; the CLI makes another backup and preserves later edits:

```bash
/usr/bin/python3 ./bin/proxy-config --mode restore
```

Supply the same `--port` if needed, fully quit/reopen Codex, and confirm it uses the direct upstream. Then stop and disable the service:

```bash
systemctl --user disable --now codex-strip-proxy
```

This retains source, unit, backups, and logs. Do not blindly copy an old whole-config backup over a current config; use it as a reference for a manual merge.

## 9. Checksums, CI, and license

`manifest.toml` lists every shipped file except `SHA256SUMS.txt`. [`ci/generate_checksums.sh`](ci/generate_checksums.sh) hashes exactly that list into [`SHA256SUMS.txt`](SHA256SUMS.txt); do not edit it by hand. [`ci/verify_checksums.sh`](ci/verify_checksums.sh) is read-only and runs before installer changes and in CI.

The workflow [`.github/workflows/ci.yml`](.github/workflows/ci.yml) checks Bash/Python syntax, runs unit tests on Ubuntu 24.04 and 26.04, and fails if checksums are stale. This proves internal consistency only, not that a fresh install works or the upstream relay is trustworthy.

This package is MIT licensed; see [LICENSE](LICENSE). The pinned upstream is not vendored; the installer clones the recorded commit and verifies its SHA-256. Its GitHub metadata reports no license, so review its terms before redistributing.

## References

- [Pinned upstream source](https://github.com/AnnaofArendelle/codex-strip-proxy/tree/f28af95966200a614c671b73aa3e1e581ac2141b)
- [Official Codex configuration reference](https://developers.openai.com/codex/config-reference/)

This is a verified local workaround and a reproducible procedure, not an official guarantee from OpenAI, Azure, or AgentRouter.
