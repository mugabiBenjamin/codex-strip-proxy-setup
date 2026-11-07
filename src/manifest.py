#!/usr/bin/env python3
"""Load and validate manifest.toml, the package's single source of truth."""
from pathlib import Path
import re
import tomllib

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = PACKAGE_ROOT / 'manifest.toml'

# Required tables, keys, and Python types. Extra keys are ignored.
_SCHEMA = {
    'proxy': {'commit': str, 'sha256': str, 'upstream': str, 'repository': str},
    'defaults': {'port': int, 'codex_home_env_var': str},
    'package': {'version': str, 'owned_files': list},
}


def load(path=None):
    """Read manifest.toml and return it as a validated dictionary.

    Raises OSError if the file cannot be read and ValueError for any missing
    key, wrong type, or malformed value.
    """
    manifest_path = Path(path) if path is not None else MANIFEST_PATH
    with manifest_path.open('rb') as stream:
        data = tomllib.load(stream)

    for table, fields in _SCHEMA.items():
        if not isinstance(data.get(table), dict):
            raise ValueError(f'manifest is missing the [{table}] table')
        for key, expected in fields.items():
            if key not in data[table]:
                raise ValueError(f'manifest is missing [{table}].{key}')
            value = data[table][key]
            if expected is int:
                valid = isinstance(value, int) and not isinstance(value, bool)
            else:
                valid = isinstance(value, expected)
            if not valid:
                raise ValueError(
                    f'manifest [{table}].{key} must be {expected.__name__}, '
                    f'not {type(value).__name__}'
                )

    proxy = data['proxy']
    if not re.fullmatch(r'[0-9a-f]{40}', proxy['commit']):
        raise ValueError('manifest [proxy].commit must be a full 40-character SHA-1')
    if not re.fullmatch(r'[0-9a-f]{64}', proxy['sha256']):
        raise ValueError('manifest [proxy].sha256 must be a 64-character SHA-256')
    if not proxy['upstream'].startswith('https://'):
        raise ValueError('manifest [proxy].upstream must be an https:// URL')
    if not proxy['repository'].startswith('https://'):
        raise ValueError('manifest [proxy].repository must be an https:// URL')

    port = data['defaults']['port']
    if not 1024 <= port <= 65535:
        raise ValueError('manifest [defaults].port must be between 1024 and 65535')
    if not re.fullmatch(r'[A-Z_][A-Z0-9_]*', data['defaults']['codex_home_env_var']):
        raise ValueError('manifest [defaults].codex_home_env_var must be an env var name')

    owned = data['package']['owned_files']
    if not owned or not all(isinstance(item, str) and item for item in owned):
        raise ValueError('manifest [package].owned_files must be a non-empty list of paths')
    return data


_MANIFEST = load()

COMMIT = _MANIFEST['proxy']['commit']
SHA256 = _MANIFEST['proxy']['sha256']
UPSTREAM = _MANIFEST['proxy']['upstream']
REPOSITORY = _MANIFEST['proxy']['repository']
DEFAULT_PORT = _MANIFEST['defaults']['port']
CODEX_HOME_ENV_VAR = _MANIFEST['defaults']['codex_home_env_var']
VERSION = _MANIFEST['package']['version']
OWNED_FILES = tuple(_MANIFEST['package']['owned_files'])
