#!/usr/bin/env python3
"""Query the installed codex-strip-proxy user service through systemd."""
import subprocess

UNIT = 'codex-strip-proxy'


def query(properties):
    """Return the requested `systemctl --user show` properties as a dict."""
    args = ['systemctl', '--user', 'show', UNIT]
    for prop in properties:
        args.extend(['-p', prop])
    output = subprocess.check_output(args, text=True)
    return dict(line.split('=', 1) for line in output.splitlines() if '=' in line)


def assert_property(service, key, expected):
    """Raise ValueError when a parsed service property differs from expected."""
    actual = service.get(key)
    if actual != expected:
        raise ValueError(f'Unexpected service {key}: {actual!r} (expected {expected!r})')


def main_pid():
    """Return the service's main PID as a string."""
    return query(['MainPID'])['MainPID']


def drop_in_paths():
    """Return the service's DropInPaths value (empty when there are none)."""
    return query(['DropInPaths'])['DropInPaths']
