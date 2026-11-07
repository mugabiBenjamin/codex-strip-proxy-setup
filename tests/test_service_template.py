"""Tests for src/template.py and the packaged systemd unit template."""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.template import render

TEMPLATE = ROOT / 'templates' / 'codex-strip-proxy.service.tmpl'
UPSTREAM = 'https://agentrouter.org'


class TemplateTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='strip-proxy-template-test-')
        self.addCleanup(self.directory.cleanup)

    def test_valid_substitution_produces_unit_text(self):
        text = render(TEMPLATE, {'PORT': 8899, 'UPSTREAM': UPSTREAM})
        self.assertIn('ExecStart=/usr/bin/python3 -I "%h/.local/share/codex-strip-proxy/codex_strip_proxy.py" 8899 ' + UPSTREAM, text)
        self.assertIn('[Install]\nWantedBy=default.target', text)
        for line in ('ProtectSystem=strict', 'ProtectHome=read-only', 'PrivateTmp=yes',
                     'ReadWritePaths=%h/.local/state/codex-strip-proxy',
                     'RestrictAddressFamilies=AF_INET AF_UNIX',
                     'RestrictRealtime=yes', 'LockPersonality=yes'):
            self.assertIn(line, text)
        self.assertNotIn('CapabilityBoundingSet=', text)
        self.assertNotIn('{{', text)

    def test_port_with_shell_metacharacter_raises(self):
        with self.assertRaises(ValueError):
            render(TEMPLATE, {'PORT': '8899; rm -rf /', 'UPSTREAM': UPSTREAM})

    def test_port_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            render(TEMPLATE, {'PORT': 80, 'UPSTREAM': UPSTREAM})

    def test_upstream_with_backtick_raises(self):
        with self.assertRaises(ValueError):
            render(TEMPLATE, {'PORT': 8899, 'UPSTREAM': 'https://example.org/`id`'})

    def test_upstream_with_dollar_raises(self):
        with self.assertRaises(ValueError):
            render(TEMPLATE, {'PORT': 8899, 'UPSTREAM': 'https://example.org/$HOME'})

    def test_missing_placeholder_key_raises(self):
        template = Path(self.directory.name) / 'extra.service.tmpl'
        template.write_text('[Service]\nExecStart=/bin/true {{EXTRA}}\n')
        with self.assertRaises(ValueError):
            render(template, {'PORT': 8899, 'UPSTREAM': UPSTREAM})

    def test_rendered_unit_passes_systemd_verify_when_available(self):
        if not shutil.which('systemd-analyze'):
            self.skipTest('systemd-analyze is not installed')
        if subprocess.run(['systemctl', '--user', 'show-environment'],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0:
            self.skipTest('no user systemd manager is available')
        unit = Path(self.directory.name) / 'codex-strip-proxy.service'
        unit.write_text(render(TEMPLATE, {'PORT': 8899, 'UPSTREAM': UPSTREAM}))
        result = subprocess.run(['systemd-analyze', '--user', 'verify', str(unit)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main(verbosity=2)
