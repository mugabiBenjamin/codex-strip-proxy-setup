#!/usr/bin/env python3
"""Render the systemd unit template with validated substitutions."""
from pathlib import Path
import re

_PLACEHOLDER = re.compile(r'\{\{([A-Z0-9_]+)\}\}')
_FORBIDDEN = set('$`\\"\n\r')


def validate_substitutions(substitutions):
    """Reject unsafe values before any template text is touched."""
    if not isinstance(substitutions, dict) or not substitutions:
        raise ValueError('Substitutions must be a non-empty mapping.')
    port = substitutions.get('PORT')
    if isinstance(port, bool) or not isinstance(port, int):
        raise ValueError('PORT substitution must be an integer.')
    if not 1024 <= port <= 65535:
        raise ValueError('PORT substitution must be between 1024 and 65535.')
    for key, value in substitutions.items():
        if not isinstance(key, str) or not re.fullmatch(r'[A-Z0-9_]+', key):
            raise ValueError(f'Invalid substitution key: {key!r}')
        if key == 'PORT':
            continue
        if not isinstance(value, str):
            raise ValueError(f'Substitution {key} must be a string.')
        if any(character in value for character in _FORBIDDEN):
            raise ValueError(f'Unsafe character in substitution {key}.')
    return substitutions


def render(template_path: Path, substitutions: dict) -> str:
    """Read the template, replace {{KEY}} placeholders, and return the unit text."""
    substitutions = validate_substitutions(substitutions)
    text = Path(template_path).read_text()
    for key, value in substitutions.items():
        text = text.replace('{{' + key + '}}', str(value))
    missing = sorted(set(_PLACEHOLDER.findall(text)))
    if missing:
        raise ValueError('Missing substitution for placeholder(s): ' + ', '.join(missing))
    return text
