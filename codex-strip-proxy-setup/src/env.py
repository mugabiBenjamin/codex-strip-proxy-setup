#!/usr/bin/env python3
"""Resolve the Codex configuration location. No parsing and no file access."""
import os
from pathlib import Path

from .manifest import CODEX_HOME_ENV_VAR


def codex_home() -> Path:
    """Return $CODEX_HOME, or ~/.codex when the variable is unset or empty."""
    value = os.environ.get(CODEX_HOME_ENV_VAR)
    if value:
        return Path(value).expanduser()
    return Path.home() / '.codex'


def config_path() -> Path:
    """Return the Codex config.toml path inside the resolved home directory."""
    return codex_home() / 'config.toml'
