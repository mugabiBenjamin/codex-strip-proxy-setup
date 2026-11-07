# codex-strip-proxy on Ubuntu: reproducible setup and verification

Run these steps after cloning the repository. Completion means a successful Codex conversation replay after restarting the desktop app.

## 1. Quick start from a fresh clone

```bash
git clone https://github.com/mugabiBenjamin/codex-strip-proxy-setup.git
cd codex-strip-proxy-setup
git switch main
bash ci/verify_files.sh --tracked
python3 -m unittest discover tests/
```

Expected: `OK: 27 shipped files exist and are tracked.` and 39 passing tests. If either command fails because packages are missing, complete the prerequisites below first.

## 2. Scope and prerequisites

- Codex already sends authenticated requests through AgentRouter.
- The selected provider has `base_url = "https://agentrouter.org/v1"` or already points at `http://127.0.0.1:8899/v1`.
- You are using an Ubuntu desktop session with a working systemd user manager.
- `/usr/bin/python3` is 3.11 or newer and includes `tomllib`.
- Run as your desktop user, never with `sudo`.
- Provider names may differ; the helper uses the selected `model_provider`.
- This package is for `agentrouter.org` only.
- Tested on Ubuntu 26.04.1. Ubuntu 24.04 has the required Python baseline but was not clean-machine tested.
- If you use profiles, `--config` overrides, another `CODEX_HOME`, project configuration, or app-managed provider settings, identify the effective config first.

### Check prerequisites

```bash
bash ./installer/prereqs.sh
```

If tools are missing:

```bash
sudo apt update
sudo apt install git python3 curl iproute2
```

### Check the selected provider

```bash
/usr/bin/python3 ./bin/proxy-config --mode check
```

This is read-only and does not print credentials. The default config is `${CODEX_HOME:-$HOME/.codex}/config.toml`.

## 3. Install

```bash
bash ./installer/setup.sh
```

Run this as your normal desktop user, without `sudo`. The installer downloads the pinned upstream proxy, verifies its SHA-256, installs the user service, runs the forwarding probe, and applies the local provider URL. Read the upstream script when prompted and confirm with `y`.

If port 8899 is occupied, inspect it first:

```bash
ss -ltnp 'sport = :8899'
```

To use another unprivileged port:

```bash
STRIP_PROXY_PORT=9900 bash ./installer/setup.sh
```

Then pass `--port 9900` to both CLIs and replace 8899 in the commands below.

### Existing installation

Update the clone first so its installer and unit template match `main`:

```bash
git pull --ff-only
```

If the installer stops because an existing service unit differs, it did not overwrite anything. To upgrade an existing install:

```bash
systemctl --user disable --now codex-strip-proxy
mv ~/.config/systemd/user/codex-strip-proxy.service \
   ~/.config/systemd/user/codex-strip-proxy.service.old
systemctl --user daemon-reload
bash ./installer/setup.sh
```

If the upgrade fails, restore the old unit:

```bash
mv ~/.config/systemd/user/codex-strip-proxy.service.old \
   ~/.config/systemd/user/codex-strip-proxy.service
systemctl --user daemon-reload
systemctl --user enable --now codex-strip-proxy
```

## 4. Verify

### A. Service, source, config, and sanitizer

```bash
/usr/bin/python3 ./bin/verify-proxy
systemctl --user status codex-strip-proxy --no-pager
ss -ltnp 'sport = :8899'
```

Expected: the service is `active`/`running` and `enabled`, and it listens only on `127.0.0.1:8899`. The verifier is read-only and sends no API requests.

### B. Forwarding without an API key

```bash
curl --silent --show-error --include --connect-timeout 10 --max-time 45 \
  --header 'Content-Type: application/json' --data '{}' \
  https://agentrouter.org/v1/responses

curl --silent --show-error --include --noproxy '*' --connect-timeout 10 --max-time 45 \
  --header 'Content-Type: application/json' --data '{}' \
  http://127.0.0.1:8899/v1/responses
```

Both should return 401 with the same error body. Do not add `curl --fail`; the 401 is the expected keyless result.

### C. Full desktop restart and two prompts

1. Finish or save active work, then use the app's Quit action to exit completely. Closing a window may leave background processes running. Do not use `pkill -f codex`.
2. Reopen the app with the same credential environment and provider configuration.
3. Confirm the config points at the local proxy:

   ```bash
   /usr/bin/python3 ./bin/proxy-config --mode check
   ```

   Current and target URLs should both be `http://127.0.0.1:8899/v1` (or your chosen port).

4. In another terminal, display only new log entries:

   ```bash
   date -Is
   tail -n 0 -F "$HOME/.local/state/codex-strip-proxy/proxy.log"
   ```

5. Create a harmless test directory and open it in Codex:

   ```bash
   mkdir -p "$HOME/codex-strip-proxy-test"
   head -c 17 /dev/zero | tr '\0' x > "$HOME/codex-strip-proxy-test/small.txt"
   head -c 1024 /dev/zero | tr '\0' x > "$HOME/codex-strip-proxy-test/medium.txt"
   head -c 4096 /dev/zero | tr '\0' x > "$HOME/codex-strip-proxy-test/large.txt"
   ```

   In one desktop chat pointed at that directory, ask: "Use a shell tool to list the files in this directory and their byte sizes. Do not modify anything."
6. In the same chat, ask: "Which of those files is the largest?"
7. Confirm the tool output, completed answers, and new HTTP 200 log entries. The follow-up should identify `large.txt` at 4,096 bytes and show a positive strip count when replay contains resource-bound fields.

Stop the log viewer with Ctrl+C; that does not stop the service.

## 5. Completion criteria

Call the installation verified only when all applicable items are observed:

- The pinned process is enabled, active, and listening only on the chosen loopback port.
- The selected provider URL points at the local proxy and persists after a full desktop restart.
- A real authenticated prompt completes a tool call and a follow-up prompt completes in the same conversation.
- Fresh log entries show HTTP 200 for those turns and demonstrate removal of replayed state.
- The returned answers and tool results are correct, with no Azure resource error.
