"""Tests for src/config_io.py against disposable configs, never the live config."""
import sys
import tempfile
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config_io import read_config

BASE = '''model_provider = "AgentRouter"
model = "keep-model"
[model_providers.AgentRouter]
name = "AgentRouter"
base_url = "https://agentrouter.org/v1" # preserve this comment
env_key = "KEEP_THIS_ENV_NAME"
wire_api = "responses"
[model_providers.Unrelated]
base_url = "https://agentrouter.org/v1"
'''


class ConfigIoTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='strip-proxy-config-io-test-')
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'config.toml'
        self.path.write_bytes(BASE.encode())
        self.path.chmod(0o600)

    def write(self, text):
        self.path.write_bytes(text.encode())

    def test_happy_path_returns_expected_tuple(self):
        raw, data, provider, settings = read_config(self.path)
        self.assertEqual(raw, BASE.encode())
        self.assertEqual(data['model'], 'keep-model')
        self.assertEqual(provider, 'AgentRouter')
        self.assertEqual(settings['base_url'], 'https://agentrouter.org/v1')
        self.assertEqual(settings['env_key'], 'KEEP_THIS_ENV_NAME')

    def test_symlink_refused(self):
        link = self.path.parent / 'link.toml'
        link.symlink_to(self.path)
        with self.assertRaises(ValueError):
            read_config(link)

    def test_profiles_refused(self):
        self.write(BASE + '\n[profiles.other]\nmodel = "other"\n')
        with self.assertRaises(ValueError):
            read_config(self.path)

    def test_missing_provider_refused(self):
        self.write(BASE.replace('model_provider = "AgentRouter"', 'model_provider = "Missing"'))
        with self.assertRaises(ValueError):
            read_config(self.path)

    def test_unsimple_provider_name_refused(self):
        self.write(BASE.replace('model_provider = "AgentRouter"', 'model_provider = "Agent Router"'))
        with self.assertRaises(ValueError):
            read_config(self.path)

    def test_missing_file_refused(self):
        with self.assertRaises(ValueError):
            read_config(self.path.parent / 'missing.toml')


if __name__ == '__main__':
    unittest.main(verbosity=2)
