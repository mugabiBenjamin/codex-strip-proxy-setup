# Validation of this revised package

Revised 7 November 2026. Live installation evidence was recorded on 6 November 2026 on the machine whose installation informed the guide. This file distinguishes live installation evidence from checks of the root-level package layout.

## Passed checks

| Check | Result and scope |
| --- | --- |
| Installer shell syntax | `bash -n` passed for [`installer/setup.sh`](installer/setup.sh), [`installer/prereqs.sh`](installer/prereqs.sh), [`installer/service_install.sh`](installer/service_install.sh), [`installer/probe.sh`](installer/probe.sh), and [`ci/verify_files.sh`](ci/verify_files.sh). |
| Documentation shell examples | All Bash blocks in this README passed `bash -n`; embedded Python snippets parsed successfully. No installation or rollback commands were executed by these syntax checks. |
| Python source syntax | Every module in [`src/`](src/), both CLIs in [`bin/`](bin/), and every test module parsed successfully (`py_compile`). |
| Unit tests | 39 tests passed with `python3 -m unittest discover tests/`. The earlier 13-case record is retained by the migrated editor tests. |
| Manifest validation | [`tests/test_manifest.py`](tests/test_manifest.py) covers valid loading, missing keys, wrong types, malformed commit, missing file, and the packaged manifest. |
| Config I/O | [`tests/test_config_io.py`](tests/test_config_io.py) covers the happy path, symlink refusal, profile refusal, missing provider, and unsimple provider names. |
| Config editor | [`tests/test_config_editor.py`](tests/test_config_editor.py) retains all 13 original cases and adds manifest-sourced `DIRECT`, multi-line `base_url` refusal, and UTC backup naming. |
| Service template | [`tests/test_service_template.py`](tests/test_service_template.py) covers rendering, hardening directives, port range and metacharacter refusal, backtick and dollar refusal, missing placeholders, and `systemd-analyze --user verify` of the rendered unit. |
| Sanitizer extraction | [`tests/test_sanitizer_check.py`](tests/test_sanitizer_check.py) covers a fixture, renamed function, invalid Python, and the real installed proxy source. The live source check passed on this machine. |
| Shipped-file inventory | `bash ci/verify_files.sh --tracked` confirmed that every path listed in `manifest.toml` exists and is tracked in Git. The installer runs the same check; a package without `.git` gets existence-only verification. |
| Repository layout | The package is at the repository root; all links and CI paths are root-relative. The nested `codex-strip-proxy-setup/` directory no longer exists. |
| License | [`LICENSE`](LICENSE) contains the MIT license for this package. The upstream proxy is cloned at install time and is not vendored here. |
| Config preview on the real installation | Passed without writing: selected provider `AgentRouter`; current and target URLs both `http://127.0.0.1:8899/v1`; `changed: false`. |
| Read-only verifier on the real installation | Passed at 2026-11-06 15:03:32 local time. Pinned commit/checksum, sanitizer, active and enabled service, process command, listener ownership, log path, disabled request dumping, and selected config all passed. |
| Saved live-test checker from the guide | Executed against the earlier CLI records and passed: same session, two completed turns, successful tool, correct follow-up, unchanged fixtures. |
| Companion links | Local links in [`README.md`](README.md) and this file resolve within the package (checked manually). |

## Existing live evidence used

The original installation used the pinned proxy and the unit rendered from [`templates/codex-strip-proxy.service.tmpl`](templates/codex-strip-proxy.service.tmpl). A real CLI tool call and follow-up completed in one session, with HTTP 200 requests stripping 7, 10, and 12 fields. After the user confirmed a full desktop restart, configuration and service state persisted, and new successful requests stripped 76, 5, and 79 fields. These are historical observations from this machine, not expected fixed counts for another installation.

At the later read-only verifier check, the same service remained active/running and enabled, with zero restarts and a listener on `127.0.0.1:8899`. Additional successful desktop requests were present in its log.

## What the CI inventory job does and does not prove

The inventory job in [`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs `ci/verify_files.sh --tracked`, which checks that every path listed in `manifest.toml` exists and is tracked in Git. It proves package completeness and repository consistency at that commit. It does not hash file contents; Git commit identity and review are the integrity mechanism.

It does not prove that the files are trustworthy, that the upstream repository is safe, that a clean installation succeeds, that the relay works, or that an authenticated Codex turn completes. Those require the live checks described in the README.

## Not claimed

- The new orchestration in [`installer/setup.sh`](installer/setup.sh) has not been exercised as a complete fresh installation on a clean machine. Its underlying service/config/probe approach was used successfully, and its phases were syntax- and component-tested, but that does not replace a clean-machine installation test.
- Ubuntu 24.04 compatibility is based on prerequisites, not a live test on that release; the GitHub Actions matrix is declared but has not been observed to run here.
- No new authenticated model test was launched merely to validate the revised documentation; the existing successful CLI evidence and ongoing desktop traffic were used.
- [`bin/verify-proxy`](bin/verify-proxy) does not send new API requests, restart the desktop app, or treat old logs as proof of a fresh completed turn.
- The hardened service unit passes `systemd-analyze --user verify`, but the new hardening directives have not been exercised against a live running service in this revision. A live restart and completed Codex turn remain required before claiming the hardened unit is fully verified.
- No guarantee is made for other relays, future payload shapes, profile/override setups, or WebSocket transport.
- ShellCheck was not installed; Bash syntax validation was performed instead. These tools provide different levels of analysis.
