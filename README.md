# codex-strip-proxy on Ubuntu: reproducible setup and verification

This package installs a pinned local workaround for the AgentRouter Responses API error:

```text
The requested item was created under a different Azure OpenAI resource.
Use the same resource that created the item to access it.
```

**Completion means successful Codex conversation replay after restarting the desktop app.** A running service or one HTTP 200 entry is an intermediate check, not sufficient proof by itself.

## 1. Package layout

| Path | Purpose |
| --- | --- |
| [`manifest.toml`](manifest.toml) | Single source of truth: pinned upstream commit and SHA-256, upstream URL, default port, and shipped-file inventory. Only [`src/manifest.py`](src/manifest.py) reads it. |
| [`installer/setup.sh`](installer/setup.sh) | Entry point. Orchestrates the phases below; contains no install logic of its own. |
| [`installer/prereqs.sh`](installer/prereqs.sh) | Read-only tool, Python, `tomllib`, and user-systemd checks. |
| [`installer/service_install.sh`](installer/service_install.sh) | Validates or clones the pinned checkout, verifies its SHA-256, renders and installs the user unit. |
| [`installer/probe.sh`](installer/probe.sh) | Keyless direct-vs-proxy forwarding comparison. |
| [`templates/codex-strip-proxy.service.tmpl`](templates/codex-strip-proxy.service.tmpl) | The only definition of the systemd unit. `{{PORT}}` and `{{UPSTREAM}}` are rendered by [`src/template.py`](src/template.py). |
| [`bin/proxy-config`](bin/proxy-config) | CLI for preview, apply, and restore of the selected provider URL. |
| [`bin/verify-proxy`](bin/verify-proxy) | Read-only local verifier. Sends no API requests. |
| [`src/`](src/) | Manifest, path, config I/O, editor, template, service, and sanitizer modules. |
| [`ci/verify_files.sh`](ci/verify_files.sh) | Checks that every shipped file exists and, inside a Git checkout, is tracked. |
| [`tests/`](tests/) | Unit tests for every module. Never touches the live config or service. |

The three installer phases and the two CLIs each run `set -euo pipefail` where applicable. Nothing here writes to `manifest.toml`.

## 2. What the proxy does—and what it does not prove

Azure Responses state can be tied to the resource that created it. The upstream project's explanation is that replaying that state through a relay that routes requests to different Azure resources can produce this error. Our verification establishes that the workaround succeeded here; it does not independently prove AgentRouter's internal routing architecture.

For a POST whose path contains `/responses`, the pinned script parses a JSON object and removes:

- Top-level `previous_response_id`.
- `id` directly on each dictionary in the `input` array.
- Keys starting with `encrypted` directly on those input items.

It preserves message content, tool `call_id`s, tool arguments, and tool outputs in the tested request shapes. It does **not** recursively remove every nested ID. JSON is serialized again, so byte layout can change. Most request headers, including POST authorization, are forwarded; transport-related headers are filtered. Response bodies are forwarded using chunked transfer, with only a limited set of response headers.

The process listens on IPv4 loopback, `127.0.0.1`. It is not a general-purpose production reverse proxy and does not implement WebSocket forwarding. The existing provider must use HTTP Responses requests with full replayable history.

Tradeoffs and boundaries:

- Encrypted reasoning state is removed on replay. Token use, latency, and reasoning behavior may change. This guide leaves your model and reasoning effort unchanged; no quality or cost improvement is promised from lowering them.
- AgentRouter receives the prompts, code/context actually sent, and its authentication credential. The proxy does not remove that existing trust requirement.
- With request dumping disabled, the proxy's normal log records timestamps, request paths, HTTP status, strip counts, and request sizes—not request bodies or authorization headers. Codex may separately retain its normal conversation records.
- The log is unbounded. Archive or rotate it through a separately reviewed retention policy; do not silently erase verification evidence.
- Loopback prevents direct remote connections under an ordinary host configuration, but it is not an authentication boundary against other local processes or deliberate port forwarding.

## 3. Scope and prerequisites

Use this package when:

1. Codex already uses AgentRouter successfully enough to send authenticated requests. This is not an API-key or account setup guide.
2. The selected provider in the effective user config has `base_url = "https://agentrouter.org/v1"`, or already points at this local proxy.
3. You are using an Ubuntu desktop session with a working systemd user manager.
4. `/usr/bin/python3` is Python 3.11 or newer, so the helpers can validate TOML with the standard-library `tomllib` module.

**Tested:** Ubuntu 26.04.1 LTS, `/usr/bin/python3` 3.14.4, port 8899, an AgentRouter provider using an existing environment-supplied API key, and HTTP Responses traffic. Ubuntu 24.04 has the required Python baseline, but this revised installer has not been tested on a clean Ubuntu 24.04 machine. The upstream proxy needs an older Python baseline than these new helper scripts; the packaged installer is not a turnkey Ubuntu 22.04 procedure.

Do not run the installer with `sudo`. It installs a service for your desktop user. Do not change the system's default Python interpreter to satisfy it.

Provider names can differ from `AgentRouter`; the helper uses the selected `model_provider`. It intentionally stops on profile tables, unexpected provider URLs, symlinked configs, unsupported inline layouts, or a provider that explicitly enables WebSockets. If you launch Codex with a profile, `--config` override, another `CODEX_HOME`, project configuration, or app-managed provider settings, identify that effective configuration first. A base-file check cannot detect every external override.

This package is specifically for `agentrouter.org`. Changing only the URL in `manifest.toml` is not sufficient to support another relay: the config editor, verifier, service command, probe expectations, and trust review would also need to change.

### Check prerequisites

From the package directory:

```bash
bash ./installer/prereqs.sh
```

Or run the individual checks:

```bash
command -v git curl ss systemctl systemd-analyze sha256sum
/usr/bin/python3 --version
/usr/bin/python3 -c 'import tomllib; print("TOML validation available")'
systemctl --user show-environment >/dev/null
```

If packages are missing, review and run only the needed installation commands. Common package mappings are `git`, `curl`, `python3`, and `iproute2` for `ss`. For example:

```bash
sudo apt update
sudo apt install git python3 curl iproute2
```

Package installation was **not needed or run** on the tested machine. There is no `pip install` step.

### Check the selected provider without printing secrets

```bash
/usr/bin/python3 ./bin/proxy-config --mode check
```

The output shows the config path, selected provider, and proposed URL. It does not print credentials or other config contents. By default, the config path is `${CODEX_HOME:-$HOME/.codex}/config.toml`, resolved in [`src/env.py`](src/env.py).

Keep the existing credential source. An API key available in a terminal may not be available to a GUI app launched separately. Avoid printing environment variables, authorization headers, or the whole config into shared logs.

## 4. Install using the reviewed scripts

Download/extract the complete package, open a terminal in its directory, and run:

```bash
bash ./installer/setup.sh
```

There is no need to mark scripts executable when invoking them with `bash`. The orchestration works from a zsh terminal because Bash interprets the scripts.

The installer:

1. Loads pinned values through `src.manifest` from [`manifest.toml`](manifest.toml).
2. Previews the selected provider with `bin/proxy-config --mode check` before changing anything.
3. Runs [`installer/prereqs.sh`](installer/prereqs.sh) and [`ci/verify_files.sh`](ci/verify_files.sh).
4. Creates a unique evidence directory under `~/.local/state/codex-strip-proxy/setup-*`.
5. Runs [`installer/service_install.sh`](installer/service_install.sh), which downloads the proxy into `~/.local/share/codex-strip-proxy`, checks out exactly:

   ```text
   f28af95966200a614c671b73aa3e1e581ac2141b
   ```

6. Verifies `codex_strip_proxy.py` against the checksum recorded in `manifest.toml`:

   ```text
   422f19081195d5586521e1abce5789b12a709ee60dbc93e19a774a4445965fc4
   ```

7. Prints the entire upstream script and waits for `y`. Read it before proceeding. Expected imports are `http.server`, `urllib.request`, `urllib.error`, `json`, `sys`, `os`, and `time`. The reviewed script runs no shell commands. Its network requests use the configured upstream; `urllib` may also honor proxy environment settings and follow redirects.
8. Renders the unit from [`templates/codex-strip-proxy.service.tmpl`](templates/codex-strip-proxy.service.tmpl), refuses to overwrite an unexpected checkout or service, and never kills a process to free the port.
9. Installs/enables the user service and waits for an active service with a reachable local socket.
10. Runs [`installer/probe.sh`](installer/probe.sh): unauthenticated direct and proxied POST requests must agree. The observed expected result is the same 401 response from each.
11. Runs the verifier, applies `bin/proxy-config --mode apply`, then runs the verifier again including the config check.

The upstream checksum establishes that the bytes match the reviewed revision; it is not an independent endorsement of the repository's trustworthiness.

If port 8899 is already occupied, inspect it first:

```bash
ss -ltnp 'sport = :8899'
```

To use a different unprivileged port in a **new** installation:

```bash
STRIP_PROXY_PORT=9900 bash ./installer/setup.sh
```

Use `--port 9900` with both CLIs, and replace 8899 in subsequent commands. Changing the port of an existing installation is a coordinated service/config change; the installer intentionally stops rather than overwriting a differing service.

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

The rendered values are the chosen port and `https://agentrouter.org`. The upstream has **no `/v1` suffix**: Codex supplies `/v1/responses`, which the proxy appends to the upstream origin. The local Codex base URL includes `/v1`.

`-I` isolates Python import behavior; it does not clear ordinary process environment variables. `UnsetEnvironment=DUMP_DIR` explicitly prevents this proxy's optional request-body dumps. `UMask=0077` makes newly created logs private to the user; it does not retroactively change permissions on old files.

The hardening directives make the system directories and home directory read-only, allow writes only to the proxy's state directory, restrict address families to IPv4/Unix sockets, and drop ambient capabilities. `ProtectHome=read-only` combined with `ReadWritePaths=%h/.local/state/codex-strip-proxy` is deliberate: the rendered service needs to read the script under `~/.local/share` and write its log under `~/.local/state`. If you change either path, update `ReadWritePaths` and retest the service.

The earlier verified service used the same core settings with an unquoted script path and without these hardening directives. The installer accepts that equivalent unquoted form. Do not start another foreground proxy on the same port while the service is running.

### Config edits and reruns

[`bin/proxy-config`](bin/proxy-config) previews by default. On `--mode apply`, it requires the selected provider's current URL to be the known upstream or target local proxy. It saves a unique backup beside the config, with mode 0600, before replacement:

```text
config.toml.bak.strip-proxy.<UTC timestamp>
```

The editor in [`src/config_editor.py`](src/config_editor.py) preserves comments, line endings, and all other bytes. It parses the result and verifies that the selected provider URL is the only changed TOML value. It checks for concurrent file changes before an atomic replacement. There is no portable lock that prevents another application from writing immediately afterward, so the post-restart config check remains necessary.

An already-correct URL is a no-op. A rerun reuses a matching clean checkout and equivalent service, creates a fresh evidence directory, and repeats local checks. It does not update the proxy revision or restart an already-running service. After an intentional unit change, a separately reviewed service restart is required for the new settings to take effect.

If setup stops halfway, it leaves files and evidence available for inspection. It does not automatically delete files or undo a potentially useful installation. It changes the Codex URL only after the service and forwarding checks pass. A failure after the URL change is reported and can be handled using the rollback section.

## 5. Verify in stages

### A. Service, source, config, and sanitizer

Run:

```bash
/usr/bin/python3 ./bin/verify-proxy
systemctl --user status codex-strip-proxy --no-pager
ss -ltnp 'sport = :8899'
```

The verifier sends no API requests. It checks the commit and checksum from `manifest.toml`, exercises the sanitizer through [`src/sanitizer_check.py`](src/sanitizer_check.py), verifies the running command and private logging settings, identifies the listener's owning PID, and confirms the selected provider URL. It prints recent logs for inspection. It deliberately labels its result **local checks only**: old successful log entries are not proof of new traffic.

The expected listener is `127.0.0.1:8899`, owned by the service's Python process. Service state should be `active`/`running` and `enabled`. Record `NRestarts`; a rising number requires investigation, although a nonzero historical count does not by itself mean the current service is broken.

### B. Forwarding without an API key

The installer already saves this comparison. To inspect it manually, send these separately:

```bash
curl --silent --show-error --include --connect-timeout 10 --max-time 45 \
  --header 'Content-Type: application/json' --data '{}' \
  https://agentrouter.org/v1/responses

curl --silent --show-error --include --noproxy '*' --connect-timeout 10 --max-time 45 \
  --header 'Content-Type: application/json' --data '{}' \
  http://127.0.0.1:8899/v1/responses
```

No API key is sent. On the verified installation, both returned 401 with `unauthorized client detected`. Compare status and error bodies; complete header equality is not expected because this proxy forwards only limited response headers. The automated probe conservatively stops if the status or body differs; a dynamic upstream error field may require manual investigation rather than indicating a broken proxy.

Do not add `curl --fail` to the keyless probe: it would classify the expected 401 as a command failure. A 401 from a **real authenticated Codex request** is a different result and requires credential/provider investigation.

Do not use GET `/v1/models` as a health check. This revision's GET handler forwards no client authorization and maps exceptions, including upstream HTTP errors, to 599. A successful unauthenticated GET could return another status, so “always 599” is inaccurate. Model-list refresh through this proxy can fail even when Responses conversations work.

### C. Fresh Codex CLI session and replay (optional if testing only the desktop)

CLI testing uses the real configured model and can incur normal model charges. Use harmless files so the test does not need to send project contents. In Bash:

```bash
umask 077
STATE="$HOME/.local/state/codex-strip-proxy"
mkdir -p "$STATE"
VERIFY_DIR="$(mktemp -d "$STATE/verification-XXXXXXXX")"
mkdir "$VERIFY_DIR/files"
/usr/bin/python3 - "$VERIFY_DIR/files" <<'PY'
from pathlib import Path
import sys
directory = Path(sys.argv[1])
for name, size in [('small.txt', 17), ('medium.txt', 1024), ('large.txt', 4096)]:
    with (directory / name).open('xb') as stream:
        stream.write(b'x' * size)
print(directory)
PY
```

Find the CLI and check its installed options:

```bash
CODEX_BIN="$(command -v codex || true)"
if [ -z "$CODEX_BIN" ] && [ -x /usr/lib/chatgpt/resources/codex ]; then
  CODEX_BIN=/usr/lib/chatgpt/resources/codex
fi
test -n "$CODEX_BIN" || { printf 'Codex CLI not found\n' >&2; exit 1; }
"$CODEX_BIN" --version
"$CODEX_BIN" exec --help
"$CODEX_BIN" exec resume --help
```

The bundled executable on the verified machine was `/usr/lib/chatgpt/resources/codex`. The commands below use flags supported by that installed version. If your CLI differs, use its help rather than adding an approvals/sandbox bypass to make a command run.

Send the first prompt and preserve its result:

```bash
"$CODEX_BIN" --no-daemon -a never exec -s read-only \
  --skip-git-repo-check --json -C "$VERIFY_DIR/files" \
  -o "$VERIFY_DIR/turn1-answer.txt" \
  'Use a shell tool to list the files in this directory and their byte sizes. Only read this directory; do not modify anything. Give a concise answer.' \
  > "$VERIFY_DIR/turn1-events.jsonl" 2> "$VERIFY_DIR/turn1-stderr.log"
TURN1_EXIT=$?
printf 'First command exit: %s\n' "$TURN1_EXIT"
```

Stop and inspect the saved events if the command fails. Before resuming, require a completed turn and successful tool execution:

```bash
SESSION_ID="$(/usr/bin/python3 - "$VERIFY_DIR/turn1-events.jsonl" <<'PY'
import json, sys
from pathlib import Path
events = [json.loads(line) for line in Path(sys.argv[1]).read_text().splitlines()]
assert any(e['type'] == 'turn.completed' for e in events), 'First turn did not complete'
assert not any(e['type'] == 'turn.failed' for e in events), 'First turn failed'
commands = [e['item'] for e in events if e['type'] == 'item.completed' and e['item']['type'] == 'command_execution']
assert commands and all(c['exit_code'] == 0 for c in commands), 'Successful shell tool execution not found'
print(next(e['thread_id'] for e in events if e['type'] == 'thread.started'))
PY
)"
```

Use that exact session ID, not `resume --last`, which could select an unrelated session:

```bash
test -n "$SESSION_ID" || { printf 'No verified session ID\n' >&2; exit 1; }
"$CODEX_BIN" --no-daemon -a never exec -s read-only \
  --skip-git-repo-check --json -C "$VERIFY_DIR/files" \
  resume "$SESSION_ID" -o "$VERIFY_DIR/turn2-answer.txt" \
  'Which of those files is the largest? Answer using the files and sizes from our previous turn.' \
  > "$VERIFY_DIR/turn2-events.jsonl" 2> "$VERIFY_DIR/turn2-stderr.log"
TURN2_EXIT=$?
printf 'Follow-up command exit: %s\n' "$TURN2_EXIT"
cat "$VERIFY_DIR/turn1-answer.txt"
cat "$VERIFY_DIR/turn2-answer.txt"
```

Require exit code 0 from each command, `turn.completed` in both event files, the same `thread_id`, and a correct follow-up: `large.txt`, 4,096 bytes. The first turn must have executed a read-only tool, not merely claimed to list files. Check fresh proxy log entries over the same time interval.

Check the saved evidence programmatically:

```bash
/usr/bin/python3 - "$VERIFY_DIR" <<'PY'
from pathlib import Path
import json, sys
directory = Path(sys.argv[1])
turns = [[json.loads(line) for line in (directory / f'turn{i}-events.jsonl').read_text().splitlines()] for i in (1, 2)]
ids = []
for events in turns:
    assert any(e['type'] == 'turn.completed' for e in events), 'Incomplete turn'
    assert not any(e['type'] == 'turn.failed' for e in events), 'Failed turn'
    ids.append(next(e['thread_id'] for e in events if e['type'] == 'thread.started'))
assert ids[0] == ids[1], 'Different sessions'
commands = [e['item'] for e in turns[0] if e['type'] == 'item.completed' and e['item']['type'] == 'command_execution']
assert commands and all(c['exit_code'] == 0 for c in commands), 'No successful shell tool'
answer = (directory / 'turn2-answer.txt').read_text()
assert 'large.txt' in answer and ('4,096' in answer or '4096' in answer), 'Unexpected answer; inspect it'
for name, size in [('small.txt', 17), ('medium.txt', 1024), ('large.txt', 4096)]:
    assert (directory / 'files' / name).read_bytes() == b'x' * size, 'Fixture changed'
print('PASS: same session, two completed turns, successful tool, correct follow-up, unchanged files')
PY
```

`-a never` suppresses interactive approval prompts; the read-only sandbox remains enabled. If the test needs an unavailable permission, inspect the failure rather than disabling that sandbox. The CLI may still save its normal session records; the read-only setting applies to the model's workspace actions.

### D. Full desktop restart and two prompts

1. Finish or save active work in the desktop app.
2. Use its Quit option or tray Quit action to exit completely. Closing a window may leave background processes alive. Do not use `pkill -f codex`: its broad match can include the proxy and other Codex work.
3. Reopen the app with the same existing credential environment and provider configuration.
4. Run `bin/proxy-config --mode check` again. The current and target URLs should both be the local proxy.
5. In another terminal, display only new log entries:

   ```bash
   date -Is
   tail -n 0 -F "$HOME/.local/state/codex-strip-proxy/proxy.log"
   ```

6. In one desktop chat pointed at the harmless fixture directory, ask: “Use a shell tool to list the files in this directory and their byte sizes. Do not modify anything.”
7. After it finishes, ask in **the same chat**: “Which of those files is the largest?”
8. Confirm the tool output, completed answers, and new HTTP 200 log entries. The follow-up should show a positive strip count when replay contains resource-bound fields. If all counts are zero, requests may be succeeding but this test has not demonstrated state removal; inspect the request flow before calling that part proven.

Capital `-F` follows the filename if the log is created later or rotated. Stop the log viewer with Ctrl+C; that does not stop the service.

Exact counts and request sizes vary. Even a first user turn can show `stripped > 0`, because a client may include existing state. Neither “first request must be zero” nor a fixed expected follow-up count is a valid general test.

### Completion criteria

Call the installation verified only when all applicable items are observed:

- The correct pinned process is enabled, active, and listening only on the chosen loopback port.
- The effective selected provider URL points at it and persists after a full desktop restart.
- A real authenticated prompt completes a tool call and a subsequent prompt completes in the same conversation.
- Fresh log entries correspond to those turns, show HTTP 200, and demonstrate removal of replayed state.
- The returned answers and tool results are correct, with no relevant Azure error.

The proxy logs HTTP status after receiving upstream response headers, **before** it finishes streaming the body. A dropped stream can therefore coexist with an HTTP 200 log line. That is why completed client turns are required.

Save a redacted report with the date/time zone, platform and versions, config path and selected provider (no key), commit/checksum, service status, backup filename, test directory/session ID, command exits, final answers, and relevant fresh log lines. These distinguish actual completion from an installation-only claim.

## 6. Evidence from the installation that informed this revision

The tested installation changed only the selected AgentRouter URL, kept the existing model/reasoning/authentication settings, and used a user service with the settings in the template. The sanitizer test removed six sample state fields while preserving the other request content. Both real CLI commands exited 0, emitted `turn.completed`, and used the same session.

The first prompt ran a read-only shell command and returned:

```text
large.txt   4096 bytes
medium.txt  1024 bytes
small.txt   17 bytes
```

The follow-up returned: “`large.txt` is the largest at 4,096 bytes.” The fixtures remained unchanged.

Observed proxy log entries, local time:

```text
2026-11-06 14:45:24 /v1/responses http=401 stripped=0 req=2B
2026-11-06 14:46:49 /v1/responses http=200 stripped=7 req=65006B
2026-11-06 14:46:57 /v1/responses http=200 stripped=10 req=66034B
2026-11-06 14:47:34 /v1/responses http=200 stripped=12 req=66560B
```

The 401 was the deliberate keyless probe. The next three entries covered the first prompt, its tool-result continuation, and the second prompt.

After the user confirmed fully quitting and reopening the desktop app, the config still pointed at the local proxy. The service remained active and enabled, with zero restarts. The resumed desktop conversation completed and produced fresh entries:

```text
2026-11-06 14:53:50 /v1/responses http=200 stripped=76 req=271855B
2026-11-06 14:54:04 /v1/responses http=200 stripped=5 req=86781B
2026-11-06 14:54:20 /v1/responses http=200 stripped=79 req=274901B
```

These observations demonstrate persistence and successful replay on that machine. They do not guarantee that the relay will never fail, that every future payload shape is covered, or that a different Codex version has identical transport behavior.

### Which original commands were skipped or initially failed?

- Prerequisite installation was skipped because the tools were already installed.
- The foreground proxy test was unnecessary: forwarding was tested through the installed service, avoiding a second listener and manual process shutdown.
- Initial DNS/network calls and `systemctl`/`ss` checks failed inside the agent's restricted execution sandbox. They succeeded with approved host access. This was not evidence that those commands were wrong for a normal desktop terminal.
- The broad `sed` edit was replaced with the provider-scoped editor and exact backup/config comparisons described above.
- Desktop shutdown was left to the user so active work was not interrupted. Completion was withheld until the restart and new traffic were verified.
- The CLI warned about existing ignored settings (`model_providers.AgentRouter.models` and `preferred_auth_method`) and some unrelated plugin-catalog requests. Both model test turns completed. Those settings were not changed as part of this fix.
- The fresh-install orchestration in this package is new. Its shell syntax, modules, and config-edit logic have been tested, and the read-only verifier has been run against the successful installation. It has not been used to reinstall this machine or claimed to have been tested on every supported Ubuntu release. See [VALIDATION.md](VALIDATION.md) for the exact checks performed on the deliverable.

## 7. Troubleshooting

| Observation | Interpretation and next check |
| --- | --- |
| Keyless direct and proxied POST both return matching 401 | Expected forwarding check. Continue with authenticated Codex verification. |
| Actual Codex request returns 401 | Authentication/client acceptance failed. Verify the app's credential source and effective provider; this is not automatically proof that the proxy is at fault. Do not share the key. |
| 400 with the Azure resource or encrypted-content message | Save the error and corresponding metadata line. The request shape may include resource-bound state the pinned sanitizer does not handle. Do not declare success. |
| Other 400 | Inspect the error body; unsupported model parameters or malformed input are different problems. |
| 429 or 5xx | Investigate relay limits or upstream availability. State stripping does not fix those. |
| 599 with `strip-proxy upstream failure` | Python failed before receiving normal upstream headers, for example DNS, TLS, connection, or timeout failure. Such POST failures are returned before the normal metadata log write. |
| No new metadata lines | Check URL/overrides and desktop restart, but also check service state, upstream failures, the configured log path, and its permissions. The script silently ignores log-write exceptions. |
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

`systemd-analyze --user verify` may emit a warning about another installed unit; one observed warning concerned `spice-vdagent.service`. Read the unit name and exit result. Do not change unrelated services to silence a warning.

## 8. Maintenance and reversible rollback

Keep the proxy pinned. Before any future revision change, inspect the diff and retest replay. `Restart=on-failure` helps after a crash; it does not detect every stalled request or guarantee uptime.

Enabled user services normally start with the user's manager at login and may stop after logout. Pre-login operation was not needed or tested here. `loginctl enable-linger` is an optional separate administrative choice, not part of the default installation. No firewall opening is required.

### Log rotation

The proxy log is unbounded. Add a reviewed rotation policy rather than deleting verification evidence by hand. For a user-level `logrotate` run, an example configuration is:

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

`copytruncate` avoids restarting the proxy and interrupting active requests. Review the retention period, ownership, and whether your rotation runner executes as the same desktop user. Do not silently truncate the active log during an investigation.

If the service needs a restart, first let active requests finish. A restart can interrupt them:

```bash
systemctl --user restart codex-strip-proxy
```

For rollback, use the companion CLI to restore **only** the selected provider's upstream URL. It makes another backup and preserves settings edited since installation:

```bash
/usr/bin/python3 ./bin/proxy-config --mode restore
```

If you selected another port, supply the same `--port` used at installation. Fully quit and reopen Codex, and confirm it now uses the direct upstream. Once no client relies on the proxy, stop and disable it:

```bash
systemctl --user disable --now codex-strip-proxy
```

This retains the source, unit, backups, and logs for recovery. No deletion or log truncation is required. If an agent performs rollback, it should obtain approval for interrupting active requests or deleting anything when the user has required that approval. Do not blindly copy an old whole-config backup over a current config: that can undo unrelated later changes. Use the backup as a reference if a manual merge is needed.

## 9. CI and file inventory

`manifest.toml` lists every shipped file. [`ci/verify_files.sh`](ci/verify_files.sh) checks that each listed file exists and, inside a Git checkout, is tracked; CI forces the tracked check with `--tracked`. The installer runs the same check before making changes, while a downloaded archive without `.git` gets existence-only verification. There is deliberately no package-wide checksum file: the upstream proxy's pinned commit and SHA-256 are the integrity pin for downloaded code, while Git commit identity and review cover this package.

The workflow in [`.github/workflows/ci.yml`](.github/workflows/ci.yml) checks Bash and Python syntax, verifies the shipped-file inventory, and runs the unit tests on Ubuntu 24.04 and 26.04. These checks prove internal consistency of this package only; they do not prove that a fresh installation works or that the upstream relay is trustworthy.

## 10. License

This package is released under the MIT License; see [LICENSE](LICENSE).

The pinned upstream `codex-strip-proxy` repository is not vendored here. The installer clones it at the recorded commit and verifies the recorded SHA-256. Its GitHub metadata currently reports no license, so review its terms before redistributing its code.

## References

- [Pinned upstream source](https://github.com/AnnaofArendelle/codex-strip-proxy/tree/f28af95966200a614c671b73aa3e1e581ac2141b)
- [Official Codex configuration reference](https://developers.openai.com/codex/config-reference/)

This is a verified local workaround and a reproducible procedure, not an official guarantee from OpenAI, Azure, or AgentRouter.
