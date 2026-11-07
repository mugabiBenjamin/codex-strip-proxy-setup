"""Tests for src/sanitizer_check.py using a fixture and the installed proxy."""
import sys
import tempfile
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.sanitizer_check import extract_and_run

INSTALLED = Path.home() / '.local/share/codex-strip-proxy/codex_strip_proxy.py'

FIXTURE = '''
import json


def sanitize(raw, path):
    if '/responses' not in path:
        return raw, 0
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        return raw, 0
    if not isinstance(data, dict):
        return raw, 0
    count = 0
    if 'previous_response_id' in data:
        del data['previous_response_id']
        count += 1
    items = data.get('input')
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue
            if 'id' in item:
                del item['id']
                count += 1
            for key in list(item):
                if key.startswith('encrypted'):
                    del item[key]
                    count += 1
    return json.dumps(data).encode(), count
'''


class SanitizerCheckTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='strip-proxy-sanitizer-test-')
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'proxy.py'

    def write(self, text):
        self.path.write_text(text)
        return self.path

    def test_fixture_sanitizer_passes(self):
        extract_and_run(self.write(FIXTURE))

    def test_renamed_function_raises_stopiteration(self):
        with self.assertRaises(StopIteration):
            extract_and_run(self.write(FIXTURE.replace('def sanitize', 'def other_name')))

    def test_invalid_python_raises_syntax_error(self):
        with self.assertRaises(SyntaxError):
            extract_and_run(self.write('def sanitize(:\n'))

    @unittest.skipUnless(INSTALLED.is_file(), 'pinned proxy is not installed on this machine')
    def test_installed_proxy_source_passes(self):
        extract_and_run(INSTALLED)


if __name__ == '__main__':
    unittest.main(verbosity=2)
