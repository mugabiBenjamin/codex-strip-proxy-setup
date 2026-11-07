"""Tests for src/manifest.py, the only reader of manifest.toml."""
import sys
import tempfile
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import manifest

VALID = '''[proxy]
commit = "f28af95966200a614c671b73aa3e1e581ac2141b"
sha256 = "422f19081195d5586521e1abce5789b12a709ee60dbc93e19a774a4445965fc4"
upstream = "https://agentrouter.org"
repository = "https://github.com/AnnaofArendelle/codex-strip-proxy.git"

[defaults]
port = 8899
codex_home_env_var = "CODEX_HOME"

[package]
version = "1.0.0"
owned_files = ["manifest.toml"]
'''


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='strip-proxy-manifest-test-')
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'manifest.toml'

    def load(self, text=VALID):
        self.path.write_text(text)
        return manifest.load(self.path)

    def test_valid_manifest_returns_typed_values(self):
        data = self.load()
        self.assertEqual(data['proxy']['commit'], manifest.COMMIT)
        self.assertIsInstance(data['defaults']['port'], int)
        self.assertIsInstance(data['package']['owned_files'], list)

    def test_missing_key_raises(self):
        text = VALID.replace('sha256 = "422f19081195d5586521e1abce5789b12a709ee60dbc93e19a774a4445965fc4"\n', '')
        with self.assertRaises(ValueError):
            self.load(text)

    def test_wrong_type_raises(self):
        with self.assertRaises(ValueError):
            self.load(VALID.replace('port = 8899', 'port = "8899"'))

    def test_malformed_commit_raises(self):
        with self.assertRaises(ValueError):
            self.load(VALID.replace('f28af95966200a614c671b73aa3e1e581ac2141b', 'f28af95'))

    def test_file_not_found_raises_oserror(self):
        with self.assertRaises(OSError):
            manifest.load(Path(self.directory.name) / 'missing.toml')

    def test_packaged_manifest_loads(self):
        data = manifest.load()
        self.assertEqual(data['proxy']['commit'], 'f28af95966200a614c671b73aa3e1e581ac2141b')
        self.assertIn('manifest.toml', data['package']['owned_files'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
