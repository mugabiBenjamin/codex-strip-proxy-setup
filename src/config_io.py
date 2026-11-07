#!/usr/bin/env python3
"""Read and validate the parts of a Codex config that this package needs."""
from pathlib import Path
import re
import tomllib


def read_config(path: Path):
    """Return (raw_bytes, parsed_data, selected_provider, provider_settings).

    Only the selected model provider is inspected. Profiles are refused because
    they can change which provider is effective at launch time.
    """
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('Config must be an existing regular file, not a symlink.')
    raw = path.read_bytes()
    data = tomllib.loads(raw.decode('utf-8'))
    if data.get('profile') or data.get('profiles'):
        raise ValueError('Profiles detected. Identify the effective profile/config before using this helper.')
    provider = data.get('model_provider')
    if not isinstance(provider, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', provider):
        raise ValueError('Expected a selected provider with a simple TOML name.')
    providers = data.get('model_providers', {})
    if not isinstance(providers, dict) or not isinstance(providers.get(provider), dict):
        raise ValueError('Selected provider is not defined in [model_providers].')
    return raw, data, provider, providers[provider]
