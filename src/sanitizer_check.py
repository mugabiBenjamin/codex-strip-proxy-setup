#!/usr/bin/env python3
"""Exercise the sanitizer from the pinned proxy without importing its server."""
import ast
import copy
import json
from pathlib import Path


def extract_and_run(source_path: Path) -> None:
    """AST-extract `sanitize` from the pinned source and assert its behaviour.

    Raises StopIteration if the function is missing, SyntaxError if the source
    is invalid Python, and ValueError if any behavioural check fails.
    """
    source_path = Path(source_path)
    source = source_path.read_text()
    tree = ast.parse(source)
    function = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == 'sanitize'
    )
    namespace = {'json': json}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(source_path), 'exec'), namespace)

    original = {
        'previous_response_id': 'resp_old',
        'model': 'test-model',
        'stream': True,
        'input': [
            {'type': 'message', 'id': 'msg_old', 'role': 'assistant',
             'content': [{'type': 'output_text', 'text': 'Keep this.'}]},
            {'type': 'reasoning', 'id': 'rs_old', 'encrypted_content': 'opaque',
             'encrypted_extra': 'opaque2', 'summary': []},
            {'type': 'function_call', 'id': 'fc_old', 'call_id': 'call_keep',
             'name': 'list_files', 'arguments': '{}'},
            {'type': 'function_call_output', 'call_id': 'call_keep', 'output': 'file.txt'},
        ],
    }
    raw = json.dumps(original).encode()
    body, count = namespace['sanitize'](raw, '/v1/responses')
    expected = copy.deepcopy(original)
    expected.pop('previous_response_id')
    for item in expected['input']:
        for key in list(item):
            if key == 'id' or key.startswith('encrypted'):
                item.pop(key)
    if json.loads(body) != expected or count != 6:
        raise ValueError('Sanitizer failed preservation/removal checks.')

    for sample, path in [(b'invalid json', '/v1/responses'),
                         (b'[]', '/v1/responses'),
                         (raw, '/v1/chat/completions')]:
        if namespace['sanitize'](sample, path) != (sample, 0):
            raise ValueError('Sanitizer passthrough check failed.')
