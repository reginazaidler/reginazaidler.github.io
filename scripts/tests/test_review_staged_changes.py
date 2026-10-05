import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from urllib.error import HTTPError
import traceback
from contextlib import redirect_stdout
from unittest.mock import patch, MagicMock

spec = importlib.util.spec_from_file_location('gate', Path(__file__).parents[1] / 'review_staged_changes.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

article_spec = importlib.util.spec_from_file_location('article', Path(__file__).parents[1] / 'generate_article.py')
article = importlib.util.module_from_spec(article_spec)
article_spec.loader.exec_module(article)


class GateTests(unittest.TestCase):
    def exercise(self, review, key='test', changed=False, network_error=False, finish_reason='stop'):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({'choices': [{'finish_reason': finish_reason, 'message': {'content': json.dumps(review)}}]}).encode()
        trees = iter([b'tree', b'changed' if changed else b'tree'])
        def git(*args):
            return next(trees) if args[0] == 'write-tree' else b'diff --git a/index.html b/index.html\n+change'
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {'OPENAI_API_KEY': key, 'RUNNER_TEMP': temp}), patch.object(gate, 'git', git), patch.object(gate.subprocess, 'run') as run, patch.object(gate, 'build_context', return_value='staged context'), patch.object(gate.urllib.request, 'urlopen', side_effect=OSError() if network_error else None, return_value=response):
            def export(*args, **kwargs):
                command = args[0]
                if 'checkout-index' in command:
                    root = Path(next(x for x in command if x.startswith('--prefix=')).split('=', 1)[1])
                    (root / 'AGENTS.md').write_text('snapshot policy')
            run.side_effect = export
            gate.run_review()
            request = gate.urllib.request.urlopen.call_args.args[0]
            payload = json.loads(request.data)
            self.assertTrue(payload['messages'][0]['content'].endswith('snapshot policy'))
            self.assertIn('checkout-index', run.call_args_list[0].args[0])
            self.assertNotEqual(run.call_args_list[1].kwargs['cwd'], os.getcwd())
            self.assertTrue((Path(temp) / 'website-code-review.json').exists())

    def test_approval(self):
        self.exercise({'approved': True, 'blocking_findings': [], 'summary': 'ok'})

    def test_rejection(self):
        with self.assertRaises(RuntimeError):
            self.exercise({'approved': False, 'blocking_findings': ['bad'], 'summary': 'bad'})

    def test_contradictory_approval(self):
        with self.assertRaises(RuntimeError):
            self.exercise({'approved': True, 'blocking_findings': ['bad'], 'summary': 'bad'})

    def test_missing_key(self):
        with self.assertRaises(RuntimeError):
            self.exercise({}, key='')

    def test_malformed_response(self):
        with self.assertRaises(RuntimeError):
            self.exercise({'approved': 'true'})

    def test_staged_mutation(self):
        with self.assertRaises(RuntimeError):
            self.exercise({'approved': True, 'blocking_findings': [], 'summary': 'ok'}, changed=True)

    def test_api_failure(self):
        with self.assertRaises(OSError):
            self.exercise({}, network_error=True)

    def test_incomplete_review_blocks(self):
        for reason in ('length', 'content_filter', None):
            with self.subTest(reason=reason), self.assertRaises(RuntimeError):
                self.exercise({'approved': True, 'blocking_findings': [], 'summary': 'ok'}, finish_reason=reason)

    def test_safe_http_diagnostics(self):
        for code in (400, 401, 403, 429, 500, 599):
            body = io.BytesIO(b'private response sk-secret')
            error = HTTPError('https://example.test/sk-secret', code, 'sk-secret\n::warning::injected', {'Authorization': 'Bearer sk-secret'}, body)
            message = gate.failure_message(error)
            self.assertIn(f'HTTP {code}:', message)
            self.assertNotIn('sk-secret', message)
            self.assertNotIn('\n', message)
            self.assertEqual(body.tell(), 0)

    def test_article_http_failure_is_safe(self):
        body = io.BytesIO(b'private response sk-secret')
        error = HTTPError('https://example.test/sk-secret', 429, 'sk-secret', {}, body)
        output = io.StringIO()
        with patch.object(article, 'api_key', return_value='test'), patch.object(article.urllib.request, 'urlopen', side_effect=error), redirect_stdout(output):
            try:
                article.call_openai('test', 'test', retries=1)
            except RuntimeError:
                trace = traceback.format_exc()
            else:
                self.fail('HTTP failure must block article generation')
        self.assertIn('HTTP 429', output.getvalue())
        self.assertNotIn('sk-secret', output.getvalue() + trace)
        self.assertEqual(body.tell(), 0)


if __name__ == '__main__':
    unittest.main()
