#!/usr/bin/env python3
"""Preview/apply one provider URL change, with an exclusive backup and TOML checks."""
import copy
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import stat
import tempfile
import tomllib

from .config_io import read_config
from .manifest import UPSTREAM

DIRECT = f'{UPSTREAM}/v1'


def prepare(raw: bytes, data: dict, provider: str, target: str) -> bytes:
    """Preserve every byte except the URL literal in the selected provider section."""
    lines = raw.decode('utf-8').splitlines(keepends=True)
    selected = False
    matches = []
    for index, line in enumerate(lines):
        if line.lstrip().startswith('['):
            try:
                header = tomllib.loads(line)
                selected = header == {'model_providers': {provider: {}}}
            except tomllib.TOMLDecodeError:
                selected = False
        if selected and re.match(r'^\s*base_url\s*=', line):
            match = re.fullmatch(r'''(\s*base_url\s*=\s*)(["'])([^"'\r\n]*)(["'])([^\r\n]*)(\r?\n)?''', line)
            if not match or match[2] != match[4]:
                raise ValueError('Expected base_url as a simple, single-line quoted string.')
            matches.append(index)
            lines[index] = line[:match.start(3)] + target + line[match.end(3):]
    if len(matches) != 1:
        raise ValueError('Expected exactly one base_url in the selected provider section; no file changed.')
    updated = ''.join(lines).encode('utf-8')
    expected = copy.deepcopy(data)
    expected['model_providers'][provider]['base_url'] = target
    if tomllib.loads(updated.decode('utf-8')) != expected:
        raise ValueError('Safety check failed: another TOML setting would change.')
    return updated


def change(path: Path, port: int, mode: str) -> dict:
    """Run the check/apply/restore pipeline and return a JSON-ready result."""
    if not 1024 <= port <= 65535:
        raise ValueError('Port must be between 1024 and 65535.')
    path = Path(path)
    raw, data, provider, settings = read_config(path)
    local = f'http://127.0.0.1:{port}/v1'
    current = settings.get('base_url')
    if current not in (DIRECT, local):
        raise ValueError('Selected provider URL is neither agentrouter.org/v1 nor the requested local proxy.')
    if settings.get('wire_api', 'responses') != 'responses':
        raise ValueError('The selected provider must use the Responses API.')
    if settings.get('supports_websockets', False):
        raise ValueError('This pinned proxy does not support WebSockets. Review the provider transport first.')
    target = DIRECT if mode == 'restore' else local
    updated = prepare(raw, data, provider, target)
    result = {'config': str(path), 'provider': provider, 'current_url': current,
              'target_url': target, 'mode': mode, 'changed': False}
    if mode == 'check' or raw == updated:
        result['status'] = 'preview' if raw != updated else 'already configured'
        return result

    # The desktop app may rewrite this file. Check for changes before replacing it.
    # Quit the app during manual use where possible; no portable lock can stop it.
    metadata = path.stat()
    if metadata.st_uid != os.getuid() or metadata.st_nlink != 1:
        raise ValueError('Config must be owned by this user and have one hard link.')
    if path.read_bytes() != raw:
        raise ValueError('Config changed concurrently; retry after closing the app.')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    backup = path.with_name(path.name + '.bak.strip-proxy.' + stamp)
    fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    temp_fd, temp_name = tempfile.mkstemp(prefix='.strip-proxy-config-', dir=path.parent)
    try:
        os.fchmod(temp_fd, stat.S_IMODE(metadata.st_mode))
        with os.fdopen(temp_fd, 'wb') as stream:
            stream.write(updated)
            stream.flush()
            os.fsync(stream.fileno())
        if path.is_symlink() or path.stat().st_ino != metadata.st_ino or path.read_bytes() != raw:
            raise ValueError('Config changed concurrently. Backup kept; config was not replaced.')
        os.replace(temp_name, path)
        if path.read_bytes() != updated:
            raise ValueError('Config changed immediately after writing. Inspect the backup and active config.')
    finally:
        # Only remove the temporary file created by this helper, if replacement did not consume it.
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    result.update(changed=True, status='verified: only selected provider URL changed', backup=str(backup))
    return result
