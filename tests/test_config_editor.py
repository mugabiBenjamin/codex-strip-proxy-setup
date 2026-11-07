"""Exercise edits and refusal cases on disposable configs, never the live config."""
import re
import sys
import tempfile
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import config_editor, manifest
from src.config_editor import change

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


class ConfigEditorTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='strip-proxy-config-test-')
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'config.toml'
        self.path.write_bytes(BASE.encode())
        self.path.chmod(0o600)

    def write(self, text):
        self.path.write_bytes(text.encode())

    def test_preview_never_writes(self):
        result = change(self.path, 8899, 'check')
        self.assertFalse(result['changed'])
        self.assertEqual(self.path.read_text(), BASE)
        self.assertEqual(len(list(self.path.parent.iterdir())), 1)

    def test_only_selected_url_changes_with_exact_backup(self):
        result = change(self.path, 8899, 'apply')
        self.assertEqual(self.path.read_text(), BASE.replace(config_editor.DIRECT, 'http://127.0.0.1:8899/v1', 1))
        backup = Path(result['backup'])
        self.assertEqual(backup.read_text(), BASE)
        self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

    def test_repeated_apply_is_noop(self):
        change(self.path, 8899, 'apply')
        count = len(list(self.path.parent.iterdir()))
        self.assertFalse(change(self.path, 8899, 'apply')['changed'])
        self.assertEqual(len(list(self.path.parent.iterdir())), count)

    def test_restore_preserves_later_edits(self):
        change(self.path, 8899, 'apply')
        self.path.write_text(self.path.read_text().replace('keep-model', 'new-model'))
        change(self.path, 8899, 'restore')
        self.assertEqual(self.path.read_text(), BASE.replace('keep-model', 'new-model'))

    def test_crlf_preserved(self):
        self.write(BASE.replace('\n', '\r\n'))
        before = self.path.read_bytes()
        change(self.path, 8899, 'apply')
        self.assertEqual(self.path.read_bytes(),
                         before.replace(config_editor.DIRECT.encode(), b'http://127.0.0.1:8899/v1', 1))

    def test_quoted_header_and_single_quotes(self):
        self.write(BASE.replace('[model_providers.AgentRouter]', '[model_providers."AgentRouter"] # section')
                  .replace('"https://agentrouter.org/v1"', "'https://agentrouter.org/v1'"))
        self.assertTrue(change(self.path, 9900, 'apply')['changed'])
        self.assertIn("'http://127.0.0.1:9900/v1'", self.path.read_text())

    def assert_refusal(self, text):
        self.write(text)
        before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            change(self.path, 8899, 'apply')
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(len(list(self.path.parent.iterdir())), 1)

    def test_wrong_upstream_refused(self):
        self.assert_refusal(BASE.replace('https://agentrouter.org', 'https://example.org'))

    def test_missing_selected_provider_refused(self):
        self.assert_refusal(BASE.replace('model_provider = "AgentRouter"', 'model_provider = "Missing"'))

    def test_profiles_refused(self):
        self.assert_refusal(BASE + '\n[profiles.other]\nmodel = "other"\n')

    def test_duplicate_url_invalid_toml_refused(self):
        self.assert_refusal(BASE.replace('env_key =', 'base_url = "https://agentrouter.org/v1"\nenv_key ='))

    def test_websockets_refused(self):
        self.assert_refusal(BASE.replace('env_key =', 'supports_websockets = true\nenv_key ='))

    def test_symlink_refused(self):
        link = self.path.parent / 'link.toml'
        link.symlink_to(self.path)
        with self.assertRaises(ValueError):
            change(link, 8899, 'apply')
        self.assertEqual(self.path.read_text(), BASE)

    def test_invalid_port_refused(self):
        with self.assertRaises(ValueError):
            change(self.path, 80, 'apply')
        self.assertEqual(self.path.read_text(), BASE)

    def test_direct_url_comes_from_manifest(self):
        self.assertEqual(config_editor.DIRECT, manifest.UPSTREAM + '/v1')

    def test_multiline_base_url_refused(self):
        self.assert_refusal(BASE.replace('base_url = "https://agentrouter.org/v1"',
                                         'base_url = """https://agentrouter.org/v1"""'))

    def test_backup_name_includes_utc_timestamp(self):
        result = change(self.path, 8899, 'apply')
        name = Path(result['backup']).name
        self.assertRegex(name, r'^config\.toml\.bak\.strip-proxy\.\d{8}T\d{6}\.\d{6}Z$')


if __name__ == '__main__':
    unittest.main(verbosity=2)
